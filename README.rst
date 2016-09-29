===============================
webquills
===============================

.. image:: https://img.shields.io/travis/veselosky/webquills.svg
        :target: https://travis-ci.org/veselosky/webquills

.. image:: https://img.shields.io/pypi/v/webquills.svg
        :target: https://pypi.python.org/pypi/webquills


Tools I use to make static websites.

Features
=======================================================================

Install the command line client `quill` to execute commands.

* quill startproject: generate a project makefile and webquills.ini
* quill new: create a new markdown file with required metadata
* quill md2json: convert a markdown file to a JSON archetype
* quill j2: render a Jinja2 template using the given JSON files as context
* quill indexitems: create a JSON index of the given archetype files

Naming conventions for JSON schemas:

* Itemtypes use first caps
* Use underscores as word separators, to ensure that all JSON keys are valid python identifiers. Otherwise they will
  not be easily accessible in template contexts. Also worth noting that python-markdown's metadata extension rejects
  entirely any keys that contain dots (but dashes work).

Task List
=======================================================================

[ ] Implement quill startproject to bootstrap makefile and webquills.ini
[ ] Implement quill j2 to render templates
[ ] Implement quill indexitems to create json index
