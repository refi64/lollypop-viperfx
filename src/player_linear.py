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

from lollypop.define import NextContext
from lollypop.player_base import BasePlayer
from lollypop.objects import Track, Album


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
            Next track based on.current_track context
            @return track as Track
        """
        # If no album available, repeat current track
        if not self._albums:
            return self.current_track

        track = Track()
        if self._albums is not None:
            album = Album(self.current_track.album.id, self.context.genre_id)
            if self.current_track.id in album.tracks_ids:
                new_track_position = album.tracks_ids.index(
                                                self.current_track.id) + 1
                # next album
                if new_track_position >= len(album.tracks) or\
                   self.context.next == NextContext.START_NEW_ALBUM:
                    if self.context.next == NextContext.START_NEW_ALBUM:
                        self.context.next = NextContext.NONE
                    pos = self._albums.index(album.id)
                    # we are on last album, go to first
                    if pos + 1 >= len(self._albums):
                        pos = 0
                    else:
                        pos += 1
                    track = Album(self._albums[pos],
                                  self.context.genre_id).tracks[0]
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
            return self.current_track

        track = Track()
        if self._albums is not None:
            album = Album(self.current_track.album.id, self.context.genre_id)
            if self.current_track.id in album.tracks_ids:
                new_track_position = album.tracks_ids.index(
                                                self.current_track.id) - 1
                # Previous album
                if new_track_position < 0:
                    pos = self._albums.index(album.id)
                    if pos - 1 < 0:  # we are on last album, go to first
                        pos = len(self._albums) - 1
                    else:
                        pos -= 1
                    track = Album(self._albums[pos],
                                  self.context.genre_id).tracks[-1]
                # Previous track
                else:
                    track = album.tracks[new_track_position]
        return track
