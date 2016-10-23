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
import copy
import datetime
import logging
import json
from gzip import GzipFile
from io import BytesIO

import colorlog
import jmespath
import jsonschema
import pkg_resources
import slugify as sluglib
from pathlib import Path


class SmartJSONEncoder(json.JSONEncoder):
    """
    JSONEncoder subclass that knows how to encode date/time.
    """

    def default(self, o):
        if isinstance(o, datetime.datetime):
            r = o.isoformat()
            if o.microsecond:
                r = r[:23] + r[26:]
            if r.endswith('+00:00'):
                r = r[:-6] + 'Z'
            return r
        elif isinstance(o, datetime.date):
            return o.isoformat()
        elif isinstance(o, datetime.time):
            r = o.isoformat()
            if o.microsecond:
                r = r[:12]
            return r
        else:
            return super(SmartJSONEncoder, self).default(o)


class Schematist(object):

    def __init__(self, config):
        self.config = config
        self.root = Path(config["options"].get("root", ""))
        schemafile = pkg_resources.resource_filename('webquills.schemas',
                                                     'Item.json')
        with open(schemafile, encoding="utf-8") as f:
            self.itemschema = json.load(f)

    def apply_defaults(self, archetype: dict, path: Path) -> dict:
        logger = getLogger()
        meta = archetype["Item"]
        configured_default = copy.deepcopy(self.config.get("item_defaults", {}))
        for key, value in configured_default.items():
            meta.setdefault(key, value)

        default_cat = {"label": str(path.parent.relative_to(self.root))}
        if default_cat["label"] == ".":
            default_cat["label"] = ""
        default_cat["name"] = default_cat["label"].replace("-", " ").title()

        meta.setdefault("category", default_cat)
        meta.setdefault("slug", str(path.stem))
        meta.setdefault("wq_output", ["html"])
        meta.setdefault("attributions", [])
        meta.setdefault("links", [])
        # If there is an author, that's the default copyright holder.
        try:
            author = jmespath.search("[?role==`author`]|[0]",
                                     meta["attributions"])
            meta.setdefault("copyright_holder", author)
        except KeyError:
            # no author
            logger.error("No author found in attributions: %s" % meta.get(
                "attributions"))
            pass
        copyright = "©%s %s" % (meta["updated"][:4],
                                meta.get("copyright_holder", {}).get("name"))
        meta.setdefault("copyright", copyright)

    def validate(self, struct):
        jsonschema.validate(struct, self.itemschema)  # Raises ValidationError
        return True


# Ugh! Why does logging have to be so damned hard?
logger = None


def getLogger():
    # TODO get verbosity from params
    global logger
    if logger is None:
        handler = colorlog.StreamHandler()
        handler.setFormatter(colorlog.ColoredFormatter(
            '%(log_color)s%(levelname)s: %(message)s', log_colors={
                'DEBUG': 'white', 'INFO': 'cyan', 'WARNING': 'yellow',
                'ERROR': 'red', 'CRITICAL': 'red,bg_white',
            }, ))
        logger = colorlog.getLogger('webquills')
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def gzip(content, filename=None, compresslevel=9, mtime=None):
    gzbuffer = BytesIO()
    gz = GzipFile(filename, 'wb', compresslevel, gzbuffer, mtime)
    gz.write(content)
    gz.close()
    return gzbuffer.getvalue()


def gunzip(gzcontent):
    gzbuffer = BytesIO(gzcontent)
    return GzipFile(None, 'rb', fileobj=gzbuffer).read()


def is_sequence(arg):
    return (not hasattr(arg, "strip") and
            (hasattr(arg, "__getitem__") or
             hasattr(arg, "__iter__")))


# Consistent slugify. Lots of stupid edge cases here but whatever. -VV
default_stopwords = ['a', 'an', 'and', 'as', 'but', 'for', 'in', 'is', 'of',
                     'on', 'or', 'than', 'the', 'to', 'with']


def slugify(instring, stopwords=default_stopwords):
    return sluglib.slugify(instring, stopwords=stopwords)
