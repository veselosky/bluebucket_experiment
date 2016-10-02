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
    quill md2json [-x EXT...] [-o OUTFILE] INFILE
    quill j2 -t DIR [-o OUTFILE] TEMPLATE [VARFILES...]

Options:
    -o --outfile OUTFILE    File to write output. Defaults to STDOUT.
    -t --templatedir DIR    Directory where templates are stored. TEMPLATE
                            path should be relative to this.
    -x --extension=EXT      A python-markdown extension module to load.

"""
from __future__ import absolute_import, print_function, unicode_literals

import copy
import json
import logging
import sys
from io import open

import jsonschema

try:  # In Python 3 ConfigParser was renamed, and "safe" became the default
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import SafeConfigParser as ConfigParser

from docopt import docopt

from webquills.mdown import new_markdown, md2archetype
import webquills.j2 as j2
from webquills.util import SmartJSONEncoder, getLogger


def configure(args):
    cfg = ConfigParser()
    cfg.read('webquills.ini')
    config = {"new": {}, "md2json": {}, "j2": {}}
    for section in cfg:
        config[section.lower()] = dict(cfg[section].items())

    # Read from config as space separated string; convert to list
    if "extensions" in config["md2json"]:
        config["md2json"]["extensions"] = \
            config["md2json"]["extensions"].split()
    else:
        config["md2json"]["extensions"] = []
    # Add any extensions requested from command line
    if "--extension" in args:
        config["md2json"]["extensions"].append(args["--extension"])

    if "--templatedir" in args:
        config["j2"]["templatedir"] = args["--templatedir"]
    return config


# MAIN: Dispatch to individual handlers
def main():
    logger = getLogger()
    item_types = {"article": "Item/Page/Article", "page": "Item/Page"}
    # Parse out the command and default options. Command options will be
    # parsed later.
    param = docopt(__doc__)
    config = configure(param)
    # logger.info(repr(config))

    # Prepare the output file handle
    if param['--outfile']:
        outfile = open(param['--outfile'], 'w')
    else:
        outfile = sys.stdout

    if param['new']:
        # TODO (someday) Prompt user for metadata values
        outfile.write(new_markdown(config, item_types[param[
            'ITEMTYPE'].lower()], title=param['TITLE']))

    elif param['md2json']:
        with open(param["INFILE"], encoding='utf-8') as infile:
            mtext = infile.read()

        try:
            metadict = md2archetype(config, mtext, param['--extension'])
        except jsonschema.ValidationError as e:
            # spits out a screwy error, make it more obvious
            lines = str(e).splitlines()
            message = lines.pop(0) +"\n"
            detail = "\n".join(lines) + "\n"
            logger.info(detail)
            logger.error(message)
            exit(1)

        json.dump(metadict, outfile, sort_keys=True, indent=2, cls=SmartJSONEncoder)

    elif param["j2"]:
        context = copy.deepcopy(config)
        for varfile in param['VARFILES']:
            context.update(j2.loadfile(varfile))
        outfile.write(j2.render(config, context, param["TEMPLATE"]))

    if outfile is not sys.stdout:
        outfile.close()
