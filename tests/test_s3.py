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
from webquills.event.s3 import S3event, parse_aws_event
import stubs


###########################################################################
# Test S3event
###########################################################################

# Given a valid event struct
# When I construct S3event from it
# Then the correct properties are set
def test_s3event_construct():
    event = stubs.generate_event()['Records'][0]
    ev = S3event(event)

    assert ev.bucket == event['s3']['bucket']['name']
    assert ev.etag == event['s3']['object']['eTag']
    assert ev.key == event['s3']['object']['key']
    assert ev.name == event['eventName']
    assert ev.region == event['awsRegion']
    assert ev.sequencer == event['s3']['object']['sequencer']
    assert ev.source == event['eventSource']
    assert ev.time == event['eventTime']
    assert hasattr(ev.datetime, 'isoformat')


def test_parse_aws_event():
    message = stubs.generate_event()
    result = parse_aws_event(message)

    assert len(result) == 1
    assert type(result[0]) == S3event


def test_parse_sns_event():
    message = stubs.sns_event
    result = parse_aws_event(message)

    assert len(result) == 1
    assert type(result[0]) == S3event


def test_parse_api_gateway_event():
    message = stubs.api_gateway_proxy_event
    result = parse_aws_event(message)

    assert result[0]["body"]["test"] == "body"
