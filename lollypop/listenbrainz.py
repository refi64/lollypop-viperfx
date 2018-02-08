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

from gi.repository import Gio

import json
import ssl
import time
from gi.repository import GObject
from http.client import HTTPSConnection

from lollypop.helper_task import TaskHelper
from lollypop.utils import debug, get_network_available

HOST_NAME = "api.listenbrainz.org"
PATH_SUBMIT = "/1/submit-listens"
SSL_CONTEXT = ssl.create_default_context()


class ListenBrainz(GObject.GObject):
    """
    Submit listens to ListenBrainz.org.

    See https://listenbrainz.readthedocs.io/en/latest/dev/api.html
    """

    user_token = GObject.Property(type=str, default=None)

    def __init__(self):
        GObject.GObject.__init__(self)
        self.__next_request_time = 0
        self.__proxy = None
        self.__check_for_proxy()

    def listen(self, track, time):
        """
            Submit a listen for a track
            @param track as Track
            @param time as int
        """
        payload = self.__get_payload(track)
        payload[0]["listened_at"] = time
        self.__submit("single", payload)

    def playing_now(self, track):
        """
            Submit a playing now notification for a track
            @param track as Track
        """
        payload = self.__get_payload(track)
        self.__submit("playing_now", payload)

    @property
    def available(self):
        """
            True if service available
        """
        return self.user_token != ""

#######################
# PRIVATE             #
#######################
    def __submit(self, listen_type, payload):
        if get_network_available():
            helper = TaskHelper()
            helper.run(self.__request, listen_type, payload)

    def __request(self, listen_type, payload, retry=0):
        self.__wait_for_ratelimit()
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
        (host, port, url) = self.__get_connection_params()
        conn = HTTPSConnection(host, port, context=SSL_CONTEXT)
        try:
            conn.request("POST", url, body, headers)
            response = conn.getresponse()
            response_data = json.loads(response.read())
            debug("ListenBrainz response %s: %r" % (response.status,
                                                    response_data))
            self.__handle_ratelimit(response)
            # Too Many Requests
            if response.status == 429 and retry < 5:
                self.__request(listen_type, payload, retry + 1)
        except Exception as e:
            print("ListenBrainz::__submit():", e)

    def __get_connection_params(self):
        if self.__proxy is not None:
            return (self.__proxy["host"], self.__proxy["port"],
                    "https://%s%s" % (HOST_NAME, PATH_SUBMIT))
        else:
            return (HOST_NAME, None, PATH_SUBMIT)

    def __wait_for_ratelimit(self):
        now = time.time()
        if self.__next_request_time > now:
            delay = self.__next_request_time - now
            debug("ListenBrainz rate limit applies, delay %d" % delay)
            time.sleep(delay)

    def __handle_ratelimit(self, response):
        remaining = int(response.getheader("X-RateLimit-Remaining", 0))
        reset_in = int(response.getheader("X-RateLimit-Reset-In", 0))
        debug("ListenBrainz X-RateLimit-Remaining: %i" % remaining)
        debug("ListenBrainz X-RateLimit-Reset-In: %i" % reset_in)
        if (remaining == 0):
            self.__next_request_time = time.time() + reset_in

    def __check_for_proxy(self):
        """
            Enable proxy if needed
        """
        try:
            proxy = Gio.Settings.new("org.gnome.system.proxy")
            https = Gio.Settings.new("org.gnome.system.proxy.https")
            mode = proxy.get_value("mode").get_string()
            if mode != "none":
                host = https.get_value("host").get_string()
                port = https.get_value("port").get_int32()
                if host != "" and port != 0:
                    self.__proxy = {
                        "host": host,
                        "port": port
                    }
            else:
                self.__proxy = None
        except Exception as e:
            print("ListenBrainz::__check_for_proxy():", e)
            pass

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
