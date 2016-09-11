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

from lollypop.define import Lp


class SearchItem:
    """
        Represent a search item
    """
    def __init__(self):
        self.is_track = False
        self.id = None  # Always None for externals
        self.ex_id = None
        # Internal
        self.artist_ids = []
        # External
        self.artists = []
        self.album_name = ""
        self.name = ""
        self.track_number = 0
        self.cover = ""
        self.smallcover = ""
        self.subitems = []

    def exists_in_db(self):
        """
            Search if item exists in db
            @return bool
        """
        artist_ids = []
        for artist in self.artists:
            artist_id = Lp().artists.get_id(artist)
            artist_ids.append(artist_id)
        if self.is_track:
            for track_id in Lp().tracks.get_ids_for_name(self.name):
                db_artist_ids = Lp().tracks.get_artist_ids(track_id)
                union = list(set(artist_ids) & set(db_artist_ids))
                if union == db_artist_ids:
                    return True
        else:
            album_ids = Lp().albums.get_ids(artist_ids, [])
            for album_id in album_ids:
                album_name = Lp().albums.get_name(album_id)
                if album_name == self.album_name:
                    return True
        return False
