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

from gi.repository import GLib, Gio, GdkPixbuf

from threading import Thread
import urllib.parse
import json

from lollypop.objects import Album
from lollypop.define import Lp, ArtSize, GOOGLE_INC


class ArtDownloader:

    def __init__(self):
        """
            Init art downloader
        """
        self._albums_queue = []
        self._in_albums_download = False

    def download_album_art(self, album_id):
        """
            Download album artwork
            @param album id as int
        """
        if Gio.NetworkMonitor.get_default().get_network_available():
            album = Lp.albums.get_name(album_id)
            artist = Lp.albums.get_artist_name(album_id)
            self._albums_queue.append((artist, album))
            if not self._in_albums_download:
                t = Thread(target=self._download_albums_art)
                t.daemon = True
                t.start()

    def get_google_arts(self, search, start=0):
        """
            Get arts on google image corresponding to search
            @param search words as string
            @param start page
            @return [urls as string]
        """
        data = None
        urls = []

        if not Gio.NetworkMonitor.get_default().get_network_available():
            return []

        try:
            f = Gio.File.new_for_uri("https://ajax.googleapis.com/"
                                     "ajax/services/search/images"
                                     "?&q=%s&v=1.0&start=%s&rsz=%s" %
                                     (urllib.parse.quote(search),
                                      start,
                                      GOOGLE_INC))
            (status, data, tag) = f.load_contents()
            if not status:
                return []
        except Exception as e:
            print(e)
            return []

        decode = json.loads(data.decode('utf-8'))
        if decode is None:
            return urls
        try:
            for item in decode['responseData']['results']:
                urls.append(item['url'])
        except:
            pass

        return urls

#######################
# PRIVATE             #
#######################
    def _download_albums_art(self):
        """
            Download albums artwork (from queue)
            @thread safe
        """
        self._in_albums_download = True
        sql = Lp.db.get_cursor()
        while self._albums_queue:
            (artist, album) = self._albums_queue.pop()
            pixbuf = self._get_album_art_spotify(artist, album)
            if pixbuf is None:
                pixbuf = self._get_album_art_itunes(artist, album)
            if pixbuf is None:
                pixbuf = self._get_album_art_lastfm(artist, album)
            if pixbuf is None:
                continue
            try:
                artist_id = Lp.artists.get_id(artist, sql)
                album_id = Lp.albums.get_id(album, artist_id, sql)
                # Compilation or album without album artist
                if album_id is None:
                    album_id = Lp.albums.get_compilation_id(album, sql)
                if album_id is not None:
                    Lp.art.save_album_artwork(pixbuf, album_id, sql)
                    Lp.art.clean_album_cache(Album(album_id), sql)
                    GLib.idle_add(Lp.art.album_artwork_update, album_id)
            except Exception as e:
                print("ArtDownloader::_download_albums_art: %s" % e)
        self._in_albums_download = False
        sql.close()

    def _get_album_art_spotify(self, artist, album):
        """
            Get album artwork from itunes
            @param artist as string
            @param album as string
            @return pixbuf as GdkPixbuf.Pixbuf
            @tread safe
        """
        pixbuf = None
        album_spotify_id = None
        try:
            album_formated = GLib.uri_escape_string(
                                album, None, True).replace(' ', '+')
            s = Gio.File.new_for_uri("https://ws.spotify.com/search/"
                                     "1/album.json?q=%s" % album_formated)
            (status, data, tag) = s.load_contents()
            if status:
                decode = json.loads(data.decode('utf-8'))
                for item in decode['albums']:
                    if item['artists'][0]['name'].lower() == artist.lower():
                        album_spotify_id = item['href'].replace(
                                    'spotify:album:', '')
                        break
            if album_spotify_id is not None:
                s = Gio.File.new_for_uri("https://api.spotify.com/"
                                         "v1/albums/%s" % album_spotify_id)
                (status, data, tag) = s.load_contents()
                if status:
                    decode = json.loads(data.decode('utf-8'))
                    url = decode['images'][0]['url']
                    s = Gio.File.new_for_uri(url)
                    (status, data, tag) = s.load_contents()
                    if status:
                        stream = Gio.MemoryInputStream.new_from_data(data,
                                                                     None)
                        pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(
                                    stream, ArtSize.MONSTER,
                                    ArtSize.MONSTER,
                                    False,
                                    None)
        except Exception as e:
            print("ArtDownloader::_get_album_art_spotify: %s" % e)
        return pixbuf

    def _get_album_art_itunes(self, artist, album):
        """
            Get album artwork from itunes
            @param artist as string
            @param album as string
            @return pixbuf as GdkPixbuf.Pixbuf
            @tread safe
        """
        pixbuf = None
        try:
            album_formated = GLib.uri_escape_string(
                                album, None, True).replace(' ', '+')
            s = Gio.File.new_for_uri("https://itunes.apple.com/search"
                                     "?entity=album&term=%s" % album_formated)
            (status, data, tag) = s.load_contents()
            if status:
                decode = json.loads(data.decode('utf-8'))
                for item in decode['results']:
                    if item['artistName'].lower() == artist.lower():
                        url = item['artworkUrl60'].replace('60x60',
                                                           '512x512')
                        s = Gio.File.new_for_uri(url)
                        (status, data, tag) = s.load_contents()
                        if status:
                            stream = Gio.MemoryInputStream.new_from_data(data,
                                                                         None)
                            pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(
                                        stream, ArtSize.MONSTER,
                                        ArtSize.MONSTER,
                                        False,
                                        None)
                        break
        except Exception as e:
            print("ArtDownloader::_get_album_art_itunes: %s" % e)
        return pixbuf

    def _get_album_art_lastfm(self, artist, album):
        """
            Get album artwork from lastfm
            @param artist as string
            @param album as string
            @return pixbuf as GdkPixbuf.Pixbuf
            @tread safe
        """
        pixbuf = None
        if Lp.lastfm is not None:
            try:
                last_album = Lp.lastfm.get_album(artist, album)
                url = last_album.get_cover_image(4)
                if url is not None:
                    s = Gio.File.new_for_uri(url)
                    (status, data, tag) = s.load_contents()
                    if status:
                        stream = Gio.MemoryInputStream.new_from_data(data,
                                                                     None)
                        pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(
                                    stream, ArtSize.MONSTER,
                                    ArtSize.MONSTER,
                                    False,
                                    None)
            except Exception as e:
                print("ArtDownloader::_get_album_art_lastfm: %s" % e)
        return pixbuf
