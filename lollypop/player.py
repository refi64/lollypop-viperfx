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

from gi.repository import Gst

from pickle import load
from random import choice

from lollypop.player_bin import BinPlayer
from lollypop.player_queue import QueuePlayer
from lollypop.player_linear import LinearPlayer
from lollypop.player_shuffle import ShufflePlayer
from lollypop.player_radio import RadioPlayer
from lollypop.player_externals import ExternalsPlayer
from lollypop.player_playlist import PlaylistPlayer
from lollypop.radios import Radios
from lollypop.objects import Track, Album
from lollypop.define import App, Type, NextContext, LOLLYPOP_DATA_PATH, Shuffle


class Player(BinPlayer, QueuePlayer, PlaylistPlayer, RadioPlayer,
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
        PlaylistPlayer.__init__(self)
        RadioPlayer.__init__(self)
        ExternalsPlayer.__init__(self)
        self.update_crossfading()
        self.__do_not_update_next = False
        App().settings.connect("changed::playback", self.__on_playback_changed)

    def prev(self):
        """
            Play previous track
        """
        if self._locked:
            return
        smart_prev = App().settings.get_value("smart-previous")
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
            RadioPlayer.load(self, track, play)
        else:
            if play:
                # Do not update next if user clicked on a track
                if self.is_party and track != self._next_track:
                    self.__do_not_update_next = True
                BinPlayer.load(self, track)
            else:
                BinPlayer._load_track(self, track)
                self.emit("current-changed")

    def add_album(self, album, index=-1):
        """
            Add album
            @param album as Album
            @param index as int
        """
        # We are not playing a user playlist anymore
        self._playlist_track_ids = []
        self._playlist_ids = []
        # We do not shuffle when user add an album
        self._albums_backup = []
        if index == -1:
            self._albums.append(album)
        else:
            self._albums.insert(index, album)
        if self._current_track.id is not None and self._current_track.id > 0:
            if not self.is_party:
                self.set_next()
            self.set_prev()
        self.emit("album-added", album.id)

    def move_album(self, album, position):
        """
            Move album to position
            @param album as Album
            @param position as int
        """
        index = self._albums.index(album)
        self._albums.insert(position, self._albums.pop(index))

    def remove_album(self, album):
        """
            Remove album from albums
            @param album as Album
        """
        try:
            self._albums.remove(album)
            if album in self._albums_backup:
                self._albums_backup.remove(album)
            if not self.is_party or self._next_track.album_id == album.id:
                self.set_next()
            self.set_prev()
            self.emit("album-added", album.id)
        except Exception as e:
            print("Player::remove_album():", e)

    def play_album(self, album):
        """
            Play album
            @param album as Album
        """
        if self.is_party:
            self.set_party(False)
        self.reset_history()
        # We are not playing a user playlist anymore
        self._playlist_track_ids = []
        self._playlist_ids = []
        if App().settings.get_enum("shuffle") == Shuffle.TRACKS:
            track = choice(album.tracks)
        else:
            track = album.tracks[0]
        self.load(track)
        self._albums = [album]

    def play_albums(self, track, genre_ids, artist_ids):
        """
            Play albums related to track/genre_ids/artist_ids
            @param track as Track
            @param genre_ids as [int]
            @param artist_ids as [int]
        """
        self._albums = []
        album_ids = []
        ShufflePlayer.reset_history(self)

        # We are not playing a user playlist anymore
        self._playlist_track_ids = []
        self._playlist_ids = []
        # We are in all artists
        if (genre_ids and genre_ids[0] == Type.ALL) or\
           (artist_ids and artist_ids[0] == Type.ALL):
            # Genres: all, Artists: compilations
            if artist_ids and artist_ids[0] == Type.COMPILATIONS:
                album_ids = App().albums.get_compilation_ids()
            # Genres: all, Artists: ids
            elif artist_ids and artist_ids[0] != Type.ALL:
                album_ids += App().albums.get_ids(artist_ids)
            # Genres: all, Artists: all
            else:
                if App().settings.get_value("show-compilations"):
                    album_ids += App().albums.get_compilation_ids()
                album_ids += App().albums.get_ids()
        # We are in populars view, add popular albums
        elif genre_ids and genre_ids[0] == Type.POPULARS:
            album_ids = App().albums.get_populars()
        # We are in loved view, add loved albums
        elif genre_ids and genre_ids[0] == Type.LOVED:
            album_ids = App().albums.get_loves()
        # We are in recents view, add recent albums
        elif genre_ids and genre_ids[0] == Type.RECENTS:
            album_ids = App().albums.get_recents()
        # We are in randoms view, add random albums
        elif genre_ids and genre_ids[0] == Type.RANDOMS:
            album_ids = App().albums.get_cached_randoms()
        # We are in compilation view without genre
        elif genre_ids and genre_ids[0] == Type.COMPILATIONS:
            album_ids = App().albums.get_compilation_ids()
        # Add albums for artists/genres
        else:
            # If we are not in compilation view and show compilation is on,
            # add compilations
            if artist_ids and artist_ids[0] == Type.COMPILATIONS:
                album_ids += App().albums.get_compilation_ids(genre_ids)
            else:
                if not artist_ids and\
                        App().settings.get_value("show-compilations"):
                    album_ids += App().albums.get_compilation_ids(genre_ids)
                album_ids += App().albums.get_ids(artist_ids, genre_ids)
        # Create album objects
        for album_id in album_ids:
            album = Album(album_id, genre_ids, artist_ids)
            self._albums.append(album)
            # Get track from album
            # to make Player.current_track present in Player.albums
            if album.id == track.album.id:
                index = album.track_ids.index(track.id)
                track = album.tracks[index]
        # Shuffle album list if needed
        self.shuffle_albums(True)
        self.load(track)

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
            if App().settings.get_value("save-state"):
                track_id = load(open(LOLLYPOP_DATA_PATH +
                                     "/track_id.bin", "rb"))
                self.set_queue(load(open(LOLLYPOP_DATA_PATH +
                               "/queue.bin", "rb")))
                playlist_ids = load(open(LOLLYPOP_DATA_PATH +
                                         "/playlist_ids.bin", "rb"))
                (is_playing, was_party) = load(open(LOLLYPOP_DATA_PATH +
                                                    "/player.bin", "rb"))
                if playlist_ids and playlist_ids[0] == Type.RADIOS:
                    radios = Radios()
                    track = Track()
                    name = radios.get_name(track_id)
                    url = radios.get_url(name)
                    track.set_radio(name, url)
                    self.load(track, is_playing)
                elif App().tracks.get_uri(track_id) != "":
                    track = Track(track_id)
                    self._load_track(track)
                    # We set this initial state
                    # because seek while failed otherwise
                    self.pause()
                    if playlist_ids:
                        track_ids = []
                        for playlist_id in playlist_ids:
                            if playlist_id == Type.POPULARS:
                                track_ids = App().tracks.get_populars()
                            elif playlist_id == Type.RECENTS:
                                track_ids = App().tracks.\
                                    get_recently_listened_to()
                            elif playlist_id == Type.NEVER:
                                track_ids = App().tracks.\
                                    get_never_listened_to()
                            elif playlist_id == Type.RANDOMS:
                                track_ids = App().tracks.get_randoms()
                            else:
                                track_ids = App().playlists.get_track_ids(
                                                                   playlist_id)
                            self.populate_playlist_by_track_ids(
                                                          list(set(track_ids)),
                                                          playlist_ids)
                    else:
                        if was_party:
                            self.emit("party-changed", True)
                        else:
                            self._albums = load(open(
                                                LOLLYPOP_DATA_PATH +
                                                "/Albums.bin",
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
            if App().settings.get_enum("playback") == NextContext.REPEAT_TRACK:
                self._prev_track = self._current_track
            else:
                # Look at externals
                self._prev_track = ExternalsPlayer.prev(self)

            # Look at radio
            if self._prev_track.id is None:
                self._prev_track = RadioPlayer.prev(self)

            # Look at user playlist then
            if self._prev_track.id is None:
                self._prev_track = PlaylistPlayer.prev(self)

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

            if App().settings.get_enum("playback") == NextContext.REPEAT_TRACK:
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
                next_track = PlaylistPlayer.next(self, force)

            # Get a random album/track then
            if next_track.id is None:
                next_track = ShufflePlayer.next(self)

            # Get a linear track then
            if next_track.id is None:
                next_track = LinearPlayer.next(self)
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
                App().settings.get_enum("shuffle") == Shuffle.TRACKS:
            self.set_next()
            # We send this signal to update next popover
            self.emit("queue-changed")
        elif self._current_track.id is not None:
            pos = self._albums.index(self._current_track.album)
            if pos + 1 >= len(self._albums):
                next_album = self._albums[0]
            else:
                next_album = self._albums[pos + 1]
            self.load(next_album.tracks[0])

    def update_crossfading(self):
        """
            Calculate if crossfading is needed
        """
        mix = App().settings.get_value("smooth-transitions")
        party_mix = App().settings.get_value("party-mix")
        self._crossfading = (mix and not party_mix) or\
                            (mix and party_mix and self.is_party)

    def track_in_playback(self, track):
        """
            True if track present in current playback
            @param track as Track
            @return bool
        """
        for album in self._albums:
            if album.id == track.album.id:
                for track_id in album.track_ids:
                    if track.id == track_id:
                        return True
        return False

    def object_by_name(self, track_name, album_name):
        """
            Get track by object name
            @track_name as str
            @param album_name as str
            @return Album is track_name is None, else Track or None
        """
        for album in self._albums:
            if str(album) == album_name:
                if track_name is None:
                    return album
                for track in album.tracks:
                    if str(track) == track_name:
                        return track
        return None

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
    def albums(self):
        """
            Return albums
            @return albums as [Album]
        """
        return self._albums

#######################
# PROTECTED           #
#######################
    def _on_bus_error(self, bus, message):
        """
            Pass error to Bin/Radio
            @param bus as Gst.Bus
            @param message as Gst.Message
        """
        BinPlayer._on_bus_error(self, bus, message)
        RadioPlayer._on_bus_error(self, bus, message)

    def _on_stream_start(self, bus, message):
        """
            On stream start, set next and previous track
        """
        if not App().scanner.is_locked():
            App().window.container.pulse(False)
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
