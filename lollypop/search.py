# Copyright (c) 2014-2018 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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
from lollypop.objects import Album, Track


class Search:
    """
        Local search
    """

    def __init__(self):
        """
            Init search
        """
        pass

    def get(self, current_search, cancellable, callback):
        """
            Get track for name
            @param current_search as str
            @param cancellable as Gio.Cancellable
            @param callback as callback
        """
        search_items = []
        for item in current_search.lower().split():
            if item not in search_items:
                search_items.append(item)
        App().task_helper.run(self.__get, search_items,
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
        explode_split = self.__explode_search_items(split_string)
        explode_search = self.__explode_search_items(search_items)
        join = list(set(explode_split) & set(explode_search))
        return len(join)

    def __explode_search_items(self, search_items):
        """
            Explose search items for all search possiblities
            @param search_items as [str]
            @return [str]
        """
        possibilities = []
        index = len(search_items)
        while index > 1:
            item = " ".join(search_items[:index])
            if item:
                possibilities.append(item)
            index -= 1
        index = len(search_items)
        while index >= 1:
            item = " ".join(search_items[index:])
            if item:
                possibilities.append(item)
            index -= 1
        return possibilities + search_items

    def __search_artists(self, search_items, cancellable):
        """
            Get artists for search
            @param search_items as [str]
            @param cancellable as Gio.Cancellable
            @return [int]
        """
        artist_ids = []
        for search_str in self.__explode_search_items(search_items):
            artist_ids += App().artists.search(search_str)
            if cancellable.is_cancelled():
                break
        return list(set(artist_ids))

    def __search_tracks(self, search_items, cancellable):
        """
            Get tracks for search items
            @param search_items as [str]
            @param cancellable as Gio.Cancellable
            @return track_ids as [int]
        """
        track_ids = []
        for search_str in self.__explode_search_items(search_items):
            track_ids += App().tracks.search(search_str)
            if cancellable.is_cancelled():
                break
        return list(set(track_ids))

    def __search_albums(self, search_items, cancellable):
        """
            Get albums for search items
            @param search_items as [str]
            @param cancellable as Gio.Cancellable
            @return track_ids as [int]
        """
        album_ids = []
        for search_str in self.__explode_search_items(search_items):
            album_ids = App().albums.search(search_str)
            if cancellable.is_cancelled():
                break
        # Same for year #TODO make this ok for all date + for tracks
        if not album_ids and not cancellable.is_cancelled():
            for search_str in self.__explode_search_items(search_items):
                try:
                    album_ids = App().albums.get_by_year(int(search_str))
                except:
                    pass
                if album_ids:
                    break
        return list(set(album_ids))

    def __get(self, search_items, cancellable):
        """
            Get track for name
            @param search_items as [str]
            @param cancellable as Gio.Cancellable
            @return items as [(int, Album, bool)]
        """
        album_ids = self.__search_albums(search_items, cancellable)
        track_ids = self.__search_tracks(search_items, cancellable)
        artist_ids = self.__search_artists(search_items, cancellable)
        # Get tracks/albums for artists
        for artist_id in set(artist_ids):
            if cancellable.is_cancelled():
                return []
            for album_id in App().albums.get_ids([artist_id], []):
                if album_id not in album_ids:
                    album_ids.append(album_id)
            for track_id in App().tracks.get_ids_by_artist(artist_id):
                if track_id not in track_ids:
                    track_ids.append(track_id)
        albums = []

        # Create albums for tracks
        album_tracks = {}
        for track_id in track_ids:
            track = Track(track_id)
            if track.album.id in album_ids:
                continue
            score = self.__calculate_score(track.name, search_items)
            for artist in track.artists:
                score += self.__calculate_score(artist, search_items)
            # Get a new album
            album = track.album
            if album.id in album_tracks.keys():
                (album, tracks, score) = album_tracks[album.id]
                tracks.append(track)
                album_tracks[track.album.id] = (album, tracks, score)
            else:
                album_tracks[track.album.id] = (album, [track], score)
        # Create albums for album results
        for album_id in album_ids:
            album = Album(album_id)
            score = self.__calculate_score(album.name, search_items)
            for artist in album.artists:
                score += self.__calculate_score(artist, search_items)
            albums.append((score, album, False))
        # Merge albums from track results
        for key in album_tracks.keys():
            (album, tracks, score) = album_tracks[key]
            album.set_tracks(tracks)
            albums.append((score, album, True))
        albums.sort(key=lambda tup: tup[0], reverse=True)
        return albums
