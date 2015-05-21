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

from gi.repository import GLib, Gio

import urllib.request
import urllib.parse
import json
from _thread import start_new_thread

from lollypop.define import Lp, Type


class LastFM:
    _API = '7a9619a850ccf7377c46cf233c51e3c6'
    """
        Init lastfm
    """
    def __init__(self):
        self._albums_queue = []
        self._in_albums_download = False
        self._artists_queue = []

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
        data = response.read()
        decode = json.loads(data.decode("utf-8"))
        if decode is None:
            return
        try:
            url = decode['artist']['image'][3]['#text']
            #Lp.art.add_artist_img_to_cache(artist, url)
        except Exception as e:
            print("LastFM::download_artist_img: %s" % e)

    """
        Download album image
        @param album id as int
    """
    def download_album_img(self, album_id):
        if Gio.NetworkMonitor.get_default().get_network_available():
            album = Lp.albums.get_name(album_id)
            artist = Lp.albums.get_artist_name(album_id)
            self._albums_queue.append((artist, album))
            if not self._in_albums_download:
                start_new_thread(self._download_albums_imgs, ())

#######################
# PRIVATE             #
#######################
    """
        Download albums images
    """
    def _download_albums_imgs(self):
        self._in_albums_download = True
        sql = Lp.db.get_cursor()
        while self._albums_queue:
            (artist, album) = self._albums_queue.pop()
            try:
                response = urllib.request.urlopen(
                                            "http://ws.audioscrobbler.com/2.0/?"
                                            "method=album.getinfo&api_key="
                                            "7a9619a850ccf7377c46cf233c51e3c6"
                                            "&artist=%s&album=%s&format=json" %\
                                             (urllib.parse.quote(artist),
                                              urllib.parse.quote(album)))
            except Exception as e:
                print("LastFM::download_artist_img1: %s" % e)
                continue
            data = response.read()
            decode = json.loads(data.decode("utf-8"))
            if decode is None:
                continue
            try:
                url = decode['album']['image'][4]['#text']
                artist_id = Lp.artists.get_id(artist, sql)
                album_id = Lp.albums.get_id(album, artist_id, sql)
                # Compilation or album without album artist
                if album_id is None:
                    album_id = Lp.albums.get_compilation_id(album, sql)
                # Do not write files outside collection
                if not Lp.albums.is_outside(album_id, sql):
                    filepath = Lp.art.get_album_art_filepath(album_id, sql)
                    urllib.request.urlretrieve(url, filepath)
                    Lp.art.clean_album_cache(album_id, sql)
                    GLib.idle_add(Lp.art.announce_cover_update, album_id)
            except Exception as e:
                print("LastFM::download_artist_img2: %s" % e)
        self._in_albums_download = False
        sql.close()
