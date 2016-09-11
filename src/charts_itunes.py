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

import xml.etree.ElementTree as xml
from gettext import gettext as _
import json
from threading import Thread
from time import sleep
from locale import getdefaultlocale


from lollypop.youtube import Youtube
from lollypop.define import DbPersistent, Lp
from lollypop.utils import debug
from lollypop.search_item import SearchItem


class ItunesCharts:
    """
        Itunes charts
    """

    __GENRES = {"alternative": 1,
                _("alternative"): 1,
                "anime": 29,
                _("anime"): 29,
                "blues": 2,
                _("blues"): 2,
                "brazil": 1122,
                _("brazil"): 1122,
                "classic": 5,
                _("classic"): 5,
                "country": 6,
                _("country"): 6,
                "Dance": 17,
                _("Dance"): 17,
                "electro": 7,
                _("electro"): 7,
                "french": 50000064,
                _("french"): 50000064,
                "german": 50000066,
                _("german"): 50000066,
                "rap": 18,
                _("rap"): 18,
                "hip hop": 18,
                _("hip hop"): 18,
                "jazz": 11,
                _("jazz"): 11,
                "latin": 12,
                _("latin"): 12,
                "new age": 13,
                _("new age"): 13,
                "opera": 9,
                _("opera"): 9,
                "pop": 14,
                _("pop"): 14,
                "soul": 15,
                _("soul"): 15,
                "r&b": 15,
                "reggae": 24,
                _("reggae"): 24,
                "rock": 21,
                _("rock"): 21,
                "soundtrack": 16,
                _("soundtrack"): 16,
                "World": 19,
                _("World"): 19
                }
    __ALL = "https://itunes.apple.com/%s/rss/topalbums/limit=20/xml"
    __GENRE = "https://itunes.apple.com/%s/rss/topalbums/limit=20/genre=%s/xml"
    __INFO = "https://itunes.apple.com/lookup?id=%s&entity=song&country=%s"

    def __init__(self):
        """
            Init charts
        """
        self.__stop = False
        self._cancel = Gio.Cancellable.new()

    def update(self):
        """
            Update charts
        """
        self.__stop = False
        t = Thread(target=self.__update)
        t.daemon = True
        t.start()

    def stop(self):
        """
            Stop downloads
        """
        self.__stop = True

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
        # Calculate genres available in db and in itunes
        itunes_ids = []
        for genre in Lp().genres.get_names():
            for itunes_genre in self.__GENRES.keys():
                if genre.lower().find(itunes_genre) != -1:
                    itunes_id = self.__GENRES[itunes_genre]
                    if itunes_id not in itunes_ids:
                        itunes_ids.append(itunes_id)

        language = getdefaultlocale()[0][0:2]
        limit = len(itunes_ids) * 20 + 20
        # Allow more albums if user do not have many genres
        if limit < 100:
            limit = 100
        self.__update_for_url(self.__ALL % language, limit)
        for itunes_id in itunes_ids:
            if self.__stop:
                return
            self.__update_for_url(self.__GENRE % (language, itunes_id), limit)

    def __update_for_url(self, url, limit):
        """
            Update charts for url
            @param url as str
            @param limit as int
        """
        if not Gio.NetworkMonitor.get_default().get_network_available():
                return
        debug("ItunesCharts::__update_for_url(): %s => %s" % (url, limit))
        yt = Youtube()
        ids = self.__get_ids(url)
        while ids:
            sleep(10)
            itunes_id = ids.pop(0)
            album = self.__get_album(itunes_id)
            if album is None or album.exists_in_db():
                continue
            if self.__stop:
                return
            Lp().db.del_tracks(Lp().tracks.get_old_from_charts(limit))
            debug("ItunesCharts::__update_for_url(): %s - %s" % (
                                                                album.name,
                                                                album.artists))
            yt.save_album(album, DbPersistent.CHARTS)

    def __get_album(self, itunes_id):
        """
            Get itunes album items, remove o
            @param id as int
            @return SearchItem/None
        """
        if not Gio.NetworkMonitor.get_default().get_network_available():
                return
        language = getdefaultlocale()[0][0:2]
        try:
            debug("ItunesCharts::__get_album(): %s" % itunes_id)
            url = self.__INFO % (itunes_id, language)
            f = Gio.File.new_for_uri(url)
            (status, data, tag) = f.load_contents(self._cancel)
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
            f = Gio.File.new_for_uri(url)
            (status, data, tag) = f.load_contents(self._cancel)
            if not status or self.__stop:
                return []
            root = xml.fromstring(data)
            for child in root:
                for element in child:
                    if len(element.keys()) > 1:
                        continue
                    for values in element.items():
                        if values[0] == '{http://itunes.apple.com/rss}id':
                            items.append(values[1])
        except Exception as e:
            print("ItunesCharts::__get_ids:", e)
        return items
