# Copyright (c) 2014-2017 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from gettext import gettext as _
from locale import getdefaultlocale
from random import shuffle
import re
import wikipedia

from lollypop.utils import get_network_available


class Wikipedia:
    """
        Wikipedia helper
    """

    def __init__(self):
        """
            Init wikipedia
        """
        language = getdefaultlocale()[0][0:2]
        wikipedia.set_lang(language)
        # Translators: Put here words added by wikipedia in band search
        # Ex: Muse_(band), Peaches(musician)
        # Unused be we keep this for now (as it"s already translated)
        self._search_str = _("musician;band")

    def search(self, search):
        """
            Search string on wikipedia
            @param search as str
            @return [str]
        """
        return wikipedia.search(search)

    def get_page_infos(self, name):
        """
            Get page infos
            @param page name as str
            @return (url as str, content as str)
        """
        if not get_network_available():
            return (None, None)
        page = wikipedia.page(name)
        if page is None:
            return (None, None)
        content = page.content
        content = re.sub(r"%s ==" % _("Modify"), " ==", content)
        jpegs = []
        shuffle(page.images)
        for url in page.images:
            if url.lower().endswith(".jpg"):
                jpegs.append(url)
            # Search specific string in urls
            if name.replace(" ", "_").lower() in url.lower():
                return (url, content.encode(encoding="UTF-8"))
        # If we only found one jpg, then use it
        url = None
        if jpegs:
            url = jpegs[0]
        return (url, content.encode(encoding="UTF-8"))

#######################
# PRIVATE             #
#######################
