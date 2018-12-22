# Copyright (c) 2014-2018 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import GLib, Soup

import json
from base64 import b64encode

from lollypop.information_store import InformationStore
from lollypop.define import App, GOOGLE_API_ID, Type
from lollypop.define import SPOTIFY_CLIENT_ID, SPOTIFY_SECRET
from lollypop.utils import get_network_available
from lollypop.logger import Logger
from lollypop.helper_task import TaskHelper


class Downloader:
    """
        Download from the web
    """

    def __init__(self):
        """
            Init art downloader
        """
        self.__albums_queue = []
        self.__albums_history = []
        self.__in_albums_download = False
        self.__cache_artists_running = False
        InformationStore.init()

    def cache_album_art(self, album_id):
        """
            Download album artwork
            @param album id as int
        """
        if album_id in self.__albums_history:
            return
        if get_network_available():
            self.__albums_queue.append(album_id)
            if not self.__in_albums_download:
                App().task_helper.run(self.__cache_albums_art)

    def cache_artists_info(self):
        """
            Cache info for all artists
        """
        if self.__cache_artists_running:
            return
        self.__cache_artists_running = True
        App().task_helper.run(self.__cache_artists_artwork)

    def get_google_search_uri(self, search):
        """
            Get google uri for search
            @param search as str
        """
        key = App().settings.get_value("cs-api-key").get_string() or\
            App().settings.get_default_value("cs-api-key").get_string()
        uri = "https://www.googleapis.com/" +\
              "customsearch/v1?key=%s&cx=%s" % (key, GOOGLE_API_ID) +\
              "&q=%s&searchType=image" % GLib.uri_escape_string(search,
                                                                "",
                                                                False)
        return uri

    def get_google_artwork(self, content):
        """
            Get artwork from Google search content
            @param content as bytes
            @return [urls as string]
        """
        uris = []
        try:
            decode = json.loads(content.decode("utf-8"))
            if decode is None:
                return uris
            for item in decode["items"]:
                uris.append(item["link"])
        except Exception as e:
            Logger.error("Downloader::get_google_artwork(): %s, %s" %
                         (e, decode))
        return uris or None

#######################
# PROTECTED           #
#######################
    def _get_lastfm_artist_artwork_uri(self, artist):
        """
            Return lastfm artist information
            @param artist as str
            @return uri as str
        """
        if App().lastfm is not None:
            return App().lastfm.get_artist_artwork_uri(artist)
        else:
            return None

    def _get_deezer_artist_artwork_uri(self, artist):
        """
            Return deezer artist information
            @param artist as str
            @return uri as str/None
        """
        try:
            artist_formated = GLib.uri_escape_string(
                artist, None, True).replace(" ", "+")
            uri = "https://api.deezer.com/search/artist/?" +\
                  "q=%s&output=json&index=0&limit=1&" % artist_formated
            helper = TaskHelper()
            (status, data) = helper.load_uri_content_sync(uri, None)
            if status:
                decode = json.loads(data.decode("utf-8"))
                return decode["data"][0]["picture_xl"]
        except Exception as e:
            Logger.debug("Downloader::_get_deezer_artist_artwork(): %s [%s]" %
                         (e, artist))
        return None

    def _get_spotify_artist_artwork_uri(self, artist):
        """
            Return spotify artist information
            @param artist as str
            @return uri as str/None
        """
        try:
            artist_formated = GLib.uri_escape_string(
                artist, None, True).replace(" ", "+")
            uri = "https://api.spotify.com/v1/search?q=%s" % artist_formated +\
                  "&type=artist"
            token = "Bearer %s" % self.__get_spotify_token(None)
            helper = TaskHelper()
            helper.add_header("Authorization", token)
            (status, data) = helper.load_uri_content_sync(uri, None)
            if status:
                decode = json.loads(data.decode("utf-8"))
                for item in decode["artists"]["items"]:
                    if item["name"].lower() == artist.lower():
                        return item["images"][0]["url"]
        except Exception as e:
            Logger.debug("Downloader::_get_spotify_artist_artwork(): %s [%s]" %
                         (e, artist))
        return None

    def _get_deezer_album_artwork(self, artist, album):
        """
            Get album artwork from deezer
            @param artist as string
            @param album as string
            @return image as bytes
            @tread safe
        """
        image = None
        try:
            album_formated = GLib.uri_escape_string(album, None, True)
            uri = "https://api.deezer.com/search/album/?" +\
                  "q=%s&output=json" % album_formated
            helper = TaskHelper()
            (status, data) = helper.load_uri_content_sync(uri, None)
            if status:
                decode = json.loads(data.decode("utf-8"))
                uri = None
                for item in decode["data"]:
                    if item["artist"]["name"].lower() == artist.lower():
                        uri = item["cover_xl"]
                        break
                if uri is not None:
                    (status, image) = helper.load_uri_content_sync(uri, None)
        except Exception as e:
            Logger.error("Downloader::__get_deezer_album_artwork: %s" % e)
        return image

    def _get_spotify_album_artwork(self, artist, album):
        """
            Get album artwork from spotify
            @param artist as string
            @param album as string
            @return image as bytes
            @tread safe
        """
        image = None
        artists_spotify_ids = []
        try:
            token = self.__get_spotify_token(None)
            artist_formated = GLib.uri_escape_string(
                artist, None, True).replace(" ", "+")
            uri = "https://api.spotify.com/v1/search?q=%s" % artist_formated +\
                  "&type=artist"
            token = "Bearer %s" % token
            helper = TaskHelper()
            helper.add_header("Authorization", token)
            (status, data) = helper.load_uri_content_sync(uri, None)
            if status:
                decode = json.loads(data.decode("utf-8"))
                for item in decode["artists"]["items"]:
                    artists_spotify_ids.append(item["id"])

            for artist_spotify_id in artists_spotify_ids:
                uri = "https://api.spotify.com/v1/artists/" +\
                      "%s/albums" % artist_spotify_id
                (status, data) = helper.load_uri_content_sync(uri, None)
                if status:
                    decode = json.loads(data.decode("utf-8"))
                    uri = None
                    for item in decode["items"]:
                        if item["name"] == album:
                            uri = item["images"][0]["url"]
                            break
                    if uri is not None:
                        (status, image) = helper.load_uri_content_sync(uri,
                                                                       None)
                    break
        except Exception as e:
            Logger.error("Downloader::_get_album_art_spotify: %s [%s/%s]" %
                         (e, artist, album))
        return image

    def _get_itunes_album_artwork(self, artist, album):
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
                album, None, True).replace(" ", "+")
            uri = "https://itunes.apple.com/search" +\
                  "?entity=album&term=%s" % album_formated
            helper = TaskHelper()
            (status, data) = helper.load_uri_content_sync(uri, None)
            if status:
                decode = json.loads(data.decode("utf-8"))
                for item in decode["results"]:
                    if item["artistName"].lower() == artist.lower():
                        uri = item["artworkUrl60"].replace("60x60",
                                                           "512x512")
                        (status, image) = helper.load_uri_content_sync(uri,
                                                                       None)
                        break
        except Exception as e:
            Logger.error("Downloader::_get_album_art_itunes: %s [%s/%s]" %
                         (e, artist, album))
        return image

    def _get_lastfm_album_artwork(self, artist, album):
        """
            Get album artwork from lastfm
            @param artist as string
            @param album as string
            @return data as bytes
            @tread safe
        """
        image = None
        if App().lastfm is not None:
            try:
                helper = TaskHelper()
                last_album = App().lastfm.get_album(artist, album)
                uri = last_album.get_cover_image(4)
                if uri is not None:
                    (status, image) = helper.load_uri_content_sync(uri, None)
            except Exception as e:
                Logger.error("Downloader::_get_album_art_lastfm: %s [%s/%s]" %
                             (e, artist, album))
        return image

