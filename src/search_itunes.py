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

from gi.repository import GLib, Gio

import json

from lollypop.search_item import SearchItem
from lollypop.lio import Lio


class ItunesSearch:
    """
        Search provider for Itunes
    """
    def __init__(self):
        """
            Init provider
        """
        if not hasattr(self, "_cancel"):
            self._cancel = Gio.Cancellable.new()

    def tracks(self, name):
        """
            Return tracks containing name
            @param name as str
        """
        try:
            formated = GLib.uri_escape_string(name, None, True).replace(
                                                                      " ", "+")
            s = Lio.File.new_for_uri("https://itunes.apple.com/search"
                                     "?entity=musicTrack&term=%s" % formated)
            (status, data, tag) = s.load_contents(self._cancel)
            if status:
                decode = json.loads(data.decode("utf-8"))
                tracks = []
                for item in decode["results"]:
                    if item["trackName"].lower() in tracks:
                        continue
                    album_item = SearchItem()
                    album_item.name = item["collectionName"]
                    search_item = SearchItem()
                    search_item.is_track = True
                    search_item.name = item["trackName"]
                    tracks.append(search_item.name.lower())
                    search_item.album = album_item
                    search_item.tracknumber = int(item["trackNumber"])
                    search_item.discnumber = int(item["discNumber"])
                    search_item.duration = int(item["trackTimeMillis"]) / 1000
                    search_item.cover = item["artworkUrl60"].replace("60x60",
                                                                     "512x512")
                    search_item.smallcover = item["artworkUrl100"]
                    search_item.artists.append(item["artistName"])
                    self._items.append(search_item)
                    GLib.idle_add(self.emit, "item-found")
        except Exception as e:
            print("SpotifySearch::tracks(): %s" % e)

    def albums(self, name):
        """
            Return albums containing name
            @param name as str
            @return albums as [SearchItem]
        """
        self.__get_albums(name)

#######################
# PRIVATE             #
#######################
    def __get_albums(self, name):
        """
            Get albums for name
            @param name as str
        """
        try:
            # Read album list
            formated = GLib.uri_escape_string(name, None, True).replace(
                                                                      " ", "+")
            s = Lio.File.new_for_uri("https://itunes.apple.com/search"
                                     "?entity=album&term=%s" % formated)
            (status, data, tag) = s.load_contents(self._cancel)
            if not status:
                raise
            decode = json.loads(data.decode("utf-8"))
            # For each album, get cover and tracks
            for item in decode["results"]:
                album_item = SearchItem()
                album_item.name = item["collectionName"]
                album_item.is_track = False
                album_item.artists = [item["artistName"]]
                album_item.cover = item["artworkUrl60"].replace("60x60",
                                                                "512x512")
                album_item.smallcover = item["artworkUrl100"]
                s = Lio.File.new_for_uri("https://itunes.apple.com/lookup"
                                         "?id=%s&entity=song" %
                                         item["collectionId"])
                (status, data, tag) = s.load_contents(self._cancel)
                if not status:
                    raise
                decode = json.loads(data.decode("utf-8"))
                for item in decode["results"]:
                    if item["wrapperType"] == "collection":
                        continue
                    track_item = SearchItem()
                    track_item.is_track = True
                    try:
                        track_item.year = decode["releaseDate"][:4]
                    except:
                        pass  # May be missing
                    track_item.name = item["trackName"]
                    track_item.album = album_item
                    track_item.tracknumber = int(item["trackNumber"])
                    track_item.discnumber = int(item["discNumber"])
                    track_item.duration = int(item["trackTimeMillis"])\
                        / 1000
                    track_item.artists.append(item["artistName"])
                    album_item.subitems.append(track_item)
                self._items.append(album_item)
                GLib.idle_add(self.emit, "item-found")
        except Exception as e:
            print("ItunesSearch::__get_albums(): %s" % e)
