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
import logging
import os

from webquills.event.s3 import Bucket, parse_aws_event
from webquills.schemas import jsonschema


def add_item(message, context):
    logger = logging.getLogger(__name__)
    level = os.environ.get("log_level", "INFO")
    logger.setLevel(level)
    events = parse_aws_event(message)
    if not events:
        logger.warn("No events found in message!\n%s" % message)
    for event in events:
        item = event["body"]
        # TODO bucket.load_config()
        bucket = Bucket(event.bucket)
        # TODO define parameter for destination key
        # TODO look up validator based on file extension.
        # FIXME should a $schema referenced in the file override config?
        # TODO retrieve the schema file
        # TODO validate item
        # TODO PUT item to bucket
