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

from gi.repository import Gio

from threading import Thread
from time import sleep
from locale import getdefaultlocale
from csv import reader

from lollypop.search_spotify import SpotifySearch
from lollypop.web import Web
from lollypop.define import DbPersistent, Lp
from lollypop.utils import debug, get_network_available


class SpotifyCharts:
    """
        Spotify charts
    """

    __ALL = "https://spotifycharts.com/regional/%s/weekly/latest/download"

    def __init__(self):
        """
            Init charts
        """
        self.__cancel = Gio.Cancellable.new()
        self.__stop = False
        self.__count = 0

    def update(self):
        """
            Update charts
        """
        self._stop = False
        self.__count = self.__get_album_count()
        t = Thread(target=self.__update)
        t.daemon = True
        t.start()

    def stop(self):
        """
            Stop search
        """
        self.__stop = True
        self.__cancel.cancel()

#######################
# PRIVATE             #
#######################
    def __get_album_count(self):
        """
            Calculate album count
            @return count as int
        """
        return 200

    def __update(self):
        """
            Update charts
        """
        sleep(5)
        if self._stop:
            return

        language = getdefaultlocale()[0][0:2]
        self.__update_for_url(self.__ALL % language)

    def __update_for_url(self, url):
        """
            Update charts for url
            @param url as str
        """
        if not get_network_available():
                return
        debug("SpotifyCharts::__update_for_url(): %s => %s" % (url,
                                                               self.__count))
        ids = self.__get_ids(url)
        web = Web()
        search = SpotifySearch()
        while ids:
            sleep(10)
            track_id = ids.pop(0)
            album_id = search.get_album_id(track_id)
            album = search.get_album(album_id)
            if album is None or album.exists_in_db():
                continue
            if self._stop:
                return
            Lp().db.del_tracks(Lp().tracks.get_old_from_charts(self.__count))
            debug("SpotifyCharts::__update_for_url(): %s - %s - %s" % (
                                                                album.name,
                                                                album.artists,
                                                                album_id))
            web.save_album(album, DbPersistent.CHARTS)

    def __get_ids(self, url):
        """
            Get album spotify ids
            @param url as str
        """
        ids = []
        try:
            f = Gio.File.new_for_uri(url)
            (status, data, tag) = f.load_contents(self.__cancel)
            if not status or self._stop:
                return []
            for line in data.decode("utf-8").split('\n'):
                try:  # CSV file is mostly broken
                    for row in reader([line]):
                        if not row:
                            continue
                        url = row[4]
                        if url == "URL":
                            continue
                        track_id = url.split('/')[-1:][0]
                        ids.append(track_id)
                except Exception as e:
                    print(e)
        except Exception as e:
            print("SpotifyCharts::__get_ids:", e)
        return ids
