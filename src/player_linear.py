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

from lollypop.define import NextContext, Type
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
        if self._albums:
            if self.current_track.album.id in self.context.genre_ids.keys():
                genre_ids = self.context.genre_ids[self.current_track.album.id]
            else:
                genre_ids = self.context.genre_ids[Type.ALL]
            album = Album(self.current_track.album.id, genre_ids)
            if self.current_track.id in album.tracks_ids:
                new_track_position = album.tracks_ids.index(
                                                self.current_track.id) + 1
                # next album
                if new_track_position >= len(album.tracks) or\
                   self.context.next == NextContext.START_NEW_ALBUM:
                    if self.context.next == NextContext.START_NEW_ALBUM:
                        self.context.next = NextContext.NONE
                    try:
                        self._finished = NextContext.STOP_ALBUM
                        pos = self._albums.index(album.id)
                        # we are on last album, go to first
                        if pos + 1 >= len(self._albums):
                            self._finished = NextContext.STOP_ALL
                            pos = 0
                        else:
                            pos += 1
                    except:
                        pos = 0  # Happens if current album has been removed
                    if self.current_track.album.id in\
                            self.context.genre_ids.keys():
                        genre_ids = self.context.genre_ids[self._albums[pos]]
                    else:
                        genre_ids = self.context.genre_ids[Type.ALL]
                    track = Album(self._albums[pos],
                                  genre_ids).tracks[0]
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
        if self._albums:
            if self.current_track.album.id in self.context.genre_ids.keys():
                genre_ids = self.context.genre_ids[self.current_track.album.id]
            else:
                genre_ids = self.context.genre_ids[Type.ALL]
            album = Album(self.current_track.album.id, genre_ids)
            if self.current_track.id in album.tracks_ids:
                new_track_position = album.tracks_ids.index(
                                                self.current_track.id) - 1
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
                    if self.current_track.album.id in\
                            self.context.genre_ids.keys():
                        genre_ids = self.context.genre_ids[self._albums[pos]]
                    else:
                        genre_ids = self.context.genre_ids[Type.ALL]
                    track = Album(self._albums[pos],
                                  genre_ids).tracks[-1]
                # Previous track
                else:
                    track = album.tracks[new_track_position]
        return track
