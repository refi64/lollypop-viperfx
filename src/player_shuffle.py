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

import random

from lollypop.define import Shuffle, NextContext, Lp, Type
from lollypop.player_base import BasePlayer
from lollypop.objects import Track, Album
from lollypop.list import LinkedList


class ShufflePlayer(BasePlayer):
    """
        Shuffle player
        Manage shuffle tracks and party mode
    """

    def __init__(self):
        """
            Init shuffle player
        """
        BasePlayer.__init__(self)
        self.reset_history()
        # Party mode
        self._is_party = False
        Lp().settings.connect('changed::shuffle', self._set_shuffle)

    def reset_history(self):
        """
            Reset history
        """
        # Tracks already played
        self._history = []
        # Used by shuffle albums to restore playlist before shuffle
        self._albums_backup = []
        # Albums already played
        self._already_played_albums = []
        # Tracks already played for albums
        self._already_played_tracks = {}
        # Reset use playlist
        self._user_playlist = []

    def next(self):
        """
            Next shuffle track
            @return Track
        """
        track_id = None
        if self._shuffle == Shuffle.TRACKS or self._is_party:
            if self._history and self._history.has_next():
                track_id = self._history.get_next().get_value()
            elif self._albums:
                track_id = self._shuffle_next()
        return Track(track_id)

    def prev(self):
        """
            Prev track based on history
            @return Track
        """
        track_id = None
        if self._shuffle == Shuffle.TRACKS or self._is_party:
            if self._history and self._history.has_prev():
                track_id = self._history.get_prev().get_value()
            else:
                track_id = self.current_track.id
        return Track(track_id)

    def get_party_ids(self):
        """
            Return party ids
            @return [ids as int]
        """
        party_settings = Lp().settings.get_value('party-ids')
        ids = []
        genre_ids = Lp().genres.get_ids()
        genre_ids.append(Type.POPULARS)
        genre_ids.append(Type.RECENTS)
        for setting in party_settings:
            if isinstance(setting, int) and\
               setting in genre_ids:
                ids.append(setting)
        return ids

    def set_party(self, party):
        """
            Set party mode on if party is True
            Play a new random track if not already playing
            @param party as bool
        """
        self.reset_history()

        if self._rg1.rgvolume is not None and self._rg2.rgvolume is not None:
            if party:
                self.context.next = NextContext.NONE
                self._rg1.rgvolume.props.album_mode = 0
                self._rg2.rgvolume.props.album_mode = 0
            else:
                self._rg1.rgvolume.props.album_mode = 1
                self._rg2.rgvolume.props.album_mode = 1

        self._is_party = party

        if party:
            self._external_tracks = []
            self.context.genre_ids = []
            self.context.track_id = None
            party_ids = self.get_party_ids()
            if party_ids:
                self._albums = Lp().albums.get_party_ids(party_ids)
            else:
                self._albums = Lp().albums.get_ids()

            # Start a new song if not playing
            if (self.current_track.id in [None, Type.RADIOS])\
                    and self._albums:
                track_id = self._get_random()
                self.load(Track(track_id))
            elif not self.is_playing():
                self.play()
        else:
            # We need to put some context, take first available genre
            if self.current_track.id:
                self.set_albums(self.current_track.id,
                                [self.current_track.album_artist_id], [])
        self.emit('party-changed', party)

    def is_party(self):
        """
            True if party mode on
            @return bool
        """
        return self._is_party

    def shuffle_albums(self, shuffle):
        """
            Shuffle album list
            @param shuffle as bool
        """
        if shuffle and self._shuffle == Shuffle.ALBUMS:
            if self._albums:
                self._albums_backup = list(self._albums)
                random.shuffle(self._albums)
        elif self._albums_backup:
            self._albums = self._albums_backup
            self._albums_backup = []

#######################
# PRIVATE             #
#######################
    def _set_shuffle(self, settings, value):
        """
            Set shuffle mode to gettings value
            @param settings as Gio.Settings, value as str
        """
        self._shuffle = Lp().settings.get_enum('shuffle')

        if self._rg1.rgvolume is not None and self._rg2.rgvolume is not None:
            if self._shuffle == Shuffle.TRACKS or self._user_playlist:
                self._rg1.rgvolume.props.album_mode = 0
                self._rg2.rgvolume.props.album_mode = 0
            else:
                self._rg1.rgvolume.props.album_mode = 1
                self._rg2.rgvolume.props.album_mode = 1

        if self._user_playlist:
            self._shuffle_playlist()
        elif self._shuffle == Shuffle.NONE:
            self.shuffle_albums(False)
        elif self._shuffle == Shuffle.ALBUMS:
            self.shuffle_albums(True)
        if self.current_track.id is not None:
            self.set_next()

    def _shuffle_next(self):
        """
            Next track in shuffle mode
            @return track id as int
        """
        try:
            track_id = self._get_random()
            # Need to clear history
            if track_id is None:
                self._albums = self._already_played_albums
                self.reset_history()
                return self._shuffle_next()
            return track_id
        except:  # Recursion error
            return None

    def _get_random(self):
        """
            Return a random track and make sure it has never been played
        """
        for album_id in sorted(self._albums,
                               key=lambda *args: random.random()):
            tracks = Album(album_id, self.context.genre_ids).tracks_ids
            for track in sorted(tracks, key=lambda *args: random.random()):
                if album_id not in self._already_played_tracks.keys() or\
                   track not in self._already_played_tracks[album_id]:
                    return track
            self._finished = NextContext.STOP_ALBUM
            # No new tracks for this album, remove it
            # If albums not in shuffle history, it's not present
            # in db anymore (update since shuffle set)
            if album_id in self._already_played_tracks.keys():
                self._already_played_tracks.pop(album_id)
                self._already_played_albums.append(album_id)
            self._albums.remove(album_id)
        self._finished = NextContext.STOP_ALL
        return None

    def _add_to_shuffle_history(self, track):
        """
            Add a track to shuffle history
            @param track as Track
        """
        if track.album_id not in self._already_played_tracks.keys():
            self._already_played_tracks[track.album_id] = []
        if track.id not in self._already_played_tracks[track.album_id]:
            self._already_played_tracks[track.album_id].append(track.id)

    def _on_stream_start(self, bus, message):
        """
            On stream start add to shuffle history
        """
        # Add track to shuffle history if needed
        if self._shuffle != Shuffle.NONE or self._is_party:
            if self._history:
                next = self._history.get_next()
                prev = self._history.get_prev()
                # Next track
                if next is not None and\
                        self.current_track.id == next.get_value():
                    next = self._history.get_next()
                    next.set_prev(self._history)
                    self._history = next
                # Previous track
                elif prev is not None and\
                        self.current_track.id == prev.get_value():
                    prev = self._history.get_prev()
                    prev.set_next(self._history)
                    self._history = prev
                # New track
                elif self._history.get_value() != self.current_track.id:
                    new_list = LinkedList(self.current_track.id,
                                          None,
                                          self._history)
                    self._history = new_list
            else:
                new_list = LinkedList(self.current_track.id)
                self._history = new_list
            self._add_to_shuffle_history(self.current_track)
