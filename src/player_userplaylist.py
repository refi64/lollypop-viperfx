# Copyright (c) 2014-2015 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

import random

from lollypop.define import Shuffle
from lollypop.player_base import BasePlayer
from lollypop.objects import Track


# Manage user playlist
class UserPlaylistPlayer(BasePlayer):
    """
        Init user playlist
    """
    def __init__(self):
        BasePlayer.__init__(self)
        self._user_playlist_id = None

    """
        Set playlist id
        @param id as int
    """
    def set_user_playlist_id(self, playlist_id):
        self._user_playlist_id = playlist_id

    """
        Get playlist id
        @return id as int
    """
    def get_user_playlist_id(self):
        return self._user_playlist_id

    """
        Set user playlist as current playback playlist
        @param array of tracks as [Track]
        @param track id as int
        @return track id as Track
    """
    def set_user_playlist(self, tracks, track_id):
        self._user_playlist = tracks
        self._shuffle_playlist()
        for track in tracks:
            if track.id == track_id:
                return track
        return None

    """
        Get user playlist
        @return track id as [int]
    """
    def get_user_playlist(self):
        return self._user_playlist

    """
        Next Track
        @return Track
    """
    def next(self):
        track = Track()
        if self._user_playlist and\
           self.current_track in self._user_playlist:
            idx = self._user_playlist.index(self.current_track)
            if idx + 1 >= len(self._user_playlist):
                idx = 0
            else:
                idx += 1
            track = self._user_playlist[idx]
        return track

    """
        Prev track id
        @return Track
    """
    def prev(self):
        track = Track()
        if self._user_playlist and\
           self.current_track in self._user_playlist:
            idx = self._user_playlist.index(self.current_track)
            if idx - 1 < 0:
                idx = len(self._user_playlist) - 1
            else:
                idx -= 1
            track = self._user_playlist[idx]
        return track

#######################
# PRIVATE             #
#######################
    """
        Shuffle/Un-shuffle playlist based on shuffle setting
    """
    def _shuffle_playlist(self):
        if self._shuffle == Shuffle.TRACKS:
            # Shuffle user playlist
            if self._user_playlist is not None:
                self._user_playlist_backup = list(self._user_playlist)
                random.shuffle(self._user_playlist)
        # Unshuffle
        else:
            if self._user_playlist_backup is not None:
                self._user_playlist = self._user_playlist_backup
                self._user_playlist_backup = None
        self.set_next()
        self.set_prev()
