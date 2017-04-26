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

from gi.repository import Gst, GstAudio, GstPbutils, GLib

from time import time
from threading import Thread

from lollypop.player_base import BasePlayer
from lollypop.tagreader import TagReader
from lollypop.player_plugins import PluginsPlayer
from lollypop.define import GstPlayFlags, NextContext, Lp
from lollypop.codecs import Codecs
from lollypop.define import Type, DbPersistent
from lollypop.utils import debug, get_network_available
from lollypop.objects import Track


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
        self.__codecs = Codecs()
        self._playbin = self.__playbin1 = Gst.ElementFactory.make(
                                                           "playbin", "player")
        self.__playbin2 = Gst.ElementFactory.make("playbin", "player")
        self.__preview = None
        self._plugins = self._plugins1 = PluginsPlayer(self.__playbin1)
        self._plugins2 = PluginsPlayer(self.__playbin2)
        self._playbin.connect("notify::volume", self.__on_volume_changed)
        for playbin in [self.__playbin1, self.__playbin2]:
            flags = playbin.get_property("flags")
            flags &= ~GstPlayFlags.GST_PLAY_FLAG_VIDEO
            playbin.set_property("flags", flags)
            playbin.set_property("buffer-size", 5 << 20)
            playbin.set_property("buffer-duration", 10 * Gst.SECOND)
            playbin.connect("about-to-finish",
                            self.__on_stream_about_to_finish)
            bus = playbin.get_bus()
            bus.add_signal_watch()
            bus.connect("message::error", self.__on_bus_error)
            bus.connect("message::eos", self.__on_bus_eos)
            bus.connect("message::element", self.__on_bus_element)
            bus.connect("message::stream-start", self._on_stream_start)
            bus.connect("message::tag", self.__on_bus_message_tag)
        self._start_time = 0

    @property
    def preview(self):
        """
            Get a preview bin
            @return Gst.Element
        """
        if self.__preview is None:
            self.__preview = Gst.ElementFactory.make("playbin", "player")
            self.set_preview_output()
        return self.__preview

    def set_preview_output(self):
        """
            Set preview output
        """
        if self.__preview is not None:
            output = Lp().settings.get_value("preview-output").get_string()
            pulse = Gst.ElementFactory.make("pulsesink", "output")
            if pulse is None:
                pulse = Gst.ElementFactory.make("alsasink", "output")
            if pulse is not None:
                pulse.set_property("device", output)
                self.__preview.set_property("audio-sink", pulse)

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

    def load(self, track):
        """
            Stop current track, load track id and play it
            @param track as Track
        """
        if self._crossfading and\
           self._current_track.id is not None and\
           self.is_playing and\
           self._current_track.id != Type.RADIOS:
            duration = Lp().settings.get_value("mix-duration").get_int32()
            self.__do_crossfade(duration, track, False)
        else:
            self.__load(track)

    def play(self):
        """
            Change player state to PLAYING
        """
        # No current playback, song in queue
        if self._current_track.id is None:
            if self._next_track.id is not None:
                self.load(self._next_track)
        else:
            self._playbin.set_state(Gst.State.PLAYING)
            self.emit("status-changed")

    def pause(self):
        """
            Change player state to PAUSED
        """
        if self._current_track.id == Type.RADIOS:
            self._playbin.set_state(Gst.State.NULL)
        else:
            self._playbin.set_state(Gst.State.PAUSED)
        self.emit("status-changed")

    def stop(self):
        """
            Change player state to STOPPED
        """
        self._playbin.set_state(Gst.State.NULL)
        self.emit("status-changed")

    def stop_all(self):
        """
            Stop all bins, lollypop should quit now
        """
        # Stop
        self.__playbin1.set_state(Gst.State.NULL)
        self.__playbin2.set_state(Gst.State.NULL)

    def play_pause(self):
        """
            Set playing if paused
            Set paused if playing
        """
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def seek(self, position):
        """
            Seek current track to position
            @param position as seconds
        """
        if self.locked or self._current_track.id is None:
            return
        # Seems gstreamer doesn"t like seeking to end, sometimes
        # doesn"t go to next track
        if position >= self._current_track.duration:
            self.next()
        else:
            self._playbin.seek_simple(Gst.Format.TIME,
                                      Gst.SeekFlags.FLUSH |
                                      Gst.SeekFlags.KEY_UNIT,
                                      position * Gst.SECOND)
            self.emit("seeked", position)

    @property
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

    @property
    def position(self):
        """
            Return bin playback position
            @HACK handle crossefade here, as we know we"re going to be
            called every seconds
            @return position as int
        """
        position = self._playbin.query_position(Gst.Format.TIME)[1] / 1000
        if self._crossfading and self._current_track.duration > 0:
            duration = self._current_track.duration - position / 1000000
            if duration < Lp().settings.get_value("mix-duration").get_int32():
                self.__do_crossfade(duration)
        return position * 60

    @property
    def current_track(self):
        """
            Current track
        """
        return self._current_track

    @property
    def volume(self):
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
        self.__playbin1.set_volume(GstAudio.StreamVolumeFormat.CUBIC, rate)
        self.__playbin2.set_volume(GstAudio.StreamVolumeFormat.CUBIC, rate)
        self.emit("volume-changed")

    def next(self):
        """
            Go next track
        """
        pass

