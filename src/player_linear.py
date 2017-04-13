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
            return self._current_track
        track = Track()
        if self._current_track.album.id in self._context.genre_ids and\
           self._albums:
            genre_ids = self._context.genre_ids[self._current_track.album.id]
            artist_ids = self._context.artist_ids[self._current_track.album.id]
            album = Album(self._current_track.album.id, genre_ids, artist_ids)
            if self._current_track.id in album.track_ids:
                new_track_position = album.track_ids.index(
                                                self._current_track.id) + 1
                # next album
                if new_track_position >= len(album.tracks):
                    try:
                        pos = self._albums.index(album.id)
                        # we are on last album, go to first
                        if pos + 1 >= len(self._albums):
                            self._next_context = NextContext.STOP
                            pos = 0
                        else:
                            pos += 1
                    except:
                        pos = 0  # Happens if current album has been removed
                    genre_ids = self._context.genre_ids[self._albums[pos]]
                    track = Album(self._albums[pos],
                                  genre_ids, artist_ids).tracks[0]
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
        track = Track()
        if self._current_track.album.id in self._context.genre_ids and \
           self._albums:
            genre_ids = self._context.genre_ids[self._current_track.album.id]
            artist_ids = self._context.artist_ids[self._current_track.album.id]
            album = Album(self._current_track.album.id, genre_ids, artist_ids)
            if self._current_track.id in album.track_ids:
                new_track_position = album.track_ids.index(
                                                self._current_track.id) - 1
                # Previous album
                if new_track_position < 0:
                    try:
                        pos = self._albums.index(album.id)
                        if pos - 1 < 0:  # we are on last album, go to first
                            pos = len(self._albums) - 1
                        else:
                            pos -= 1
                    except:
                        pos = 0  # Happens if current album has been removed
                    genre_ids = self._context.genre_ids[self._albums[pos]]
                    track = Album(self._albums[pos],
                                  genre_ids, artist_ids).tracks[-1]
                # Previous track
                else:
                    track = album.tracks[new_track_position]
        return track
