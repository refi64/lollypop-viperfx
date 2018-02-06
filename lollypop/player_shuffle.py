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

import random

from lollypop.helper_task import TaskHelper
from lollypop.define import Shuffle, NextContext, App, Type
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
        App().settings.connect("changed::shuffle", self.__set_shuffle)

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
        helper = TaskHelper()
        helper.run(self.__init_party_blacklist)
        # Reset user playlist
        self._playlist_track_ids = []
        self._playlist_ids = []

    @property
    def shuffle_has_next(self):
        """
            True if history provide a next track
            @return bool
        """
        return self.__history and self.__history.has_next

    @property
    def shuffle_has_prev(self):
        """
            True if history provide a prev track
            @return bool
        """
        return self.__history and self.__history.has_prev

    def next(self):
        """
            Next shuffle track
            @return Track
        """
        track = None
        if self._shuffle == Shuffle.TRACKS or self.__is_party:
            if self.shuffle_has_next:
                track = self.__history.next.value
            elif self._albums:
                track = self.__shuffle_next()
            else:
                track = self._current_track
        return track or Track()

    def prev(self):
        """
            Prev track based on history
            @return Track
        """
        track = None
        if self._shuffle == Shuffle.TRACKS or self.__is_party:
            if self.shuffle_has_prev:
                track = self.__history.prev.value
            else:
                track = self._current_track
        return track or Track()

    def get_party_ids(self):
        """
            Return party ids
            @return [ids as int]
        """
        party_settings = App().settings.get_value("party-ids")
        ids = []
        genre_ids = App().genres.get_ids()
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
            self.set_party_ids()
            # Start a new song if not playing
            if (self._current_track.id in [None, Type.RADIOS])\
                    and self._albums:
                track = self.__get_random()
                self.load(track)
            elif not self.is_playing:
                self.play()
        else:
            self._albums = albums_backup
            # We want current album to continue playback
            if self._current_track.album not in self._albums:
                self._albums.insert(0, self._current_track.album)
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
                if self._current_track.album in self._albums:
                    self._albums.remove(self._current_track.album)
                    self._albums.insert(0, self._current_track.album)
        elif self._albums_backup:
            self._albums = self._albums_backup
            self._albums_backup = []

    def set_party_ids(self):
        """
            Set party mode ids
        """
        party_ids = self.get_party_ids()
        if party_ids:
            album_ids = App().albums.get_party_ids(party_ids)
        else:
            album_ids = App().albums.get_ids()
        self._albums = [Album(album_id) for album_id in album_ids]

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
                next = self.__history.next
                prev = self.__history.prev
                # Next track
                if next is not None and\
                        self._current_track == next.value:
                    next = self.__history.next
                    next.set_prev(self.__history)
                    self.__history = next
                # Previous track
                elif prev is not None and\
                        self._current_track == prev.value:
                    prev = self.__history.prev
                    prev.set_next(self.__history)
                    self.__history = prev
                # New track
                elif self.__history.value != self._current_track:
                    new_list = LinkedList(self._current_track,
                                          None,
                                          self.__history)
                    self.__history = new_list
            else:
                new_list = LinkedList(self._current_track)
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
        self._shuffle = App().settings.get_enum("shuffle")

        if self._plugins1.rgvolume is not None and\
           self._plugins2.rgvolume is not None:
            if self._shuffle == Shuffle.TRACKS or self._playlist_track_ids:
                self._plugins1.rgvolume.props.album_mode = 0
                self._plugins2.rgvolume.props.album_mode = 0
            else:
                self._plugins1.rgvolume.props.album_mode = 1
                self._plugins2.rgvolume.props.album_mode = 1

        if self._playlist_track_ids:
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
            @return track as Track
        """
        try:
            track = self.__get_random()
            # Need to clear history
            if track.id is None:
                self._albums = self.__already_played_albums
                self.reset_history()
                return self.__shuffle_next()
            return track
        except:  # Recursion error
            return None

    def __get_random(self):
        """
            Return a random track and make sure it has never been played
            @return Track
        """
        for album in sorted(self._albums, key=lambda *args: random.random()):
            tracks = album.tracks
            for track in sorted(tracks, key=lambda *args: random.random()):
                if album not in self.__already_played_tracks.keys() or\
                   track not in self.__already_played_tracks[album]:
                    return track
            # Remove album from current albums
            self._albums.remove(album)
            if album in self.__already_played_tracks.keys():
                self.__already_played_tracks.pop(album)
                self.__already_played_albums.append(album)
        self._next_context = NextContext.STOP
        return Track()

    def __add_to_shuffle_history(self, track):
        """
            Add a track to shuffle history
            @param track as Track
        """
        if track.album not in self.__already_played_tracks.keys():
            self.__already_played_tracks[track.album] = []
        if track not in self.__already_played_tracks[track.album]:
            self.__already_played_tracks[track.album].append(track)

    def __init_party_blacklist(self):
        """
            Add party mode blacklist to already played tracks
        """
        if self.__is_party:
            for track_id in App().playlists.get_track_ids(Type.NOPARTY):
                track = Track(track_id)
                self.__add_to_shuffle_history(track)
