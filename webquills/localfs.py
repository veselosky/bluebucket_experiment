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

UTF8 = "utf-8"


class LocalArchivist(object):

    def __init__(self, config):
        self.config = config
        self.root = Path(config["options"]["root"])
        self.source_dir = Path(config["options"]["source"])

    def load_json(self, path: Path, default=None):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except OSError:
            data = None
        return data or default

    def load_text(self, path: Path) -> str:
        return path.read_text(encoding=UTF8)

    def newer(self, inpath: Path, than: Path = None) -> bool:
        if than is None:
            return True
        try:
            src = inpath.stat().st_mtime
            dest = than.stat().st_mtime
            return src > dest
        except FileNotFoundError:
            return True

    def write_text(self, path: Path, text: str):
        return path.write_text(text, encoding=UTF8)

    def write_json(self, path: Path, struct: dict, pretty=False):
        args = {"cls": SmartJSONEncoder}
        if pretty:
            args.update({"indent": 2, "sort_keys": True})

        return path.write_text(json.dumps(struct, **args), encoding=UTF8)

    def gather_sources(self):
        sourcedir = self.source_dir
        destdir = self.root
        for src in sourcedir.glob("**/*"):
            dest = destdir/src.relative_to(sourcedir)
            if src.is_dir():
                dest.mkdir(parents=True, exist_ok=True)
            elif self.newer(src, than=dest):
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(src), str(dest))

    def sources_needing_update(self):
        builddir = self.root
        needs_update = []
        for src in builddir.glob("**/*.md"):
            if not src.is_file():
                continue
            dest = src.with_suffix(".json")
            if self.newer(src, than=dest):
                needs_update.append(src)
        return needs_update

    def archetypes_needing_indexing(self):
        builddir = self.root
        index = builddir/"_index.json"
        needs_update = []
        for src in builddir.glob("**/*.json"):
            if not src.is_file() or src == index:
                continue
            if self.newer(src, than=index):
                needs_update.append(src)
        return needs_update

    def archetypes_needing_render(self):
        # - (if webquills.ini changed, rebuild all)
        # - (if the index changed, rebuild all Catalogs)
        # otherwise calculate each output file, and compared timestamps
        # Fuck it, this is kinda hard. For now, just render everything. -VV
        builddir = self.root
        index = builddir/"_index.json"
        needs_update = []
        for src in builddir.glob("**/*.json"):
            if not src.is_file() or src == index:
                continue
            needs_update.append(src)
        return needs_update
