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

import xml.etree.ElementTree as xml

from lollypop.utils import get_network_available
from lollypop.lio import Lio


class TuneItem:
    TEXT = ""
    URL = ""
    LOGO = ""


class TuneIn:
    """
        Get radios from Tune in
    """

    def __init__(self):
        """
            Init tunein
        """
        pass

    def get_items(self, url):
        """
            Get radio entries for uri
            @param uri as string
        """
        items = []
        if not get_network_available():
            raise
        f = Lio.File.new_for_uri(url)
        (status, data, tag) = f.load_contents()
        if not status:
            raise
        root = xml.fromstring(data)
        for child in root.iter("outline"):
            try:
                item = TuneItem()
                item.URL = child.attrib["URL"]
                item.TEXT = child.attrib["text"]
                try:
                    item.LOGO = child.attrib["image"]
                except:
                    pass
                item.TYPE = child.attrib["type"]
                items.append(item)
            except:
                del item
        return items
