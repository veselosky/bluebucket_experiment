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
import json
import shutil
from pathlib import Path

from webquills.util import SmartJSONEncoder

def loadjson(fname):
    with Path(fname).open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def newer(inpath, than=None):
    if than is None:
        return True
    try:
        src = Path(inpath).stat().st_mtime
        dest = Path(than).stat().st_mtime
        return src > dest
    except FileNotFoundError:
        return True


def read_index(config):
    builddir = Path(config["options"]["root"])
    indexfile = builddir.joinpath("_index.json")
    try:
        index = loadjson(indexfile)
    except FileNotFoundError:
        index = {}
    return index


def write_index(config, index):
    builddir = Path(config["options"]["root"])
    indexfile = builddir.joinpath("_index.json")
    out = json.dumps(index, cls=SmartJSONEncoder)
    indexfile.write_text(out, encoding="utf-8")


def copysources(config):
    sourcedir = Path(config["options"]["source"])
    destdir = Path(config["options"]["root"])
    for src in sourcedir.glob("**/*"):
        dest = destdir.joinpath(src.relative_to(sourcedir))
        if src.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
        elif newer(src, than=dest):
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dest))


def sources_needing_update(config):
    builddir = Path(config["options"]["root"])
    needs_update = []
    for src in builddir.glob("**/*.md"):
        if not src.is_file():
            continue
        dest = src.with_suffix(".json")
        if newer(src, than=dest):
            needs_update.append(src)
    return needs_update


def archetypes_needing_indexing(config):
    builddir = Path(config["options"]["root"])
    index = builddir.joinpath("_index.json")
    needs_update = []
    for src in builddir.glob("**/*.json"):
        if not src.is_file() or src == index:
            continue
        if newer(src, than=index):
            needs_update.append(src)
    return needs_update


def archetypes_needing_render(config):
    # - (if webquills.ini changed, rebuild all)
    # - (if the index changed, rebuild all Catalogs)
    # otherwise calculate each output file, and compared timestamps
    # Fuck it, this is kinda hard. For now, just render everything. -VV
    builddir = Path(config["options"]["root"])
    index = builddir.joinpath("_index.json")
    needs_update = []
    for src in builddir.glob("**/*.json"):
        if not src.is_file() or src == index:
            continue
        needs_update.append(src)
    return needs_update
