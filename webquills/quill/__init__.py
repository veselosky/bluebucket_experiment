# vim: set fileencoding=utf-8 :
#
#   Copyright 2016 Vince Veselosky and contributors
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
"""
WebQuills command line interface.

Usage:
    quill new [-o OUTFILE] ITEMTYPE [TITLE]
    quill md2json [-r ROOT] [-x EXT...] [-o OUTFILE] INFILE
    quill md2json [-r ROOT] -i FILES...
    quill j2 [-r ROOT] [-t DIR] [-o OUTFILE] TEMPLATE [VARFILES...]
    quill index [-r ROOT] (-o OUTFILE | -A OUTFILE) JSON...
    quill render [-r ROOT] [-t DIR] [-c CONTEXT]... JSON...

Options:
    -A --addto=OUTFILE      For the index command, the output file will be
                            read and extended with new data, not overwritten. It
                            will be created if it does not exist.
    -c --context=CONTEXT    CONTEXT is a JSON file that will be added to the
                            template context for each template rendered. If
                            given multiple times, all files are added.
    -i --inplace            Use input filename to determine output filename.
    -o --outfile=OUTFILE    File to write output. Defaults to STDOUT.
                            If the destination file exists, it will be
                            overwritten.
    -r --root=ROOT          The destination build directory. All calculated
                            paths will be relative to this directory.
    -t --templatedir=DIR    Directory where templates are stored. TEMPLATE
                            path should be relative to this.
    -x --extension=EXT      A python-markdown extension module to load.

"""
import copy
import json
import sys
from configparser import ConfigParser
from pathlib import Path

import jsonschema
import webquills.indexer as indexer
import webquills.j2 as j2
from docopt import docopt
from webquills.mdown import archetype_from_file, new_markdown
from webquills.util import SmartJSONEncoder, getLogger


UTF8 = "utf-8"


def configure(args):
    configurator = ConfigParser()
    configurator.read('webquills.ini')
    cfg = {"markdown": {}, "jinja2": {}}
    for section in configurator:
        cfg[section.lower()] = dict(configurator[section].items())

    # Read from config as space separated string; convert to list
    cfg["options"]["context"] = cfg["options"].get("context", "").split()
    cfg["markdown"]["extensions"] = \
        cfg["markdown"].get("extensions", "").split()

    for key, value in args.items():
        if key == "--extension":
            cfg["markdown"]["extensions"].extend(value)
        elif key == "--context":
            cfg["options"]["context"].extend(value)
        elif key.startswith("--") and value is not None:
            cfg["options"][key[2:]] = value
    return cfg


# MAIN: Dispatch to individual handlers
def main():
    logger = getLogger()
    item_types = {"article": "Item/Page/Article", "page": "Item/Page"}
    param = docopt(__doc__)
    cfg = configure(param)
    # logger.info(repr(cfg))
    # logger.debug(repr(param))

    if param['new']:
        # TODO (someday) Prompt user for metadata values
        doc = new_markdown(cfg, item_types[param['ITEMTYPE'].lower()],
                           title=param['TITLE'])
        # Prepare the output file handle
        if param['--outfile']:
            Path(param["--outfile"]).write_text(doc, encoding=UTF8)
        else:
            print(doc)

    elif param['md2json']:
        if param["--inplace"]:
            files = [ Path(f) for f in param["FILES"] ]
        else:
            files = [ Path(param["INFILE"]) ]

        for filename in files:
            logger.info("Processing %s" % filename)
            try:
                (metadict, target)= archetype_from_file(cfg, filename)
            except jsonschema.ValidationError as e:
                # spits out a screwy error, make it more obvious
                lines = str(e).splitlines()
                message = lines.pop(0) + "\n"
                detail = "\n".join(lines) + "\n"
                logger.info(detail)
                logger.error("in %s: %s" % (filename, message))
                continue

            # Prepare the output file handle
            if param['--outfile']:  # If to file, use compact representation
                with open(param['--outfile'], 'w', encoding=UTF8) as outfile:
                    json.dump(metadict, outfile, cls=SmartJSONEncoder)

            elif param["--inplace"]:
                with target.open('w', encoding=UTF8) as outfile:
                    json.dump(metadict, outfile, cls=SmartJSONEncoder)

            else:  # If stdout, pretty print
                json.dump(metadict, sys.stdout, sort_keys=True, indent=2,
                          cls=SmartJSONEncoder)

    elif param["j2"]:
        context = copy.deepcopy(cfg)
        for file in param['VARFILES']:
            context.update(j2.loadfile(file))
        doc = j2.render(cfg, context, param["TEMPLATE"])
        if param['--outfile']:
            Path(param['--outfile']).write_text(doc, encoding=UTF8)
        else:
            print(doc)

    elif param["render"]:
        base_context = copy.deepcopy(cfg)
        for file in cfg["options"]["context"]:
            base_context.update(j2.loadfile(file))

        for file in param['JSON']:
            logger.info("Processing %s" % file)
            item = j2.loadfile(file)
            if not "Item" in item:
                logger.warning("Skipping non-Item JSON file: %s" % file)
                continue
            context = dict(base_context, **item)
            templates = j2.templates_from_context(context)
            logger.info(item["Item"]["itemtype"])
            for key in templates:
                out = j2.render(cfg, context, templates[key])
                Path(file).with_suffix('.'+key).write_text(out, encoding=UTF8)

    elif param["index"]:
        index = {}
        target = None
        if param["--addto"]:
            target = param["--addto"]
            try:
                with open(target, encoding=UTF8) as the_index:
                    index = json.load(the_index)
            except FileNotFoundError as e:
                logger.info("File does not exist. Creating: %s" % target)
                pass
        elif param['--outfile']:
            target = param['--outfile']

        for infile in param["JSON"]:
            try:
                data = json.loads(Path(infile).read_text(encoding=UTF8))
            except Exception as e:
                logger.info(str(e))
                logger.error("File could not be parsed: %s" % infile)
                continue
            index = indexer.add_to_index(index, data)
        if target:  # If to file, use compact representation
            with open(target, 'w', encoding=UTF8) as outfile:
                json.dump(index, outfile, cls=SmartJSONEncoder)
        else:  # If stdout, pretty print
            json.dump(index, sys.stdout, sort_keys=True, indent=2,
                          cls=SmartJSONEncoder)
