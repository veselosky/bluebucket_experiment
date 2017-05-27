# vim: set fileencoding=utf-8 :
#
#   Copyright 2017 Vince Veselosky and contributors
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
from pkg_resources import resource_filename as pkgfile
from unittest import mock

import stubs
from webquills.event.s3 import parse_aws_event
from webquills.lambdas.archivechanged import EventDispatcher


#############################################################################
# Test is_sequence
#############################################################################
def test_event_dispatcher():
    cfgfile = pkgfile("webquills.schemas", "Config.example.json")
    with open(cfgfile) as f:
        cfg = json.load(f)

    bucket = mock.Mock()
    bucket.load_config.return_value = cfg
    bucketclass = mock.Mock(return_value=bucket)
    ev = EventDispatcher(bucket_class=bucketclass)
    ev.notify = mock.Mock()

    raw_event = stubs.generate_event(key="cat1/cat2/example.itempage.json")

    for event in parse_aws_event(raw_event):
        ev.dispatch_event(event)
    assert ev.notify.call_count == 10
