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

from gettext import gettext as _
import json
from threading import Thread
from time import sleep
from locale import getdefaultlocale


from lollypop.web import Web
from lollypop.define import DbPersistent, Lp
from lollypop.utils import debug, get_network_available
from lollypop.search_item import SearchItem
from lollypop.lio import Lio


class ItunesCharts:
    """
        Itunes charts
    """

    __GENRES = {"alternative": 1,
                # Translators: Only translate this music genre
                # if it makes sense for you
                _("alternative"): 1,
                "anime": 29,
                # Translators: Only translate this music genre
                # if it makes sense for you
                _("anime"): 29,
                "blues": 2,
                # Translators: Only translate this music genre
                # if it makes sense for you
                _("blues"): 2,
                "brazil": 1122,
                # Translators: Only translate this music genre
                # if it makes sense for you
                _("brazil"): 1122,
                "classic": 5,
                # Translators: Only translate this music genre
                # if it makes sense for you
                _("classic"): 5,
                "country": 6,
                # Translators: Only translate this music genre
                # if it makes sense for you
                _("country"): 6,
                "dance": 17,
                # Translators: Only translate this music genre
                # if it makes sense for you
                _("dance"): 17,
                "electro": 7,
                # Translators: Only translate this music genre
                # if it makes sense for you
                _("electro"): 7,
                "french": 50000064,
                # Translators: Only translate this music genre
                # if it makes sense for you
                _("french"): 50000064,
                "german": 50000066,
                # Translators: Only translate this music genre
                # if it makes sense for you
                _("german"): 50000066,
                "rap": 18,
                # Translators: Only translate this music genre
                # if it makes sense for you
                _("rap"): 18,
                "hip hop": 18,
                # Translators: Only translate this music genre
                # if it makes sense for you
                _("hip hop"): 18,
                "jazz": 11,
                # Translators: Only translate this music genre
                # if it makes sense for you
                _("jazz"): 11,
                "latin": 12,
                # Translators: Only translate this music genre
                # if it makes sense for you
                _("latin"): 12,
                "new age": 13,
                # Translators: Only translate this music genre
                # if it makes sense for you
                _("new age"): 13,
                "opera": 9,
                # Translators: Only translate this music genre
                # if it makes sense for you
                _("opera"): 9,
                "pop": 14,
                # Translators: Only translate this music genre
                # if it makes sense for you
                _("pop"): 14,
                "soul": 15,
                # Translators: Only translate this music genre
                # if it makes sense for you
                _("soul"): 15,
                "r&b": 15,
                "reggae": 24,
                # Translators: Only translate this music genre
                # if it makes sense for you
                _("reggae"): 24,
                "rock": 21,
                # Translators: Only translate this music genre
                # if it makes sense for you
                _("rock"): 21,
                "soundtrack": 16,
                # Translators: Only translate this music genre
                # if it makes sense for you
                _("soundtrack"): 16,
                "world": 19,
                # Translators: Only translate this music genre
                # if it makes sense for you
                _("world"): 19
                }
    __LIMIT = 40
    __MIN = 100
    __ALL = "https://itunes.apple.com/%s/rss/topalbums/limit=%s/json"
    __GENRE = \
        "https://itunes.apple.com/%s/rss/topalbums/limit=%s/genre=%s/json"
    __INFO = "https://itunes.apple.com/lookup?id=%s&entity=song&country=%s"

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
        self.__stop = False
        self.__cancel.reset()
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
        count = len(self.__get_genre_ids()) * self.__LIMIT + self.__LIMIT
        return count if count > self.__MIN else self.__MIN

    def __update(self):
        """
            Update charts
        """
        sleep(5)
        if self.__stop:
            return
        country = getdefaultlocale()[0][3:]
        itunes_ids = self.__get_genre_ids()
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
                                                              self.__count))
        web = Web()
        ids = self.__get_ids(url)
        while ids:
            sleep(10)
            (itunes_id, itunes_genre) = ids.pop(0)
            album = self.__get_album(itunes_id)
            if self.__stop:
                return
            if album is None or album.exists_in_db():
                continue
            Lp().db.del_tracks(Lp().tracks.get_old_from_charts(self.__count))
            debug("ItunesCharts::__update_for_url(): %s - %s" % (
                                                                album.name,
                                                                album.artists))
            web.save_album(album, DbPersistent.CHARTS, itunes_genre)

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
            decode = json.loads(data.decode('utf-8'))
            item = decode['results'][0]
            album_item = SearchItem()
            album_item.name = item['collectionName']
            album_item.album_name = album_item.name
            album_item.artists.append(item['artistName'])
            album_item.cover = item['artworkUrl60'].replace(
                                               '60x60',
                                               '512x512')

            for item in decode['results'][1:]:
                track_item = SearchItem()
                track_item.is_track = True
                track_item.name = item['trackName']
                track_item.album = album_item.name
                track_item.year = item['releaseDate'][:4]
                track_item.tracknumber = int(
                                          item['trackNumber'])
                track_item.discnumber = int(
                                           item['discNumber'])
                track_item.duration = int(
                                    item['trackTimeMillis']) / 1000
                if album_item.artists[0] != item['artistName']:
                    track_item.artists.append(album_item.artists[0])
                track_item.artists.append(item['artistName'])
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
            decode = json.loads(data.decode('utf-8'))
            for entry in decode['feed']['entry']:
                itunes_id = entry['id']['attributes']['im:id']
                itunes_genre = entry['category']['attributes']['term']
                items.append((itunes_id, itunes_genre))
        except Exception as e:
            print("ItunesCharts::__get_ids:", e)
        return items

    def __get_genre_ids(self):
        """
            Get genre ids
            @return ids as [int]
        """
        # Calculate genres available in db and in itunes
        itunes_ids = []
        for genre in Lp().genres.get_names():
            for itunes_genre in self.__GENRES.keys():
                if genre.lower().find(itunes_genre) != -1:
                    itunes_id = self.__GENRES[itunes_genre]
                    if itunes_id not in itunes_ids:
                        itunes_ids.append(itunes_id)
        return itunes_ids
