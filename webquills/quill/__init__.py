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
"""
WebQuills command line interface.

Usage:
    quill new [-o OUTFILE] ITEMTYPE [TITLE]
    quill putS3redirects [-v] [-r ROOT] REDIR_FILE
    quill config [-v] (new|QUERY)
    quill setup [-v] BUCKET

Options:
    --dev                   Development mode. Ignore future publish restriction
                            and include all items.
    -o --outfile=OUTFILE    File to write output. Defaults to STDOUT.
                            If the destination file exists, it will be
                            overwritten.
    -r --root=ROOT          The destination build directory. All calculated
                            paths will be relative to this directory.
    -v --verbose            Verbose logging

"""
from pathlib import Path

import boto3
import jmespath
import yaml
from docopt import docopt
# from webquills.localfs import LocalArchivist
from webquills.mdown import md2archetype, new_markdown
from webquills import util
from webquills.event import s3


def configure(args, configfile=None):
    cfg = util.load_config(configfile)
    for key, value in args.items():
        if key.startswith("--") and value is not None:
            cfg["options"][key[2:]] = value
    return cfg


# MAIN: Dispatch to individual handlers
def main():
    param = docopt(__doc__)
    # TODO check param for explicit configfile
    configfile = util.find_config()
    if not configfile:
        answer = input("webqullls.yml not found. Create now? [Yes/No]")
        if answer.lower().startswith("y"):
            util.write_config(util.config_defaults(), "webquills.yml")
    cfg = configure(param, configfile)
    logger = util.getLogger(cfg)
    item_types = {
        "article": "Item/Page/Article",
        "page": "Item/Page",
        "catalog": "Item/Page/Catalog"
    }
    # arch = LocalArchivist(cfg)
    # schema = util.Schematist(cfg)

    if param['new']:
        # TODO (someday) Prompt user for metadata values
        doc = new_markdown(cfg, item_types[param['ITEMTYPE'].lower()],
                           title=param['TITLE'])
        # Prepare the output file handle
        if param['--outfile']:
            dest = Path(param["--outfile"])
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(doc, encoding="utf_8")
        else:
            print(doc)

    elif param["config"]:
        out = repr(cfg)
        if param["QUERY"]:
            out = repr(jmespath.search(param["QUERY"], cfg))
        out = out.strip().strip('"\'')
        print(out)

    elif param["putS3redirects"]:
        out = repr(cfg)
        if not cfg["root"].startswith("s3"):
            logger.error("Root is not an S3 bucket!")
            exit(1)
        with open(param["REDIR_FILE"]) as f:
            redirs = yaml.load(f, Loader=yaml.BaseLoader)
        aws = boto3.client('s3')
        for redir in redirs["redirects"]:
            aws.put_object(Bucket=cfg["options"]["root"],
                           Key=redir["from"],
                           WebSiteRedirect=redir["to"]
                           )
    elif param["setup"]:
        bucket = s3.Bucket(param["BUCKET"], config=cfg)
        bucket.init()
