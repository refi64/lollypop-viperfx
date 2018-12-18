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

from gi.repository import Gst, GLib

from pickle import load
from random import choice, shuffle
from lollypop.player_bin import BinPlayer
from lollypop.player_queue import QueuePlayer
from lollypop.player_linear import LinearPlayer
from lollypop.player_shuffle import ShufflePlayer
from lollypop.player_radio import RadioPlayer
from lollypop.player_playlist import PlaylistPlayer
from lollypop.radios import Radios
from lollypop.logger import Logger
from lollypop.objects import Track, Album
from lollypop.define import App, Type, NextContext, LOLLYPOP_DATA_PATH, Shuffle


class Player(BinPlayer, QueuePlayer, PlaylistPlayer, RadioPlayer,
             LinearPlayer, ShufflePlayer):
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
        self.update_crossfading()
        self.__do_not_update_next = False
        App().settings.connect("changed::playback", self.__on_playback_changed)
        self._albums_backup = []

    def prev(self):
        """
            Play previous track
        """
        if self._is_locked:
            return
        if self._prev_track.id is not None:
            if self.position / Gst.SECOND > 2:
                self.seek(0)
            else:
                self.load(self._prev_track)
        else:
            self.stop()

    def next(self):
        """
            Play next track
        """
        if self._is_locked:
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
            Add album to player. We may merge album!
            @param album as Album
            @param index as int
        """
        # We are not playing a user playlist anymore
        self._playlist_tracks = []
        self._playlist_ids = []
        # We do not shuffle when user add an album
        self._albums_backup = []
        if index == -1:
            if self._albums and self._albums[-1].id == album.id:
                self._albums[-1].set_tracks(self._albums[-1].tracks +
                                            album.tracks)
            else:
                self._albums.append(album)
        else:
            self._albums.insert(index, album)
        if self._current_track.id is not None and self._current_track.id > 0:
            if not self.is_party:
                self.set_next()
            self.set_prev()
        self.emit("album-added", album.id)
        self.emit("playlist-changed")

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
            self.emit("album-removed", album.id)
            self.emit("playlist-changed")
        except Exception as e:
            Logger.error("Player::remove_album(): %s" % e)

    def remove_album_by_id(self, album_id):
        """
            Remove all instance of album with id from albums
            @param album_id as int
        """
        try:
            for album in self._albums:
                if album.id == album_id:
                    self.remove_album(album)
            self.emit("playlist-changed")
        except Exception as e:
            Logger.error("Player::remove_album_by_id(): %s" % e)

    def remove_disc(self, disc, album_id):
        """
            Remove disc for album_id
            @param disc as Disc
            @param album_id as int
        """
        try:
            removed = []
            for album in self._albums:
                if album.id == album_id:
                    for track in list(album.tracks):
                        if track.id in disc.track_ids:
                            empty = album.remove_track(track)
                            if empty:
                                removed.append(album)
            for album in removed:
                self._albums.remove(album)
            self.emit("playlist-changed")
        except Exception as e:
            Logger.error("Player::remove_disc(): %s" % e)

    def play_album(self, album):
        """
            Play album
            @param album as Album
        """
        if self.is_party:
            App().lookup_action("party").change_state(GLib.Variant("b", False))
        self.reset_history()
        # We are not playing a user playlist anymore
        self._playlist_tracks = []
        self._playlist_ids = []
        if App().settings.get_enum("shuffle") == Shuffle.TRACKS:
            track = choice(album.tracks)
        else:
            track = album.tracks[0]
        self.load(track)
        self._albums = [album]
        self.emit("playlist-changed")

    def play_albums(self, album_id, filter1_ids, filter2_ids):
        """
            Play albums related to track/genre_ids/artist_ids
            @param album_id as int/None
            @param filter1_ids as [int]
            @param filter2_ids as [int]
        """
        self._albums = []
        album_ids = [] if album_id is None else [album_id]
        self.reset_history()
        # We are not playing a user playlist anymore
        self._playlist_tracks = []
        self._playlist_ids = []
        # We are in all artists
        if (filter1_ids and filter1_ids[0] == Type.ALL) or\
           (filter2_ids and filter2_ids[0] == Type.ALL):
            # Genres: all, Artists: compilations
            if filter2_ids and filter2_ids[0] == Type.COMPILATIONS:
                album_ids += App().albums.get_compilation_ids([], True)
            # Genres: all, Artists: ids
            elif filter2_ids and filter2_ids[0] != Type.ALL:
                album_ids += App().albums.get_ids(filter2_ids, [], True)
            # Genres: all, Artists: all
            else:
                if App().settings.get_value("show-compilations-in-album-view"):
                    album_ids += App().albums.get_compilation_ids([], True)
                album_ids += App().albums.get_ids([], [], True)
        # We are in populars view, add popular albums
        elif filter1_ids and filter1_ids[0] == Type.POPULARS:
            album_ids += App().albums.get_populars()
        # We are in loved view, add loved albums
        elif filter1_ids and filter1_ids[0] == Type.LOVED:
            album_ids += App().albums.get_loved_albums()
        # We are in recents view, add recent albums
        elif filter1_ids and filter1_ids[0] == Type.RECENTS:
            album_ids += App().albums.get_recents()
        # We are in randoms view, add random albums
        elif filter1_ids and filter1_ids[0] == Type.RANDOMS:
            album_ids += App().albums.get_cached_randoms()
        # We are in compilation view without genre
        elif filter1_ids and filter1_ids[0] == Type.COMPILATIONS:
            album_ids += App().albums.get_compilation_ids([])
        # We are in years view
        elif filter1_ids and filter1_ids[0] == Type.YEARS:
            album_ids += []
            for year in filter2_ids:
                album_ids += App().albums.get_albums_for_year(year)
                album_ids += App().albums.get_compilations_for_year(year)
        # Add albums for artists/genres
        else:
            # If we are not in compilation view and show compilation is on,
            # add compilations
            if filter2_ids and filter2_ids[0] == Type.COMPILATIONS:
                album_ids += App().albums.get_compilation_ids(
                    filter1_ids, True)
            elif filter2_ids:
                # In artist view, play all albums if ignoring return []
                album_ids += App().albums.get_ids(
                    filter2_ids, filter1_ids, True)
                if not album_ids:
                    album_ids += App().albums.get_ids(
                        filter2_ids, filter1_ids, False)
            elif App().settings.get_value(
                            "show-compilations-in-album-view"):
                album_ids += App().albums.get_compilation_ids(
                    filter1_ids, True)
                album_ids += App().albums.get_ids([], filter1_ids, True)
            else:
                album_ids += App().albums.get_ids([], filter1_ids, True)

        shuffle_setting = App().settings.get_enum("shuffle")
        if not album_ids:
            return
        elif shuffle_setting == Shuffle.ALBUMS:
            if album_id is None:
                shuffle(album_ids)
                album = Album(album_ids.pop(0), filter1_ids, filter2_ids, True)
            else:
                album = Album(album_ids.pop(0), filter1_ids, filter2_ids, True)
                shuffle(album_ids)
        else:
            album = Album(album_ids.pop(0), filter1_ids, filter2_ids, True)
        # Select a track and start playback
        track = None
        self._albums = [album]
        if shuffle_setting == Shuffle.TRACKS:
            track = choice(album.tracks)
        elif shuffle_setting == Shuffle.ALBUMS:
            if self._albums and self._albums[0].tracks:
                track = self._albums[0].tracks[0]
        elif album.tracks:
            track = album.tracks[0]

        # Create album objects
        for _album_id in album_ids:
            if _album_id == album_id:
                continue
            album = Album(_album_id, filter1_ids, filter2_ids, True)
            self._albums.append(album)
        if track is not None:
            self.load(track)
        self.emit("playlist-changed")

    def clear_albums(self):
        """
            Clear all albums
        """
        self._albums = []
        self.set_next()
        self.set_prev()
        self.emit("playlist-changed")

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
                current_track_id = load(open(LOLLYPOP_DATA_PATH +
                                             "/track_id.bin", "rb"))
                self.set_queue(load(open(LOLLYPOP_DATA_PATH +
                                         "/queue.bin", "rb")))
                albums = load(open(LOLLYPOP_DATA_PATH + "/Albums.bin", "rb"))
                playlist_ids = load(open(LOLLYPOP_DATA_PATH +
                                         "/playlist_ids.bin", "rb"))
                (is_playing, was_party) = load(open(LOLLYPOP_DATA_PATH +
                                                    "/player.bin", "rb"))
                if playlist_ids and playlist_ids[0] == Type.RADIOS:
                    radios = Radios()
                    track = Track()
                    name = radios.get_name(current_track_id)
                    url = radios.get_url(name)
                    track.set_radio(name, url)
                    self.load(track, is_playing)
                elif App().tracks.get_uri(current_track_id) != "":
                    if albums:
                        if was_party:
                            App().lookup_action("party").change_state(
                                GLib.Variant("b", True))
                        else:
                            self._albums = load(open(
                                                LOLLYPOP_DATA_PATH +
                                                "/Albums.bin",
                                                "rb"))
                        # Load track from player albums
                        current_track = Track(current_track_id)
                        index = self.album_ids.index(current_track.album.id)
                        for track in self._albums[index].tracks:
                            if track.id == current_track_id:
                                self._load_track(track)
                                break
                    else:
                        for playlist_id in playlist_ids:
                            tracks = App().playlists.get_tracks(playlist_id)
                            App().player.populate_playlist_by_tracks(
                                tracks, playlist_ids)
                            for track in tracks:
                                if track.id == current_track_id:
                                    self._load_track(track)
                                    break
                    if is_playing:
                        self.play()
                    else:
                        self.pause()
                    position = load(open(LOLLYPOP_DATA_PATH + "/position.bin",
                                    "rb"))
                    self.seek(position / Gst.SECOND)
                else:
                    Logger.info("Player::restore_state(): track missing")
                self.emit("playlist-changed")
        except Exception as e:
            Logger.error("Player::restore_state(): %s" % e)

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
            # Same track
            if App().settings.get_enum("playback") == NextContext.REPEAT_TRACK:
                prev_track = self._current_track
            # Look at shuffle
            else:
                prev_track = ShufflePlayer.prev(self)

            # Look at user playlist then
            if prev_track.id is None:
                prev_track = PlaylistPlayer.prev(self)

            # Get a linear track then
            if prev_track.id is None:
                prev_track = LinearPlayer.prev(self)
            self._prev_track = prev_track
            self.emit("prev-changed")
        except Exception as e:
            Logger.error("Player::set_prev(): %s" % e)

    def set_next(self, force=False):
        """
            Play next track
            @param sql as sqlite cursor
            @param force as bool
        """
        try:
            # Reset finished context
            self._next_context = NextContext.NONE

            # Same track
            if App().settings.get_enum("playback") == NextContext.REPEAT_TRACK:
                next_track = self._current_track
            # Look first at user queue
            else:
                next_track = QueuePlayer.next(self)

            # Look at shuffle
            if next_track.id is None:
                next_track = ShufflePlayer.next(self)

            # Look at user playlist then
            if next_track.id is None:
                next_track = PlaylistPlayer.next(self, force)

            # Get a linear track then
            if next_track.id is None:
                next_track = LinearPlayer.next(self)
            self._next_track = next_track
            self.emit("next-changed")
        except Exception as e:
            Logger.error("Player::set_next(): %s" % e)

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
            self.pause()
            self.load(self._current_track.album.tracks[-1])
            self.set_next()
            self.next()

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

    def get_albums_for_id(self, album_id):
        """
            Get albums for id
            @param album_id as int
            @return [Album]
        """
        return [album for album in self._albums if album.id == album_id]

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

    @property
    def album_ids(self):
        """
            Return albums ids
            @return albums ids as [int]
        """
        return [album.id for album in self._albums]

#######################
# PROTECTED           #
#######################
    def _on_stream_start(self, bus, message):
        """
            On stream start, set next and previous track
        """
        if not App().scanner.is_locked():
            App().window.container.pulse(False)
        if self._current_track.id is not None and self._current_track.id >= 0:
            ShufflePlayer._on_stream_start(self, bus, message)
        if self.track_in_queue(self._current_track):
            self.remove_from_queue(self._current_track.id)
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
