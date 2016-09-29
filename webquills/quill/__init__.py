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
    quill new ITEMTYPE [TITLE]
    quill md2json [-x EXT...] INFILE [OUTFILE]

Options:
    -x --extension=EXT      A python-markdown extension module to load.
"""
from __future__ import absolute_import, print_function, unicode_literals

import logging
import json
import sys
from io import open
from os import path
try:  # In Python 3 ConfigParser was renamed, and "safe" became the default
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import SafeConfigParser as ConfigParser

from docopt import docopt

from webquills.quill.mdown import new_markdown, md2archetype
from webquills.util import SmartJSONEncoder


def configure(args):
    # TODO (maybe) Some args might get copied to config
    cfg = ConfigParser()
    cfg.read('webquills.ini')
    config = {}
    for section in cfg:
        config[section.lower()] = dict(cfg[section].items())

    return config


# MAIN: Dispatch to individual handlers
def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    item_types = {"article": "Item/Page/Article", "page": "Item/Page"}
    # Parse out the command and default options. Command options will be
    # parsed later.
    param = docopt(__doc__, options_first=True)
    config = configure(param)
    # logger.info(repr(config))

    if param['new']:
        # TODO (someday) Prompt user for metadata values
        print(new_markdown(config, item_types[param['ITEMTYPE'].lower()],
                           title=param['TITLE']))

    elif param['md2json']:
        arguments = docopt(md2archetype.__doc__)
        with open(arguments['<infile>'], encoding='utf-8') as infile:
            mtext = infile.read()

        metadict = md2archetype(config, mtext, arguments['--extension'])

        if arguments['<outfile>']:
            outfile = open(arguments['<outfile>'], 'w')
            metadict['path'] = path.abspath(arguments['<outfile>'])
        else:
            outfile = sys.stdout

        json.dump(metadict, outfile, sort_keys=True, indent=2, cls=SmartJSONEncoder)
