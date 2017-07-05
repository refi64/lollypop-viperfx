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

import json
from time import sleep
from locale import getdefaultlocale


from lollypop.web import Web
from lollypop.define import DbPersistent, Lp, Type
from lollypop.utils import debug, get_network_available
from lollypop.search_item import SearchItem
from lollypop.tagreader import TagReader
from lollypop.sqlcursor import SqlCursor
from lollypop.lio import Lio


class ItunesCharts:
    """
        Itunes charts
    """

    __GENRES = {"alternative": 20,
                "anime": 29,
                "blues": 2,
                "brazil": 1122,
                "children": 4,
                "chinese": 1232,
                "gospel": 22,
                "comedy": 3,
                "classic": 5,
                "country": 6,
                "dance": 17,
                "disney": 50000063,
                "easy": 25,
                "enka": 28,
                "fitness": 50,
                "electro": 7,
                "french": 50000064,
                "german pop": 50000066,
                "german folk": 50000068,
                "holiday": 8,
                "indian": 1262,
                "instrumental": 53,
                "j-pop": 27,
                "k-pop": 51,
                "karaoke": 52,
                "kayokyoku": 30,
                "korean": 1243,
                "singer": 10,
                "vocal": 23,
                "rap": 18,
                "hip hop": 18,
                "jazz": 11,
                "latino": 12,
                "new age": 13,
                "opera": 9,
                "pop": 14,
                "soul": 15,
                "r&b": 15,
                "reggae": 24,
                "rock": 21,
                "soundtrack": 16,
                "world": 19,
                }
    __LIMIT = 40
    __ALL = "https://itunes.apple.com/%s/rss/topalbums/limit=%s/json"
    __GENRE = \
        "https://itunes.apple.com/%s/rss/topalbums/limit=%s/genre=%s/json"
    __INFO = "https://itunes.apple.com/lookup?id=%s&entity=song&country=%s"

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
        self.__stop = False
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
        if self.__stop:
            return
        country = getdefaultlocale()[0][3:]
        itunes_ids = list(self.__GENRES.values())
        self.__update_for_url(self.__ALL % (country, self.__LIMIT))
        for itunes_id in itunes_ids:
            if self.__stop:
                return
            self.__update_for_url(self.__GENRE % (country,
                                                  self.__LIMIT,
                                                  itunes_id))

    def __update_for_url(self, url):
        """
            Update charts for url
            @param url as str
        """
        if not get_network_available():
                return
        debug("ItunesCharts::__update_for_url(): %s => %s" % (url,
                                                              self.__LIMIT))
        web = Web()
        ids = self.__get_ids(url)
        position = len(ids)
        while ids:
            sleep(10)
            (itunes_id, itunes_genre) = ids.pop(0)
            album = self.__get_album(itunes_id)
            if self.__stop:
                return
            if album is None or not album.subitems:
                position -= 1
                continue
            album.mtime = self.__time + position
            for item in album.subitems:
                item.mtime = self.__time
            debug("ItunesCharts::__update_for_url(): %s - %s" % (
                                                                album.name,
                                                                album.artists))
            t = TagReader()
            with SqlCursor(Lp().db) as sql:
                genre_ids = t.add_genres(itunes_genre)
                sql.commit()
            genre_ids.append(Type.ITUNES)
            web.save_album_thread(album, DbPersistent.CHARTS, genre_ids)
            position -= 1

    def __get_album(self, itunes_id):
        """
            Get itunes album items
            @param id as int
            @return SearchItem/None
        """
        if not get_network_available():
                return
        country = getdefaultlocale()[0][3:]
        try:
            debug("ItunesCharts::__get_album(): %s" % itunes_id)
            url = self.__INFO % (itunes_id, country)
            f = Lio.File.new_for_uri(url)
            (status, data, tag) = f.load_contents(self.__cancel)
            if not status or self.__stop:
                return
            decode = json.loads(data.decode("utf-8"))
            item = decode["results"][0]
            album_item = SearchItem()
            album_item.name = item["collectionName"]
            album_item.artists.append(item["artistName"])
            album_item.cover = item["artworkUrl60"].replace(
                                               "60x60",
                                               "512x512")

            for item in decode["results"][1:]:
                track_item = SearchItem()
                track_item.is_track = True
                track_item.name = item["trackName"]
                track_item.album = album_item
                track_item.year = item["releaseDate"][:4]
                track_item.tracknumber = int(
                                          item["trackNumber"])
                track_item.discnumber = int(
                                           item["discNumber"])
                track_item.duration = int(
                                    item["trackTimeMillis"]) / 1000
                if album_item.artists[0] != item["artistName"]:
                    track_item.artists.append(album_item.artists[0])
                track_item.artists.append(item["artistName"])
                album_item.subitems.append(track_item)
            return album_item
        except Exception as e:
            print("ItunesCharts::__get_album()", e)
        return None

    def __get_ids(self, url):
        """
            Get album itunes ids
            @param url as str
        """
        items = []
        try:
            f = Lio.File.new_for_uri(url)
            (status, data, tag) = f.load_contents(self.__cancel)
            if not status or self.__stop:
                return []
            decode = json.loads(data.decode("utf-8"))
            for entry in decode["feed"]["entry"]:
                itunes_id = entry["id"]["attributes"]["im:id"]
                itunes_genre = entry["category"]["attributes"]["term"]
                items.append((itunes_id, itunes_genre))
        except Exception as e:
            print("ItunesCharts::__get_ids:", e)
        return items
