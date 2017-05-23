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

from gi.repository import Gio, GLib, Gst

from pickle import load
from random import choice

from lollypop.player_bin import BinPlayer
from lollypop.player_queue import QueuePlayer
from lollypop.player_linear import LinearPlayer
from lollypop.player_shuffle import ShufflePlayer
from lollypop.player_radio import RadioPlayer
from lollypop.player_externals import ExternalsPlayer
from lollypop.player_userplaylist import UserPlaylistPlayer
from lollypop.radios import Radios
from lollypop.objects import Track, Album
from lollypop.define import Lp, Type, NextContext, DataPath, Shuffle


class Player(BinPlayer, QueuePlayer, UserPlaylistPlayer, RadioPlayer,
             LinearPlayer, ShufflePlayer, ExternalsPlayer):
    """
        Player object used to manage playback and playlists
    """

    def __init__(self):
        """
            Init player
        """
        BinPlayer.__init__(self)
        QueuePlayer.__init__(self)
        LinearPlayer.__init__(self)
        ShufflePlayer.__init__(self)
        UserPlaylistPlayer.__init__(self)
        RadioPlayer.__init__(self)
        ExternalsPlayer.__init__(self)
        self.update_crossfading()
        self.__do_not_update_next = False
        Lp().settings.connect("changed::playback", self.__on_playback_changed)

    @property
    def next_track(self):
        """
            Current track
        """
        return self._next_track

    @property
    def prev_track(self):
        """
            Current track
        """
        return self._prev_track

    @property
    def context(self):
        """
            Current track
        """
        return self._context

    def prev(self):
        """
            Play previous track
        """
        if self._locked:
            return
        smart_prev = Lp().settings.get_value("smart-previous")
        if self._prev_track.id is not None:
            if smart_prev and self.position / Gst.SECOND > 2:
                self.seek(0)
            else:
                self.load(self._prev_track)
        else:
            self.stop()

    def next(self):
        """
            Play next track
        """
        if self._locked:
            return
        if self._next_track.id is not None:
            self._scrobble(self._current_track, self._start_time)
            self.load(self._next_track)
        else:
            self.stop()

    def load(self, track, play=True):
        """
            Stop current track, load track id and play it
            @param track as Track
            @param play as bool, ignored for radios
        """
        if track.id == Type.RADIOS:
            if not Lp().scanner.is_locked():
                Lp().window.pulse(False)
                Lp().window.pulse(True)
            RadioPlayer.load(self, track)
        else:
            if play:
                if track.is_web and\
                        not Gio.NetworkMonitor.get_default(
                                                     ).get_network_available():
                    self._current_track = track
                    self.set_next()
                    GLib.idle_add(self.next)
                    return
                # Do not update next if user clicked on a track
                if self.is_party and track != self._next_track:
                    self.__do_not_update_next = True
                BinPlayer.load(self, track)
            else:
                BinPlayer._load_track(self, track)
                self.emit("current-changed")

    def add_album(self, album):
        """
            Add album
            @param album as Album
        """
        # We are not playing a user playlist anymore
        self._user_playlist = []
        self._user_playlist_ids = []
        self.shuffle_albums(False)
        # If album already exists, merge genres/artists
        if album.id in self._albums:
            genre_ids = self._context.genre_ids[album.id]
            for genre_id in album.genre_ids:
                if genre_id >= 0 and genre_id not in genre_ids:
                    self._context.genre_ids[album.id].append(genre_id)
            artist_ids = self._context.artist_ids[album.id]
            for artist_id in album.artist_ids:
                if artist_id >= 0 and artist_id not in artist_ids:
                    self._context.artist_ids[album.id].append(artist_id)
        else:
            self._albums.append(album.id)
            self._context.genre_ids[album.id] = list(album.genre_ids)
            self._context.artist_ids[album.id] = list(album.artist_ids)
        self.shuffle_albums(True)
        if self._current_track.id is not None and self._current_track.id > 0:
            if not self.is_party:
                self.set_next()
            self.set_prev()
        self.emit("album-added", album.id)

    def move_album(self, album_id, position):
        """
            Move album to position
            @param album id as int
            @param position as int
        """
        index = self._albums.index(album_id)
        self._albums.insert(position, self._albums.pop(index))

    def remove_album(self, album):
        """
            Remove album from albums
            @param album as Album
        """
        try:
            # Remove genre ids from context
            genre_ids = self._context.genre_ids[album.id]
            for genre_id in album.genre_ids:
                if genre_id in genre_ids:
                    genre_ids.remove(genre_id)
            artist_ids = self._context.artist_ids[album.id]
            # Remove artist ids from context
            for artist_id in album.artist_ids:
                if artist_id in artist_ids:
                    artist_ids.remove(artist_id)
            if not genre_ids or not artist_ids:
                self._context.genre_ids.pop(album.id, None)
                self._context.artist_ids.pop(album.id, None)
                self._albums.remove(album.id)
                if album.id in self._albums_backup:
                    self._albums_backup.remove(album.id)
            if not self.is_party or self._next_track.album_id == album.id:
                self.set_next()
            self.set_prev()
            self.emit("album-added", album.id)
        except Exception as e:
            print("Player::remove_album():", e)

    def get_genre_ids(self, album_id):
        """
            Return genre ids for album
            @param album id as int
            @return genre ids as [int]
        """
        if album_id in self._context.genre_ids.keys():
            return self._context.genre_ids[album_id]
        else:
            return []

    def get_artist_ids(self, album_id):
        """
            Return artist ids for album
            @param album id as int
            @return artist ids as [int]
        """
        if album_id in self._context.artist_ids.keys():
            return self._context.artist_ids[album_id]
        else:
            return []

    def has_album(self, album):
        """
            Check if player has album
            @param album as Album
            @return bool
        """
        is_genres = True
        is_artists = True
        if album.id in self._albums:
            for genre_id in album.genre_ids:
                if album.id in self._context.genre_ids.keys() and\
                   self._context.genre_ids[album.id] and\
                   genre_id not in self._context.genre_ids[album.id]:
                    is_genres = False
            for artist_id in album.artist_ids:
                if album.id in self._context.artist_ids.keys() and\
                   self._context.artist_ids[album.id] and\
                   artist_id not in self._context.artist_ids[album.id]:
                    is_artists = False
        else:
            is_genres = False
            is_artists = False
        return is_genres and is_artists

    def play_album(self, album):
        """
            Play album
            @param album as Album
        """
        if self.is_party:
            self.set_party(False)
        self.reset_history()
        # We are not playing a user playlist anymore
        self._user_playlist = []
        self._user_playlist_ids = []
        self._context.genre_ids = {}
        self._context.artist_ids = {}
        self._context.genre_ids[album.id] = []
        self._context.artist_ids[album.id] = []
        for genre_id in album.genre_ids:
            if genre_id >= 0:
                self._context.genre_ids[album.id].append(genre_id)
        for artist_id in album.artist_ids:
            if artist_id >= 0:
                self._context.artist_ids[album.id].append(artist_id)
        if Lp().settings.get_enum("shuffle") == Shuffle.TRACKS:
            track = choice(album.tracks)
        else:
            track = album.tracks[0]
        self.load(track)
        self._albums = [album.id]

    def set_albums(self, track_id, artist_ids, genre_ids):
        """
            Set album list (for next/prev)
            @param track id as int
            @param artist id as int
            @param genre id as int
        """
        # Invalid track
        if track_id is None:
            return
        self._albums = []
        self._context.genre_ids = {}
        self._context.aritst_ids = {}
        ShufflePlayer.reset_history(self)

        # We are not playing a user playlist anymore
        self._user_playlist = []
        self._user_playlist_ids = []
        # We are in all artists
        if (genre_ids and genre_ids[0] == Type.ALL) or\
           (artist_ids and artist_ids[0] == Type.ALL):
            # Genres: all, Artists: compilations
            if artist_ids and artist_ids[0] == Type.COMPILATIONS:
                self._albums += Lp().albums.get_compilation_ids()
            # Genres: all, Artists: ids
            elif artist_ids and artist_ids[0] != Type.ALL:
                self._albums += Lp().albums.get_ids(artist_ids)
            # Genres: all, Artists: all
            else:
                if Lp().settings.get_value("show-compilations"):
                    self._albums += Lp().albums.get_compilation_ids()
                self._albums += Lp().albums.get_ids()
        # We are in populars view, add popular albums
        elif genre_ids and genre_ids[0] == Type.POPULARS:
            self._albums = Lp().albums.get_populars()
        # We are in loved view, add loved albums
        elif genre_ids and genre_ids[0] == Type.LOVED:
            self._albums = Lp().albums.get_loves()
        # We are in recents view, add recent albums
        elif genre_ids and genre_ids[0] == Type.RECENTS:
            self._albums = Lp().albums.get_recents()
        # We are in randoms view, add random albums
        elif genre_ids and genre_ids[0] == Type.RANDOMS:
            self._albums = Lp().albums.get_cached_randoms()
        # We are in compilation view without genre
        elif genre_ids and genre_ids[0] == Type.COMPILATIONS:
            self._albums = Lp().albums.get_compilation_ids()
        # We are in charts view with a genre
        elif artist_ids and artist_ids[0] == Type.CHARTS:
            self._albums = Lp().albums.get_charts_ids(genre_ids)
        # Add albums for artists/genres
        else:
            # If we are not in compilation view and show compilation is on,
            # add compilations
            if artist_ids and artist_ids[0] == Type.COMPILATIONS:
                self._albums += Lp().albums.get_compilation_ids(genre_ids)
            else:
                if not artist_ids and\
                        Lp().settings.get_value("show-compilations"):
                    self._albums += Lp().albums.get_compilation_ids(genre_ids)
                self._albums += Lp().albums.get_ids(artist_ids, genre_ids)

        # We do not store genre_ids for ALL/POPULARS/...
        if genre_ids and genre_ids[0] < 0:
            genre_ids = []
        # Set context for each album
        for album_id in self._albums:
            self._context.genre_ids[album_id] = []
            self._context.artist_ids[album_id] = []
            for genre_id in genre_ids:
                if genre_id >= 0:
                    self._context.genre_ids[album_id].append(genre_id)
            for artist_id in artist_ids:
                if artist_id >= 0:
                    self._context.artist_ids[album_id].append(artist_id)
        # Shuffle album list if needed
        self.shuffle_albums(True)

    def get_albums(self):
        """
            Return albums
            @return albums as [int]
        """
        return self._albums

    def clear_albums(self):
        """
            Clear all albums
        """
        self._albums = []

    def get_current_artists(self):
        """
            Get current artist
            @return artist as string
        """
        artist_ids = self._current_track.album.artist_ids
        if artist_ids[0] == Type.COMPILATIONS:
            artists = ", ".join(self._current_track.artists)
        else:
            artists = ", ".join(self._current_track.album_artists)
        return artists

    def restore_state(self):
        """
            Restore player state
        """
        try:
            if Lp().settings.get_value("save-state"):
                track_id = load(open(DataPath + "/track_id.bin", "rb"))
                playlist_ids = load(open(DataPath + "/playlist_ids.bin",
                                    "rb"))
                (is_playing, was_party) = load(open(DataPath + "/player.bin",
                                                    "rb"))
                if playlist_ids and playlist_ids[0] == Type.RADIOS:
                    radios = Radios()
                    track = Track()
                    name = radios.get_name(track_id)
                    url = radios.get_url(name)
                    track.set_radio(name, url)
                    self.load(track)
                elif Lp().tracks.get_uri(track_id) != "":
                    track = Track(track_id)
                    if Lp().notify is not None:
                        Lp().notify.inhibit()
                    self._load_track(track)
                    # We set this initial state
                    # because seek while failed otherwise
                    self.pause()
                    if playlist_ids:
                        pids = []
                        for playlist_id in playlist_ids:
                            pids.append(int(playlist_id))
                        track_ids = []
                        for playlist_id in playlist_ids:
                            if playlist_id == Type.POPULARS:
                                tracks = Lp().tracks.get_populars()
                            elif playlist_id == Type.RECENTS:
                                tracks = Lp().tracks.get_recently_listened_to()
                            elif playlist_id == Type.NEVER:
                                tracks = Lp().tracks.get_never_listened_to()
                            elif playlist_id == Type.RANDOMS:
                                tracks = Lp().tracks.get_randoms()
                            else:
                                tracks = Lp().playlists.get_track_ids(
                                                                   playlist_id)
                            for track_id in tracks:
                                if track_id not in track_ids:
                                    track_ids.append(track_id)
                            self.populate_user_playlist_by_tracks(track_ids,
                                                                  pids)
                    else:
                        if was_party:
                            self.emit("party-changed", True)
                        else:
                            self._albums = load(open(
                                                DataPath + "/albums.bin",
                                                "rb"))
                            self.shuffle_albums(True)
                            self._context.genre_ids = load(open(
                                                DataPath + "/genre_ids.bin",
                                                "rb"))
                            self._context.artist_ids = load(open(
                                                DataPath + "/artist_ids.bin",
                                                "rb"))
                    self.set_next()
                    self.set_prev()
                    if is_playing:
                        self.play()
                    else:
                        self.pause()
                else:
                    print("Player::restore_state(): track missing")
        except Exception as e:
            print("Player::restore_state()", e)

    def set_party(self, party):
        """
            Set party mode on if party is True
            Play a new random track if not already playing
            @param party as bool
        """
        ShufflePlayer.set_party(self, party)
        self.set_next()
        self.set_prev()
        self.update_crossfading()

    def set_prev(self):
        """
            Set previous track
        """
        try:
            if Lp().settings.get_enum("playback") == NextContext.REPEAT_TRACK:
                self._prev_track = self._current_track
            else:
                # Look at externals
                self._prev_track = ExternalsPlayer.prev(self)

            # Look at radio
            if self._prev_track.id is None:
                self._prev_track = RadioPlayer.prev(self)

            # Look at user playlist then
            if self._prev_track.id is None:
                self._prev_track = UserPlaylistPlayer.prev(self)

            # Look at shuffle
            if self._prev_track.id is None:
                self._prev_track = ShufflePlayer.prev(self)

            # Get a linear track then
            if self._prev_track.id is None:
                self._prev_track = LinearPlayer.prev(self)
            self.emit("prev-changed")
        except Exception as e:
            print("Player::set_prev():", e)

    def set_next(self, force=False):
        """
            Play next track
            @param sql as sqlite cursor
            @param force as bool
        """
        try:
            # Reset finished context
            self._next_context = NextContext.NONE

            if Lp().settings.get_enum("playback") == NextContext.REPEAT_TRACK:
                next_track = self._current_track
            else:
                # Look at externals
                next_track = ExternalsPlayer.next(self)

            # Look at radio
            if next_track.id is None:
                next_track = RadioPlayer.next(self)

            # Look first at user queue
            if next_track.id is None:
                next_track = QueuePlayer.next(self)

            # Look at user playlist then
            if next_track.id is None:
                next_track = UserPlaylistPlayer.next(self, force)

            # Get a random album/track then
            if next_track.id is None:
                next_track = ShufflePlayer.next(self)

            # Get a linear track then
            if next_track.id is None:
                next_track = LinearPlayer.next(self)
            if next_track.is_web:
                self._load_web(next_track, False)
            self._next_track = next_track
            self.emit("next-changed")
        except Exception as e:
            print("Player::set_next():", e)

    def skip_album(self):
        """
            Skip current album
        """
        # In party or shuffle, just update next track
        if self.is_party or\
                Lp().settings.get_enum("shuffle") == Shuffle.TRACKS:
            self.set_next()
            # We send this signal to update next popover
            self.emit("queue-changed")
        elif self._current_track.id is not None:
            pos = self._albums.index(self._current_track.album.id)
            if pos + 1 >= len(self._albums):
                next_album = self._albums[0]
            else:
                next_album = self._albums[pos + 1]
            self.load(Album(next_album).tracks[0])

    def update_crossfading(self):
        """
            Calculate if crossfading is needed
        """
        mix = Lp().settings.get_value("mix")
        party_mix = Lp().settings.get_value("party-mix")
        self._crossfading = (mix and not party_mix) or\
                            (mix and party_mix and self.is_party)

#######################
# PROTECTED           #
#######################
    def _on_stream_start(self, bus, message):
        """
            On stream start, set next and previous track
        """
        if not Lp().scanner.is_locked():
            Lp().window.pulse(False)
        if self._current_track.id is not None and self._current_track.id >= 0:
            ShufflePlayer._on_stream_start(self, bus, message)
        if self.track_in_queue(self._current_track):
            self.del_from_queue(self._current_track.id)
        else:
            if self.shuffle_has_next or not self.__do_not_update_next:
                self.set_next()
            self.__do_not_update_next = False
            self.set_prev()
        BinPlayer._on_stream_start(self, bus, message)

#######################
# PRIVATE             #
#######################
    def __on_playback_changed(self, settings, value):
        """
            reset next/prev
            @param settings as Gio.Settings, value as str
        """
        self.set_next()
        self.set_prev()
