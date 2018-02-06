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

import random

from lollypop.define import Shuffle, NextContext
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
        self.__playlist_backup = []

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
        self.populate_playlist_by_track_ids([track.id for track in tracks],
                                            playlist_ids)

    def populate_playlist_by_track_ids(self, track_ids, playlist_ids):
        """
            Set user playlist as current playback playlist
            @param array of track_ids as [int]
            @param playlist ids as [int]
        """
        if self.is_party:
            self.set_party(False)
        self._albums = []
        self.__playlist_backup = []
        self._playlist_track_ids = track_ids
        self._playlist_ids = playlist_ids
        self._shuffle_playlist()

    def update_playlist(self, tracks):
        """
            Update user playlist content
            @param tracks as [Track]
        """
        if self._albums:
            return
        self._playlist_track_ids = [track.id for track in tracks]
        self.__playlist_backup = []
        self._shuffle_playlist()

    def get_playlist(self):
        """
            Get user playlist
            @return track id as [int]
        """
        if self.__playlist_backup:
            return self.__playlist_backup
        else:
            return self._playlist

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
        if self._playlist_track_ids and\
           current_track.id in self._playlist_track_ids:
            idx = self._playlist_track_ids.index(current_track.id)
            if idx + 1 >= len(self._playlist_track_ids):
                self._next_context = NextContext.STOP
                idx = 0
            else:
                idx += 1
            track = Track(self._playlist_track_ids[idx])
        return track

    def prev(self):
        """
            Prev track id
            @return Track
        """
        track = Track()
        if self._playlist_track_ids and\
           self._current_track.id in self._playlist_track_ids:
            idx = self._playlist_track_ids.index(self._current_track.id)
            if idx - 1 < 0:
                idx = len(self._playlist_track_ids) - 1
            else:
                idx -= 1
            track = Track(self._playlist_track_ids[idx])
        return track

#######################
# PROTECTED           #
#######################
    def _shuffle_playlist(self):
        """
            Shuffle/Un-shuffle playlist based on shuffle setting
        """
        if self._shuffle == Shuffle.TRACKS:
            # Shuffle user playlist
            if self._playlist_track_ids:
                self.__playlist_backup = list(self._playlist_track_ids)
                random.shuffle(self._playlist_track_ids)
        # Unshuffle
        else:
            if self.__playlist_backup:
                self._playlist_track_ids = self.__playlist_backup
                self.__playlist_backup = []
        self.set_next()
        self.set_prev()
