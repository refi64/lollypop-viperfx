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

from gi.repository import GObject, GLib

from lollypop.tagreader import TagReader
from lollypop.player_base import BasePlayer
from lollypop.player_queue import QueuePlayer
from lollypop.player_linear import LinearPlayer
from lollypop.player_shuffle import ShufflePlayer
from lollypop.player_userplaylist import UserPlaylistPlayer
from lollypop.define import Objects, Navigation, CurrentTrack
from lollypop.define import Shuffle, PlayContext


# Player object used to manage playback and playlists
class Player(GObject.GObject, BasePlayer, QueuePlayer, UserPlaylistPlayer,
             LinearPlayer, ShufflePlayer, TagReader):
    __gsignals__ = {
        'current-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'seeked': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        'status-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'volume-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'queue-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'cover-changed': (GObject.SignalFlags.RUN_FIRST, None, (int,))
    }

    """
        Create a gstreamer bin and listen to signals on bus
    """
    def __init__(self):
        GObject.GObject.__init__(self)
        BasePlayer.__init__(self)
        QueuePlayer.__init__(self)
        LinearPlayer.__init__(self)
        ShufflePlayer.__init__(self)
        UserPlaylistPlayer.__init__(self)
        TagReader.__init__(self)

        self.current = CurrentTrack()
        self.context = PlayContext()
        # Albums in current playlist
        self._albums = None
        # Current shuffle mode
        self._shuffle = Objects.settings.get_enum('shuffle')
        # Tracks already played
        self._played_tracks_history = []
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
    """
    def prev(self):
        # Look at user playlist then
        track_id = UserPlaylistPlayer.prev(self)
        
        # Look at shuffle
        if track_id is None:
            track_id = ShufflePlayer.prev(self)
            
        if track_id is None:
            track_id = LinearPlayer.prev(self)

        if track_id:
            self.load(track_id)

    """
        Play next track
        @param force as bool
        @param sql as sqlite cursor
    """
    def next(self, force=True, sql=None):
        # Look first at user queue
        track_id = QueuePlayer.next(self)

        # Look at user playlist then
        if track_id is None:
            track_id = UserPlaylistPlayer.next(self)

        # Get a random album/track
        if track_id is None:
            track_id = ShufflePlayer.next(self, sql)

        # Get a linear track
        if track_id is None:
            track_id = LinearPlayer.next(self, sql)

        if track_id:
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
            self._shuffle_albums()
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

        if self._shuffle in [Shuffle.TRACKS, Shuffle.TRACKS_ARTIST] or\
           self._user_playlist:
            self._rgvolume.props.album_mode = 0
        else:
            self._rgvolume.props.album_mode = 1

        if self._user_playlist:
            self._shuffle_playlist()
        else:
            self.set_albums(self.current.id,
                            self.current.aartist_id,
                            self.context.genre_id)

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
