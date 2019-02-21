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

from gi.repository import GLib, Soup

import json
from base64 import b64encode
from time import time

from lollypop.logger import Logger
from lollypop.helper_task import TaskHelper
from lollypop.define import SPOTIFY_CLIENT_ID, SPOTIFY_SECRET, App


class SpotifyHelper:
    """
        Helper for Spotify
    """
    __EXPIRES = 0
    __TOKEN = None
    __LOADING_TOKEN = False

    def get_token():
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
                SpotifyHelper.__EXPIRES = int(time()) + int(
                                                          decode["expires_in"])
                SpotifyHelper.__TOKEN = decode["access_token"]
        except Exception as e:
            Logger.error("SpotifyHelper::get_token(): %s", e)

    def wait_for_token():
        """
            True if should wait for token
            @return bool
        """
        def on_token(token):
            SpotifyHelper.__LOADING_TOKEN = False
        # Remove 60 seconds to be sure
        wait = int(time()) + 60 > SpotifyHelper.__EXPIRES or\
            SpotifyHelper.__TOKEN is None
        if wait and not SpotifyHelper.__LOADING_TOKEN:
            SpotifyHelper.__LOADING_TOKEN = True
            App().task_helper.run(SpotifyHelper.get_token,
                                  callback=(on_token,))
        return wait

    def get_artist_id(artist_name, callback):
        """
            Get artist id
            @param artist_name as str
            @param callback as function
        """
        if SpotifyHelper.wait_for_token():
            GLib.timeout_add(
                500, SpotifyHelper.get_artist_id, artist_name, callback)
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
            token = "Bearer %s" % SpotifyHelper.__TOKEN
            helper = TaskHelper()
            helper.add_header("Authorization", token)
            uri = "https://api.spotify.com/v1/search?q=%s&type=artist" %\
                artist_name
            helper.load_uri_content(uri, None, on_content)
        except Exception as e:
            Logger.error("SpotifyHelper::get_artist_id(): %s", e)

    def get_similar_artists(artist_id, callback):
        """
            Get artist id
            @param artist_name as str
            @param callback as function
        """
        if SpotifyHelper.wait_for_token():
            GLib.timeout_add(
                500, SpotifyHelper.get_similar_artists, artist_id, callback)
            return
        try:
            def on_content(uri, status, data):
                if status:
                    decode = json.loads(data.decode("utf-8"))
                    artists = []
                    for item in decode["artists"]:
                        artists.append(item["name"])
                    callback(artists)
            token = "Bearer %s" % SpotifyHelper.__TOKEN
            helper = TaskHelper()
            helper.add_header("Authorization", token)
            uri = "https://api.spotify.com/v1/artists/%s/related-artists" %\
                artist_id
            helper.load_uri_content(uri, None, on_content)
        except Exception as e:
            Logger.error("SpotifyHelper::get_artist_id(): %s", e)

#######################
# PRIVATE             #
#######################
