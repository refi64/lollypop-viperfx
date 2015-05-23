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

from pylast import LastFMNetwork
import urllib.request
import re
import html.parser
from locale import getdefaultlocale
from _thread import start_new_thread

from lollypop.define import Lp, Type
from lollypop.utils import translate_artist_name

class LastFM(LastFMNetwork):
    _API_KEY = '7a9619a850ccf7377c46cf233c51e3c6'
    """
        Init lastfm
    """
    def __init__(self):
        LastFMNetwork.__init__(self, api_key = self._API_KEY)
        self._albums_queue = []
        self._in_albums_download = False

    """
        Download album image
        @param album id as int
    """
    def download_album_img(self, album_id):
        if Gio.NetworkMonitor.get_default().get_network_available():
            album = Lp.albums.get_name(album_id)
            artist = Lp.albums.get_artist_name(album_id)
            self._albums_queue.append((translate_artist_name(artist), album))
            if not self._in_albums_download:
                start_new_thread(self._download_albums_imgs, ())

    """
        Get artist infos
        @param artist as str
        @return (url as str, image url as str, content as str)
    """
    def get_artist_infos(self, artist):
        if not Gio.NetworkMonitor.get_default().get_network_available():
            return (None, None, None)
        artist = translate_artist_name(artist)
        try:
            last_artist = self.get_artist(artist)
            url = last_artist.get_url()
            try:
                content = last_artist.get_bio_summary(
                                           language=getdefaultlocale()[0][0:2])
            except:
                content = last_artist.get_bio_summary()
            content = re.sub(r'.*Last.fm.*', '', content)
            content = re.sub(r'<.*?>', '', content)
            image_url = last_artist.get_cover_image(3)
            return (url, image_url, html.parser.HTMLParser().unescape(content))
        except:
            return (None, None, None)
        
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
                last_album = self.get_album(artist, album)
                url = last_album.get_cover_image(4)
                if url is None:
                    continue
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
                print("LastFM::download_album_img: %s" % e)
        self._in_albums_download = False
        sql.close()
