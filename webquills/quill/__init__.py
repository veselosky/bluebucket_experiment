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
from pathlib import Path

import jmespath
import jsonschema
import webquills.indexer as indexer
import webquills.j2 as j2
import yaml
from docopt import docopt
from webquills.localfs import LocalArchivist
from webquills.mdown import md2archetype, new_markdown
import webquills.util as util


UTF8 = "utf-8"


def configure(args):
    with open("webquills.yml") as f:
        cfg = yaml.load(f, Loader=yaml.BaseLoader)
    cfg.setdefault("markdown", {})
    cfg.setdefault("jinja2", {})
    cfg.setdefault("options", {})
    cfg.setdefault("site", {})

    for key, value in args.items():
        if key.startswith("--") and value is not None:
            cfg["options"][key[2:]] = value
    return cfg


# MAIN: Dispatch to individual handlers
def main():
    logger = util.getLogger()
    item_types = {"article": "Item/Page/Article", "page": "Item/Page"}
    param = docopt(__doc__)
    cfg = configure(param)
    arch = LocalArchivist(cfg)
    schema = util.Schematist(cfg)

    if param["build"]:
        # 1. cp any files from srcdir needing update to root
        arch.gather_sources()
        # 2. find root sources needing JSON; md2json them
        for filename in arch.sources_needing_update():
            logger.info("Updating source: %s" % filename)
            itemmeta = schema.item_defaults_for(filename)
            archetype = md2archetype(cfg, filename.read_text(encoding=UTF8),
                                     itemmeta)
            try:
                schema.validate(archetype)
            except jsonschema.ValidationError as e:
                logger.info(str(e))
                logger.error("%s: %s at %s" % (filename, e.message, e.path))
                continue
            target = arch.root/archetype["Item"]["category"][
                "label"]/archetype["Item"]["slug"]
            target = target.with_suffix(".json")
            arch.write_json(target,archetype)

        # 3. find json files needing indexing; index them
        index = arch.load_json(arch.root/"_index.json", default={})
        for file in arch.archetypes_needing_indexing():
            logger.info("Indexing %s" % file)
            indexer.add_to_index(index, arch.load_json(file))
        arch.write_json(arch.root / "_index.json", index)

        # 4. find any json files needing outputs
        base_context = copy.deepcopy(cfg)
        for file in arch.archetypes_needing_render():
            logger.info("Rendering %s" % file)
            item = arch.load_json(file)
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
