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

from lollypop.define import Lp, NextContext
from lollypop.player_base import PlayerBase
from lollypop.track import Track

# Manage normal playback
class PlayerLinear(PlayerBase):
    """
        Init linear player
    """
    def __init__(self):
        PlayerBase.__init__(self)

    """
        Next track based on.current_track context
        @return track as Track
    """
    def next(self):
        track_id = None
        if self._albums:
            tracks = Lp.albums.get_tracks(self.current_track.album_id,
                                          self.context.genre_id)
            if self.current_track.id in tracks:
                new_track_position = tracks.index(self.current_track.id) + 1
                # next album
                if new_track_position >= len(tracks) or\
                   self.context.next == NextContext.START_NEW_ALBUM:
                    self.context.next = NextContext.NONE
                    pos = self._albums.index(self.current_track.album_id)
                    # we are on last album, go to first
                    if pos + 1 >= len(self._albums):
                        pos = 0
                    else:
                        pos += 1
                    tracks = Lp.albums.get_tracks(self._albums[pos],
                                                  self.context.genre_id)
                    track_id = tracks[0]
                # next track
                else:
                    track_id = tracks[new_track_position]
        return Track(track_id)

    """
        Prev track base on.current_track context
        @return track as Track
    """
    def prev(self):
        track_id = None
        if self._albums:
            tracks = Lp.albums.get_tracks(self.current_track.album_id,
                                          self.context.genre_id)
            if self.current_track.id in tracks:
                new_track_position = tracks.index(self.current_track.id) - 1
                # Previous album
                if new_track_position < 0:
                    pos = self._albums.index(self.current_track.album_id)
                    if pos - 1 < 0:  # we are on last album, go to first
                        pos = len(self._albums) - 1
                    else:
                        pos -= 1
                    tracks = Lp.albums.get_tracks(self._albums[pos],
                                                  self.context.genre_id)
                    track_id = tracks[len(tracks) - 1]
                # Previous track
                else:
                    track_id = tracks[new_track_position]
        return Track(track_id)
