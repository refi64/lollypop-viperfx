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
from lollypop.player_base import PlayerBase
from lollypop.track import Track


# Manage user playlist
class ExternalsPlayer(PlayerBase):
    """
        Init user playlist
    """
    def __init__(self):
        PlayerBase.__init__(self)

    """
        Play track
        @param track as Track
    """
    def load(self, track):
        pass

    """
        Load external tracks
        @param uri as str
        @param name as string
    """
    def load_external(self, uri, name=''):
        try:
            uri = GLib.filename_to_uri(uri)
        except:
            pass
        track = Track()
        track.artist = name
        track.uri = uri
        if track.uri.startswith('file://'):
            track.id = Type.EXTERNALS
        else:
            track.id = Type.RADIOS
        self._external_tracks.append(track)

    """
        Play url if in externals
        @param url as string
    """
    def play_this_external(self, url):
        search = None
        for track in self._external_tracks:
            if track.uri == url:
                search = track
                break
        if search is not None:
            self.load(search)

    """
        Play first external track
    """
    def play_first_external(self):
        if self._external_tracks:
            self.load(self._external_tracks[0])

    """
        Clear externals
    """
    def clear_externals(self):
        self._external_tracks = []

    """
        Next Track
        @return Track
    """
    def next(self):
        track = Track()
        if self._external_tracks and\
           self.current_track in self._external_tracks:
            idx = self._external_tracks.index(self.current_track)
            if idx + 1 >= len(self._external_tracks):
                idx = 0
            else:
                idx += 1
            track = self._external_tracks[idx]
        return track

    """
        Prev track id
        @return Track
    """
    def prev(self):
        track = Track()
        if self._external_tracks and\
           self.current_track in self._external_tracks:
            idx = self._external_tracks.index(self.current_track)
            if idx - 1 < 0:
                idx = len(self._external_tracks) - 1
            else:
                idx -= 1

            track = self._external_tracks[idx]
        return track

#######################
# PRIVATE             #
#######################
