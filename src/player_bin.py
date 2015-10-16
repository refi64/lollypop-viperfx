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

from gi.repository import Gst, GstAudio, GstPbutils

from gettext import gettext as _
from time import time

from lollypop.player_base import BasePlayer
from lollypop.tagreader import ScannerTagReader
from lollypop.player_rg import ReplayGainPlayer
from lollypop.define import GstPlayFlags, NextContext, Lp
from lollypop.codecs import Codecs
from lollypop.define import Type
from lollypop.utils import debug


class BinPlayer(ReplayGainPlayer, BasePlayer):
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
        self._playbin = Gst.ElementFactory.make('playbin', 'player')
        flags = self._playbin.get_property("flags")
        flags &= ~GstPlayFlags.GST_PLAY_FLAG_VIDEO
        self._playbin.set_property('flags', flags)
        self._playbin.set_property('buffer-size', 5 << 20)
        self._playbin.set_property('buffer-duration', 10 * Gst.SECOND)
        ReplayGainPlayer.__init__(self, self._playbin)
        self._playbin.connect('about-to-finish',
                              self._on_stream_about_to_finish)
        bus = self._playbin.get_bus()
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
        ok, state, pending = self._playbin.get_state(0)
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
        ok, state, pending = self._playbin.get_state(0)
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
        self._stop()
        if self._load_track(track):
            self.play()

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
        self._stop()
        self.emit("status-changed")

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
            @return position as int
        """
        position = self._playbin.query_position(Gst.Format.TIME)[1] / 1000
        return position * 60

    def get_volume(self):
        """
            Return player volume rate
            @return rate as double
        """
        return self._playbin.get_volume(GstAudio.StreamVolumeFormat.LINEAR)

    def set_volume(self, rate):
        """
            Set player volume rate
            @param rate as double
        """
        self._playbin.set_volume(GstAudio.StreamVolumeFormat.LINEAR, rate)
        self.emit('volume-changed')

    def next(self):
        """
            Go next track
        """
        pass

#######################
# PRIVATE             #
#######################
    def _stop(self):
        """
            Stop current track (for track change)
        """
        self._playbin.set_state(Gst.State.NULL)

    def _load_track(self, track, sql=None):
        """
            Load track
            @param track as Track
            @param sql as sqlite cursor
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
        if self._codecs.is_missing_codec(message):
            self._codecs.install()
            Lp.scanner.stop()
        elif Lp.notify is not None:
            Lp.notify.send(_("File doesn't exist: %s") %
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
        else:
            self.next()

    def _on_stream_about_to_finish(self, playbin):
        """
            When stream is about to finish, switch to next track without gap
            @param playbin as Gst bin
        """
        if self.current_track.id == Type.RADIOS:
            return
        finished = self.current_track
        finished_start_time = self._start_time
        if self.next_track.id is not None:
            self._load_track(self.next_track)
        # Increment popularity
        if not Lp.scanner.is_locked():
            Lp.tracks.set_more_popular(finished.id)
            Lp.albums.set_more_popular(finished.album_id)
        # Scrobble on lastfm
        if Lp.lastfm is not None:
            if finished.album_artist_id == Type.COMPILATIONS:
                artist = finished.artist
            else:
                artist = finished.album_artist
            if time() - finished_start_time > 30:
                Lp.lastfm.scrobble(artist,
                                   finished.album_name,
                                   finished.title,
                                   int(finished_start_time),
                                   int(finished.duration))

    def _on_stream_start(self, bus, message):
        """
            On stream start
            Emit "current-changed" to notify others components
            @param bus as Gst.Bus
            @param message as Gst.Message
        """
        self._start_time = time()
        debug("Player::_on_stream_start(): %s" % self.current_track.uri)
        self.emit('current-changed')
        # Update now playing on lastfm
        if Lp.lastfm is not None and self.current_track.id >= 0:
            if self.current_track.album_artist_id == Type.COMPILATIONS:
                artist = self.current_track.artist
            else:
                artist = self.current_track.album_artist
                Lp.lastfm.now_playing(artist,
                                      self.current_track.album_name,
                                      self.current_track.title,
                                      int(self.current_track.duration))
        if not Lp.scanner.is_locked():
            Lp.tracks.set_listened_at(self.current_track.id, int(time()))
        self._handled_error = None
