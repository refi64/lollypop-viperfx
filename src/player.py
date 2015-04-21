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

from gi.repository import GLib, GObject, Gst, GstAudio
import random
from os import path

from lollypop.tagreader import TagReader
from lollypop.player_base import BasePlayer
from lollypop.player_queue import QueuePlayer
from lollypop.define import Objects, Navigation, NextContext, CurrentTrack
from lollypop.define import Shuffle, PlayerContext, GstPlayFlags
from lollypop.utils import translate_artist_name



# Player object used to manage playback and playlists
class Player(BasePlayer, QueuePlayer, TagReader):
    """
        Create a gstreamer bin and listen to signals on bus
    """
    def __init__(self):
        BasePlayer.__init__(self)
        QueuePlayer.__init__(self)
        TagReader.__init__(self)

        self.current = CurrentTrack()
        self.context = PlayContext()
        # Albums in current playlist
        self._albums = None
        # Used by shuffle albums to restore playlist before shuffle
        self._albums_backup = None
        self._shuffle = Objects.settings.get_enum('shuffle')
        # Tracks already played
        self._played_tracks_history = []
        # Albums already played
        self._already_played_albums = []
        # Tracks already played for albums
        self._already_played_tracks = {}
        # Party mode
        self._is_party = False
        # Player errors
        self._errors = 0

        self._playbin.connect("about-to-finish",
                              self._on_stream_about_to_finish)
        Objects.settings.connect('changed::shuffle', self._set_shuffle)

        self._bus = self._playbin.get_bus()
        self._bus.add_signal_watch()
        self._bus.connect('message::error', self._on_bus_error)
        self._bus.connect('message::eos', self._on_bus_eos)
        self._bus.connect('message::stream-start', self._on_stream_start)

    """
        Play previous track
        If shuffle or party => go backward in shuffle history
        Else => Get previous track in currents albums
    """
    def prev(self):
        track_id = None
        if self._shuffle == Shuffle.TRACKS or self._is_party:
            try:
                track_id = self._played_tracks_history[-2]
                self._played_tracks_history.pop()
                self._played_tracks_history.pop()
            except:
                track_id = None
        # Look at user playlist then
        elif self._user_playlist:
            self.context.position -= 1
            if self.context.position < 0:
                self.context.position = len(self._user_playlist) - 1
            self.load(self._user_playlist[self.context.position])
        elif self.context.position is not None:
            tracks = Objects.albums.get_tracks(self.current.album_id,
                                               self.current.genre_id)
            if self.context.position <= 0:  # Prev album
                pos = self._albums.index(self.current.album_id)
                if pos - 1 < 0:  # we are on last album, go to first
                    pos = len(self._albums) - 1
                else:
                    pos -= 1
                self.current.album_id = self._albums[pos]
                tracks = Objects.albums.get_tracks(self.current.album_id,
                                                   self.current.genre_id)
                self.context.album_id = self.current.album_id
                self.context.position = len(tracks) - 1
                track_id = tracks[self.context.position]
            else:
                self.context.position -= 1
                track_id = tracks[self.context.position]

        if track_id:
            self.load(track_id)

    """
        Play next track
        If shuffle or party => get a random file not already played
        Else => get next track in currents albums
        if force is True (default), don't wait for end of stream
        a fresh sqlite cursor should be pass as sql if we are in a thread
    """
    def next(self, force=True, sql=None):
        # Look first at user queue
        track_id = QueuePlayer.next(self)
        if track_id is not None:
            if force:
                self.load(track_id)
            else:
                self._load_track(track_id, sql)
        # Look at user playlist then
        elif self._user_playlist:
            self.context.position += 1
            if self.context.position >= len(self._user_playlist):
                self.context.position = 0
            if force:
                self.load(self._user_playlist[self.context.position])
            else:
                self._load_track(self._user_playlist[self.context.position],
                                 sql)
        # Get a random album/track
        elif self._shuffle in [Shuffle.TRACKS, Shuffle.TRACKS_ARTIST] or\
             self._is_party:
            if self._albums:
                self._shuffle_next(force, sql)
        elif self.context.position is not None and self._albums:
            track_id = None
            tracks = Objects.albums.get_tracks(self.context.album_id,
                                               self.context.genre_id,
                                               sql)
            if self.context.position + 1 >= len(tracks):  # next album
                pos = self._albums.index(self.context.album_id)
                # we are on last album, go to first
                if pos + 1 >= len(self._albums):
                    pos = 0
                else:
                    pos += 1
                self.context.album_id = self._albums[pos]
                self.context.position = 0
                track_id = Objects.albums.get_tracks(self._albums[pos],
                                                     self.context.genre_id,
                                                     sql)[0]
            else:
                self.context.position += 1
                track_id = tracks[self.context.position]

            if force:
                self.load(track_id)
            else:
                self._load_track(track_id, sql)

    """
        Play album
        @param album id as int
        @param genre id as int
    """
    def play_album(self, album_id, genre_id=None):
        # Empty user playlist
        self._user_playlist = None
        # Get first track from album
        track_id = Objects.albums.get_tracks(album_id, genre_id)[0]
        Objects.player.load(track_id)
        if not Objects.player.is_party():
            if genre_id:
                self.set_albums(self.current.id,
                                self.current.aartist_id,
                                genre_id)
            else:
                self.set_album(album_id)

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

    """
        Set album as current album list (for next/prev)
        Set track as current track in album
        @param album_id as int
    """
    def set_album(self, album_id):
        self._albums = [album_id]
        self.context.album_id = album_id
        self.context.genre_id = None
        tracks = Objects.albums.get_tracks(album_id, None)
        self.context.position = tracks.index(self.current.id)

    """
        Set album list (for next/prev)
        @param track id as int
        @param artist id as int
        @param genre id as int
    """
    def set_albums(self, track_id, artist_id, genre_id):
        # Invalid track
        if track_id is None:
            return
        album_id = Objects.tracks.get_album_id(track_id)
        self._albums = []
        self._played_tracks_history = []
        self._already_played_tracks = {}
        self._already_played_albums = []
        self.context.genre_id = genre_id

        # When shuffle from artist is active, we want only artist's albums,
        # we need to ignore genre
        # Do not set genre_id directly as it will changes current context
        if self._shuffle in [Shuffle.TRACKS_ARTIST, Shuffle.ALBUMS_ARTIST]:
            genre_id_lookup = None
        else:
            genre_id_lookup = genre_id

        # We are not playing a user playlist anymore
        self._user_playlist = None
        # We are in all artists
        if genre_id_lookup == Navigation.ALL or artist_id == Navigation.ALL:
            self._albums = Objects.albums.get_compilations(Navigation.ALL)
            self._albums += Objects.albums.get_ids()
        # We are in popular view, add popular albums
        elif genre_id_lookup == Navigation.POPULARS:
            self._albums = Objects.albums.get_populars()
        # We are in recent view, add recent albums
        elif genre_id_lookup == Navigation.RECENTS:
            self._albums = Objects.albums.get_recents()
        # Random tracks/albums for genre
        elif self._shuffle in [Shuffle.TRACKS, Shuffle.ALBUMS]:
            self._albums = Objects.albums.get_ids(None, genre_id_lookup)
        # Random tracks/albums for artist
        elif self._shuffle in [Shuffle.TRACKS_ARTIST, Shuffle.ALBUMS_ARTIST]:
            self._albums = Objects.albums.get_ids(artist_id, genre_id_lookup)
        # Add all albums for genre
        else:
            self._albums = Objects.albums.get_compilations(genre_id_lookup)
            self._albums += Objects.albums.get_ids(None, genre_id_lookup)

        self.context.album_id = album_id
        tracks = Objects.albums.get_tracks(album_id, genre_id_lookup)
        if track_id in tracks:
            self.context.position = tracks.index(track_id)
            self.context.genre_id = genre_id
            # Shuffle album list if needed
            self._shuffle_playlist()
        else:
            self.stop()


    """
        Restore player state
    """
    def restore_state(self):
        track_id = Objects.settings.get_value('track-id').get_int32()
        if Objects.settings.get_value('save-state') and track_id > 0:
            path = Objects.tracks.get_path(track_id)
            if path != "":
                self._load_track(track_id)
                self.set_albums(track_id, Navigation.ALL, Navigation.ALL)
                self.emit('current-changed')
            else:
                print("Player::restore_state(): track missing")
    
