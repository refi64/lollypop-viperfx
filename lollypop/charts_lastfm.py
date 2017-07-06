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

from gi.repository import Gio

from time import sleep
import json

from lollypop.search_network import NetworkSearch
from lollypop.web import Web
from lollypop.define import DbPersistent, Lp, Type
from lollypop.utils import debug, get_network_available
from lollypop.lio import Lio


class LastfmCharts:
    """
        Spotify charts
    """

    __ALL = "http://ws.audioscrobbler.com/2.0/?method=chart.gettoptracks"\
            "&api_key=7a9619a850ccf7377c46cf233c51e3c6&format=json"

    def __init__(self, time):
        """
            Init charts
            @param time as int
        """
        self.__time = time
        self.__cancel = Gio.Cancellable.new()
        self.__stop = False

    def update(self):
        """
            Update charts
        """
        if not Lp().settings.get_value("show-charts"):
            return
        self.__cancel.reset()
        self._stop = False
        self.__update()

    def stop(self):
        """
            Stop search
        """
        self.__stop = True
        self.__cancel.cancel()

#######################
# PRIVATE             #
#######################
    def __update(self):
        """
            Update charts
        """
        sleep(5)
        if self._stop:
            return
        self.__update_for_url(self.__ALL)

    def __update_for_url(self, url):
        """
            Update charts for url
            @param url as str
        """
        if not get_network_available():
                return
        debug("LastfmCharts::__update_for_url(): %s" % (url))
        ids = self.__get_ids(url)
        position = len(ids)
        while ids:
            sleep(10)
            (track_name, artist_name) = ids.pop(0)
            search = NetworkSearch()
            search.connect("item-found", self.__on_item_found, position)
            search.do_tracks(track_name + " " + artist_name)
            if self.__stop:
                return
            position -= 1

    def __get_ids(self, url):
        """
            Get album itunes ids
            @param url as str
            @return [(track name, artist name)] as [(str, str)]
        """
        items = []
        try:
            f = Lio.File.new_for_uri(url)
            (status, data, tag) = f.load_contents(self.__cancel)
            if not status or self.__stop:
                return []
            decode = json.loads(data.decode("utf-8"))
            for entry in decode["tracks"]["track"]:
                track = entry["name"]
                artist = entry["artist"]["name"]
                items.append((track, artist))
        except Exception as e:
            print("LastfmCharts::__get_ids:", e)
        return items

    def __on_item_found(self, search, position):
        """
            Get track from search
            @param search as NetworkSearch
            @param position as int
        """
        if search.items:
            item = search.items[0]
            if item.is_track:
                debug("LastfmCharts::__on_item_found(): %s - %s" % (
                                                                item.name,
                                                                item.artists))
                search.stop()
                search.disconnect_by_func(self.__on_item_found)
                item.mtime = self.__time + position
                web = Web()
                web.save_track(item, DbPersistent.CHARTS, [Type.LASTFM])
