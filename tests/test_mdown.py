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
import json
from pathlib import Path

import jsonschema
import pkg_resources
import pytest
from webquills.mdown import md2archetype
import webquills.util as util

schemafile = pkg_resources.resource_filename('webquills.schemas',
                                             'Item.json')
with open(schemafile, encoding="utf-8") as f:
    schema = json.load(f)


mdoc_nometa = """
Testing 0
=============

This is a plain old markdown doc wth no metadata.
"""

mdoc_missing_required = """---
Itemtype: Item/Page/Article
...
Testing 0.1
=============

Testing the heck out of this markdown stuff!
"""

mdoc_required_meta = """---
Itemtype: Item/Page/Article
GUID: 25cf55b5-345e-48e3-86ae-bc6c186f0fb1
Attributions:
- role: author
  name: Vince Veselosky
Copyright: 2016 Vince Veselosky
Published: 2016-09-29T18:00:00-0700
Title: A Test Article
...
Testing 1
=============

Testing the heck out of this markdown stuff!
"""

mdoc_override_defaults = """---
Itemtype: Item/Page/Article
GUID: 25cf55b5-345e-48e3-86ae-bc6c186f0fb1
Created: 2016-09-27T15:35:38
Published: 28 Sept 2016
Updated: 2016-09-29T18:00:00-0700
Copyright: 2016 Vince Veselosky
Attributions:
- role: author
  name: Vince Veselosky
Title: A Test Article
slug: i-made-this-up
...
Testing 1 2 3
=============

Testing the heck out of this markdown stuff!
"""

archetype = Path("/root/fake-to-prevent-expected-failure")
config = {"options": {"root": "/root"}, "site": {"timezone": "America/New_York"}}


def test_md2archetype_nometa():
    with pytest.raises(jsonschema.ValidationError):
        data = md2archetype(config, mdoc_nometa)
        S = util.Schematist(config)
        S.apply_defaults(data, archetype)
        data["Item"]["archetype"] = {"href": str(archetype)}
        print(repr(data))
        jsonschema.validate(data, schema)


def test_md2archetype_missing_required():
    with pytest.raises(jsonschema.ValidationError):
        data = md2archetype(config, mdoc_missing_required)
        S = util.Schematist(config)
        S.apply_defaults(data, archetype)
        data["Item"]["archetype"] = {"href": str(archetype)}
        print(repr(data))
        jsonschema.validate(data, schema)


def test_md2archetype_required_meta():
    testdata = md2archetype(config, mdoc_required_meta)
    S = util.Schematist(config)
    S.apply_defaults(testdata, archetype)
    testdata["Item"]["archetype"] = {"href": str(archetype)}
    testdata["Item"]["published"] = "2016-09-29T18:00:00-07:00"
    testdata["Item"]["updated"] = "2016-09-29T18:00:00-07:00"

    # raises ValidationError if not valid
    jsonschema.validate(testdata, schema)
    assert testdata['Item']['updated'] == testdata['Item']['published']


def test_md2archetype_override_defaults():
    testdata = md2archetype(config, mdoc_override_defaults)
    S = util.Schematist(config)
    S.apply_defaults(testdata, archetype)
    testdata["Item"]["archetype"] = {"href": str(archetype)}

    # raises ValidationError if not valid
    jsonschema.validate(testdata, schema)
    assert testdata['Item']['updated'] == "2016-09-29T18:00:00-07:00"
    assert testdata['Item']['published'] == "2016-09-28T00:00:00-04:00"
    assert testdata['Item']['slug'] == "i-made-this-up"
