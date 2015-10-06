# Copyright (c) 2014-2015 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import Gio

from gettext import gettext as _
from locale import getdefaultlocale
import re
import wikipedia


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
            @return (url as str, image url as str, content as str)
        """
        if not Gio.NetworkMonitor.get_default().get_network_available():
            return (None, None, None)
        try:
            words = name.split(' ')
            page = wikipedia.page(name)
            if page is None:
                return (None, None, None)
            content = page.content
            content = re.sub(r'%s ==' % _('Modify'), ' ==', content)
            url = page.url
            for image in page.images:
                # Search specific string in urls
                for word in words:
                    if word.lower() in image.lower():
                        return (url, image, content)
            return (url, None, content)
        except Exception as e:
            print("Wikipedia::get_page_infos(): %s" % e)
            return (None, None, None)

#######################
# PRIVATE             #
#######################
