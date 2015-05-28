#!/usr/bin/python
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
from lollypop.track import Track


# Manage user playlist
class UserPlaylistPlayer(BasePlayer):
    """
        Init user playlist
    """
    def __init__(self):
        BasePlayer.__init__(self)
        self._position = 0

    """
        Set user playlist as current playback playlist
        @param array of track id as int
        @param starting track id as int
    """
    def set_user_playlist(self, tracks, track_id):
        self._user_playlist = tracks
        self._position = self._user_playlist.index(track_id)
        self._shuffle_playlist()

    """
        Add track to user playlist
    """
    def add_to_user_playlist(self, track_id):
        self._user_playlist.append(track_id)

    """
        Clear user playlist
    """
    def clear_user_playlist(self):
        self._user_playlist = []

    """
        Next track id
        @return Track
    """
    def next(self):
        track_id = None
        if self._user_playlist:
            self._position += 1
            if self._position >= len(self._user_playlist):
                self._position = 0
            track_id = self._user_playlist[self._position]
        return Track(track_id)

    """
        Prev track id
        @return Track
    """
    def prev(self):
        track_id = None
        if self._user_playlist:
            self._position -= 1
            if self._position < 0:
                self._position = len(self._user_playlist) - 1
            track_id = self._user_playlist[self._position]
        return Track(track_id)

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
                current = self._user_playlist.pop(self._position)
                random.shuffle(self._user_playlist)
                self._user_playlist.insert(0, current)
                self._position = 0
        # Unshuffle
        else:
            if self._user_playlist_backup is not None:
                self._user_playlist = self._user_playlist_backup
                self._position = self._user_playlist.index(
                    self.current_track.id)
                self._user_playlist_backup = None
