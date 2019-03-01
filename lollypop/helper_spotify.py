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

from gi.repository import GLib, Soup, GObject

import json
from base64 import b64encode
from time import time, sleep
from gettext import gettext as _

from lollypop.sqlcursor import SqlCursor
from lollypop.tagreader import TagReader
from lollypop.logger import Logger
from lollypop.objects import Album
from lollypop.helper_task import TaskHelper
from lollypop.define import SPOTIFY_CLIENT_ID, SPOTIFY_SECRET, App


class SpotifyHelper(GObject.Object):
    """
        Helper for Spotify
    """

    __gsignals__ = {
        "new-album": (GObject.SignalFlags.RUN_FIRST, None,
                      (GObject.TYPE_PYOBJECT,)),
        "search-finished": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self):
        """
            Init object
        """
        GObject.Object.__init__(self)
        self.__token_expires = 0
        self.__token = None
        self.__loading_token = False

    def get_token(self):
        """
            Get a new auth token
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
                self.__token_expires = int(time()) + int(decode["expires_in"])
                self.__token = decode["access_token"]
        except Exception as e:
            Logger.error("SpotifyHelper::get_token(): %s", e)

    def wait_for_token(self):
        """
            True if should wait for token
            @return bool
        """
        def on_token(token):
            self.__loading_token = False
        # Remove 60 seconds to be sure
        wait = int(time()) + 60 > self.__token_expires or\
            self.__token is None
        if wait and not self.__loading_token:
            self.__loading_token = True
            App().task_helper.run(self.get_token, callback=(on_token,))
        return wait

    def get_artist_id(self, artist_name, callback):
        """
            Get artist id
            @param artist_name as str
            @param callback as function
        """
        if self.wait_for_token():
            GLib.timeout_add(
                500, self.get_artist_id, artist_name, callback)
            return
        try:
            def on_content(uri, status, data):
                if status:
                    decode = json.loads(data.decode("utf-8"))
                    for item in decode["artists"]["items"]:
                        artist_id = item["uri"].split(":")[-1]
                        callback(artist_id)
                        return
            artist_name = GLib.uri_escape_string(
                artist_name, None, True).replace(" ", "+")
            token = "Bearer %s" % self.__token
            helper = TaskHelper()
            helper.add_header("Authorization", token)
            uri = "https://api.spotify.com/v1/search?q=%s&type=artist" %\
                artist_name
            helper.load_uri_content(uri, None, on_content)
        except Exception as e:
            Logger.error("SpotifyHelper::get_artist_id(): %s", e)

    def get_similar_artists(self, artist_id, callback):
        """
            Get artist id
            @param artist_name as str
            @param callback as function
        """
        if self.wait_for_token():
            GLib.timeout_add(
                500, self.get_similar_artists, artist_id, callback)
            return
        try:
            def on_content(uri, status, data):
                if status:
                    decode = json.loads(data.decode("utf-8"))
                    artists = []
                    for item in decode["artists"]:
                        artists.append(item["name"])
                    callback(artists)
            token = "Bearer %s" % self.__token
            helper = TaskHelper()
            helper.add_header("Authorization", token)
            uri = "https://api.spotify.com/v1/artists/%s/related-artists" %\
                artist_id
            helper.load_uri_content(uri, None, on_content)
        except Exception as e:
            Logger.error("SpotifyHelper::get_artist_id(): %s", e)

    def search(self, search, cancellable):
        """
            Get albums related to search
            We need a thread because we are going to populate DB
            @param search as str
            @param cancellable as Gio.Cancellable
        """
        try:
            while self.wait_for_token():
                if cancellable.is_cancelled():
                    raise Exception("cancelled")
                sleep(1)
            token = "Bearer %s" % self.__token
            helper = TaskHelper()
            helper.add_header("Authorization", token)
            uri = "https://api.spotify.com/v1/search?"
            uri += "q=%s&type=album,track" % search
            (status, data) = helper.load_uri_content_sync(uri, cancellable)
            if status:
                decode = json.loads(data.decode("utf-8"))
                album_ids = []
                self.__create_albums_from_album_payload(
                                                 decode["albums"]["items"],
                                                 album_ids,
                                                 cancellable)
                self.__create_albums_from_track_payload(
                                                 decode["tracks"]["items"],
                                                 album_ids,
                                                 cancellable)
            GLib.idle_add(self.emit, "search-finished", search)
        except Exception as e:
            Logger.error("SpotifyHelper::search(): %s", e)

#######################
# PRIVATE             #
#######################
    def __create_album(self, album_id, cover_uri, cancellable):
        """
            Create album and download cover
            @param cancellable as Gio.Cancellable
        """
        # Create albums
        album = Album(album_id)
        App().art.copy_uri_to_cache
        (status, data) = App().task_helper.load_uri_content_sync(
            cover_uri, cancellable)
        if status:
            App().art.save_album_artwork(data, album_id)
        if cancellable.is_cancelled():
            raise Exception("cancelled")
        GLib.idle_add(self.emit, "new-album", album)

    def __create_albums_from_track_payload(self, payload, album_ids,
                                           cancellable):
        """
            Get albums from a track payload
            @param payload as {}
            @param album_ids as [int]
            @param cancellable as Gio.Cancellable
        """
        # Populate tracks
        for item in payload:
            if App().db.exists_in_db(item["album"]["name"],
                                     [artist["name"]
                                     for artist in item["artists"]],
                                     item["name"]):
                continue
            (album_id,
             track_id,
             cover_uri) = self.__save_track(item)
            if album_id not in album_ids:
                album_ids.append(album_id)
                self.__create_album(album_id, cover_uri, cancellable)

    def __create_albums_from_album_payload(self, payload, album_ids,
                                           cancellable):
        """
            Get albums from an album payload
            @param payload as {}
            @param album_ids as [int]
            @param cancellable as Gio.Cancellable
        """
        # Populate tracks
        for album_item in payload:
            if App().db.exists_in_db(album_item["name"],
                                     [artist["name"]
                                     for artist in album_item["artists"]],
                                     None):
                continue
            uri = "https://api.spotify.com/v1/albums/%s" % album_item["id"]
            token = "Bearer %s" % self.__token
            helper = TaskHelper()
            helper.add_header("Authorization", token)
            (status, data) = helper.load_uri_content_sync(uri, cancellable)
            if status:
                decode = json.loads(data.decode("utf-8"))
                track_payload = decode["tracks"]["items"]
                for item in track_payload:
                    item["album"] = album_item
                self.__create_albums_from_track_payload(track_payload,
                                                        album_ids,
                                                        cancellable)

    def __save_track(self, payload):
        """
            Save track to DB as non persistent
            @param payload as {}
            @return track_id
        """
        t = TagReader()
        title = payload["name"]
        _artists = []
        for artist in payload["artists"]:
            _artists.append(artist["name"])
        _album_artists = []
        for artist in payload["album"]["artists"]:
            _album_artists.append(artist["name"])
        # Translate to tag value
        artists = ";".join(_artists)
        album_artists = ";".join(_album_artists)
        album_name = payload["album"]["name"]
        genres = _("Web")
        discnumber = int(payload["disc_number"])
        discname = None
        tracknumber = int(payload["track_number"])
        try:
            timestamp = payload["release_date"]
            year = timestamp[:4]
        except:
            timestamp = ""
            year = None
            pass
        duration = payload["duration_ms"] // 1000
        mb_album_id = mb_track_id = None
        a_sortnames = aa_sortnames = ""
        cover_uri = payload["album"]["images"][2]["url"]
        uri = "web://%s" % payload["id"]
        Logger.debug("SpotifyHelper::__save_track(): Add artists %s" % artists)
        artist_ids = t.add_artists(artists, a_sortnames)

        Logger.debug("SpotifyHelper::__save_track(): "
                     "Add album artists %s" % album_artists)
        album_artist_ids = t.add_album_artists(album_artists, aa_sortnames)
        # User does not want compilations
        if not App().settings.get_value("show-compilations") and\
                not album_artist_ids:
            album_artist_ids = artist_ids

        missing_artist_ids = list(set(album_artist_ids) - set(artist_ids))
        # https://github.com/gnumdk/lollypop/issues/507#issuecomment-200526942
        # Special case for broken tags
        # Can't do more because don't want to break split album behaviour
        if len(missing_artist_ids) == len(album_artist_ids):
            artist_ids += missing_artist_ids

        Logger.debug("SpotifyHelper::__save_track(): Add album: "
                     "%s, %s" % (album_name, album_artist_ids))
        album_id = t.add_album(album_name, mb_album_id, album_artist_ids,
                               "", False, 0, 0, 0)

        genre_ids = t.add_genres(genres)

        # Add track to db
        Logger.debug("SpotifyHelper::__save_track(): Add track")
        track_id = App().tracks.add(title, uri, duration,
                                    tracknumber, discnumber, discname,
                                    album_id, year, timestamp, 0,
                                    0, False, 0,
                                    0, mb_track_id)
        Logger.debug("SpotifyHelper::__save_track(): Update track")
        App().scanner.update_track(track_id, artist_ids, genre_ids)
        Logger.debug("SpotifyHelper::__save_track(): Update album")
        SqlCursor.commit(App().db)
        App().scanner.update_album(album_id, album_artist_ids,
                                   genre_ids, year, timestamp)
        SqlCursor.commit(App().db)
        return (album_id, track_id, cover_uri)
