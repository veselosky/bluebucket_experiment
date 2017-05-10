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

Redirects
---------------------------

Reasons to have a redirect:

* 301 A resource has moved to a new location on the site (path changed)
* 301 A resource has moved to another site (URL changed)
* 301 The URL is a mnemonic "shortcut" for a longer URL
* 301 The URL is a common misspelling or commonly typed error
* 302 The URL is an "alias" for a resource that will change URLs over time 
  (e.g. /today vs /2017-03-13)

INVALID reasons to have a redirect:

* To serve a different resource based on device capabilities (use content
  negotiation and/or client-side composition)

So there ARE cases where you want to store a redirect at a URL that is not and
never was a true object. 

In the source repo, is it better to store these individually, or have a 
list like a redirects.json?

In FS archives, how do we handle output of redirects? Implementation of
redirects varies between platforms: S3, Apache httpd, Nginx, etc. There is no
one correct output. Apache and Nginx require redirects output to a config file
or map file, that is, aggregated together in a single file. S3 requires each 
redirect to be PUT individually to the key representing the FROM. However, since
there is no on-disk representation of this that can be uploaded using the CLI
(unless we switch to raw S3 json output), we need to have dedicated code for
uploading them.

For the "resource has moved" use cases, what are the pros/cons of storing the
moved-from URLs as metadata on the object vs as redirect data on the site?

As metadata:
* Generating redirect output is harder, because it must be collected from a
  crawl, or added to the index.
* There will me multiple places to look for redirects.
* Difficult to prevent resource-moved redirects from being duplicated in the
  site redirects list.

Is there a reason you would need to know the previous URLs for a specific
object? I can't think of one. And you could get it from a reverse index.

Okay. Implementation should be a separate redirects list.

Where to put the source?

* webquills.yml - means it will get handed to every template. Waste of memory.
* redirects.json - where to store? Is name hard-coded, or referenced from 
  config, or what?