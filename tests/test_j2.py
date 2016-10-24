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
import webquills.j2 as j2


def test_templates_from_context():
    context = {
        "Item": {
            "itemtype": "Item/Page/Article",
            "wq_output": ["html"]
            }
        }
    result = j2.templates_from_context(context)
    assert result == {"html": ["Item_Page_Article.html.j2", "Item_Page.html.j2",
                      "Item.html.j2"]}
