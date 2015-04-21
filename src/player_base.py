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

from gi.repository import GObject, Gst

from lollypop.player_rg import ReplayGainPlayer


# Base player class
class BasePlayer(GObject.GObject, ReplayGainPlayer):
    __gsignals__ = {
        'current-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'seeked': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        'status-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'volume-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'queue-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'cover-changed': (GObject.SignalFlags.RUN_FIRST, None, (int,))
    }

    """
        Init playbin
    """
    def __init__(self):
        GObject.GObject.__init__(self)
        Gst.init(None)
        self._playbin = Gst.ElementFactory.make('playbin', 'player')
        flags = self._playbin.get_property("flags")
        flags &= ~GstPlayFlags.GST_PLAY_FLAG_VIDEO
        self._playbin.set_property("flags", flags)
        ReplayGainPlayer.__init__(self, self._playbin)

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

#######################
# PRIVATE             #
#######################
    """
        Stop current track (for track change)
    """
    def _stop(self):
        self._playbin.set_state(Gst.State.NULL)