#######################
# PROTECTED           #
#######################
    def _load_track(self, track, init_volume=True):
        """
            Load track
            @param track as Track
            @param init volume as bool
            @return False if track not loaded
        """
        if self.__need_to_stop():
            return False
        if init_volume:
            self._plugins.volume.props.volume = 1.0
        debug("BinPlayer::_load_track(): %s" % track.uri)
        try:
            self._current_track = track
            if track.is_web:
                loaded = self._load_web(track)
                # If track not loaded, go next
                if not loaded:
                    self.set_next()
                    GLib.timeout_add(500, self.__load,
                                     self.next_track, init_volume)
                return False  # Return not loaded as handled by load_web()
            else:
                self._playbin.set_property("uri", track.uri)
        except Exception as e:  # Gstreamer error
            print("BinPlayer::_load_track(): ", e)
            return False
        return True

    def _load_web(self, track, play=True):
        """
            Load track url and play it
            @param track as Track
            @param play as bool
            @return True if loading
        """
        if not get_network_available():
            # Force widgets to update (spinners)
            self.emit("current-changed")
            return False
        try:
            from lollypop.web import Web
            if play:
                self.emit("loading-changed", True)
            t = Thread(target=Web.play_track,
                       args=(track, play, self.__set_gv_uri))
            t.daemon = True
            t.start()
            return True
        except Exception as e:
            self._current_track = Track()
            self.stop()
            self.emit("current-changed")
            if Lp().notify is not None:
                Lp().notify.send(str(e), track.uri)
            print("PlayerBin::_load_web()", e)

    def _scrobble(self, finished, finished_start_time):
        """
            Scrobble on lastfm
            @param finished as Track
            @param finished_start_time as int
        """
        # Last.fm policy
        if finished.duration < 30:
            return
        # Scrobble on lastfm
        if Lp().lastfm is not None:
            artists = ", ".join(finished.artists)
            played = time() - finished_start_time
            # We can scrobble if the track has been played
            # for at least half its duration, or for 4 minutes
            if played >= finished.duration / 2 or played >= 240:
                Lp().lastfm.do_scrobble(artists,
                                        finished.album_name,
                                        finished.title,
                                        int(finished_start_time))

    def _on_stream_start(self, bus, message):
        """
            On stream start
            Emit "current-changed" to notify others components
            @param bus as Gst.Bus
            @param message as Gst.Message
        """
        self._start_time = time()
        debug("Player::_on_stream_start(): %s" % self._current_track.uri)
        self.emit("current-changed")
        # Update now playing on lastfm
        if Lp().lastfm is not None and self._current_track.id >= 0:
            artists = ", ".join(self._current_track.artists)
            Lp().lastfm.now_playing(artists,
                                    self._current_track.album_name,
                                    self._current_track.title,
                                    int(self._current_track.duration))
        try:
            if not Lp().scanner.is_locked():
                Lp().tracks.set_listened_at(self._current_track.id,
                                            int(time()))
        except:  # Locked database
            pass

