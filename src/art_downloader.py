# Copyright (c) 2014-2016 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from threading import Thread
import json

from lollypop.cache import InfoCache
from lollypop.define import Lp
from lollypop.utils import debug


class ArtDownloader:
    """
        Download artwork from the web
    """
    try:
        from lollypop.wikipedia import Wikipedia
    except:
        Wikipedia = None

    _KEY = "AIzaSyBiaYluG8pVYxgKRGcc4uEbtgE9q8la0dw"
    _ID = "015987506728554693370:waw3yqru59a"

    def __init__(self):
        """
            Init art downloader
        """
        self._albums_queue = []
        self._albums_history = []
        self._in_albums_download = False
        self._cache_artists_running = False

    def download_album_art(self, album_id):
        """
            Download album artwork
            @param album id as int
        """
        if album_id in self._albums_history:
            return
        if Gio.NetworkMonitor.get_default().get_network_available():
            self._albums_queue.append(album_id)
            if not self._in_albums_download:
                t = Thread(target=self._download_albums_art)
                t.daemon = True
                t.start()

    def cache_artists_art(self):
        """
            Cache artwork for all artists
        """
        if self._cache_artists_running:
            return
        self._cache_artists_running = True
        t = Thread(target=self._cache_artists_art)
        t.daemon = True
        t.start()

    def get_google_arts(self, search):
        """
            Get arts on duck image corresponding to search
            @param search words as string
            @return [urls as string]
        """
        data = None
        urls = []

        if not Gio.NetworkMonitor.get_default().get_network_available():
            return []

        cs_api_key = Lp().settings.get_value('cs-api-key').get_string()
        if cs_api_key == "":
            cs_api_key = self._KEY

        try:
            f = Gio.File.new_for_uri("https://www.googleapis.com/"
                                     "customsearch/v1?key=%s&cx=%s"
                                     "&q=%s&searchType=image" %
                                     (cs_api_key,
                                      self._ID,
                                      GLib.uri_escape_string(search,
                                                             "",
                                                             False)))

            (status, data, tag) = f.load_contents()
            if not status:
                return []
        except Exception as e:
            print(e)
            return []
        try:
            decode = json.loads(data.decode('utf-8'))
            if decode is None:
                return urls
            for item in decode['items']:
                urls.append(item['link'])
        except:
            pass

        return urls

