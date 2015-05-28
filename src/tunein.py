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

import xml.etree.ElementTree as xml
import urllib.request
from locale import getdefaultlocale


class TuneItem:
    TEXT = ''
    URL = ''
    LOGO = ''


# Read radios from the web
class TuneIn:
    """
        Init tunein
    """
    def __init__(self):
        pass

    """
        Get radio entries for uri
        @param uri as string
    """
    def get_items(self, url="http://opml.radiotime.com/Browse.ashx?c="):
        headers = {"Accept-Language": getdefaultlocale()[0]}
        items = []
        if not Gio.NetworkMonitor.get_default().get_network_available():
            return items
        try:
            req = urllib.request.Request(url, None, headers)
            response = urllib.request.urlopen(req)
            root = xml.fromstring(response.read())
            for child in root.iter('outline'):
                try:
                    item = TuneItem()
                    item.URL = child.attrib['URL']
                    item.TEXT = child.attrib['text']
                    try:
                        item.LOGO = child.attrib['image']
                    except:
                        pass
                    item.TYPE = child.attrib['type']
                    items.append(item)
                except:
                    del item
        except Exception as e:
            print("TuneIn::get_radios: %s" % e)
        return items
