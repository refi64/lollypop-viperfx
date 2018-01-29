# Copyright (c) 2018 Philipp Wolfer <ph.wolfer@gmail.com>
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

import gi
gi.require_version("Secret", "1")
# from gi.repository import Gio

from gettext import gettext as _

try:
    from gi.repository import Secret
except Exception as e:
    print(e)
    print(_("Last.fm authentication disabled"))
    Secret = None

import json
import os
import ssl
from http.client import HTTPSConnection

from lollypop.utils import debug

HOST_NAME = "api.listenbrainz.org"
SSL_CONTEXT = ssl.create_default_context()

# TODO: Configure token
# TODO: Honor rate limiting


class ListenBrainz:
    """
    Submit listens to ListenBrainz.org.

    See https://listenbrainz.readthedocs.io/en/latest/dev/api.html
    """

    def __init__(self):
        # self.user_token = None
        # FIXME: Configure token
        self.user_token = os.environ["LISTENBRAINZ_USER_TOKEN"]
        debug("ListenBrainz token: %s" % self.user_token)

    def listen(self, time, track):
        payload = self.__get_payload(track)
        payload[0]["listened_at"] = time
        self.__submit("single", payload)

    def playing_now(self, track):
        payload = self.__get_payload(track)
        self.__submit("playing_now", payload)

    def __submit(self, listen_type, payload):
        debug("ListenBrainz %s: %r" % (listen_type, payload))
        data = {
            "listen_type": listen_type,
            "payload": payload
        }
        headers = {
            "Authorization": "Token %s" % self.user_token,
            "Content-Type": "application/json"
        }
        body = json.dumps(data)
        conn = HTTPSConnection(HOST_NAME, context=SSL_CONTEXT)
        try:
            conn.request("POST", "/1/submit-listens", body, headers)
            response = conn.getresponse()
            response_data = json.loads(response.read())
            debug("ListenBrainz response %s: %r" % (response.status,
                                                    response_data))
        except Exception as e:
            print("ListenBrainz::__submit():", e)

    def __get_payload(self, track):
        artists = ", ".join(track.artists)
        payload = {
            "track_metadata": {
                "artist_name": artists,
                "track_name": track.title,
                "release_name": track.album_name,
                "additional_info": {
                    "release_mbid": track.album.mb_album_id,
                    "recording_mbid": track.mb_track_id,
                    "tracknumber": track.number
                }
            }
        }

        return [payload]
