#!/usr/bin/env python
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

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
import sys

# Add all required libraries to requirements.txt
with open('requirements.txt') as f:
    requirements = [line for line in f.read().split('\n') if line]

test_requirements = [
    # TODO: put package test requirements here
]

about = {}
with open("webquills/__about__.py") as fp:
    exec(fp.read(), about)

if sys.argv[-1] == 'info':
    for k, v in about.items():
        print('%s: %s' % (k, v))
    sys.exit()

with open('README.rst') as readme_file:
    readme = readme_file.read()

setup(
    name=about['__name__'],
    version=about['__version__'],
    description=about['__description__'],
    long_description=readme,
    author=about['__author__'],
    author_email=about['__author_email__'],
    url=about['__url__'],
    packages=['webquills'],
    package_dir={'webquills': 'webquills'},
    include_package_data=True,
    entry_points={'console_scripts': ['quill = webquills.quill:main']},
    install_requires=requirements,
    license=about['__license__'],
    zip_safe=False,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
