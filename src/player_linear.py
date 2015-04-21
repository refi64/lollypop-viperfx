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

from lollypop.define import Objects

# Manage normal playback
# Can only be used as child of Player class
class LinearPlayer:
    """
        Init linear player
    """
    def __init__(self):
        pass

    """
        Next track based on current context
        @param sql as sqlite cursor
        @return track id as int or None
    """
    def next(self, sql=None):
        track_id = None
        if self.context.position is not None and self._albums:
            tracks = Objects.albums.get_tracks(self.context.album_id,
                                               self.context.genre_id,
                                               sql)
            if self.context.position + 1 >= len(tracks):  # next album
                pos = self._albums.index(self.context.album_id)
                # we are on last album, go to first
                if pos + 1 >= len(self._albums):
                    pos = 0
                else:
                    pos += 1
                self.context.album_id = self._albums[pos]
                self.context.position = 0
                track_id = Objects.albums.get_tracks(self._albums[pos],
                                                     self.context.genre_id,
                                                     sql)[0]
            else:
                self.context.position += 1
                track_id = tracks[self.context.position]
        return track_id

    """
        Prev track base on current context
        @param sql as sqlite cursor
        @return track id as int or None
    """
    def prev(self, sql=None):
        track_id = None
        if track_id is None and self.context.position is not None:
            tracks = Objects.albums.get_tracks(self.current.album_id,
                                               self.current.genre_id)
            if self.context.position <= 0:  # Prev album
                pos = self._albums.index(self.current.album_id)
                if pos - 1 < 0:  # we are on last album, go to first
                    pos = len(self._albums) - 1
                else:
                    pos -= 1
                self.current.album_id = self._albums[pos]
                tracks = Objects.albums.get_tracks(self.current.album_id,
                                                   self.current.genre_id)
                self.context.album_id = self.current.album_id
                self.context.position = len(tracks) - 1
                track_id = tracks[self.context.position]
            else:
                self.context.position -= 1
                track_id = tracks[self.context.position]
        return track_id
