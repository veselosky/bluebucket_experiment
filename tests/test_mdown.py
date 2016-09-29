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
from __future__ import absolute_import, print_function, unicode_literals
import pkg_resources
import json
import jsonschema
import pytest
from webquills.quill.mdown import md2archetype, new_markdown

schemafile = pkg_resources.resource_filename('webquills.schemas',
                                             'Item.json')
with open(schemafile, encoding="utf-8") as f:
    schema = json.load(f)


mdoc_nometa = """
Testing 0
=============

This is a plain old markdown doc wth no metadata.
"""

mdoc_missing_required = """Itemtype: Item/Page/Article
Author: Vince Veselosky
Title: A Test Article

Testing 0.1
=============

Testing the heck out of this markdown stuff!
"""

mdoc_required_meta = """Itemtype: Item/Page/Article
GUID: 25cf55b5-345e-48e3-86ae-bc6c186f0fb1
Author: Vince Veselosky
Copyright: 2016 Vince Veselosky
Published: 2016-09-29T18:00:00
Title: A Test Article

Testing 1
=============

Testing the heck out of this markdown stuff!
"""

mdoc_override_defaults = """Itemtype: Item/Page/Article
GUID: 25cf55b5-345e-48e3-86ae-bc6c186f0fb1
Created: 2016-09-27T15:35:38
Published: 28 Sept 2016
Updated: 2016-09-29T18:00:00
Copyright: 2016 Vince Veselosky
Author: Vince Veselosky
Title: A Test Article
slug: i-made-this-up

Testing 1 2 3
=============

Testing the heck out of this markdown stuff!
"""


def test_md2archetype_nometa():
    with pytest.raises(jsonschema.ValidationError):
        md2archetype({}, mdoc_nometa)


def test_md2archetype_missing_required():
    with pytest.raises(jsonschema.ValidationError):
        md2archetype({}, mdoc_missing_required)


def test_md2archetype_required_meta():
    testdata = md2archetype({}, mdoc_required_meta)

    # raises ValidationError if not valid
    jsonschema.validate(testdata, schema)
    assert testdata['Item']['updated'] == testdata['Item']['published']


def test_md2archetype_override_defaults():
    testdata = md2archetype({"site": {"timezone": "America/New_York"}},
                            mdoc_override_defaults)

    # raises ValidationError if not valid
    jsonschema.validate(testdata, schema)
    assert testdata['Item']['updated'] == "2016-09-29T18:00:00-04:00"
    assert testdata['Item']['published'] == "2016-09-28T00:00:00-04:00"
    assert testdata['Item']['slug'] == "i-made-this-up"
