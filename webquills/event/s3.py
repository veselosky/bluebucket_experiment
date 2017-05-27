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
from webquills.__about__ import __version__

UTF8 = "utf_8"
FunctionName = "WQArchiveChanged"
RoleName = "WQArchivistRole"
AssumeRolePolicyDocument = '''{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
'''


class Bucket(object):

    def __init__(self, name, region="us-east-1", s3=None, logger=None,
                 config=None, services=None):
        super().__init__()
        self.name = name
        self.region = region
        self._account = None
        self.services = services or {}
        self.logger = logger
        self.config = config
        self.cfg_key = "_WQ/config.json"
        if s3:
            self.services["s3"] = s3

        if self.logger is None:
            self.logger = logging.getLogger(__name__)

    @property
    def arn(self):
        return "arn:aws:s3:::" + self.name

    @property
    def account(self):
        if not self._account:
            # There's no direct way to discover the account id, but it is part of
            # the ARN of the user, so we get the current user and parse it out.
            iam = self.get_service('iam')
            resp = iam.get_user()
            # 'arn:aws:iam::128119582937:user/vince'
            m = re.match(r'arn:aws:iam::(\d+):.*', resp["User"]["Arn"])
            self._account = m.group(1)
        return self._account

    def get_service(self, servicename):
        if servicename not in self.services:
            self.services[servicename] = boto3.client(servicename)
        return self.services[servicename]

    def init(self):
        "Initialize a bucket and ensure AWS resources are up to date."
        # Create bucket if necessary
        s3 = self.get_service("s3")
        logger = self.logger
        bucket = self.name

        try:
            s3.head_bucket(Bucket=bucket)
            logger.info("Bucket already exists, modifying: %s" % bucket)
        except ClientError as e:
            error_code = int(e.response['Error']['Code'])
            if error_code != 404:
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

        # PUT Schema files
        logger.info("Checking for standard schema files: %s" % bucket)
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

        # Grant S3 permission to invoke ArchiveChanged
        # NOTE (LOL) DO NOT have to grant permission on all spectator functions!
        # They are invoked by a Lambda, not by S3!
        logger.info("Granting Lambda execute privilege for S3: %s" % bucket)
        idthing = FunctionName + self.name.replace('.', '_')  # no dots :(
        lam = self.get_service("lambda")
        try:
            # ARGH: get_function returns a different struct than create_function
            # Create returns the "Configuration" part as the root, no Code
            # To make them match, we unwrap the Configuration
            func = lam.get_function(FunctionName=FunctionName)["Configuration"]
        except lam.exceptions.ResourceNotFoundException as e:
            logger.error("Lambda function not found. Attempting to install.")
            func = self.make_lambdas()

        try:
            lam.add_permission(
                FunctionName=FunctionName,
                StatementId=idthing,
                Action="lambda:InvokeFunction",
                Principal="s3.amazonaws.com",
                SourceArn=self.arn,
                SourceAccount=self.account
            )
        except lam.exceptions.ResourceConflictException as e:
            # Statement already created. Assume it's the right one. :/
            pass

        # Configure Event Sources for this bucket.
        logger.info("Adding S3 notifications for: %s" % bucket)
        s3.put_bucket_notification_configuration(
            Bucket=bucket,
            NotificationConfiguration={
                "LambdaFunctionConfigurations": [
                    {
                        "Id": idthing,
                        "LambdaFunctionArn": func["FunctionArn"],
                        "Events": ["s3:ObjectCreated:*", "s3:ObjectRemoved:*"]
                    }
                ]
            }
        )

    def make_lambdas(self, upgrade=False):
        "Install Lambda functions to account"
        # Need to create the role, then the function
        iam = self.get_service("iam")
        lam = self.get_service("lambda")
        logger = self.logger
        logger.info("Establishing Lambda role")
        try:
            role = iam.get_role(RoleName=RoleName)
        except iam.exceptions.NoSuchEntityException as e:
            role = iam.create_role(
                RoleName=RoleName,
                AssumeRolePolicyDocument=AssumeRolePolicyDocument
            )
        logger.debug("Lambda role: " + repr(role))
        # READ-WRITE ACCESS to ALL S3 buckets!
        # KISS: Naming the policy is hard if it is per-bucket. Bucket names can
        # be longer than policy names. If you are worried about accidentally
        # touching unmanaged buckets, use a separate AWS account for Webquills!
        # TODO Add permissions for SQS, SNS
        logger.info("Establishing Lambda role policy")
        iam.put_role_policy(
            RoleName=role["Role"]["RoleName"],
            PolicyName="WQLambdaS3ReadWriteAll",
            PolicyDocument="""{
                "Statement": [
                    {
                        "Action": [
                            "logs:CreateLogGroup",
                            "logs:CreateLogStream",
                            "logs:PutLogEvents"
                        ],
                        "Effect": "Allow",
                        "Resource": "arn:aws:logs:*:*:*"
                    },
                    {
                        "Action": [
                            "s3:*"
                        ],
                        "Effect": "Allow",
                        "Resource": [
                            "arn:aws:s3:::*"
                        ]
                    }
                ]
            }"""
        )

        # Find or create ArchiveChanged function
        try:
            func = lam.get_function(FunctionName=FunctionName)
            ArchiveChanged = func["Configuration"]
            if upgrade:
                logger.info("Upgrading existing Lambda WQArchiveChanged")
                lam.update_function_code(
                    FunctionName=ArchiveChanged["FunctionName"],
                    S3Bucket="dist.webquills.net",
                    S3Key=__version__ + '/lambda-archivechanged.zip',
                    Publish=True
                )

        except lam.exceptions.ResourceNotFoundException as e:
            ArchiveChanged = lam.create_function(
                FunctionName=FunctionName,
                Runtime="python3.6",
                Role=role["Role"]["Arn"],
                Handler="webquills.archive_changed",
                Code={
                    "S3Bucket": "dist.webquills.net",
                    "S3Key": __version__ + '/lambda-archivechanged.zip'
                },
                Description="ArchiveChanged is called by S3",
                Timeout=3,
                MemorySize=128,
                Publish=True
            )

        return ArchiveChanged

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

        self.get_service("s3").put_object(**obj)

    def put_redirect(self, from_key, to_url):
        "Store a redirect in the archive."
        self.get_service("s3").put_object(Bucket=self.bucket,
                                          Key=from_key,
                                          WebsiteRedirectLocation=to_url)

    def load_config(self):
        s3 = self.get_service("s3")
        resp = s3.get_object(Bucket=self.name, Key=self.cfg_key)
        # NOTE: In Python 3.6+ loads allows bytes as well, but just being safe
        text = resp["Body"].read().decode("utf_8")
        config = json.loads(text)
        if self.config is None:
            self.config = config
        return config

    def object_is_public(self, key):
        s3 = self.get_service("s3")
        try:
            meta = s3.get_object_acl(Bucket=self.name, Key=key)
        except s3.exceptions.NoSuchKey as e:
            return False
        for grant in meta["Grants"]:
            grantee = grant["Grantee"].get("URI", "")
            if "AllUsers" in grantee and grant["Permission"] == "READ":
                return True
        return False


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
        return json.dumps({"Records": [self.event]})


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

