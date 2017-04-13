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
        self.name = ""
        self.track_number = 0
        self.cover = ""
        self.smallcover = ""
        self.year = None
        self.subitems = []
        self.album = None
        self.mtime = 0

    def exists_in_db(self):
        """
            Search if item exists in db
            @return (bool, int)
        """
        artist_ids = []
        for artist in self.artists:
            artist_id = Lp().artists.get_id(artist)
            artist_ids.append(artist_id)
        if self.is_track:
            album_id = Lp().albums.get_id(self.album.name, artist_ids, True)
            track_id = Lp().tracks.get_id_by(self.name,
                                             album_id,
                                             artist_ids)
            return (track_id is not None, track_id)
        else:
            album_id = Lp().albums.get_id(self.name, artist_ids, True)
            return (album_id is not None, album_id)
        return (False, None)
