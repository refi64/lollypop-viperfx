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
from locale import getdefaultlocale
from csv import reader

from lollypop.search_spotify import SpotifySearch
from lollypop.web import Web
from lollypop.define import DbPersistent, Lp, Type
from lollypop.utils import debug, get_network_available
from lollypop.lio import Lio


class SpotifyCharts:
    """
        Spotify charts
    """

    __ALL = "https://spotifycharts.com/regional/%s/weekly/latest/download"

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
        # Try to get region
        try:
            language = getdefaultlocale()[0][3:5].lower()
        except:
            language = getdefaultlocale()[0][0:2]
        self.__update_for_url(self.__ALL % language)

    def __update_for_url(self, url):
        """
            Update charts for url
            @param url as str
        """
        if not get_network_available():
                return
        debug("SpotifyCharts::__update_for_url(): %s" % (url))
        ids = self.__get_ids(url)
        web = Web()
        search = SpotifySearch()
        position = len(ids)
        while ids:
            sleep(10)
            track_id = ids.pop(0)
            album = search.get_track(track_id)
            if self.__stop:
                return
            if album is None or not album.subitems:
                position -= 1
                continue
            for item in album.subitems:
                item.mtime = self.__time + position
            debug("SpotifyCharts::__update_for_url(): %s - %s - %s" % (
                                                                album.name,
                                                                album.artists,
                                                                track_id))
            web.save_album_thread(album, DbPersistent.CHARTS, [Type.SPOTIFY])
            position -= 1

    def __get_ids(self, url):
        """
            Get track spotify ids
            @param url as str
        """
        ids = []
        try:
            f = Lio.File.new_for_uri(url)
            (status, data, tag) = f.load_contents(self.__cancel)
            if not status or self._stop:
                return []
            for line in data.decode("utf-8").split("\n"):
                try:  # CSV file is mostly broken
                    for row in reader([line]):
                        if not row:
                            continue
                        url = row[4]
                        if url == "URL":
                            continue
                        track_id = url.split("/")[-1:][0]
                        ids.append(track_id)
                except Exception as e:
                    print(e)
        except Exception as e:
            print("SpotifyCharts::__get_ids:", e)
        return ids
