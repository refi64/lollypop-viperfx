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

from gi.repository import GObject

import urllib.request
import urllib.parse
import json

from lollypop.define import Lp


class LastFM:
    _API = '7a9619a850ccf7377c46cf233c51e3c6'
    __gsignals__ = {
        'artist-img': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }
    """
        Init lastfm
    """
    def __init__(self):
        pass

    """
        Download artist image
        @param artist as string
    """
    def download_artist_img(self, artist):
        try:
            response = urllib.request.urlopen(
                                        "http://ws.audioscrobbler.com/2.0/?"
                                        "method=artist.getinfo&api_key="
                                        "7a9619a850ccf7377c46cf233c51e3c6"
                                        "&artist=%s&format=json" %\
                                         urllib.parse.quote(artist))
        except Exception as e:
            print("LastFM::download_artist_img: %s" % e)
            return
        print('ici')
        data = response.read()
        decode = json.loads(data.decode("utf-8"))
        if decode is None:
            return
        try:
            url = decode['artist']['image'][3]['#text']
            Lp.art.add_artist_img_to_cache(artist, url)
        except Exception as e:
            print("LastFM::download_artist_img: %s" % e)
