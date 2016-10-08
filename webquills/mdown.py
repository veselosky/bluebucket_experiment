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
import json
import re
import string
import uuid
from pathlib import Path

import arrow
import jsonschema
import markdown
import pkg_resources
from dateutil.parser import parse as parse_date
from dateutil.tz import tzlocal
from markdown.extensions.toc import TocExtension

from webquills.util import slugify, is_sequence

category_seo_msg = '''
For SEO, please assign a keyword-rich category like "keyword/seo" above.
It will be used to generate a URL. Category will be inferred from the
file path otherwise. Recommendations:

Title: <75 characters
Url: <90 characters (category + slug)
Description: <160 characters
'''

itemschema = None
md = None
UTF8 = "utf-8"


def new_markdown(config, item_type, title=None, **kwargs):
    """quill new <itemtype> [<title>]

        Generates a new markdown file from a template based on the requested
        item type. Prints to STDOUT, redirect it where you want it. Types
        supported are anything that has a JSON schema in the webquills.schemas
        package. If supplied, <title> will be added to the metadata.
        """
    # Some defaults
    timezone = config.get("site", {}).get("timezone", tzlocal())
    now = arrow.now(timezone).isoformat().replace("+00:00", "Z")
    text = ""

    metas = ['itemtype: %s' % item_type, 'guid: %s' % uuid.uuid4()]
    for key in kwargs:
        metas.append('%s: %s' % (key, kwargs[key]))
    if 'created' not in kwargs:
        metas.append('created: %s' % now)
    if 'updated' not in kwargs:
        metas.append('updated: %s' % now)
    if 'published' not in kwargs:
        metas.append('published: %s' % now)
    if 'category' not in kwargs:
        text += category_seo_msg

    if title:
        metas.append('slug: %s' % slugify(title))
        metas.append('title: %s' % title)
    else:
        metas.append('title:')
        text += "\nYou need to set a title. It's a required field!\n"

    return "\n".join(metas) + "\n\n" + text


def md2archetype(config, mtext, extensions=None):
    """
    Markdown to JSON.

    Usage:
        quill md2json [-x EXT...] <infile> [<outfile>]

    Options:
        -x --extension=EXT      A python-markdown extension module to load.

    """
    # Cache at module level to save setup on multiple calls
    global itemschema
    global md
    if md is None:
        default_extensions = [
            'markdown.extensions.extra',
            'markdown.extensions.admonition',
            'markdown.extensions.codehilite',
            'markdown.extensions.meta',
            'markdown.extensions.sane_lists',
            TocExtension(permalink=True),  # replaces headerId
            'pyembed.markdown'
        ]
        if extensions is None:
            extensions = []
        extensions.extend(default_extensions)
        extensions.extend(config["markdown"]["extensions"])
        md = markdown.Markdown(extensions=extensions, output_format='html5',
                               lazy_ol=False)

    html = md.convert(mtext)
    # TODO (Someday) Extract headline from the HTML body for meta

    zone = config.get("site", {}).get("timezone", tzlocal())
    # hard coded defaults: markdown can only represent HTML pages
    itemmeta = {
        "contenttype": "text/html; charset=utf-8",
        "itemtype": "Item/Page"
    }
    # User configurable defaults
    metadata = copy.deepcopy(config.get("item_defaults", {}))
    # Actual document metadata
    metadata.update(md.Meta)

    # Here we implement some special case transforms for data that may need
    # cleanup or is hard to encode using markdown's simple format.
    for key, value in metadata.items():
        # markdown meta reads all items as arrays. unpack
        if is_sequence(value) and len(value) == 1:
            value = value[0]
        if key in ['created', 'date', 'published', 'updated']:
            # because humans are sloppy, we parse and normalize date values
            dt = arrow.get(parse_date(value), zone)
            if key == 'date':  # Legacy DC.date, convert to specific
                key = 'published'
            itemmeta[key] = dt.isoformat().replace("+00:00", "Z")

        elif key == 'itemtype':
            itemmeta['itemtype'] = string.capwords(value, '/')

        elif key == 'author':
            itemmeta["attribution"] = [
                {"role": "author", "name": value}]

        elif key == "license":
            # FIXME License logic a mess. Replace w/symbol lookup (e.g. CC-BY)
            if "links" not in itemmeta:
                itemmeta["links"] = []
            itemmeta["links"].append({"href": value, "rel": "license"})

        elif key == "category":  # Typical usage provides only name
            itemmeta["category"] = {"name": value, "label": slugify(value)}

        elif key.startswith("category-"):
            if "category" not in itemmeta:
                itemmeta["category"] = {}
            itemmeta["category"][key[9:]] = value

        # Defined as space-separated list
        elif key in ("tags", "template"):
            itemmeta[key] = value.lower().split()

        else:
            itemmeta[key] = value

    itemmeta['published'] = itemmeta.get('published') or itemmeta.get('updated')
    itemmeta['updated'] = itemmeta.get('updated') or itemmeta.get('published')

    if re.search(r'\bArticle\b', itemmeta["itemtype"]):
        archetype = {"Item": itemmeta, "Article": {"body": html}}
    else:
        archetype = {"Item": itemmeta, "Page": {"text": html}}

    if itemschema is None:
        schemafile = pkg_resources.resource_filename('webquills.schemas',
                                                    'Item.json')
        with open(schemafile, encoding="utf-8") as f:
            itemschema = json.load(f)

    jsonschema.validate(archetype, itemschema)  # Raises ValidationError
    return archetype


# When reading from a file, we can infer some additional metadata
def archetype_from_file(config, infile):
    infile = Path(infile)
    # intentionally allow exceptions to propagate up:
    archetype = md2archetype(config, infile.read_text(encoding=UTF8))
    # A little extra magic: populate some defaults from the source
    # file name if not explicitly defined.
    item = archetype["Item"]
    root = config["options"].get("root", "")
    default_cat = {"label": str(infile.parent.relative_to(root))}
    if default_cat["label"] == ".":
        default_cat["label"] = ""
    default_cat["name"] = default_cat["label"].replace("-", " ").title()
    item.setdefault("category", default_cat)
    item.setdefault("slug", str(infile.stem))

    target = Path(root, item["category"]["label"], item["slug"] + ".json")
    item.setdefault("links", []).extend([{
        "rel": "wq:source", "href": "/" + str(infile.relative_to(root))
    }, {
        "rel": "wq:archetype", "href": "/" + str(target.relative_to(root))
    }, ])

    return (archetype, target)
