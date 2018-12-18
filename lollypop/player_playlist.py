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

from gi.repository import GLib

from lollypop.define import NextContext, App
from lollypop.player_base import BasePlayer
from lollypop.objects import Track


class PlaylistPlayer(BasePlayer):
    """
        Manage user playlist
        Assertion: we never have same track ids in playlists player
    """

    def __init__(self):
        """
            Init user playlist
        """
        BasePlayer.__init__(self)

    def insert_track(self, track, position):
        """
            Insert track as position
            @param track as Track
            @param position as int
        """
        self._playlist_tracks.insert(position, track)
        self.set_next()
        self.set_prev()
        self.emit("playlist-changed")

    def remove_track(self, track_id):
        """
            Remove track from player
            @param track_id as int
        """
        for track in self._playlist_tracks:
            if track.id == track_id:
                self._playlist_tracks.remove(track)
                break
        self.set_next()
        self.set_prev()
        self.emit("playlist-changed")

    def populate_playlist_by_tracks(self, tracks, playlist_ids):
        """
            Set user playlist as current playback playlist
            @param array of tracks as [Track]
            @param playlist ids as [int]
        """
        App().lookup_action("party").change_state(GLib.Variant("b", False))
        self._albums = []
        self._playlist_tracks = tracks
        self._playlist_ids = playlist_ids
        self.set_next()
        self.set_prev()
        self.emit("playlist-changed")

    def update_playlist(self, tracks):
        """
            Update user playlist content
            @param tracks as [Track]
        """
        if self._albums:
            return
        self._playlist_tracks = tracks
        self.emit("playlist-changed")

    def next(self, force):
        """
            Next Track
            @param force as bool
            @return Track
        """
        track = Track()
        if force:
            current_track_id = self._next_track.id
        else:
            current_track_id = self._current_track.id
        track_ids = self.playlist_track_ids
        if track_ids and current_track_id in track_ids:
            idx = track_ids.index(current_track_id)
            if idx + 1 >= len(track_ids):
                self._next_context = NextContext.STOP
                idx = 0
            else:
                idx += 1
            track = self._playlist_tracks[idx]
        return track

    def prev(self):
        """
            Prev track id
            @return Track
        """
        track = Track()
        current_track_id = self._current_track.id
        track_ids = self.playlist_track_ids
        if track_ids and current_track_id in track_ids:
            idx = track_ids.index(current_track_id)
            if idx - 1 < 0:
                idx = len(track_ids) - 1
            else:
                idx -= 1
            track = self._playlist_tracks[idx]
        return track

    @property
    def playlist_tracks(self):
        """
            Get playlist tracks
            @return Track
        """
        return self._playlist_tracks

    @property
    def playlist_track_ids(self):
        """
            Get playlist track ids
            @return [int]
        """
        return [track.id for track in self._playlist_tracks]

    @property
    def playlist_ids(self):
        """
            Get playlist id
            @return id as int
        """
        return self._playlist_ids

#######################
# PROTECTED           #
#######################
