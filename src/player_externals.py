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

from gi.repository import GLib

from lollypop.define import Type
from lollypop.player_base import BasePlayer
from lollypop.track import Track


# Manage user playlist
class ExternalsPlayer(BasePlayer):
    """
        Init user playlist
    """
    def __init__(self):
        BasePlayer.__init__(self)
        self._uris = []

    """
        Play track
        @param track as Track
    """
    def load(self, track):
        pass

    """
        Load track
    """
    def load_first_external(self):
        if self._uris:
            track = Track()
            track.uri = self._uris[0]
            if track.uri.startswith('file://'):
                track.id = Type.EXTERNAL
            else:
                track.id = Type.RADIOS
            self.load(track)

    """
        Load external tracks and play first track
        @param uri as str
    """
    def load_external(self, uri):
        try:
            self._uris.append(GLib.filename_to_uri(uri))
        except:
            self._uris.append(uri)
    """
        Clear externals
    """
    def clear_externals(self):
        self._uris = []

    """
        Next Track
        @return Track
    """
    def next(self):
        track = Track()
        if self._uris and self.current_track.uri in self._uris:
            idx = self._uris.index(self.current_track.uri)
            if idx + 1 >= len(self._uris):
                idx = 0
            else:
                idx += 1
            track.uri = self._uris[idx]
            if track.uri.startswith('file://'):
                track.id = Type.EXTERNAL
            else:
                track.id = Type.RADIOS
        return track

    """
        Prev track id
        @return Track
    """
    def prev(self):
        track = Track()
        if self._uris and self.current_track.uri in self._uris:
            idx = self._uris.index(self.current_track.uri)
            if idx - 1 < 0:
                idx = len(self._uris) - 1
            else:
                idx -= 1

            track.uri = self._uris[idx]
            if track.uri.startswith('file://'):
                track.id = Type.EXTERNAL
            else:
                track.id = Type.RADIOS
        return track

#######################
# PRIVATE             #
#######################