#######################
# PRIVATE             #
#######################
    """
        Add a track to shuffle history
        @param track id as int
        @param album id as int
    """
    def _add_to_shuffle_history(self, track_id, album_id):
        if self.current.album_id not in self._already_played_tracks.keys():
            self._already_played_tracks[self.current.album_id] = []
        self._already_played_tracks[self.current.album_id].append(self.current.id)

              

    """
        Set shuffle mode to gettings value
        @param settings as Gio.Settings, value as str
    """
    def _set_shuffle(self, settings, value):
        self._shuffle = Objects.settings.get_enum('shuffle')
        self._shuffle_playlist()

        if self._shuffle in [Shuffle.TRACKS, Shuffle.TRACKS_ARTIST] or\
           self._user_playlist:
            self._rgvolume.props.album_mode = 0
        else:
            self._rgvolume.props.album_mode = 1

        if not self._user_playlist:
            self.set_albums(self.current.id,
                            self.current.aartist_id,
                            self.context.genre_id)

    """
        Next track in shuffle mode
        if force, stop current track
        a fresh sqlite cursor should be passed as sql if we are in a thread
        @param bool, sqlite cursor
    """
    def _shuffle_next(self, force=False, sql=None):
        track_id = self._get_random(sql)
        # Need to clear history
        if not track_id:
            self._albums = self._already_played_albums
            self._played_tracks_history = []
            self._already_played_tracks = {}
            self._already_played_albums = []
            self._shuffle_next(force)
            return

        if force:
            self.load(track_id)
        else:
            self._load_track(track_id, sql)

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

    """
        On stream start
        Emit "current-changed" to notify others components
    """
    def _on_stream_start(self, bus, message):
        self.emit("current-changed")
        self._errors = 0
        # Add track to shuffle history if needed
        if self._shuffle != Shuffle.NONE or self._is_party:
            if self.current.id in self._played_tracks_history:
                self._played_tracks_history.remove(self.current.id)
            self._played_tracks_history.append(self.current.id)
            self._add_to_shuffle_history(self.current.id,
                                         self.current.album_id)

    """
        On error, next()
    """
    def _on_bus_error(self, bus, message):
        print("Error playing: ", self.current.path)
        self.next(True)
        return False

    """
        On eos, force loading if queue fails,
        if on_stream_about_to_finish never get send
    """
    def _on_bus_eos(self, bus, message):
        self.load(self.current.id)

    """
        When stream is about to finish, switch to next track without gap
    """
    def _on_stream_about_to_finish(self, obj):
        self._previous_track_id = self.current.id
        # We are in a thread, we need to create a new cursor
        sql = Objects.db.get_cursor()
        self.next(False, sql)
        # Add populariy if we listen to the song
        album_id = Objects.tracks.get_album_id(self._previous_track_id, sql)
        try:
            Objects.albums.set_more_popular(album_id, sql)
        except:
            pass
        sql.close()

    """
        On error, try 3 more times playing a track
    """
    def _on_errors(self):
        self._errors += 1
        if self._errors < 3:
            GLib.idle_add(self.next, True)
        else:
            self.current = CurrentTrack()
            GLib.idle_add(self.stop)
            GLib.idle_add(self.emit, 'current-changed')

    """
        Load track
        @param track id as int, sqlite cursor
        @return False if track not loaded
    """
    def _load_track(self, track_id, sql=None):
        stop = False

        # Stop if needed
        if self.context.next == NextContext.STOP_TRACK:
            self.context.next = NextContext.STOP_NONE
            stop = True

        # Stop if album changed
        new_album_id = Objects.tracks.get_album_id(
                                                track_id,
                                                sql)
        if self.context.next == NextContext.STOP_ALBUM and\
           self.current.album_id != new_album_id:
            self.context.next = NextContext.STOP_NONE
            stop = True

        # Stop if aartist changed
        new_aartist_id = Objects.tracks.get_aartist_id(
                                                track_id,
                                                sql)
        if self.context.next == NextContext.STOP_ARTIST and\
           self.current.aartist_id != new_aartist_id:
            self.context.next = NextContext.STOP_NONE
            stop = True

        self.current.id = track_id
        self.current.title = Objects.tracks.get_name(
                                                self.current.id,
                                                sql)
        self.current.album_id = new_album_id
        self.current.album = Objects.albums.get_name(
                                                self.current.album_id,
                                                sql)
        self.current.aartist_id = new_aartist_id
        self.current.aartist = translate_artist_name(
                                        Objects.artists.get_name(
                                                self.current.aartist_id,
                                                sql))
        artist_name = ""
        for artist_id in Objects.tracks.get_artist_ids(self.current.id,
                                                       sql):
            artist_name += translate_artist_name(
                            Objects.artists.get_name(artist_id, sql)) + ", "
        self.current.artist = artist_name[:-2]

        self.current.genre = Objects.albums.get_genre_name(
                                                self.current.album_id,
                                                sql)
        self.current.duration = Objects.tracks.get_length(self.current.id, sql)
        self.current.number = Objects.tracks.get_number(self.current.id, sql)
        self.current.path = Objects.tracks.get_path(self.current.id, sql)
        if path.exists(self.current.path):
            try:
                self._playbin.set_property('uri',
                                           GLib.filename_to_uri(
                                                        self.current.path))
            except:  # Gstreamer error, stop
               self._on_errors()
               return False
        else:
            print("File doesn't exist: ", self.current.path)
            self._on_errors()
            return False

        if stop:
            GLib.idle_add(self.stop)
            GLib.idle_add(self.emit, "current-changed")
        return True
