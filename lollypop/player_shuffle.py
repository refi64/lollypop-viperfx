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

import random
from threading import Thread

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
        # Party mode
        self.__is_party = False
        self.reset_history()
        Lp().settings.connect("changed::shuffle", self.__set_shuffle)

    def reset_history(self):
        """
            Reset history
        """
        # Tracks already played
        self.__history = []
        # Used by shuffle albums to restore playlist before shuffle
        self._albums_backup = []
        # Albums already played
        self.__already_played_albums = []
        # Tracks already played for albums
        self.__already_played_tracks = {}
        # If we have tracks/albums to ignore in party mode, add them
        t = Thread(target=self.__init_party_blacklist)
        t.daemon = True
        t.start()
        # Reset user playlist
        self._user_playlist = []
        self._user_playlist_ids = []

    @property
    def shuffle_has_next(self):
        """
            True if history provide a next track
            @return bool
        """
        return self.__history and self.__history.has_next()

    @property
    def shuffle_has_prev(self):
        """
            True if history provide a prev track
            @return bool
        """
        return self.__history and self.__history.has_prev()

    def next(self):
        """
            Next shuffle track
            @return Track
        """
        track_id = None
        if self._shuffle == Shuffle.TRACKS or self.__is_party:
            if self.shuffle_has_next:
                track_id = self.__history.get_next().get_value()
            elif self._albums:
                track_id = self.__shuffle_next()
            else:
                track_id = self._current_track.id
        return Track(track_id)

    def prev(self):
        """
            Prev track based on history
            @return Track
        """
        track_id = None
        if self._shuffle == Shuffle.TRACKS or self.__is_party:
            if self.shuffle_has_prev:
                track_id = self.__history.get_prev().get_value()
            else:
                track_id = self._current_track.id
        return Track(track_id)

    def get_party_ids(self):
        """
            Return party ids
            @return [ids as int]
        """
        party_settings = Lp().settings.get_value("party-ids")
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
        self.__is_party = party
        albums_backup = self._albums_backup
        self.reset_history()

        if self._plugins1.rgvolume is not None and\
           self._plugins2.rgvolume is not None:
            if party:
                self._plugins1.rgvolume.props.album_mode = 0
                self._plugins2.rgvolume.props.album_mode = 0
            else:
                self._plugins1.rgvolume.props.album_mode = 1
                self._plugins2.rgvolume.props.album_mode = 1

        if party:
            self._albums_backup = self._albums
            self._external_tracks = []
            self._context.genre_ids = {}
            self.set_party_ids()
            # Start a new song if not playing
            if (self._current_track.id in [None, Type.RADIOS])\
                    and self._albums:
                track_id = self.__get_random()
                self.load(Track(track_id))
            elif not self.is_playing:
                self.play()
        else:
            self._albums = albums_backup
            # We want current album to continue playback
            if self._current_track.album.id not in self._albums:
                self._albums.insert(0, self._current_track.album.id)
            self.set_next()
            self.set_prev()
        self.emit("party-changed", party)

    @property
    def is_party(self):
        """
            True if party mode on
            @return bool
        """
        return self.__is_party

    def shuffle_albums(self, shuffle):
        """
            Shuffle album list
            @param shuffle as bool
        """
        if shuffle and self._shuffle == Shuffle.ALBUMS:
            if self._albums:
                self._albums_backup = list(self._albums)
                random.shuffle(self._albums)
                # In album shuffle, keep current album on top
                if self._current_track.album.id in self._albums:
                    self._albums.remove(self._current_track.album.id)
                    self._albums.insert(0, self._current_track.album.id)
        elif self._albums_backup:
            self._albums = self._albums_backup
            self._albums_backup = []

    def set_party_ids(self):
        """
            Set party mode ids
        """
        party_ids = self.get_party_ids()
        if party_ids:
            self._albums = Lp().albums.get_party_ids(party_ids)
        else:
            self._albums = Lp().albums.get_ids()
        # We do not store genre_ids for ALL/POPULARS/...
        genre_ids = []
        for genre_id in party_ids:
            if genre_id > 0:
                genre_ids.append(genre_id)
        # Set context for each album
        for album_id in self._albums:
            self._context.genre_ids[album_id] = genre_ids
            self._context.artist_ids[album_id] = []

