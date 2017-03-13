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

Usage
======
WebQuills command line interface.

::

    Usage:
        quill new [-o OUTFILE] ITEMTYPE [TITLE]
        quill build [-r ROOT] [-t DIR] [-s SRCDIR] [--dev]
        quill config [-r ROOT] [-t DIR] [-s SRCDIR] [QUERY]

    Options:
        --dev                   Development mode. Ignore future publish restriction
                                and include all items.
        -o --outfile=OUTFILE    File to write output. Defaults to STDOUT.
                                If the destination file exists, it will be
                                overwritten.
        -r --root=ROOT          The destination build directory. All calculated
                                paths will be relative to this directory.
        -s --source=SRCDIR      The directory from which to read source files
                                (markdown, etc.)
        -t --templatedir=DIR    Directory where templates are stored. TEMPLATE
                                path should be relative to this.
        -v --verbose            Verbose logging


Features
=======================================================================

The quill new command can be used to generate a skeleton markdown file for
various item types.

The quill build command converts your markdown files to HTML.


Task List
=======================================================================

* [ ] Implement redirect objects or rules
* [ ] Implement quill startproject to bootstrap webquills.yml


Thinking Out Loud
=================

Generally one project == one web site.

A web site may need to include things other than the content archive. Things:

* The archive itself (with all tracked resources)
* Server configurations for a web server (Apache configs)
* Redirect rules or extra metadata for S3 (e.g. Content-Encoding)
* Static assets used with the Theme (CSS, JS, theme images, fonts)
* Templates used for generating HTML or other representations
* Makefile and other build-related artifacts

Principles:

* Theme files should be kept separate from content files, so that themes can be
  pluggable. The build process will need to merge theme files into the archive.
* Templates MAY be included in the git repo with the content archive, but may
  also be pulled from Python packages or other external sources.
* Server configurations should never be part of the content archive, but may
  need to be stored in the source repo.

Suggested project layout::

    Makefile
    requirements.txt
    README.md
    webquills.ini
    content/
    config/
    templates/
    theme/

Naming conventions for JSON schemas:

* Itemtypes use first caps
* Use underscores as word separators, to ensure that all JSON keys are valid
  python identifiers. Otherwise they will not be easily accessible in template
  contexts. Also worth noting that python-markdown's metadata extension rejects
  entirely any keys that contain dots (but dashes work).
