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

from lollypop.define import Shuffle, NextContext, Objects


# Manage shuffle tracks and party mode
# Can only be used as child of Player class
class ShufflePlayer:
    """
        Init shuffle player
    """
    def __init__(self):
        # Used by shuffle albums to restore playlist before shuffle
        self._albums_backup = None
        # Albums already played
        self._already_played_albums = []
        # Tracks already played for albums
        self._already_played_tracks = {}
        # Party mode
        self._is_party = False

    """
        Next shuffle track
        @return track_id as int or None
    """
    def next(self, sql=None):
        track_id = None
        if self._shuffle in [Shuffle.TRACKS, Shuffle.TRACKS_ARTIST] or\
             self._is_party:
            if self._albums:
                track_id = self._shuffle_next(sql)
        return track_id

    """
        Prev track based on history
        @return track id as int or None
    """
    def prev(self):
        track_id = None
        if self._shuffle == Shuffle.TRACKS or self._is_party:
            try:
                track_id = self._played_tracks_history[-2]
                self._played_tracks_history.pop()
                self._played_tracks_history.pop()
            except:
                track_id = self.current.id
        return track_id

    """
        Return party ids
        @return [ids as int]
    """
    def get_party_ids(self):
        party_settings = Objects.settings.get_value('party-ids')
        ids = []
        genre_ids = Objects.genres.get_ids()
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
            self.context.next = NextContext.STOP_NONE
            self._rgvolume.props.album_mode = 0
        else:
            self._rgvolume.props.album_mode = 1
        self._is_party = party
        self._played_tracks_history = []
        if party:
            party_ids = self.get_party_ids()
            if party_ids:
                self._albums = Objects.albums.get_party_ids(party_ids)
            else:
                self._albums = Objects.albums.get_ids()
            # Start a new song if not playing
            if not self.is_playing() and self._albums:
                track_id = self._get_random()
                self.load(track_id)
        else:
            # We need to put some context, take first available genre
            if self.current.id:
                self.set_albums(self.current.id,
                                self.current.aartist_id, None)

    """
        True if party mode on
        @return bool
    """
    def is_party(self):
        return self._is_party

#######################
# PRIVATE             #
#######################g
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
        if force, stop current track
        a fresh sqlite cursor should be passed as sql if we are in a thread
        @param sqlite cursor
        @return track id as int
    """
    def _shuffle_next(self, sql=None):
        track_id = self._get_random(sql)
        # Need to clear history
        if not track_id:
            self._albums = self._already_played_albums
            self._played_tracks_history = []
            self._already_played_tracks = {}
            self._already_played_albums = []
            return self._shuffle_next(sql)

        return track_id

    """
        Return a random track and make sure it has never been played
        @param sqlite cursor as sql if running in a thread
    """
    def _get_random(self, sql=None):
        for album_id in sorted(self._albums,
                               key=lambda *args: random.random()):
            tracks = Objects.albums.get_tracks(album_id,
                                               self.current.genre_id,
                                               sql)
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
