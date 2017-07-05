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

from gi.repository import GLib, Gio, Soup

import json
from base64 import b64encode
from time import time

from lollypop.search_item import SearchItem
from lollypop.lio import Lio
from lollypop.utils import debug
from lollypop.define import SPOTIFY_CLIENT_ID, SPOTIFY_SECRET


class SpotifySearch:
    """
        Search provider for Spotify
    """
    __EXPIRES = 0
    __TOKEN = None

    def get_token(cancellable):
        """
            Get a new auth token
            @param cancellable as Gio.Cancellable
            @return str
        """
        # Remove 60 seconds to be sure
        if int(time()) + 60 < SpotifySearch.__EXPIRES and\
                SpotifySearch.__TOKEN is not None:
            debug("Use spotify token: %s" % SpotifySearch.__TOKEN)
            return SpotifySearch.__TOKEN
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
                SpotifySearch.__EXPIRES = int(time()) +\
                    int(decode["expires_in"])
                SpotifySearch.__TOKEN = decode["access_token"]
                return SpotifySearch.__TOKEN
        except:
            return ""

    def __init__(self):
        """
            Init provider
        """
        self.__token = SpotifySearch.get_token(None)
        if not hasattr(self, "_cancel"):
            self._cancel = Gio.Cancellable.new()

    def tracks(self, name):
        """
            Return tracks containing name
            @param name as str
        """
        try:
            formated = GLib.uri_escape_string(name, None, True).replace(
                                                                      " ", "+")
            s = Lio.File.new_for_uri("https://api.spotify.com/v1/search?q=%s"
                                     "&type=track" % formated)
            s.add_spotify_headers(self.__token)
            (status, data, tag) = s.load_contents(self._cancel)
            if status:
                decode = json.loads(data.decode("utf-8"))
                tracks = []
                for item in decode["tracks"]["items"]:
                    if item["name"].lower() in tracks:
                        continue
                    album_item = SearchItem()
                    search_item = SearchItem()
                    search_item.is_track = True
                    search_item.name = item["name"]
                    album_item.name = item["name"]
                    search_item.album = album_item
                    tracks.append(search_item.name.lower())
                    search_item.tracknumber = int(item["track_number"])
                    search_item.discnumber = int(item["disc_number"])
                    search_item.duration = int(item["duration_ms"]) / 1000
                    search_item.cover = item["album"]["images"][0]["url"]
                    search_item.smallcover = item["album"]["images"][2]["url"]
                    for artist in item["artists"]:
                        search_item.artists.append(artist["name"])
                    self._items.append(search_item)
                    GLib.idle_add(self.emit, "item-found")
        except Exception as e:
            print("SpotifySearch::tracks(): %s" % e)

    def albums(self, name):
        """
            Return albums containing name
            @param name as str
            @return albums as [SearchItem]
        """
        self.__get_artists(name)
        self.__get_albums(name)

    def get_album_id(self, track_id):
        """
            Get album id for track
            @param track id as str
            @return album id as str
        """
        try:
            s = Lio.File.new_for_uri("https://api.spotify.com/v1/"
                                     "tracks/%s" % track_id)
            s.add_spotify_headers(self.__token)
            (status, data, tag) = s.load_contents(self._cancel)
            if status:
                decode = json.loads(data.decode("utf-8"))
                return decode["album"]["id"]
        except Exception as e:
            print("SpotifySearch::get_album_id():", e, track_id)

    def get_album(self, album_id):
        """
            Return spotify album as SearchItem
            @param album id as str
            @return SearchItem
        """
        try:
            s = Lio.File.new_for_uri("https://api.spotify.com/v1/"
                                     "albums/%s" % album_id)
            s.add_spotify_headers(self.__token)
            (status, data, tag) = s.load_contents(self._cancel)
            if status:
                decode = json.loads(data.decode("utf-8"))
                album_item = SearchItem()
                album_item.name = decode["name"]
                album_item.cover = decode["images"][0]["url"]
                album_item.smallcover = decode["images"][2]["url"]
                album_item.ex_id = album_id
                for item in decode["tracks"]["items"]:
                    track_item = SearchItem()
                    track_item.is_track = True
                    track_item.name = item["name"]
                    track_item.album = album_item.name
                    try:
                        track_item.year = decode[
                                                "release_date"][:4]
                    except:
                        pass  # May be missing
                    track_item.tracknumber = int(
                                              item["track_number"])
                    track_item.discnumber = int(
                                               item["disc_number"])
                    track_item.duration = int(
                                        item["duration_ms"]) / 1000
                    for artist in item["artists"]:
                        track_item.artists.append(artist["name"])
                    if not album_item.artists:
                        album_item.artists = track_item.artists
                    album_item.subitems.append(track_item)
                return album_item
        except Exception as e:
            print("SpotifySearch::get_album:", e)
        return None

    def get_track(self, track_id):
        """
            Return spotify track as SearchItem
            @param track id as str
            @return SearchItem
        """
        try:
            s = Lio.File.new_for_uri("https://api.spotify.com/v1/"
                                     "tracks/%s" % track_id)
            s.add_spotify_headers(self.__token)
            (status, data, tag) = s.load_contents(self._cancel)
            if status:
                decode = json.loads(data.decode("utf-8"))
                album_item = SearchItem()
                album_item.name = decode["album"]["name"]
                album_item.cover = decode["album"]["images"][0]["url"]
                album_item.smallcover = decode["album"]["images"][2]["url"]

                track_item = SearchItem()
                track_item.is_track = True
                track_item.name = decode["name"]
                track_item.album = album_item
                track_item.tracknumber = int(
                                          decode["track_number"])
                track_item.discnumber = int(
                                           decode["disc_number"])
                track_item.duration = int(
                                    decode["duration_ms"]) / 1000
                for artist in decode["artists"]:
                    track_item.artists.append(artist["name"])
                album_item.artists = track_item.artists
                album_item.subitems.append(track_item)
                return album_item
        except Exception as e:
            print("SpotifySearch::get_track", e)
        return None

