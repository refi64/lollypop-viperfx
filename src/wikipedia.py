#!/usr/bin/python
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

from locale import getdefaultlocale
import wikipedia

class Wikipedia:
    """
        Init wikipedia
    """
    def __init__(self):
        language=getdefaultlocale()[0][0:2]
        wikipedia.set_lang(language)

    """
        Get artist infos
        @param artist as str
        @return (url as str, image url as str, content as str)
    """
    def get_artist_infos(self, artist):
        if not Gio.NetworkMonitor.get_default().get_network_available():
            return (None, None, None)
        try:
            page = wikipedia.page(artist)
            content = page.content
            url = page.url
            for image in page.images:
                if image.endswith('.jpg'):
                    img = image
                    break
            return (url, img, content)
        except:
            return (None, None, None) 
