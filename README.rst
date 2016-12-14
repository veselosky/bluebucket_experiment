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

* [NOT IMPLEMENTED] quill startproject: generate a project makefile and webquills.ini
* quill new: create a new markdown file with required metadata
* quill build: convert markdown to JSON and render templates
* quill config: read values from webquills.yml (handly for make/shell scripts)

Naming conventions for JSON schemas:

* Itemtypes use first caps
* Use underscores as word separators, to ensure that all JSON keys are valid
  python identifiers. Otherwise they will not be easily accessible in template
  contexts. Also worth noting that python-markdown's metadata extension rejects
  entirely any keys that contain dots (but dashes work).
