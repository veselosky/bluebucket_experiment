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
import datetime
import re
import string
import uuid
from collections import OrderedDict

import arrow
import markdown
import yaml
from dateutil.parser import parse as parse_date
from dateutil.tz import tzlocal
from markdown.extensions.toc import TocExtension

category_seo_msg = '''
For SEO, please assign a keyword-rich category like "keyword/seo" above.
It will be used to generate a URL. Category will be inferred from the
file path otherwise. Recommendations:

Title: <75 characters
Url: <90 characters (category + slug)
Description: <160 characters
'''

md = None


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
    metas = OrderedDict(itemtype=item_type,
                        guid='"urn:UUID:' + str(uuid.uuid4()) + '"')
    metas.update(kwargs)
    metas.setdefault("created", now)
    metas.setdefault("updated", now)
    metas.setdefault("published", now)

    if 'category' not in metas:
        text += category_seo_msg

    if title:
        metas["title"] = '"' + title + '"'
    else:
        text += "\nYou need to set a title. It's a required field!\n"
    # Once again pyyaml is trying to be far too clever and cluttering output,
    # so we do this the old fashioned way. -VV 2016-10-23
    out = "---\n"
    for key, value in metas.items():
        out += "%s: %s\n" % (key, value)
    out += "...\n"
    out += text
    return out


def md2archetype(config, intext: str):
    """
    Markdown to JSON.

    Usage:
        quill md2json [-x EXT...] <infile> [<outfile>]

    Options:
        -x --extension=EXT      A python-markdown extension module to load.

    """
    # Cache at module level to save setup on multiple calls
    global md
    if md is None:
        extensions = [
            'markdown.extensions.extra',
            'markdown.extensions.admonition',
            'markdown.extensions.codehilite',
            'markdown.extensions.sane_lists',
            TocExtension(permalink=True),  # replaces headerId
            'pyembed.markdown'
        ]
        md = markdown.Markdown(extensions=extensions, output_format='html5',
                               lazy_ol=False)

    # Clean the input and check for yaml front matter
    mdtext = intext.strip()
    metadata = {}
    archetype = {}
    if mdtext.startswith('---'):
        _, yamltext, mdtext = re.split(r'^\.{3,}|-{3,}$', mdtext,
                                       maxsplit=2, flags=re.MULTILINE)
        # YAML parses datetime inconsistently, and incorrectly (loses timezone)
        # Using BaseLoader prevents it from trying to be clever
        frontmatter = yaml.load(yamltext, Loader=yaml.BaseLoader)
        if "Item" in frontmatter:
            # Metadata is in "full" format.
            metadata = frontmatter.pop("Item")
            archetype = frontmatter
        else:
            # Metadata is in "itemmeta" format
            metadata = frontmatter
            metadata.setdefault("itemtype", "Item/Page/Article")

    html = md.convert(mdtext)
    # TODO (Someday) Extract headline from the HTML body for meta

    zone = config.get("site", {}).get("timezone", tzlocal())
    # Here we implement some special case transforms for data that may need
    # cleanup or is hard to encode using markdown's simple format.
    itemmeta = {}
    catalog_meta = {}
    for key, value in metadata.items():
        key = key.lower()
        if key in ['created', 'date', 'published', 'updated']:
            # Because humans are sloppy, we parse and normalize date values.
            # Because we care about timezones, we use arrow, not yaml/datetime.
            # We want unspecified timezones to default to local, but to honor
            # any zone specified.
            default_datetime = arrow.now(zone).replace(hour=0, minute=0,
                                                       second=0,
                                                       microsecond=0).datetime
            dt = arrow.get(parse_date(value, default=default_datetime))
            if key == 'date':  # Legacy DC.date, convert to specific
                key = 'published'
            itemmeta[key] = dt.isoformat().replace("+00:00", "Z")

        elif key == 'itemtype':
            itemmeta[key] = string.capwords(value, '/')

        else:
            itemmeta[key] = value

    itemmeta['published'] = itemmeta.get(
        'published') or itemmeta.get('updated')
    itemmeta['updated'] = itemmeta.get('updated') or itemmeta.get('published')
    # hard coded defaults: markdown typically represents HTML pages
    itemmeta.setdefault("contenttype", "text/html; charset=utf-8")
    itemmeta.setdefault("itemtype", "Item/Page")

    archetype["Item"] = itemmeta
    archetype.setdefault("Page", {})
    if re.search(r'\bArticle\b', itemmeta["itemtype"]):
        archetype.setdefault("Article", {})
        archetype["Article"]["body"] = html
    elif re.search(r'\bCatalog\b', itemmeta["itemtype"]):
        archetype["Page"]["text"] = html
        archetype.setdefault("Catalog", catalog_meta)
    else:
        archetype["Page"]["text"] = html

    return archetype
