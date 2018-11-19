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


from lollypop.define import NextContext
from lollypop.player_base import BasePlayer
from lollypop.objects import Track


class PlaylistPlayer(BasePlayer):
    """
        Manage user playlist
    """

    def __init__(self):
        """
            Init user playlist
        """
        BasePlayer.__init__(self)

    def get_playlist_ids(self):
        """
            Get playlist id
            @return id as int
        """
        return self._playlist_ids

    def populate_playlist_by_tracks(self, tracks, playlist_ids):
        """
            Set user playlist as current playback playlist
            @param array of tracks as [Track]
            @param playlist ids as [int]
        """
        if self.is_party:
            self.set_party(False)
        self._albums = []
        self._playlist_tracks = tracks
        self._playlist_ids = playlist_ids
        self.set_next()
        self.set_prev()

    def update_playlist(self, tracks):
        """
            Update user playlist content
            @param tracks as [Track]
        """
        if self._albums:
            return
        self._playlist_tracks = tracks

    def get_playlist_tracks(self):
        """
            Get user playlist tracks
            @return [Track]
        """
        return self._playlist_tracks

    def next(self, force):
        """
            Next Track
            @param force as bool
            @return Track
        """
        track = Track()
        if force:
            current_track = self._next_track
        else:
            current_track = self._current_track
        if self._playlist_tracks and\
           current_track in self._playlist_tracks:
            idx = self._playlist_tracks.index(current_track)
            if idx + 1 >= len(self._playlist_tracks):
                self._next_context = NextContext.STOP
                idx = 0
            else:
                idx += 1
            track = self._playlist_tracks[idx]
        return track

    def prev(self):
        """
            Prev track id
            @return Track
        """
        track = Track()
        if self._playlist_tracks and\
           self._current_track in self._playlist_tracks:
            idx = self._playlist_tracks.index(self._current_track)
            if idx - 1 < 0:
                idx = len(self._playlist_tracks) - 1
            else:
                idx -= 1
            track = self._playlist_tracks[idx]
        return track

#######################
# PROTECTED           #
#######################
