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
    quill build [-r ROOT] [-t DIR] [-s SRCDIR] [-x EXT]...
    quill config [-r ROOT] [-t DIR] [-s SRCDIR] [QUERY]

Options:
    -o --outfile=OUTFILE    File to write output. Defaults to STDOUT.
                            If the destination file exists, it will be
                            overwritten.
    -r --root=ROOT          The destination build directory. All calculated
                            paths will be relative to this directory.
    -s --source=SRCDIR      The directory from which to read source files
                            (markdown, etc.)
    -t --templatedir=DIR    Directory where templates are stored. TEMPLATE
                            path should be relative to this.
    -x --extension=EXT      A python-markdown extension module to load.

"""
import copy
import json
import sys
from configparser import ConfigParser
from pathlib import Path

import jmespath
import jsonschema
import webquills.indexer as indexer
import webquills.j2 as j2
from docopt import docopt
from webquills import localfs as localfs
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

    if param["build"]:
        # 1. cp any files from srcdir needing update to root
        localfs.copysources(cfg)
        # 2. find root sources needing JSON; md2json them
        for filename in localfs.sources_needing_update(cfg):
            try:
                (metadict, target) = archetype_from_file(cfg, filename)
            except jsonschema.ValidationError as e:
                # spits out a screwy error, make it more obvious
                lines = str(e).splitlines()
                message = lines.pop(0) + "\n"
                detail = "\n".join(lines) + "\n"
                logger.info(detail)
                logger.error("in %s: %s" % (filename, message))
                continue
            with target.open('w', encoding=UTF8) as outfile:
                    json.dump(metadict, outfile, cls=SmartJSONEncoder)

        # 3. find json files needing indexing; index them
        index = localfs.read_index(cfg)
        for file in localfs.archetypes_needing_indexing(cfg):
            indexer.add_to_index(index, localfs.loadjson(file))
        localfs.write_index(cfg, index)

        # 4. find any json files needing outputs
        base_context = copy.deepcopy(cfg)
        for file in localfs.archetypes_needing_render(cfg):
            logger.info("Processing %s" % file)
            item = localfs.loadjson(file)
            if not "Item" in item:
                logger.warning("Skipping non-Item JSON file: %s" % file)
                continue
            context = dict(base_context, **item)
            if item["Item"]["itemtype"].startswith("Item/Page/Catalog"):
                context["Index"] = index
            # returns a dict of {".ext": ["templates", ]
            templates = j2.templates_from_context(context)
            for key in templates:
                # Allows items to override output format, or request
                # additional formats
                if key not in context["Item"].get("wq_output", ["html"]):
                    continue
                out = j2.render(cfg, context, templates[key])
                file.with_suffix('.' + key).write_text(out, encoding=UTF8)

    elif param['new']:
        # TODO (someday) Prompt user for metadata values
        doc = new_markdown(cfg, item_types[param['ITEMTYPE'].lower()],
                           title=param['TITLE'])
        # Prepare the output file handle
        if param['--outfile']:
            Path(param["--outfile"]).write_text(doc, encoding=UTF8)
        else:
            print(doc)

    elif param["config"]:
        out = repr(cfg)
        if param["QUERY"]:
            out = repr(jmespath.search(param["QUERY"], cfg))
        out = out.strip().strip('"\'')
        print(out)