#######################
# PRIVATE             #
#######################
    def __get_artists(self, name):
        """
            Get albums for artists name
            @param name as str
        """
        try:
            # Read album list
            formated = GLib.uri_escape_string(name, None, True).replace(
                                                                      " ", "+")
            s = Lio.File.new_for_uri("https://api.spotify.com/v1/search?q=%s"
                                     "&type=artist" % formated)
            s.add_spotify_headers(self.__token)
            (status, data, tag) = s.load_contents(self._cancel)
            if status:
                decode = json.loads(data.decode("utf-8"))
                # For each album, get cover and tracks
                artists = []
                for item in decode["artists"]["items"]:
                    album_items = []
                    artist_id = item["id"]
                    if item["name"].lower() in artists:
                        continue
                    artists.append(item["name"].lower())
                    s = Lio.File.new_for_uri("https://api.spotify.com/"
                                             "v1/artists/%s/albums" %
                                             artist_id)
                    s.add_spotify_headers(self.__token)
                    (status, data, tag) = s.load_contents(self._cancel)
                    if status:
                        decode = json.loads(data.decode("utf-8"))
                        albums = []
                        for item in decode["items"]:
                            if item["name"].lower() in albums:
                                continue
                            album_item = SearchItem()
                            album_item.name = item["name"]
                            albums.append(album_item.name.lower())
                            album_item.cover = item["images"][0]["url"]
                            album_item.smallcover = item["images"][2]["url"]
                            album_items.append(album_item)
                            album_item.ex_id = item["id"]

                    for album_item in album_items:
                        s = Lio.File.new_for_uri("https://api.spotify.com/v1/"
                                                 "albums/%s" %
                                                 album_item.ex_id)
                        s.add_spotify_headers(self.__token)
                        (status, data, tag) = s.load_contents(self._cancel)
                        if status:
                            decode = json.loads(data.decode("utf-8"))
                            for item in decode["tracks"]["items"]:
                                track_item = SearchItem()
                                track_item.is_track = True
                                track_item.name = item["name"]
                                track_item.album = album_item
                                try:
                                    track_item.year = decode[
                                                            "release_date"][:4]
                                except:
                                    pass  # May be missing
                                track_item.tracknumber = int(
                                                          item["track_number"])
                                track_item.discnumber = int(
                                                           item["disc_number"])
                                track_item.duration = int(
                                                    item["duration_ms"]) / 1000
                                for artist in item["artists"]:
                                    track_item.artists.append(artist["name"])
                                if not album_item.artists:
                                    album_item.artists = track_item.artists
                                album_item.subitems.append(track_item)
                        self._items.append(album_item)
                        GLib.idle_add(self.emit, "item-found")
        except Exception as e:
            print("SpotifySearch::albums(): %s" % e)

    def __get_albums(self, name):
        """
            Get albums for name
            @param name as str
        """
        try:
            # Read album list
            formated = GLib.uri_escape_string(name, None, True).replace(
                                                                      " ", "+")
            s = Lio.File.new_for_uri("https://api.spotify.com/v1/search?q=%s"
                                     "&type=album" % formated)
            s.add_spotify_headers(self.__token)
            (status, data, tag) = s.load_contents(self._cancel)
            if status:
                decode = json.loads(data.decode("utf-8"))
                # For each album, get cover and tracks
                for item in decode["albums"]["items"]:
                    album_item = SearchItem()
                    album_item.name = item["name"]
                    album_item.is_track = False
                    album_item.cover = item["images"][0]["url"]
                    album_item.smallcover = item["images"][2]["url"]
                    s = Lio.File.new_for_uri("https://api.spotify.com/v1/"
                                             "albums/%s" % item["id"])
                    s.add_spotify_headers(self.__token)
                    (status, data, tag) = s.load_contents(self._cancel)
                    if status:
                        decode = json.loads(data.decode("utf-8"))
                        for item in decode["tracks"]["items"]:
                            track_item = SearchItem()
                            track_item.is_track = True
                            try:
                                track_item.year = decode[
                                                        "release_date"][:4]
                            except:
                                pass  # May be missing
                            track_item.name = item["name"]
                            track_item.album = album_item
                            track_item.tracknumber = int(item["track_number"])
                            track_item.discnumber = int(item["disc_number"])
                            track_item.duration = int(item["duration_ms"])\
                                / 1000
                            for artist in item["artists"]:
                                track_item.artists.append(artist["name"])
                            if not album_item.artists:
                                album_item.artists = track_item.artists
                            album_item.subitems.append(track_item)
                    self._items.append(album_item)
                    GLib.idle_add(self.emit, "item-found")
        except Exception as e:
            print("SpotifySearch::albums(): %s" % e)