#######################
# PRIVATE             #
#######################
    def _get_spotify_artist_artwork(self, artist):
        """
            Return spotify artwork url
            @param artist as str
            @return url as str/None
        """
        try:
            artist_formated = GLib.uri_escape_string(
                                artist, None, True).replace(' ', '+')
            s = Gio.File.new_for_uri("https://api.spotify.com/v1/search?q=%s"
                                     "&type=artist" % artist_formated)
            (status, data, tag) = s.load_contents()
            if status:
                decode = json.loads(data.decode('utf-8'))
                for item in decode['artists']['items']:
                    if item['name'].lower() == artist.lower():
                        return item['images'][0]['url']
        except Exception as e:
            debug("ArtDownloader::get_spotify_artist_artwork(): %s [%s]" %
                  (e, artist))
        return None

    def _cache_artists_art(self):
        """
            Cache artwork for all artists
        """
        # We create cache if needed
        InfoCache.init()
        # Then cache artwork for lastfm/wikipedia/spotify
        # We cache content as the same time
        # TODO Make this code more generic
        for (artist_id, artist) in Lp().artists.get([]):
            debug("ArtDownloader::_cache_artists_art(): %s" % artist)
            artwork_set = False
            if not Gio.NetworkMonitor.get_default().get_network_available() or\
                    InfoCache.exists_in_cache(artist):
                continue
            if Lp().lastfm is not None:
                try:
                    (url, content) = Lp().lastfm.get_artist_infos(artist)
                    if url is not None:
                        s = Gio.File.new_for_uri(url)
                        (status, data, tag) = s.load_contents()
                        if status:
                            artwork_set = True
                            InfoCache.cache(artist, content, data, "lastfm")
                        else:
                            InfoCache.cache(artist, None, None, "lastfm")
                except:
                    InfoCache.cache(artist, None, None, "lastfm")
            if ArtDownloader.Wikipedia is not None:
                try:
                    wp = ArtDownloader.Wikipedia()
                    (url, content) = wp.get_page_infos(artist)
                    if url is not None:
                        s = Gio.File.new_for_uri(url)
                        (status, data, tag) = s.load_contents()
                        if status:
                            artwork_set = True
                            InfoCache.cache(artist, content, data, "wikipedia")
                        else:
                            InfoCache.cache(artist, None, None, "wikipedia")
                except:
                    InfoCache.cache(artist, None, None, "wikipedia")
            url = self._get_spotify_artist_artwork(artist)
            if url is not None:
                s = Gio.File.new_for_uri(url)
                (status, data, tag) = s.load_contents()
                if status:
                    artwork_set = True
                    InfoCache.cache(artist, None, data, "spotify")
                else:
                    InfoCache.cache(artist, None, None, "spotify")
            if artwork_set:
                Lp().art.emit('artist-artwork-changed', artist)
        self._cache_artists_running = False

    def _download_albums_art(self):
        """
            Download albums artwork (from queue)
            @thread safe
        """
        self._in_albums_download = True
        while self._albums_queue:
            album_id = self._albums_queue.pop()
            album = Lp().albums.get_name(album_id)
            artist = ", ".join(Lp().albums.get_artists(album_id))
            data = self._get_album_art_spotify(artist, album)
            if data is None:
                data = self._get_album_art_itunes(artist, album)
            if data is None:
                data = self._get_album_art_lastfm(artist, album)
            if data is None:
                self._albums_history.append(album_id)
                continue
            try:
                    Lp().art.save_album_artwork(data, album_id)
            except Exception as e:
                print("ArtDownloader::_download_albums_art: %s" % e)
                self._albums_history.append(album_id)
        self._in_albums_download = False

    def _get_album_art_spotify(self, artist, album):
        """
            Get album artwork from itunes
            @param artist as string
            @param album as string
            @return image as bytes
            @tread safe
        """
        image = None
        artists_spotify_ids = []
        try:
            artist_formated = GLib.uri_escape_string(
                                artist, None, True).replace(' ', '+')
            s = Gio.File.new_for_uri("https://api.spotify.com/v1/search?q=%s"
                                     "&type=artist" % artist_formated)
            (status, data, tag) = s.load_contents()
            if status:
                decode = json.loads(data.decode('utf-8'))
                for item in decode['artists']['items']:
                    artists_spotify_ids.append(item['id'])

            for artist_spotify_id in artists_spotify_ids:
                s = Gio.File.new_for_uri("https://api.spotify.com/v1/artists/"
                                         "%s/albums" % artist_spotify_id)
                (status, data, tag) = s.load_contents()
                if status:
                    decode = json.loads(data.decode('utf-8'))
                    url = None
                    for item in decode['items']:
                        if item['name'] == album:
                            url = item['images'][0]['url']
                            break

                    if url is not None:
                        s = Gio.File.new_for_uri(url)
                        (status, image, tag) = s.load_contents()
                    break
        except Exception as e:
            print("ArtDownloader::_get_album_art_spotify: %s [%s/%s]" %
                  (e, artist, album))
        return image

    def _get_album_art_itunes(self, artist, album):
        """
            Get album artwork from itunes
            @param artist as string
            @param album as string
            @return image as bytes
            @tread safe
        """
        image = None
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
                        (status, image, tag) = s.load_contents()
                        break
        except Exception as e:
            print("ArtDownloader::_get_album_art_itunes: %s [%s/%s]" %
                  (e, artist, album))
        return image

    def _get_album_art_lastfm(self, artist, album):
        """
            Get album artwork from lastfm
            @param artist as string
            @param album as string
            @return data as bytes
            @tread safe
        """
        image = None
        if Lp().lastfm is not None:
            try:
                last_album = Lp().lastfm.get_album(artist, album)
                url = last_album.get_cover_image(4)
                if url is not None:
                    s = Gio.File.new_for_uri(url)
                    (status, image, tag) = s.load_contents()
            except Exception as e:
                print("ArtDownloader::_get_album_art_lastfm: %s [%s/%s]" %
                      (e, artist, album))
        return image