#######################
# PRIVATE             #
#######################
    def __get_spotify_token(self, cancellable):
        """
            Get a new auth token
            @param cancellable as Gio.Cancellable
            @return str
        """
        try:
            token_uri = "https://accounts.spotify.com/api/token"
            credentials = "%s:%s" % (SPOTIFY_CLIENT_ID, SPOTIFY_SECRET)
            encoded = b64encode(credentials.encode("utf-8"))
            credentials = encoded.decode("utf-8")
            session = Soup.Session.new()
            data = {"grant_type": "client_credentials"}
            msg = Soup.form_request_new_from_hash("POST", token_uri, data)
            msg.request_headers.append("Authorization",
                                       "Basic %s" % credentials)
            status = session.send_message(msg)
            if status == 200:
                body = msg.get_property("response-body")
                data = body.flatten().get_data()
                decode = json.loads(data.decode("utf-8"))
                return decode["access_token"]
        except:
            return ""

    def __cache_artists_artwork(self):
        """
            Cache artwork for all artists
        """
        # Then cache for lastfm/spotify/deezer/...
        for (artist_id, artist, sort) in App().artists.get([]):
            if not get_network_available() or\
                    InformationStore.artwork_exists(artist):
                continue
            artwork_set = False
            for (api, helper, unused) in InformationStore.WEBSERVICES:
                Logger.debug("Downloader::__cache_artists_info(): %s@%s" %
                             (artist, api))
                if helper is None:
                    continue
                try:
                    method = getattr(self, helper)
                    uri = method(artist)
                    if uri is not None:
                        (status, data) = TaskHelper().load_uri_content_sync(
                            uri,
                            None)
                        if status:
                            InformationStore.add_artist_artwork(
                                artist,
                                data)
                            artwork_set = True
                            Logger.debug("""Downloader::
                                         __cache_artists_info(): %s""" % uri)
                        else:
                            InformationStore.add_artist_artwork(
                                artist,
                                None)
                        break
                except Exception as e:
                    Logger.error("Downloader::__cache_artists_info(): %s, %s" %
                                 (e, artist))
                    InformationStore.add_artist_artwork(
                                artist,
                                None)
            if artwork_set:
                GLib.idle_add(App().art.emit, "artist-artwork-changed", artist)
        self.__cache_artists_running = False

    def __cache_albums_art(self):
        """
            Cache albums artwork (from queue)
            @thread safe
        """
        self.__in_albums_download = True
        try:
            while self.__albums_queue:
                album_id = self.__albums_queue.pop()
                album = App().albums.get_name(album_id)
                artist_ids = App().albums.get_artist_ids(album_id)
                is_compilation = artist_ids and\
                    artist_ids[0] == Type.COMPILATIONS
                if is_compilation:
                    artist = ""
                else:
                    artist = ", ".join(App().albums.get_artists(album_id))
                for (api, unused, helper) in InformationStore.WEBSERVICES:
                    if helper is None:
                        continue
                    method = getattr(self, helper)
                    data = method(artist, album)
                    if data is not None:
                        self.__albums_history.append(album_id)
                        App().art.save_album_artwork(data, album_id)
                        break
        except Exception as e:
            Logger.error("Downloader::__cache_albums_art: %s" % e)
        self.__albums_history.append(album_id)
        self.__in_albums_download = False
