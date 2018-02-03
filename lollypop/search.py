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

from lollypop.define import App
from lollypop.helper_task import TaskHelper
from lollypop.objects import Album, Track


class Search:
    """
        Local search
    """

    def __init__(self):
        """
            Init search
        """
        self.__current_search = ""

    def get(self, current_search, cancellable, callback):
        """
            Get track for name
            @param current_search as str
            @param cancellable as Gio.Cancellable
            @param callback as callback
        """
        self.__current_search = current_search.lower()
        search_items = []
        for item in self.__current_search.split():
            if item not in search_items:
                search_items.append(item)
        helper = TaskHelper()
        helper.run(self.__get, search_items,
                   cancellable, callback=callback)

#######################
# PRIVATE             #
#######################
    def __calculate_score(self, string, search_items):
        """
            Calculate string score for search items
            @param string as str
            @param search_item as [str]
        """
        split_string = string.lower().split()
        join = list(set(split_string) & set(search_items))
        return len(join)

    def __get(self, search_items, cancellable):
        """
            Get track for name
            @param search_items as [str]
            @param cancellable as Gio.Cancellable
            @return items as [SearchItem]
        """
        album_ids = []
        track_ids = []
        albums = []
        for item in search_items:
            if cancellable.is_cancelled():
                return
            # Get all albums for all artists and non album_artist tracks
            for artist_id in App().artists.search(item):
                if cancellable.is_cancelled():
                    return
                for album_id in App().albums.get_ids([artist_id], []):
                    if (album_id, artist_id) not in albums:
                        album_ids.append(album_id)
                for track_id in App().tracks.get_for_artist(artist_id):
                    track_ids.append(track_id)
            try:
                year = int(item)
                album_ids += App().albums.get_by_year(year)
            except:
                pass
            album_ids += App().albums.search(item)
            for track_id in App().tracks.search(item):
                track_ids.append(track_id)

        # Create albums for tracks
        album_tracks = {}
        for track_id in list(set(track_ids)):
            track = Track(track_id)
            score = self.__calculate_score(track.name, search_items)
            for artist in track.artists:
                score += self.__calculate_score(artist, search_items)
            # Score existing album
            if track.album.id in album_ids:
                # Remove all album.id occurences
                album_ids = list(filter((track.album.id).__ne__, album_ids))
            # Get a new album
            album = track.album
            if album.id in album_tracks.keys():
                (album, tracks, score) = album_tracks[album.id]
                tracks.append(track)
                album_tracks[track.album.id] = (album, tracks, score)
            else:
                album_tracks[track.album.id] = (album, [track], score)
        # Create albums for album results
        for album_id in list(set(album_ids)):
            album = Album(album_id)
            score = self.__calculate_score(album.name, search_items)
            for artist in album.artists:
                score += self.__calculate_score(artist, search_items)
            albums.append((score, album))
        # Merge albums from track results
        for key in album_tracks.keys():
            (album, tracks, score) = album_tracks[key]
            album.set_tracks(tracks)
            albums.append((score, album))
        albums.sort(key=lambda tup: tup[0], reverse=True)
        return [album for (score, album) in albums]
