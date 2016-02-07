# Copyright (c) 2014-2016 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import Gst, GstAudio, GstPbutils, GLib

from gettext import gettext as _
from time import time

from lollypop.player_base import BasePlayer
from lollypop.tagreader import ScannerTagReader
from lollypop.player_rg import ReplayGainPlayer
from lollypop.define import GstPlayFlags, NextContext, Lp
from lollypop.codecs import Codecs
from lollypop.define import Type
from lollypop.utils import debug


class BinPlayer(BasePlayer):
    """
        Gstreamer bin player
    """

    def __init__(self):
        """
            Init playbin
        """
        Gst.init(None)
        BasePlayer.__init__(self)
        self._codecs = Codecs()
        self._gst_duration = 0
        self._crossfading = False
        self._playbin = self._playbin1 = Gst.ElementFactory.make(
                                                           'playbin', 'player')
        self._playbin2 = Gst.ElementFactory.make('playbin', 'player')
        self._rg1 = ReplayGainPlayer(self._playbin1)
        self._rg2 = ReplayGainPlayer(self._playbin2)
        self._volume = 1.0
        self._volume_id = self._playbin.connect('notify::volume',
                                                self._on_volume_changed)
        for playbin in [self._playbin1, self._playbin2]:
            flags = playbin.get_property("flags")
            flags &= ~GstPlayFlags.GST_PLAY_FLAG_VIDEO
            playbin.set_property('flags', flags)
            playbin.set_property('buffer-size', 5 << 20)
            playbin.set_property('buffer-duration', 10 * Gst.SECOND)
            playbin.connect('about-to-finish',
                            self._on_stream_about_to_finish)
            bus = playbin.get_bus()
            bus.add_signal_watch()
            bus.connect('message::error', self._on_bus_error)
            bus.connect('message::eos', self._on_bus_eos)
            bus.connect('message::element', self._on_bus_element)
            bus.connect('message::stream-start', self._on_stream_start)
            bus.connect("message::tag", self._on_bus_message_tag)
        self._handled_error = None
        self._start_time = 0

    def is_playing(self):
        """
            True if player is playing
            @return bool
        """
        ok, state, pending = self._playbin.get_state(Gst.CLOCK_TIME_NONE)
        if ok == Gst.StateChangeReturn.ASYNC:
            return pending == Gst.State.PLAYING
        elif ok == Gst.StateChangeReturn.SUCCESS:
            return state == Gst.State.PLAYING
        else:
            return False

    def get_status(self):
        """
            Playback status
            @return Gstreamer state
        """
        ok, state, pending = self._playbin.get_state(Gst.CLOCK_TIME_NONE)
        if ok == Gst.StateChangeReturn.ASYNC:
            state = pending
        elif (ok != Gst.StateChangeReturn.SUCCESS):
            state = Gst.State.NULL
        return state

    def load(self, track, notify=True):
        """
            Stop current track, load track id and play it
            @param track as Track
            @param notify as bool
        """
        if self._crossfading:
            duration = Lp().settings.get_value('mix-duration').get_int32()
            self._do_crossfade(duration, track, False, notify)
        else:
            self._load(track, notify)

    def play(self):
        """
            Change player state to PLAYING
        """
        # No current playback, song in queue
        if self.current_track.id is None:
            if self.next_track.id is not None:
                self.load(self.next_track)
        else:
            self._playbin.set_state(Gst.State.PLAYING)
            self.emit("status-changed")

    def pause(self):
        """
            Change player state to PAUSED
        """
        self._playbin.set_state(Gst.State.PAUSED)
        self.emit("status-changed")

    def stop(self):
        """
            Change player state to STOPPED
        """
        self._gst_duration = 0
        self._playbin.set_state(Gst.State.NULL)
        self.emit("status-changed")

    def stop_all(self):
        """
            Stop all bins, lollypop should quit now
        """
        self._gst_duration = 0
        # Stop crossfade
        if self._playbin == self._playbin2:
            self._playbin = self._playbin1
        else:
            self._playbin = self._playbin2
        # Restore volume
        self._playbin1.set_volume(GstAudio.StreamVolumeFormat.LINEAR,
                                  self._volume)
        self._playbin2.set_volume(GstAudio.StreamVolumeFormat.LINEAR,
                                  self._volume)
        # Stop
        self._playbin1.set_state(Gst.State.NULL)
        self._playbin2.set_state(Gst.State.NULL)

    def play_pause(self):
        """
            Set playing if paused
            Set paused if playing
        """
        if self.is_playing():
            self.pause()
        else:
            self.play()

    def seek(self, position):
        """
            Seek current track to position
            @param position as seconds
        """
        # Seems gstreamer doesn't like seeking to end, sometimes
        # doesn't go to next track
        if position > self.current_track.duration - 1:
            self.next()
        else:
            self._playbin.seek_simple(Gst.Format.TIME,
                                      Gst.SeekFlags.FLUSH |
                                      Gst.SeekFlags.KEY_UNIT,
                                      position * Gst.SECOND)
            self.emit("seeked", position)

    def get_position_in_track(self):
        """
            Return bin playback position
            @HACK handle crossefade here, as we know we're going to be
            called every seconds
            @return position as int
        """
        position = self._playbin.query_position(Gst.Format.TIME)[1] / 1000
        if self._crossfading and self._gst_duration > 0:
            duration = (self._gst_duration - position) / 1000000
            if duration < Lp().settings.get_value('mix-duration').get_int32():
                self._do_crossfade(duration)
        return position * 60

    def get_volume(self):
        """
            Return player volume rate
            @return rate as double
        """
        return self._playbin.get_volume(GstAudio.StreamVolumeFormat.CUBIC)

    def set_volume(self, rate):
        """
            Set player volume rate
            @param rate as double
        """
        self._volume = rate
        self._playbin1.set_volume(GstAudio.StreamVolumeFormat.CUBIC, rate)
        self._playbin2.set_volume(GstAudio.StreamVolumeFormat.CUBIC, rate)
        self.emit('volume-changed')

    def next(self):
        """
            Go next track
        """
        pass

