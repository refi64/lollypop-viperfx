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

from gi.repository import GObject

import random

from lollypop.define import PlayerContext, Shuffle


# Manage user playlist
class UserPlaylistPlayer:
    """
        Init user playlist
    """
    def __init__(self):
        # A user playlist used as current playlist
        self._user_playlist = None
        # Used by shuffle tracks to restore user playlist before shuffle
        self._user_playlist_backup = None
        
        # Should be overriden by parent class
        # Albums in current player playlist
        self._albums = None
        # Used by shuffle albums to restore playlist before shuffle
        self._albums_backup = None
        self._shuffle = Shuffle.NONE

    """
        Set user playlist as current playback playlist
        @param array of track id as int
        @param starting track id as int
    """
    def set_user_playlist(self, tracks, track_id):
        self._user_playlist = tracks
        self.context.album_id = None
        self.context.position = self._user_playlist.index(track_id)
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

#######################
# PRIVATE             #
#######################
    """
        Shuffle/Un-shuffle playlist based on shuffle setting
    """
    def _shuffle_playlist(self):
        if self._shuffle in [Shuffle.ALBUMS, Shuffle.ALBUMS_ARTIST]:
            # No albums shuffle when playing a user playlist
            if self._user_playlist_backup is not None:
                self._user_playlist = self._user_playlist_backup
                self.context.position = self._user_playlist.index(
                                                              self.current.id)
                self._user_playlist_backup = None
        elif self._shuffle in [Shuffle.TRACKS, Shuffle.TRACKS_ARTIST]:
            # Shuffle user playlist
            if self._user_playlist is not None:
                self._user_playlist_backup = list(self._user_playlist)
                current = self._user_playlist.pop(self.context.position)
                random.shuffle(self._user_playlist)
                self._user_playlist.insert(0, current)
                self.context.position = 0

        # Unshuffle
        elif self._shuffle == Shuffle.NONE:
            if self._user_playlist_backup is not None:
                self._user_playlist = self._user_playlist_backup
                self.context.position = self._user_playlist.index(
                                                              self.current.id)
                self._user_playlist_backup = None
