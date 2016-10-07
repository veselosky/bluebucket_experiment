===========================================
webquills: Tools for making static websites
===========================================

.. image:: https://img.shields.io/pypi/v/webquills.svg
        :target: https://pypi.python.org/pypi/webquills

Quick facts::

    'Development Status :: 3 - Alpha',
    'License :: OSI Approved :: Apache Software License',
    'Programming Language :: Python :: 3 :: Only',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',

Features
========

Install the command line client `quill` to execute commands.

* quill startproject: generate a project makefile and webquills.ini
* quill new: create a new markdown file with required metadata
* quill md2json: convert markdown files to a JSON archetypes
* quill j2: render a Jinja2 template using the given JSON files as context
* quill render: render a list of JSON archetypes using auto-selected templates
* quill index: create a JSON index of the given archetype files

Naming conventions for JSON schemas:

* Itemtypes use first caps
* Use underscores as word separators, to ensure that all JSON keys are valid
  python identifiers. Otherwise they will not be easily accessible in template
  contexts. Also worth noting that python-markdown's metadata extension rejects
  entirely any keys that contain dots (but dashes work).
