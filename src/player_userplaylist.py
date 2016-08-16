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

import random

from lollypop.define import Shuffle, Lp, NextContext
from lollypop.player_base import BasePlayer
from lollypop.objects import Track


class UserPlaylistPlayer(BasePlayer):
    """
        Manage user playlist
    """

    def __init__(self):
        """
            Init user playlist
        """
        BasePlayer.__init__(self)
        self.__user_playlist_ids = []
        self.__user_playlist = []
        self.__user_playlist_backup = []

    def get_user_playlist_ids(self):
        """
            Get playlist id
            @return id as int
        """
        return self.__user_playlist_ids

    def populate_user_playlist_by_tracks(self, track_ids, playlist_ids):
        """
            Set user playlist as current playback playlist
            @param array of track ids as [int]
            @param playlist ids as [int]
        """
        if not Lp().settings.get_value('repeat'):
            self._context.next = NextContext.STOP_ALL
        if Lp().player.is_party:
            Lp().player.set_party(False)
        self.__user_playlist = []
        for track_id in track_ids:
            self.__user_playlist.append(track_id)
        self._albums = []
        self.__user_playlist_ids = playlist_ids
        self.__user_playlist_backup = []
        self._shuffle_playlist()

    def update_user_playlist(self, track_ids):
        """
            Update user playlist content
            @param track_ids as int
        """
        if self._albums:
            return
        self.__user_playlist = track_ids
        self.__user_playlist_backup = []
        self._shuffle_playlist()

    def get_user_playlist(self):
        """
            Get user playlist
            @return track id as [int]
        """
        if self.__user_playlist_backup:
            return self.__user_playlist_backup
        else:
            return self.__user_playlist

    def next(self):
        """
            Next Track
            @return Track
        """
        track = Track()
        if self.__user_playlist and\
           self._current_track.id in self.__user_playlist:
            idx = self.__user_playlist.index(self._current_track.id)
            if idx + 1 >= len(self.__user_playlist):
                self._finished = NextContext.STOP_ALL
                idx = 0
            else:
                idx += 1
            track = Track(self.__user_playlist[idx])
        return track

    def prev(self):
        """
            Prev track id
            @return Track
        """
        track = Track()
        if self.__user_playlist and\
           self._current_track.id in self.__user_playlist:
            idx = self.__user_playlist.index(self._current_track.id)
            if idx - 1 < 0:
                idx = len(self.__user_playlist) - 1
            else:
                idx -= 1
            track = Track(self.__user_playlist[idx])
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
            if self.__user_playlist:
                self.__user_playlist_backup = list(self.__user_playlist)
                random.shuffle(self.__user_playlist)
        # Unshuffle
        else:
            if self.__user_playlist_backup:
                self.__user_playlist = self.__user_playlist_backup
                self.__user_playlist_backup = []
        self.set_next()
        self.set_prev()
