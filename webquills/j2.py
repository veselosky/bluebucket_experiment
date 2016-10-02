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
Jinja2 template renderer.

This script will render a jinja2 template to STDOUT. The template context is
constructed from data files fed to the script.

Usage:
    j2.py [options] TEMPLATE [VARFILES...]

Options:
    -r --root ROOT          The path to the "document root" of the web site.
                            Used to calculate relative URLs.
    -t --templatedir DIR    Directory where templates are stored. TEMPLATE
                            path should be relative to this.

Other VARFILES will be merged into the top level template context. They will
be processed in order, so duplicates are last value wins.
"""
from __future__ import absolute_import, print_function, unicode_literals

import jinja2
import yaml


def loadfile(filename):
    # json is a subset of yaml, so the yaml parser can handle both! yay!
    try:
        with open(filename) as fp:
            data = yaml.load(fp)
    except yaml.scanner.ScannerError:
        raise TypeError(
            "Unrecognized file type. Data files must be JSON or YAML.")
    return data


def render(config, context, templatename):
    # TODO Hard-coded FSLoader very limiting. Allow other loaders by config.
    # Certainly we will want package loader, possibly S3 loader.
    jinja = jinja2.Environment(
        loader=jinja2.FileSystemLoader(config["j2"]["templatedir"]))
    template = jinja.get_template(templatename)
    return template.render(context)

