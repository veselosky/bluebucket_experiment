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
from __future__ import absolute_import, print_function, unicode_literals

import datetime
import string
import uuid
from datetime import datetime

import markdown
import pytz
from dateutil.parser import parse as parse_date
from markdown.extensions.toc import TocExtension

from webquills.util import slugify


def new_markdown(item_type, title=None, **kwargs):
    """quill new <itemtype> [<title>]

        Generates a new markdown file from a template based on the requested
        item type. Prints to STDOUT, redirect it where you want it. Types
        supported are anything that has a JSON schema in the webquills.schemas
        package. If supplied, <title> will be added to the metadata.
        """
    # Some defaults
    now = datetime.now()
    # FIXME Get TZ from config, default to something reasonable
    now = pytz.timezone('America/New_York').localize(now)
    text = ""

    metas = ['itemtype: %s' % item_type, 'guid: %s' % uuid.uuid4()]
    for key in kwargs:
        metas.append('%s: %s' % (key, kwargs[key]))
    if 'created' not in kwargs:
        metas.append('updated: %s' % now.isoformat())
    if 'updated' not in kwargs:
        metas.append('updated: %s' % now.isoformat())
    if 'category' not in kwargs:
        text += '''
        For SEO, please assign a keyword-rich category like "keyword/seo" above.
        It will be used to generate a URL. Category will be inferred from the
        file path otherwise.
        '''

    if title:
        metas.append('slug: %s' % slugify(title))
        metas.append('title: %s' % title)
    else:
        metas.append('title:')
        text += "\nYou need to set a title. It's a required field!\n"

    return "\n".join(metas) + "\n\n" + text


def md2archetype(mtext, extensions=None):
    """
    Markdown to JSON.

    Usage:
        quill md2json [-x EXT...] <infile> [<outfile>]

    Options:
        -x --extension=EXT      A python-markdown extension module to load.

    """
    # FIXME Get TZ from config, default to something reasonable
    zone = pytz.timezone('America/New_York')
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
    extensions = set(extensions + default_extensions)

    md = markdown.Markdown(extensions=extensions, output_format='html5',
                           lazy_ol=False)

    html = md.convert(mtext)
    metadata = md.Meta
    if not metadata:
        # FIXME This error message is embarassing. Fix it.
        raise TypeError('Missing required metadata')
    # The metadata needs clean up, because:
    # 1. meta ext reads everything as a list, but most values should be scalar
    # 2. because humans are sloppy, we parse and normalize date values
    itemmeta = {"contenttype": "text/html; charset=utf-8"}
    # Here we implement some special case transforms for data that may need
    # cleanup or is hard to encode using markdown's simple format.
    for key, value in metadata.items():
        if key in ['created', 'date', 'published', 'updated']:
            # because humans are sloppy, we parse and normalize date values
            dt = parse_date(value[0])
            if dt.tzinfo:
                dt = dt.astimezone(zone)
            else:
                dt = zone.localize(dt)
            if key == 'date':  # Legacy DC.date, convert to specific
                key = 'published'
            itemmeta[key] = dt.isoformat()

        elif key == 'itemtype':
            itemmeta['itemtype'] = string.capwords(metadata['itemtype'][0], '/')

        elif key == 'author':
            itemmeta["attribution"] = [
                {"role": "author", "name": metadata[key][0]}]

        elif key == "copyright":  # Typical usage provides only notice
            itemmeta["rights"] = {"copyright_notice": metadata[key][0]}
        elif key.startswith("rights-"):
            if "rights" not in itemmeta:
                itemmeta["rights"] = {}
            itemmeta["rights"][key[7:]] = metadata[key][0]

        elif key == "category":  # Typical usage provides only name
            itemmeta["category"] = {"name": metadata[key][0]}
        elif key.startswith("category-"):
            if "category" not in itemmeta:
                itemmeta["category"] = {}
            itemmeta["category"][key[9:]] = metadata[key][0]

        else:
            # reads everything as list, but most values should be scalar
            itemmeta[key] = value[0] if len(value) == 1 else value

    itemmeta['published'] = itemmeta.get('published') or itemmeta.get('updated')
    itemmeta['updated'] = itemmeta.get('updated') or itemmeta.get('published')

    return {"Item": itemmeta, "Article": {"body": html}}