#######################
# PRIVATE             #
#######################
    def _load(self, track, notify=True):
        """
            Stop current track, load track id and play it
            @param track as Track
        """
        self._playbin.set_state(Gst.State.NULL)
        if self._load_track(track):
            if notify:
                self.play()
            else:
                self._playbin.set_state(Gst.State.PLAYING)

    def _volume_up(self, playbin, duration):
        """
            Make volume going up smoothly
            @param playbin as Gst.Bin
            @param duration as int
        """
        # We are not the active playbin, stop all
        if self._playbin != playbin:
            return
        if duration > 0:
            vol = playbin.get_volume(GstAudio.StreamVolumeFormat.LINEAR)
            steps = duration / 0.25
            vol_up = (self._volume - vol) / steps
            rate = vol + vol_up
            if rate < self._volume:
                playbin.set_volume(GstAudio.StreamVolumeFormat.LINEAR, rate)
                GLib.timeout_add(250, self._volume_up,
                                 playbin, duration - 0.25)
            else:
                playbin.set_volume(GstAudio.StreamVolumeFormat.LINEAR,
                                   self._volume)
                if self._volume_id is None:
                    self._volume_id = playbin.connect('notify::volume',
                                                      self._on_volume_changed)

    def _volume_down(self, playbin, duration):
        """
            Make volume going down smoothly
            @param playbin as Gst.Bin
            @param duration as int
        """
        # We are again the active playbin, stop all
        if self._playbin == playbin:
            return
        if duration > 0:
            vol = playbin.get_volume(GstAudio.StreamVolumeFormat.LINEAR)
            steps = duration / 0.25
            vol_down = vol / steps
            rate = vol - vol_down
            if rate > 0:
                playbin.set_volume(GstAudio.StreamVolumeFormat.LINEAR, rate)
                GLib.timeout_add(250, self._volume_down,
                                 playbin, duration - 0.25)
            else:
                playbin.set_state(Gst.State.NULL)
                playbin.set_volume(GstAudio.StreamVolumeFormat.LINEAR,
                                   self._volume)

    def _do_crossfade(self, duration, track=None, next=True, notify=True):
        """
            Crossfade tracks
            @param duration as int
            @param next as bool
            @param track as Track
            @param notify as bool
        """
        if self.current_track.id == Type.RADIOS:
            return
        if self._volume_id is not None:
            self._playbin.disconnect(self._volume_id)
            self._volume_id = None
        GLib.idle_add(self._volume_down, self._playbin, duration)
        if self._playbin == self._playbin2:
            self._playbin = self._playbin1
        else:
            self._playbin = self._playbin2

        finished = self.current_track
        finished_start_time = self._start_time
        if track is not None:
            self._load(track, notify)
            self._playbin.set_volume(GstAudio.StreamVolumeFormat.LINEAR,
                                     0)
            GLib.idle_add(self._volume_up, self._playbin, duration)
        elif next and self.next_track.id is not None:
            self._load(self.next_track, notify)
            self._playbin.set_volume(GstAudio.StreamVolumeFormat.LINEAR,
                                     0)
            GLib.idle_add(self._volume_up, self._playbin, duration)
        elif self.prev_track.id is not None:
            self._load(self.prev_track, notify)
            self._playbin.set_volume(GstAudio.StreamVolumeFormat.LINEAR,
                                     0)
            GLib.idle_add(self._volume_up, self._playbin, duration)
        self._track_finished(finished, finished_start_time)

    def _load_track(self, track):
        """
            Load track
            @param track as Track
            @return False if track not loaded
        """
        stop = False

        # Stop if needed
        if self.context.next == NextContext.STOP_TRACK:
            stop = True

        # Stop if album changed
        if self.context.next == NextContext.STOP_ALBUM and\
           self.current_track.album.id != track.album.id:
            stop = True

        # Stop if album_artist changed
        if self.context.next == NextContext.STOP_ARTIST and\
           self.current_track.album_artist_id != track.album_artist_id:
            stop = True

        if stop and self.is_playing():
            return False

        self.current_track = track

        try:
            self._playbin.set_property('uri',
                                       self.current_track.uri)
        except Exception as e:  # Gstreamer error
            print("BinPlayer::_load_track(): ", e)
            return False

        return True

    def _track_finished(self, finished, finished_start_time):
        """
            Do some actions for played track
            @param finished as Track
            @param finished_start_time as int
        """
        # Increment popularity
        if not Lp().scanner.is_locked():
            Lp().tracks.set_more_popular(finished.id)
            Lp().albums.set_more_popular(finished.album_id)
        # Scrobble on lastfm
        if Lp().lastfm is not None:
            if finished.album_artist_id == Type.COMPILATIONS:
                artist = finished.artist
            else:
                artist = finished.album_artist
            if time() - finished_start_time > 30:
                Lp().lastfm.scrobble(artist,
                                     finished.album_name,
                                     finished.title,
                                     int(finished_start_time),
                                     int(finished.duration))

    def _on_volume_changed(self, playbin, sink):
        """
            Update volume
            @param playbin as Gst.Bin
            @param sink as Gst.Sink
        """
        volume = playbin.get_volume(GstAudio.StreamVolumeFormat.LINEAR)
        if volume != self._volume:
            self._volume = volume
            self.emit('volume-changed')

    def _on_bus_message_tag(self, bus, message):
        """
            Read tags from stream
            @param bus as Gst.Bus
            @param message as Gst.Message
        """
        if self.current_track.id >= 0 or\
           self.current_track.duration > 0.0:
            return
        debug("Player::_on_bus_message_tag(): %s" % self.current_track.uri)
        reader = ScannerTagReader()
        tags = message.parse_tag()

        title = reader.get_title(tags, '')
        if title != '':
            self.current_track.name = title
        if self.current_track.name == '':
            self.current_track.name = self.current_track.uri

        artist = reader.get_artists(tags)
        if artist != '':
            self.current_track.artist_names = artist

        # If title set, force artist
        if self.current_track.title != '' and self.current_track.artist == '':
            self.current_track.artist_names = self.current_track.album_artist

        if self.current_track.id == Type.EXTERNALS:
            (b, duration) = self._playbin.query_duration(Gst.Format.TIME)
            if b:
                self.current_track.duration = duration/1000000000
            # We do not use tagreader as we need to check if value is None
            self.current_track.album_name = tags.get_string_index('album',
                                                                  0)[1]
            if self.current_track.album_name is None:
                self.current_track.album_name = ''
            self.current_track.artist_names = reader.get_artists(tags)
            self.current_track.set_album_artist(reader.get_album_artist(tags))
            if self.current_track.album_artist == '':
                self.current_track.set_album_artist(self.current_track.artist)
            self.current_track.genre_name = reader.get_genres(tags)
        self.emit('current-changed')

    def _on_bus_element(self, bus, message):
        """
            Set elements for missings plugins
            @param bus as Gst.Bus
            @param message as Gst.Message
        """
        if GstPbutils.is_missing_plugin_message(message):
            if self._codecs is not None:
                self._codecs.append(message)

    def _on_bus_error(self, bus, message):
        """
            Handle first bus error, ignore others
            @param bus as Gst.Bus
            @param message as Gst.Message
        """
        debug("Error playing: %s" % self.current_track.uri)
        Lp().window.pulse(False)
        if self._codecs.is_missing_codec(message):
            self._codecs.install()
            Lp().scanner.stop()
        elif Lp().notify is not None:
            Lp().notify.send(_("File doesn't exist: %s") %
                             self.current_track.uri)
        self.stop()
        self.emit('current-changed')
        return True

    def _on_bus_eos(self, bus, message):
        """
            On end of stream, stop playing if user ask for,
            go next otherwise
        """
        debug("Player::_on_bus_eos(): %s" % self.current_track.uri)
        if self.context.next not in [NextContext.NONE,
                                     NextContext.START_NEW_ALBUM]:
            self.stop()
            self.context.next = NextContext.NONE
            if self.next_track.id is not None:
                self._load_track(self.next_track)
            self.emit('current-changed')
        elif not Lp().settings.get_value('mix'):
            self.next()

    def _on_stream_about_to_finish(self, playbin):
        """
            When stream is about to finish, switch to next track without gap
            @param playbin as Gst bin
        """
        # Don't do anything if crossfade on
        if self._playbin != playbin:
            return
        if self.current_track.id == Type.RADIOS:
            return
        finished = self.current_track
        finished_start_time = self._start_time
        if self.next_track.id is not None:
            self._load_track(self.next_track)
        self._track_finished(finished, finished_start_time)

    def _on_stream_start(self, bus, message):
        """
            On stream start
            Emit "current-changed" to notify others components
            @param bus as Gst.Bus
            @param message as Gst.Message
        """
        self._start_time = time()
        self._gst_duration = self._playbin.query_duration(
                                                    Gst.Format.TIME)[1] / 1000
        debug("Player::_on_stream_start(): %s" % self.current_track.uri)
        self.emit('current-changed')
        # Update now playing on lastfm
        if Lp().lastfm is not None and self.current_track.id >= 0:
            if self.current_track.album_artist_id == Type.COMPILATIONS:
                artist = self.current_track.artist
            else:
                artist = self.current_track.album_artist
                Lp().lastfm.now_playing(artist,
                                        self.current_track.album_name,
                                        self.current_track.title,
                                        int(self.current_track.duration))
        if not Lp().scanner.is_locked():
            Lp().tracks.set_listened_at(self.current_track.id, int(time()))
        self._handled_error = None
