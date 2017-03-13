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
    quill build [-v] [-r ROOT] [-t DIR] [-s SRCDIR] [--dev]
    quill config [-v] [QUERY]

Options:
    --dev                   Development mode. Ignore future publish restriction
                            and include all items.
    -o --outfile=OUTFILE    File to write output. Defaults to STDOUT.
                            If the destination file exists, it will be
                            overwritten.
    -r --root=ROOT          The destination build directory. All calculated
                            paths will be relative to this directory.
    -s --source=SRCDIR      The directory from which to read source files
                            (markdown, etc.)
    -t --templatedir=DIR    Directory where templates are stored. TEMPLATE
                            path should be relative to this.
    -v --verbose            Verbose logging

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
    param = docopt(__doc__)
    cfg = configure(param)
    logger = util.getLogger(cfg)
    item_types = {
        "article": "Item/Page/Article",
        "page": "Item/Page",
        "catalog": "Item/Page/Catalog"
    }
    arch = LocalArchivist(cfg)
    schema = util.Schematist(cfg)

    if param["build"]:
        # 1. cp any files from srcdir needing update to root
        arch.gather_sources()
        # 2. find root sources needing JSON; md2json them
        for src in arch.sources_needing_update():
            logger.info("Updating source: %s" % src)
            archetype = md2archetype(cfg, src.read_text(encoding=UTF8))
            schema.apply_defaults(archetype, src)

            # FIXME Because done before validation, category may not be right
            # type. Gives confusing error message.
            target = schema.root / archetype["Item"]["category"]["label"] / \
                archetype["Item"]["slug"]
            target = target.with_suffix(".json")
            archetype["Item"]["archetype"] = {
                "href": "/" + str(target.relative_to(arch.root)),
                "rel": "wq:archetype"
            }
            archetype["Item"]["source"] = {
                "href": "/" + str(src.relative_to(arch.root)),
                "rel": "wq:source"
            }

            try:
                schema.validate(archetype)
            except jsonschema.ValidationError as e:
                logger.info(str(e))
                logger.error("%s: %s at %s" % (src, e.message, e.path))
                logger.debug(archetype)
                continue
            arch.write_json(target, archetype)

        # 3. find json files needing indexing; index them
        indexfile = arch.root / "_index.json"
        index = arch.load_json(indexfile, default={})
        for file in arch.archetypes_needing_indexing():
            logger.info("Indexing %s" % file)
            indexer.add_to_index(index, arch.load_json(file),
                                 include_future=param['--dev'])
        arch.write_json(indexfile, index)

        # 4. find any json files needing outputs
        base_context = copy.deepcopy(cfg)
        for file in arch.archetypes_needing_render():
            logger.info("Rendering %s" % file)
            item = arch.load_json(file)
            if "Item" not in item:
                logger.warning("Skipping non-Item JSON file: %s" % file)
                continue
            context = copy.deepcopy(base_context)
            context.update(item)
            if item["Item"]["itemtype"].startswith("Item/Page/Catalog"):
                context["Index"] = index

            outputs = j2.templates_from_context(context)
            for extension, templatelist in outputs.items():
                # Allows items to override output format, or request
                # additional formats
                if extension not in context["Webquills"]["scribes"]:
                    continue
                out = j2.render(cfg, context, templatelist)
                file.with_suffix(
                    '.' + extension).write_text(out, encoding=UTF8)

    elif param['new']:
        # TODO (someday) Prompt user for metadata values
        doc = new_markdown(cfg, item_types[param['ITEMTYPE'].lower()],
                           title=param['TITLE'])
        # Prepare the output file handle
        if param['--outfile']:
            dest = Path(param["--outfile"])
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(doc, encoding=UTF8)
        else:
            print(doc)

    elif param["config"]:
        out = repr(cfg)
        if param["QUERY"]:
            out = repr(jmespath.search(param["QUERY"], cfg))
        out = out.strip().strip('"\'')
        print(out)
