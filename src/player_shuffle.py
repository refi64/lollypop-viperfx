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

import random

from lollypop.define import Shuffle, NextContext, Lp, Type
from lollypop.player_base import BasePlayer
from lollypop.track import Track


# Manage shuffle tracks and party mode
class ShufflePlayer(BasePlayer):
    """
        Init shuffle player
    """
    def __init__(self):
        BasePlayer.__init__(self)
        self.reset_history()
        # Party mode
        self._is_party = False
        Lp.settings.connect('changed::shuffle', self._set_shuffle)

    """
        Reset history
    """
    def reset_history(self):
        # Position in history
        self._tracks_history_position = -1
        # Tracks already played
        self._played_tracks_history = []
        # Used by shuffle albums to restore playlist before shuffle
        self._albums_backup = None
        # Albums already played
        self._already_played_albums = []
        # Tracks already played for albums
        self._already_played_tracks = {}

    """
        Next shuffle track
        @return track_id as int or None
    """
    def next(self):
        track_id = None
        if self._shuffle in [Shuffle.TRACKS, Shuffle.TRACKS_ARTIST] or\
             self._is_party:
            # Get a new random track
            if self._tracks_history_position == \
                                        len(self._played_tracks_history) - 1:
                if self._albums:
                    track_id = self._shuffle_next()
            # Look in history
            else:
                track_id = self._played_tracks_history[
                                            self._tracks_history_position + 1]
        return Track(track_id)

    """
        Prev track based on history
        @return track id as int or None
    """
    def prev(self):
        track_id = None
        if self._tracks_history_position > 0:
            track_id = self._played_tracks_history[
                                            self._tracks_history_position - 1]
        else:
            track_id = self.current_track.id
        return Track(track_id)

    """
        Return party ids
        @return [ids as int]
    """
    def get_party_ids(self):
        party_settings = Lp.settings.get_value('party-ids')
        ids = []
        genre_ids = Lp.genres.get_ids()
        genre_ids.append(Type.POPULARS)
        genre_ids.append(Type.RECENTS)
        for setting in party_settings:
            if isinstance(setting, int) and\
               setting in genre_ids:
                ids.append(setting)
        return ids

    """
        Set party mode on if party is True
        Play a new random track if not already playing
        @param party as bool
    """
    def set_party(self, party):
        self._played_tracks_history = []
        self._already_played_tracks = {}
        self._already_played_albums = []
        self._user_playlist = None
        if party:
            self.context.next = NextContext.NONE
            self._rgvolume.props.album_mode = 0
        else:
            self._rgvolume.props.album_mode = 1
        self._is_party = party
        self._played_tracks_history = []
        if party:
            party_ids = self.get_party_ids()
            if party_ids:
                self._albums = Lp.albums.get_party_ids(party_ids)
            else:
                self._albums = Lp.albums.get_ids()

            # Start a new song if not playing
            if (self.current_track.id == Type.RADIOS or not self.is_playing())\
               and self._albums:
                track_id = self._get_random()
                self.load(Track(track_id))
            else:
                self._played_tracks_history.append(self.current_track.id)
                self._add_to_shuffle_history(self.current_track)
        else:
            # We need to put some context, take first available genre
            if self.current_track.id:
                self.set_albums(self.current_track.id,
                                self.current_track.aartist_id, None)
        self.emit('party-changed', party)
        Lp.window.update_view()

    """
        True if party mode on
        @return bool
    """
    def is_party(self):
        return self._is_party

#######################
# PRIVATE             #
#######################
    """
        Set shuffle mode to gettings value
        @param settings as Gio.Settings, value as str
    """
    def _set_shuffle(self, settings, value):
        self._shuffle = Lp.settings.get_enum('shuffle')

        if self._shuffle in [Shuffle.TRACKS, Shuffle.TRACKS_ARTIST] or\
           self._user_playlist:
            self._rgvolume.props.album_mode = 0
        else:
            self._rgvolume.props.album_mode = 1

        if self._user_playlist:
            self._shuffle_playlist()
        else:
            self.set_albums(self.current_track.id,
                            self.current_track.aartist_id,
                            self.context.genre_id)

    """
        Shuffle album list
    """
    def _shuffle_albums(self):
        if self._shuffle in [Shuffle.ALBUMS, Shuffle.ALBUMS_ARTIST]:
            if self._albums:
                self._albums_backup = list(self._albums)
                random.shuffle(self._albums)
        elif self._shuffle == Shuffle.NONE:
            if self._albums_backup:
                self._albums = self._albums_backup
                self._albums_backup = None

    """
        Next track in shuffle mode
        @return track id as int
    """
    def _shuffle_next(self):
        track_id = self._get_random()
        # Need to clear history
        if not track_id:
            self._albums = self._already_played_albums
            self.reset_history()
            return self._shuffle_next()

        return track_id

    """
        Return a random track and make sure it has never been played
    """
    def _get_random(self):
        for album_id in sorted(self._albums,
                               key=lambda *args: random.random()):
            tracks = Lp.albums.get_tracks(album_id,
                                          self.context.genre_id)
            for track in sorted(tracks, key=lambda *args: random.random()):
                if album_id not in self._already_played_tracks.keys() or\
                   track not in self._already_played_tracks[album_id]:
                    return track
            # No new tracks for this album, remove it
            # If albums not in shuffle history, it's not present
            # in db anymore (update since shuffle set)
            if album_id in self._already_played_tracks.keys():
                self._already_played_tracks.pop(album_id)
                self._already_played_albums.append(album_id)
            self._albums.remove(album_id)

        return None

    """
        Add a track to shuffle history
        @param track as Track
    """
    def _add_to_shuffle_history(self, track):
        if track.album_id not in self._already_played_tracks.keys():
            self._already_played_tracks[track.album_id] = []
        if track.id not in self._already_played_tracks[track.album_id]:
            self._already_played_tracks[track.album_id].append(track.id)

    """
        On stream start add to shuffle history
    """
    def _on_stream_start(self, bus, message):
        # Add track to shuffle history if needed
        if self._shuffle != Shuffle.NONE or self._is_party:
            if self.current_track.id in self._played_tracks_history:
                self._tracks_history_position =\
                       self._played_tracks_history.index(self.current_track.id)
            else:
                self._played_tracks_history.append(self.current_track.id)
                self._tracks_history_position += 1

            self._add_to_shuffle_history(self.current_track)
