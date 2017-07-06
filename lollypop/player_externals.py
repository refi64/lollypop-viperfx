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

from gi.repository import GLib

from lollypop.define import Type
from lollypop.player_base import BasePlayer
from lollypop.objects import Track


class ExternalsPlayer(BasePlayer):
    """
        Manage user playlist
    """

    def __init__(self):
        """
            Init user playlist
        """
        BasePlayer.__init__(self)

    def load(self, track):
        """
            Play track
            @param track as Track
        """
        pass

    def load_external(self, uri, name=""):
        """
            Load external tracks
            @param uri as str
            @param name as string
        """
        track = Track()
        track.set_album_artists([name])
        track.set_uri(uri)
        if track.uri.startswith("file://"):
            track.id = Type.EXTERNALS
            track.name = GLib.path_get_basename(GLib.filename_from_uri(uri)[0])
        else:
            track.name = uri
            track.id = Type.RADIOS
        self._external_tracks.append(track)

    def play_this_external(self, uri):
        """
            Play url if in externals
            @param uri as string
        """
        search = None
        for track in self._external_tracks:
            if track.uri == uri:
                search = track
                break
        if search is not None:
            self.load(search)

    def play_first_external(self):
        """
            Play first external track
        """
        if self._external_tracks:
            self.load(self._external_tracks[0])

    def get_externals(self):
        """
            Return external list
            @return array of Track
        """
        return self._external_tracks

    def clear_externals(self):
        """
            Clear externals
        """
        self._external_tracks = []

    def next(self):
        """
            Next Track
            @return Track
        """
        track = Track()
        if self._external_tracks and\
           self._current_track in self._external_tracks:
            idx = self._external_tracks.index(self._current_track)
            if idx + 1 >= len(self._external_tracks):
                idx = 0
            else:
                idx += 1
            track = self._external_tracks[idx]
        return track

    def prev(self):
        """
            Prev track id
            @return Track
        """
        # If no prev, current
        if self._current_track.id == Type.EXTERNALS and\
                not self._external_tracks:
            return self._current_track
        track = Track()
        if self._external_tracks and\
           self._current_track in self._external_tracks:
            idx = self._external_tracks.index(self._current_track)
            if idx - 1 < 0:
                idx = len(self._external_tracks) - 1
            else:
                idx -= 1

            track = self._external_tracks[idx]
        return track

#######################
# PRIVATE             #
#######################