#######################
# PRIVATE             #
#######################
    def __update_current_duration(self, reader, track):
        """
            Update current track duration
            @param reader as TagReader
            @param track id as int
        """
        try:
            duration = reader.get_info(track.uri).get_duration() / 1000000000
            if duration != track.duration and duration > 0:
                Lp().tracks.set_duration(track.id, duration)
                self._current_track.set_duration(duration)
                GLib.idle_add(self.emit, "duration-changed", track.id)
        except:
            pass

    def __load(self, track, init_volume=True):
        """
            Stop current track, load track id and play it
            If was playing, do not use play as status doesn"t changed
            @param track as Track
            @param init volume as bool
        """
        was_playing = self.is_playing
        self._playbin.set_state(Gst.State.NULL)
        if self._load_track(track, init_volume):
            if was_playing:
                self._playbin.set_state(Gst.State.PLAYING)
            else:
                self.play()

    def __volume_up(self, playbin, plugins, duration):
        """
            Make volume going up smoothly
            @param playbin as Gst.Bin
            @param plugins as PluginsPlayer
            @param duration as int
        """
        # We are not the active playbin, stop all
        if self._playbin != playbin:
            return
        if duration > 0:
            vol = plugins.volume.props.volume
            steps = duration / 0.25
            vol_up = (1.0 - vol) / steps
            rate = vol + vol_up
            if rate < 1.0:
                plugins.volume.props.volume = rate
                GLib.timeout_add(250, self.__volume_up,
                                 playbin, plugins, duration - 0.25)
            else:
                plugins.volume.props.volume = 1.0
        else:
            plugins.volume.props.volume = 1.0

    def __volume_down(self, playbin, plugins, duration):
        """
            Make volume going down smoothly
            @param playbin as Gst.Bin
            @param plugins as PluginsPlayer
            @param duration as int
        """
        # We are again the active playbin, stop all
        if self._playbin == playbin:
            return
        if duration > 0:
            vol = plugins.volume.props.volume
            steps = duration / 0.25
            vol_down = vol / steps
            rate = vol - vol_down
            if rate > 0:
                plugins.volume.props.volume = rate
                GLib.timeout_add(250, self.__volume_down,
                                 playbin, plugins, duration - 0.25)
            else:
                plugins.volume.props.volume = 0.0
                playbin.set_state(Gst.State.NULL)
        else:
            plugins.volume.props.volume = 0.0
            playbin.set_state(Gst.State.NULL)

    def __do_crossfade(self, duration, track=None, next=True):
        """
            Crossfade tracks
            @param duration as int
            @param track as Track
            @param next as bool
        """
        # No cossfading if we need to stop
        if self.__need_to_stop() and next:
            return

        if track is None:
            self._scrobble(self._current_track, self._start_time)
            # Increment popularity
            if not Lp().scanner.is_locked():
                Lp().tracks.set_more_popular(self._current_track.id)
                # In party mode, linear popularity
                if self.is_party:
                    pop_to_add = 1
                # In normal mode, based on tracks count
                else:
                    count = Lp().albums.get_tracks_count(
                                                 self._current_track.album_id)
                    if count:
                        pop_to_add = int(Lp().albums.max_count / count)
                    else:
                        pop_to_add = 0
                if pop_to_add > 0:
                    Lp().albums.set_more_popular(self._current_track.album_id,
                                                 pop_to_add)

        GLib.idle_add(self.__volume_down, self._playbin,
                      self._plugins, duration)
        if self._playbin == self.__playbin2:
            self._playbin = self.__playbin1
            self._plugins = self._plugins1
        else:
            self._playbin = self.__playbin2
            self._plugins = self._plugins2

        if track is not None:
            self.__load(track, False)
            self._plugins.volume.props.volume = 0
            GLib.idle_add(self.__volume_up, self._playbin,
                          self._plugins, duration)
        elif next and self._next_track.id is not None:
            self.__load(self._next_track, False)
            self._plugins.volume.props.volume = 0
            GLib.idle_add(self.__volume_up, self._playbin,
                          self._plugins, duration)
        elif self._prev_track.id is not None:
            self.__load(self._prev_track, False)
            self._plugins.volume.props.volume = 0
            GLib.idle_add(self.__volume_up, self._playbin,
                          self._plugins, duration)

    def __need_to_stop(self):
        """
            Return True if playback needs to stop
            @return bool
        """
        stop = False
        playback = Lp().settings.get_enum("playback")
        if playback == NextContext.STOP:
            if (not self._albums and
                not self.queue and
                not self._user_playlist_ids) or\
                    playback == self._next_context:
                stop = True
        return stop and self.is_playing

    def __on_volume_changed(self, playbin, sink):
        """
            Update volume
            @param playbin as Gst.Bin
            @param sink as Gst.Sink
        """
        if playbin == self.__playbin1:
            vol = self.__playbin1.get_volume(GstAudio.StreamVolumeFormat.CUBIC)
            self.__playbin2.set_volume(GstAudio.StreamVolumeFormat.CUBIC, vol)
        else:
            vol = self.__playbin2.get_volume(GstAudio.StreamVolumeFormat.CUBIC)
            self.__playbin1.set_volume(GstAudio.StreamVolumeFormat.CUBIC, vol)
        self.emit("volume-changed")

    def __on_bus_message_tag(self, bus, message):
        """
            Read tags from stream
            @param bus as Gst.Bus
            @param message as Gst.Message
        """
        # Some radio streams send message tag every seconds!
        changed = False
        if self._current_track.persistent == DbPersistent.INTERNAL and\
            (self._current_track.id >= 0 or
             self._current_track.duration > 0.0):
            return
        debug("Player::__on_bus_message_tag(): %s" % self._current_track.uri)
        reader = TagReader()

        # Update duration of non internals
        if self._current_track.persistent != DbPersistent.INTERNAL:
            t = Thread(target=self.__update_current_duration,
                       args=(reader, self._current_track))
            t.daemon = True
            t.start()
            return

        tags = message.parse_tag()
        title = reader.get_title(tags, "")
        if title != "" and self._current_track.name != title:
            self._current_track.name = title
            changed = True
        if self._current_track.name == "":
            self._current_track.name = self._current_track.uri
            changed = True
        artists = reader.get_artists(tags)
        if artists != "" and self._current_track.artists != artists:
            self._current_track.artists = artists.split(",")
            changed = True
        if not self._current_track.artists:
            self._current_track.artists = self._current_track.album_artists
            changed = True

        if self._current_track.id == Type.EXTERNALS:
            (b, duration) = self._playbin.query_duration(Gst.Format.TIME)
            if b:
                self._current_track.duration = duration/1000000000
            # We do not use tagreader as we need to check if value is None
            self._current_track.album_name = tags.get_string_index("album",
                                                                   0)[1]
            if self._current_track.album_name is None:
                self._current_track.album_name = ""
            self._current_track.genres = reader.get_genres(tags).split(",")
            changed = True
        if changed:
            self.emit("current-changed")

    def __on_bus_element(self, bus, message):
        """
            Set elements for missings plugins
            @param bus as Gst.Bus
            @param message as Gst.Message
        """
        if GstPbutils.is_missing_plugin_message(message):
            self.__codecs.append(message)

    def __on_bus_error(self, bus, message):
        """
            Handle first bus error, ignore others
            @param bus as Gst.Bus
            @param message as Gst.Message
        """
        debug("Error playing: %s" % self._current_track.uri)
        Lp().window.pulse(False)
        if self.__codecs.is_missing_codec(message):
            self.__codecs.install()
            Lp().scanner.stop()
        elif Lp().notify is not None:
            Lp().notify.send(message.parse_error()[0].message)
        self.emit("current-changed")
        return True

    def __on_bus_eos(self, bus, message):
        """
            On end of stream, stop playback
            go next otherwise
        """
        debug("Player::__on_bus_eos(): %s" % self._current_track.uri)
        if self._playbin.get_bus() == bus:
            self.stop()
            self._next_context = NextContext.NONE
            if self._next_track.id is not None:
                self._load_track(self._next_track)
            self.emit("current-changed")

    def __on_stream_about_to_finish(self, playbin):
        """
            When stream is about to finish, switch to next track without gap
            @param playbin as Gst bin
        """
        debug("Player::__on_stream_about_to_finish(): %s" % playbin)
        # Don"t do anything if crossfade on, track already changed
        if self._crossfading:
            return
        if self._current_track.id == Type.RADIOS:
            return
        self._scrobble(self._current_track, self._start_time)
        # Increment popularity
        if not Lp().scanner.is_locked() and self._current_track.id >= 0:
            Lp().tracks.set_more_popular(self._current_track.id)
            # In party mode, linear popularity
            if self.is_party:
                pop_to_add = 1
            # In normal mode, based on tracks count
            else:
                # Some users report an issue where get_tracks_count() return 0
                # See issue #886
                # Don"t understand how this can happen!
                count = Lp().albums.get_tracks_count(
                                                 self._current_track.album_id)
                if count:
                    pop_to_add = int(Lp().albums.max_count / count)
                else:
                    pop_to_add = 1
            Lp().albums.set_more_popular(self._current_track.album_id,
                                         pop_to_add)
        if self._next_track.id is not None:
            self._load_track(self._next_track)

    def __set_gv_uri(self, uri, track, play):
        """
            Play uri for io
            @param uri as str
            @param track as Track
            @param play as bool
        """
        track.set_uri(uri)
        if play:
            self.load(track)
