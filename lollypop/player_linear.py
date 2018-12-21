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
from lollypop.logger import Logger


class LinearPlayer(BasePlayer):
    """
        Manage normal playback
    """

    def __init__(self):
        """
            Init linear player
        """
        BasePlayer.__init__(self)

    def next(self):
        """
            Next track for current album or next album
            @return track as Track
        """
        # If no album available, repeat current track
        if not self._albums:
            return self._current_track
        album = self._current_track.album
        new_track_position = self._current_track.position + 1
        # next album
        if new_track_position >= len(album.track_ids):
            try:
                pos = self.album_ids.index(album.id)
                # we are on last album, go to first
                if pos + 1 >= len(self._albums):
                    self._next_context = NextContext.STOP
                    pos = 0
                else:
                    pos += 1
            except Exception as e:
                Logger.error("LinearPlayer::next(): %s", e)
                pos = 0  # Happens if current album has been removed
            track = self._albums[pos].tracks[0]
        # next track
        else:
            track = album.tracks[new_track_position]
        return track

    def prev(self):
        """
            Prev track base on.current_track context
            @return track as Track
        """
        # If no album available, repeat current track
        if not self._albums:
            return self._current_track
        album = self._current_track.album
        new_track_position = self._current_track.position - 1
        # Previous album
        if new_track_position < 0:
            try:
                pos = self.album_ids.index(album.id)
                if pos - 1 < 0:  # we are on last album, go to first
                    pos = len(self._albums) - 1
                else:
                    pos -= 1
            except Exception as e:
                Logger.error("LinearPlayer::prev(): %s", e)
                pos = 0  # Happens if current album has been removed
            track = self._albums[pos].tracks[-1]
        # Previous track
        else:
            track = album.tracks[new_track_position]
        return track
