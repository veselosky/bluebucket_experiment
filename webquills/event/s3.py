# vim: set fileencoding=utf-8 :
#
#   Copyright 2016-2017 Vince Veselosky and contributors
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
import logging
import re

import boto3
from botocore.exceptions import ClientError
from dateutil.parser import parse as parse_date
from pkg_resources import resource_filename as pkgfile

from webquills import util


UTF8 = "utf_8"


class Bucket(object):

    def __init__(self, name, region="us-east-1", s3=None, logger=None,
                 config=None):
        super().__init__()
        self.name = name
        self.region = region
        self.s3 = s3
        self.logger = logger
        self.config = config
        self.cfg_key = "_WQ/config.json"

        if self.s3 is None:
            self.s3 = boto3.client("s3")

        if self.logger is None:
            self.logger = logging.getLogger(__name__)

    def init(self):
        "Initialize a bucket and ensure AWS resources are up to date."
        # Create bucket if necessary
        s3 = self.s3
        logger = self.logger
        bucket = self.name

        try:
            s3.head_bucket(Bucket=bucket)
            logger.info("Bucket already exists, modifying: %s" % bucket)
        except Exception as e:
            if "404" not in str(e):
                raise
            s3.create_bucket(Bucket=bucket)
            logger.info("Creating bucket: %s" % bucket)

        # Bucket should exist now. Paint it Blue!
        logger.info("Enabling versioning for bucket: %s" % bucket)
        s3.put_bucket_versioning(
            Bucket=bucket,
            VersioningConfiguration={
                'MFADelete': 'Disabled',
                'Status': 'Enabled'
            }
        )
        logger.info("Enabling website serving for bucket: %s" % bucket)
        s3.put_bucket_website(
            Bucket=bucket,
            WebsiteConfiguration={
                'IndexDocument': {
                    'Suffix': 'index.html'
                }
            }
        )

        # PUT the config file if it does not exist
        try:
            s3.head_object(Bucket=bucket, Key=self.cfg_key)
            logger.info("Preserving existing config file.")
        except ClientError as e:
            error_code = int(e.response['Error']['Code'])
            if error_code != 404:
                raise
            logger.info("Writing config to bucket: %s" % bucket)
            self.put(key=self.cfg_key,
                     contenttype='application/json',
                     content=self.config
                     )

        # TODO PUT Schema files
        for filename in ["Item.json"]:
            key = "_WQ/schemas/" + filename
            try:
                s3.head_object(Bucket=bucket, Key=key)
            except ClientError as e:
                error_code = int(e.response['Error']['Code'])
                if error_code != 404:
                    raise
                schemafile = pkgfile('webquills.schemas', 'Item.json')
                with open(schemafile, mode='rb') as schema:
                    s3.put_object(
                        Bucket=bucket,
                        Key=key,
                        ACL="public-read",
                        ContentType='application/json',
                        Body=schema
                    )

        # TODO Create/update Lambda ArchiveChanged

        # TODO Configure Event Sources for this bucket.
        # logger.info("Adding S3 notifications for: %s" % bucket)

        # s3.put_bucket_notification_configuration(
        #     Bucket=bucket,
        #     NotificationConfiguration={
        #     }
        # )

    def put(self, key, content, contenttype=None, metadata=None,
            acl="public-read"):
        "Store an object into the archive."
        # TODO Support additional put_object args
        obj = {
            "Bucket": self.name,
            "Key": key,
            "ACL": acl
        }
        if metadata:
            obj["Metadata"] = metadata

        body = None
        what = type(content)
        if what == bytes:
            body = content
        elif what == str:
            body = what.encode(encoding=UTF8)
        else:
            body = json.dumps(content, sort_keys=True).encode(encoding=UTF8)
        obj["Body"] = body

        if contenttype is None:
            contenttype = util.guess_type(key)
        obj["ContentType"] = contenttype

        self.s3.put_object(**obj)

    def put_redirect(self, from_key, to_url):
        "Store a redirect in the archive."
        self.s3.put_object(Bucket=self.bucket,
                           Key=from_key,
                           WebsiteRedirectLocation=to_url)


#######################################################################
# S3 Events
#######################################################################
class S3event(object):
    def __init__(self, event=None, **kwargs):
        self.event = event or {"s3": {"object": {}, "bucket": {}}, }
        for key, val in kwargs.items():
            setattr(self, key, val)

    @property
    def bucket(self):
        return self.event['s3']['bucket']['name']

    @bucket.setter
    def bucket(self, newval):
        self.event['s3']['bucket']['name'] = newval

    @property
    def datetime(self):
        "The event time as a datetime object, rather than a string."
        return parse_date(self.time)

    @property
    def etag(self):
        return self.event['s3']['object']['eTag']

    @etag.setter
    def etag(self, newval):
        self.event['s3']['object']['eTag'] = newval

    @property
    def is_save_event(self):
        return 'ObjectCreated' in self.name

    @property
    def key(self):
        return self.event['s3']['object']['key']

    @key.setter
    def key(self, newval):
        self.event['s3']['object']['key'] = newval

    @property
    def name(self):
        return self.event['eventName']

    @name.setter
    def name(self, newval):
        self.event['eventName'] = newval

    @property
    def region(self):
        return self.event['awsRegion']

    @region.setter
    def region(self, newval):
        self.event['awsRegion'] = newval

    @property
    def sequencer(self):
        return self.event['s3']['object']['sequencer']

    @sequencer.setter
    def sequencer(self, newval):
        self.event['s3']['object']['sequencer'] = newval

    @property
    def source(self):
        return self.event['eventSource']

    @source.setter
    def source(self, newval):
        self.event['eventSource'] = newval

    @property
    def time(self):
        return self.event['eventTime']

    @time.setter
    def time(self, newval):
        self.event['eventTime'] = newval

    def as_json(self):
        "Returns a serialized JSON string of the S3 event"
        return json.dumps(self.event)


def parse_aws_event(message, **kwargs):
    logger = logging.getLogger(__name__)
    eventlist = message['Records']
    events = []
    for event in eventlist:
        if 'eventSource' in event and event['eventSource'] == 'aws:s3':
            events.append(S3event(event))
        elif "EventSource" in event and event['EventSource'] == "aws:sns":
            try:
                unwrapped = json.loads(event['Sns']['Message'])
                ev_list = unwrapped['Records']
            except Exception:
                logger.error(json.dumps(event))
                raise
            for ev in ev_list:
                if 'eventSource' in ev and ev['eventSource'] == 'aws:s3':
                    events.append(S3event(ev))
        else:
            # Event from elsewhere. Log it.
            logger.warn("Unrecognized event message:\n%s" %
                        json.dumps(message, sort_keys=True))
            return []

    return events

