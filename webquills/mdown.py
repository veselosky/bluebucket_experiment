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
import re
import string
import uuid

import arrow
import markdown
import yaml
from dateutil.parser import parse as parse_date
from dateutil.tz import tzlocal
from markdown.extensions.toc import TocExtension

import webquills.util as util

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
        metas.append('slug: %s' % util.slugify(title))
        metas.append('title: %s' % title)
    else:
        metas.append('title:')
        text += "\nYou need to set a title. It's a required field!\n"

    return "\n".join(metas) + "\n\n" + text


def md2archetype(config, intext: str, itemmeta: dict):
    """
    Markdown to JSON.

    Usage:
        quill md2json [-x EXT...] <infile> [<outfile>]

    Options:
        -x --extension=EXT      A python-markdown extension module to load.

    """
    logger = util.getLogger()
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
    if mdtext.startswith('---'):
        _, yamltext, mdtext = re.split(r'^\.{3,}|-{3,}$', mdtext,
                                       maxsplit=3, flags=re.MULTILINE)
        # YAML parses datetime inconsistently, and incorrectly (loses timezone)
        # Using BaseLoader prevents it from trying to be clever
        metadata = yaml.load(yamltext, Loader=yaml.BaseLoader)

    html = md.convert(mdtext)
    # TODO (Someday) Extract headline from the HTML body for meta

    zone = config.get("site", {}).get("timezone", tzlocal())
    # hard coded defaults: markdown can only represent HTML pages
    metadata.setdefault("contenttype", "text/html; charset=utf-8")
    metadata.setdefault("itemtype", "Item/Page")
    metadata.setdefault("attributions", [])
    metadata.setdefault("links", [])

    # Here we implement some special case transforms for data that may need
    # cleanup or is hard to encode using markdown's simple format.
    for key, value in metadata.items():
        key = key.lower()
        if key in ['created', 'date', 'published', 'updated']:
            # Because humans are sloppy, we parse and normalize date values.
            # Because we care about timezones, we use arrow, not yaml/datetime.
            dt = arrow.get(parse_date(value), zone)
            if key == 'date':  # Legacy DC.date, convert to specific
                key = 'published'
            itemmeta[key] = dt.isoformat().replace("+00:00", "Z")

        elif key == 'itemtype':
            itemmeta[key] = string.capwords(value, '/')

        elif key == 'author':
            itemmeta["attributions"] = [
                {"role": "author", "name": value}]

        else:
            itemmeta[key] = value

    itemmeta['published'] = itemmeta.get('published') or itemmeta.get('updated')
    itemmeta['updated'] = itemmeta.get('updated') or itemmeta.get('published')

    if re.search(r'\bArticle\b', itemmeta["itemtype"]):
        archetype = {"Item": itemmeta, "Page": {}, "Article": {"body": html}}
    else:
        archetype = {"Item": itemmeta, "Page": {"text": html}}

    return archetype
