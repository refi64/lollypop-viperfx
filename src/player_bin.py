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

from gi.repository import Gst, GLib, GstAudio

from os import path

from lollypop.player_base import BasePlayer
from lollypop.player_rg import ReplayGainPlayer
from lollypop.define import GstPlayFlags, NextContext, Objects, CurrentTrack
from lollypop.utils import translate_artist_name


# Bin player class
class BinPlayer(ReplayGainPlayer, BasePlayer):
    """
        Init playbin
    """
    def __init__(self):
        Gst.init(None)
        BasePlayer.__init__(self)
        self._playbin = Gst.ElementFactory.make('playbin', 'player')
        flags = self._playbin.get_property("flags")
        flags &= ~GstPlayFlags.GST_PLAY_FLAG_VIDEO
        self._playbin.set_property("flags", flags)
        ReplayGainPlayer.__init__(self, self._playbin)
        self._playbin.connect("about-to-finish",
        self._on_stream_about_to_finish)
        bus = self._playbin.get_bus()
        bus.add_signal_watch()
        bus.connect('message::error', self._on_bus_error)
        bus.connect('message::eos', self._on_bus_eos)
        bus.connect('message::stream-start', self._on_stream_start)

    """
        True if player is playing
        @return bool
    """
    def is_playing(self):
        ok, state, pending = self._playbin.get_state(0)
        if ok == Gst.StateChangeReturn.ASYNC:
            return pending == Gst.State.PLAYING
        elif ok == Gst.StateChangeReturn.SUCCESS:
            return state == Gst.State.PLAYING
        else:
            return False

    """
        Emit a "cover-changed" signal
        @param album id as int
    """
    def announce_cover_update(self, album_id):
        self.emit("cover-changed", album_id)

    """
        Playback status
        @return Gstreamer state
    """
    def get_status(self):
        ok, state, pending = self._playbin.get_state(0)
        if ok == Gst.StateChangeReturn.ASYNC:
            state = pending
        elif (ok != Gst.StateChangeReturn.SUCCESS):
            state = Gst.State.NULL
        return state

    """
        Stop current track, load track id and play it
        @param track id as int
    """
    def load(self, track_id):
        self._stop()
        if self._load_track(track_id):
            self.play()

    """
        Change player state to PLAYING
    """
    def play(self):
        self._playbin.set_state(Gst.State.PLAYING)
        self.emit("status-changed")

    """
        Change player state to PAUSED
    """
    def pause(self):
        self._playbin.set_state(Gst.State.PAUSED)
        self.emit("status-changed")

    """
        Change player state to STOPPED
    """
    def stop(self):
        self._stop()
        self.emit("status-changed")

    """
        Set PLAYING if PAUSED
        Set PAUSED if PLAYING
    """
    def play_pause(self):
        if self.is_playing():
            self.pause()
        else:
            self.play()

    """
        Seek current track to position
        @param position as seconds
    """
    def seek(self, position):
        self._playbin.seek_simple(Gst.Format.TIME,
                                  Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                                  position * Gst.SECOND)
        self.emit("seeked", position)

    """
        Return bin playback position
        @return position as int
    """
    def get_position_in_track(self):
        position = self._playbin.query_position(Gst.Format.TIME)[1] / 1000
        return position*60

    """
        Return player volume rate
        @return rate as double
    """
    def get_volume(self):
        return self._playbin.get_volume(GstAudio.StreamVolumeFormat.LINEAR)

    """
        Set player volume rate
        @param rate as double
    """
    def set_volume(self, rate):
        self._playbin.set_volume(GstAudio.StreamVolumeFormat.LINEAR, rate)
        self.emit('volume-changed')

    """
        Go next track
        @param force as bool
        @param sql as sqlite cursor
    """
    def next(self, force, sql):
        pass

#######################
# PRIVATE             #
#######################
    """
        Stop current track (for track change)
    """
    def _stop(self):
        self._playbin.set_state(Gst.State.NULL)

    """
        Load track
        @param track id as int, sqlite cursor
        @return False if track not loaded
    """
    def _load_track(self, track_id, sql=None):
        stop = False

        # Stop if needed
        if self.context.next == NextContext.STOP_TRACK:
            stop = True

        # Stop if album changed
        new_album_id = Objects.tracks.get_album_id(
                                                track_id,
                                                sql)
        if self.context.next == NextContext.STOP_ALBUM and\
           self.current.album_id != new_album_id:
            stop = True

        # Stop if aartist changed
        new_aartist_id = Objects.tracks.get_aartist_id(
                                                track_id,
                                                sql)
        if self.context.next == NextContext.STOP_ARTIST and\
           self.current.aartist_id != new_aartist_id:
            stop = True

        if stop:
            return False

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
            except Exception as e:  # Gstreamer error, stop
                print("BasePlayer::_load_track(): ", e)
                self._on_errors()
                return False
        else:
            print("File doesn't exist: ", self.current.path)
            self._on_errors()
            return False
        return True

    """
        On error, next()
    """
    def _on_bus_error(self, bus, message):
        print("Error playing: ", self.current.path)
        self.next(True)
        return False

    """
        On end of stream, stop playing if user ask for
        Else force playing current track
    """
    def _on_bus_eos(self, bus, message):
        if self.context.next != NextContext.STOP_NONE:
            self.context.next = NextContext.STOP_NONE
            self.stop()
            self.next(False)
            self.emit("current-changed")
        else:
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
        On stream start
        Emit "current-changed" to notify others components
    """
    def _on_stream_start(self, bus, message):
        self.emit("current-changed")
        self._errors = 0
