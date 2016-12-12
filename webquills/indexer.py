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
import arrow
from webquills import util


def add_to_index(index, *args, include_future=False):
    logger = util.getLogger()
    index.setdefault("Items", {})
    now = arrow.now()
    for archetype in args:
        # Rather than validate every one against schema, just duck-type
        try:
            item = archetype["Item"]
            pub_date = arrow.get(item['published'])
            if not include_future and pub_date > now:
                logger.info("Skipping %s, future publish at %s" % (item['archetype']['href'], pub_date))
                continue
            index["Items"][item["guid"]] = item
        except KeyError:  # ignore inputs that don't conform
            pass

    index["totalResults"] = len(index["Items"])
    return index