#######################
# PROTECTED           #
#######################
    def _on_stream_start(self, bus, message):
        """
            On stream start add to shuffle history
        """
        # Add track to shuffle history if needed
        if self._shuffle == Shuffle.TRACKS or self.__is_party:
            if self.__history:
                next = self.__history.get_next()
                prev = self.__history.get_prev()
                # Next track
                if next is not None and\
                        self._current_track.id == next.get_value():
                    next = self.__history.get_next()
                    next.set_prev(self.__history)
                    self.__history = next
                # Previous track
                elif prev is not None and\
                        self._current_track.id == prev.get_value():
                    prev = self.__history.get_prev()
                    prev.set_next(self.__history)
                    self.__history = prev
                # New track
                elif self.__history.get_value() != self._current_track.id:
                    new_list = LinkedList(self._current_track.id,
                                          None,
                                          self.__history)
                    self.__history = new_list
            else:
                new_list = LinkedList(self._current_track.id)
                self.__history = new_list
            self.__add_to_shuffle_history(self._current_track)

#######################
# PRIVATE             #
#######################
    def __set_shuffle(self, settings, value):
        """
            Set shuffle mode to gettings value
            @param settings as Gio.Settings, value as str
        """
        self._shuffle = Lp().settings.get_enum("shuffle")

        if self._plugins1.rgvolume is not None and\
           self._plugins2.rgvolume is not None:
            if self._shuffle == Shuffle.TRACKS or self._user_playlist:
                self._plugins1.rgvolume.props.album_mode = 0
                self._plugins2.rgvolume.props.album_mode = 0
            else:
                self._plugins1.rgvolume.props.album_mode = 1
                self._plugins2.rgvolume.props.album_mode = 1

        if self._user_playlist:
            self._shuffle_playlist()
        elif self._shuffle == Shuffle.NONE:
            self.shuffle_albums(False)
        elif self._shuffle == Shuffle.ALBUMS:
            self.shuffle_albums(True)
        if self._current_track.id is not None:
            self.set_next()

    def __shuffle_next(self):
        """
            Next track in shuffle mode
            @return track id as int
        """
        try:
            track_id = self.__get_random()
            # Need to clear history
            if track_id is None:
                self._albums = self.__already_played_albums
                self.reset_history()
                return self.__shuffle_next()
            return track_id
        except:  # Recursion error
            return None

    def __get_random(self):
        """
            Return a random track and make sure it has never been played
        """
        for album_id in sorted(self._albums,
                               key=lambda *args: random.random()):
            # We need to check this as in party mode, some items do not
            # have a valid genre (Populars, ...)
            if album_id in self._context.genre_ids.keys():
                genre_ids = self._context.genre_ids[album_id]
            else:
                genre_ids = []
            tracks = Album(album_id, genre_ids).track_ids
            for track in sorted(tracks, key=lambda *args: random.random()):
                if album_id not in self.__already_played_tracks.keys() or\
                   track not in self.__already_played_tracks[album_id]:
                    return track
            # No new tracks for this album, remove it
            # If albums not in shuffle history, it"s not present
            # in db anymore (update since shuffle set)
            if album_id in self.__already_played_tracks.keys():
                self.__already_played_tracks.pop(album_id)
                self.__already_played_albums.append(album_id)
            self._albums.remove(album_id)
        self._next_context = NextContext.STOP
        return None

    def __add_to_shuffle_history(self, track):
        """
            Add a track to shuffle history
            @param track as Track
        """
        if track.album_id not in self.__already_played_tracks.keys():
            self.__already_played_tracks[track.album_id] = []
        if track.id not in self.__already_played_tracks[track.album_id]:
            self.__already_played_tracks[track.album_id].append(track.id)

    def __init_party_blacklist(self):
        """
            Add party mode blacklist to already played tracks
        """
        if self.__is_party:
            for track_id in Lp().playlists.get_track_ids(Type.NOPARTY):
                track = Track(track_id)
                self.__add_to_shuffle_history(track)
