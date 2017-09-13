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

from lollypop.define import Lp
from lollypop.helper_task import TaskHelper


class SearchItem:
    """
        Represent a search item
    """
    def __init__(self):
        self.is_track = False
        self.id = None


class Search:
    """
        Local search
    """

    def __init__(self):
        """
            Init search
        """
        pass

    def get(self, search_items, cancellable, callback):
        """
            Get track for name
            @param search_items as [str]
            @param cancellable as Gio.Cancellable
            @param callback as callback
        """
        helper = TaskHelper()
        helper.run(self.__get, search_items, cancellable, callback=callback)

#######################
# PRIVATE             #
#######################
    def __get(self, search_items, cancellable):
        """
            Get track for name
            @param search_items as [str]
            @param cancellable as Gio.Cancellable
            @return items as [SearchItem]
        """
        items = []
        added_album_ids = []
        added_track_ids = []
        for item in search_items:
            if cancellable.is_cancelled():
                return
            albums = []
            tracks_non_album_artist = []
            # Get all albums for all artists and non album_artist tracks
            for artist_id in Lp().artists.search(item):
                if cancellable.is_cancelled():
                    return
                for album_id in Lp().albums.get_ids([artist_id], []):
                    if (album_id, artist_id) not in albums:
                        albums.append((album_id, artist_id))
                for track_id, track_name in Lp(
                                   ).tracks.get_as_non_album_artist(artist_id):
                    tracks_non_album_artist.append((track_id, track_name))

            for album_id, artist_id in albums:
                if cancellable.is_cancelled():
                    return
                if album_id in added_album_ids:
                    continue
                search_item = SearchItem()
                search_item.id = album_id
                added_album_ids.append(album_id)
                search_item.is_track = False
                search_item.artist_ids = [artist_id]
                search_item.year = Lp().albums.get_year(album_id)
                items.append(search_item)

            try:
                year = int(item)
                albums = Lp().albums.get_by_year(year)
            except:
                albums = []
            albums += Lp().albums.search(item)
            for album_id in albums:
                if cancellable.is_cancelled():
                    return
                if album_id in added_album_ids:
                    continue
                search_item = SearchItem()
                search_item.id = album_id
                added_album_ids.append(album_id)
                search_item.is_track = False
                search_item.artist_ids = Lp().albums.get_artist_ids(album_id)
                search_item.year = Lp().albums.get_year(album_id)
                items.append(search_item)

            for track_id, track_name in Lp().tracks.search(
                                               item) + tracks_non_album_artist:
                if cancellable.is_cancelled():
                    return
                if track_id in added_track_ids:
                    continue
                search_item = SearchItem()
                search_item.id = track_id
                added_track_ids.append(track_id)
                search_item.is_track = True
                search_item.artist_ids = Lp().tracks.get_artist_ids(track_id)
                items.append(search_item)
        return items
