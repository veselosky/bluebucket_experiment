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
from pathlib import PurePosixPath as Path
import os

import boto3
from botocore.exceptions import ClientError

from webquills.event.s3 import Bucket, parse_aws_event


class EventDispatcher(object):

    def __init__(self, bucket_class=Bucket, logger=None):
        super().__init__()
        self.bucket_class = bucket_class
        self.logger = logger or logging.getLogger(__name__)
        self._services = {}

    def dispatch_event(self, event):
        # Load the config for the bucket to get the spectators
        logger = self.logger
        logger.info("EVENT: %s | %s" % (event.name, event.key))
        bucket = self.bucket_class(event.bucket, logger=logger)
        config = bucket.load_config()
        logger.info("Config: " + repr(config))

        # Parse the event key into its component parts
        key = Path(event.key)
        prefixes = key.parents
        categories = key.parts[:-1]
        extensions = key.suffixes
        if extensions:
            extension = ''.join(extensions)  # dots are included
            offset = 0 - len(extension)
            basename = key.name[:offset]
        else:
            extension = ''
            basename = key.name
        name = key.parent / basename

        # Look up spectators for each component
        spectators = []
        specs = config.get("spectators", {})
        spectators.extend(specs.get("key", {}).get(str(key), []))
        spectators.extend(specs.get("name", {}).get(str(name), []))
        spectators.extend(specs.get("basename", {}).get(str(basename), []))
        spectators.extend(specs.get("extensions", {}).get(extension, []))
        for prefix in prefixes:
            spectators.extend(specs.get("prefix", {}).get(str(prefix), []))
        for ext in extensions:
            spectators.extend(specs.get("extension", {}).get(str(ext), []))
        for cat in categories:
            spectators.extend(specs.get("category", {}).get(str(cat), []))

        logger.info("Spectators:" + repr(spectators))
        # Dispatch accordingly
        for spec in spectators:
            logger.info(spec["name"])
            # Before calling notify, check visibility against object's ACL
            visibility = spec.get("visibility", "public")
            if visibility.lower() == "public" and \
                    not bucket.object_is_public(event.key):
                logger.info("Skipping notification of private event")
                continue
            self.notify(spec, event)

    def service(self, name):
        if name not in self._services:
            self._services[name] = boto3.client(name)
        return self._services[name]

    def notify(self, spec, event):
        if spec["type"].lower() == "lambda":
            try:
                service = self.service("lambda")
                service.invoke(
                    FunctionName=spec["id"],
                    InvocationType="Event",
                    LogType="None",
                    Payload=event.as_json().encode("utf_8")
                )
            except ClientError as e:
                self.logger.error(str(e))

        elif spec["type"].lower() == "sns":
            try:
                service = self.service("SNS")
                service.publish(
                    TopicArn=spec["id"],
                    Message=event.as_json()
                )
            except ClientError as e:
                self.logger.error(str(e))

        elif spec["type"].lower() == "sqs":
            try:
                service = self.service("SQS")
                service.send_message(
                    QueueUrl=spec["id"],
                    MessageBody=event.as_json()
                )
            except ClientError as e:
                self.logger.error(str(e))
        else:
            self.logger.error("Unknown spec type: " + spec["type"])


# This is the function triggered by Lambda
def archive_changed(message, context):
    logger = logging.getLogger(__name__)
    level = os.environ.get("log_level", "INFO")
    logger.setLevel(level)
    events = parse_aws_event(message)
    if not events:
        logger.warn("No events found in message!\n%s" % message)
    dispatcher = EventDispatcher(logger=logger)
    for event in events:
        dispatcher.dispatch_event(event)
