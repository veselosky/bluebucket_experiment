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
    quill md2json [-x EXT...] [-o OUTFILE] INFILE
    quill md2json -i FILES...
    quill j2 -t DIR [-o OUTFILE] TEMPLATE [VARFILES...]
    quill index (-o OUTFILE | -A OUTFILE) JSON...
    quill render -t DIR [-c CONTEXT]... JSON...

Options:
    -A --addto=OUTFILE      For the index command, the output file will be
                            read and extended with new data, not overwritten. It
                            will be created if it does not exist.
    -c --context CONTEXT    CONTEXT is a JSON file that will be added to the
                            template context for each template rendered. If
                            given multiple times, all files are added.
    -i --inplace            Use input filename to determine output filename.
    -o --outfile=OUTFILE    File to write output. Defaults to STDOUT.
                            If the destination file exists, it will be
                            overwritten.
    -t --templatedir=DIR    Directory where templates are stored. TEMPLATE
                            path should be relative to this.
    -x --extension=EXT      A python-markdown extension module to load.

"""
from __future__ import absolute_import, print_function, unicode_literals

import copy
import json
import sys
from configparser import ConfigParser
from io import open

import jsonschema
import webquills.indexer as indexer
import webquills.j2 as j2
from docopt import docopt
from webquills.mdown import md2archetype, new_markdown
from webquills.util import SmartJSONEncoder, getLogger, change_ext


def configure(args):
    cfg = ConfigParser()
    cfg.read('webquills.ini')
    config = {"new": {}, "md2json": {}, "j2": {}}
    for section in cfg:
        config[section.lower()] = dict(cfg[section].items())

    # Read from config as space separated string; convert to list
    if "extensions" in config["md2json"]:
        config["md2json"]["extensions"] = \
            config["md2json"]["extensions"].split()
    else:
        config["md2json"]["extensions"] = []
    # Add any extensions requested from command line
    if "--extension" in args:
        config["md2json"]["extensions"].append(args["--extension"])

    if "--templatedir" in args:
        config["j2"]["templatedir"] = args["--templatedir"]
    return config


# MAIN: Dispatch to individual handlers
def main():
    logger = getLogger()
    item_types = {"article": "Item/Page/Article", "page": "Item/Page"}
    # Parse out the command and default options. Command options will be
    # parsed later.
    param = docopt(__doc__)
    config = configure(param)
    # logger.debug(repr(config))
    # logger.debug(repr(param))

    if param['new']:
        # TODO (someday) Prompt user for metadata values
        doc = new_markdown(config, item_types[param['ITEMTYPE'].lower()],
                           title=param['TITLE'])
        # Prepare the output file handle
        if param['--outfile']:
            with open(param['--outfile'], 'w', encoding="utf-8") as outfile:
                outfile.write(doc)
        else:
            print(doc)

    elif param['md2json'] and param["--inplace"]:
        for filename in param["FILES"]:
            target = change_ext(filename, '.json')
            logger.info("Processing %s" % target)
            with open(filename, encoding="utf-8") as f:
                mtext = f.read()
            try:
                metadict = md2archetype(config, mtext, param['--extension'])
            except jsonschema.ValidationError as e:
                # spits out a screwy error, make it more obvious
                lines = str(e).splitlines()
                message = lines.pop(0) + "\n"
                detail = "\n".join(lines) + "\n"
                logger.info(detail)
                logger.error("in %s: %s" % (filename, message))
                continue
            with open(target, 'w', encoding="utf-8") as outfile:
                json.dump(metadict, outfile, cls=SmartJSONEncoder)

    elif param['md2json']:
        with open(param["INFILE"], encoding='utf-8') as infile:
            mtext = infile.read()

        try:
            metadict = md2archetype(config, mtext, param['--extension'])
        except jsonschema.ValidationError as e:
            # spits out a screwy error, make it more obvious
            lines = str(e).splitlines()
            message = lines.pop(0) +"\n"
            detail = "\n".join(lines) + "\n"
            logger.info(detail)
            logger.error("in %s: %s" % (param["INFILE"], message))
            exit(1)

        # Prepare the output file handle
        if param['--outfile']:  # If to file, use compact representation
            with open(param['--outfile'], 'w', encoding="utf-8") as outfile:
                json.dump(metadict, outfile, cls=SmartJSONEncoder)
        else:  # If stdout, pretty print
            json.dump(metadict, sys.stdout, sort_keys=True, indent=2,
                      cls=SmartJSONEncoder)

    elif param["j2"]:
        context = copy.deepcopy(config)
        for varfile in param['VARFILES']:
            context.update(j2.loadfile(varfile))
        doc = j2.render(config, context, param["TEMPLATE"])
        if param['--outfile']:
            with open(param['--outfile'], 'w', encoding="utf-8") as outfile:
                outfile.write(doc)
        else:
            print(doc)

    elif param["index"]:
        index = {}
        if param["--addto"]:
            target = param["--addto"]
            try:
                with open(target, encoding="utf-8") as the_index:
                    index = json.load(the_index)
            except FileNotFoundError as e:
                logger.info("File does not exist. Creating: %s" % target)
                pass
        elif param['--outfile']:
            target = param['--outfile']

        for infile in param["JSON"]:
            try:
                with open(infile, encoding="utf-8") as handle:
                    data = json.load(handle)
            except Exception as e:
                logger.info(str(e))
                logger.error("File could not be parsed: %s" % infile)
                continue
            index = indexer.add_to_index(index, data)
        if target:  # If to file, use compact representation
            with open(target, 'w', encoding="utf-8") as outfile:
                json.dump(index, outfile, cls=SmartJSONEncoder)
        else:  # If stdout, pretty print
            json.dump(index, sys.stdout, sort_keys=True, indent=2,
                          cls=SmartJSONEncoder)
