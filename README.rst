===============================
webquills
===============================

.. image:: https://img.shields.io/travis/veselosky/webquills.svg
        :target: https://travis-ci.org/veselosky/webquills

.. image:: https://img.shields.io/pypi/v/webquills.svg
        :target: https://pypi.python.org/pypi/webquills


Tools I use to make static websites

Features
=======================================================================

Naming conventions for JSON schemas:

* Itemtypes use first caps
* Use underscores as word separators, to ensure that all JSON keys are valid python identifiers. Otherwise they will
  not be easily accessible in template contexts. Also worth noting that python-markdown's metadata extension rejects
  entirely any keys that contain dots (but dashes work).

Task List
=======================================================================

