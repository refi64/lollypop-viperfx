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

from gi.repository import TotemPlParser, Gio, Gst

from lollypop.radios import Radios
from lollypop.player_base import BasePlayer
from lollypop.define import Type
from lollypop.objects import Track


class RadioPlayer(BasePlayer):
    """
        Radio player
        This class neeed the parent object to be a BinPlayer
        We keep a version of available radios (set_radios()) because we
        need to be in sync with current/last view and not with db (popularity
        changes)
    """

    def __init__(self):
        """
            Init radio player
        """
        BasePlayer.__init__(self)
        self._current = None
        self._radios = []

    def load(self, track):
        """
            Load radio at uri
            @param track as Track
        """
        if Gio.NetworkMonitor.get_default().get_network_available():
            try:
                self._current = track
                parser = TotemPlParser.Parser.new()
                parser.connect("entry-parsed", self._on_entry_parsed, track)
                parser.parse_async(track.uri, True,
                                   None, self._on_parse_finished, track)
            except Exception as e:
                print("RadioPlayer::load(): ", e)
            if self.is_party():
                self.set_party(False)
            self.next_track = Track()
            self.emit('next-changed')

    def next(self):
        """
            Return next radio name, uri
            @return Track
        """
        track = Track()
        if self.current_track.id != Type.RADIOS:
            return track

        i = 0
        for (name, url) in self._radios:
            i += 1
            if self.current_track.album_artists == name:
                break

        # Get next radio
        if i >= len(self._radios):
            i = 0

        name = self._radios[i][0]
        url = self._radios[i][1]
        if url:
            track.set_radio(name, url)
        return track

    def prev(self):
        """
            Return prev radio name, uri
            @return Track
        """
        track = Track()
        if self.current_track.id != Type.RADIOS:
            return track

        i = len(self._radios) - 1
        for (name, url) in reversed(self._radios):
            i -= 1
            if self.current_track.album_artists == name:
                break

        # Get prev radio
        if i < 0:
            i = len(self._radios) - 1

        name = self._radios[i][0]
        url = self._radios[i][1]
        if url:
            track.set_radio(name, url)
        return track

    def set_radios(self, radios):
        """
            Set available radios
            @param radios as (name, url)
        """
        self._radios = radios

#######################
# PRIVATE             #
#######################
    def _start_playback(self, track):
        """
            Start playing track
            @param track as Track:
        """
        self._plugins.volume.props.volume = 1.0
        self._playbin.set_state(Gst.State.NULL)
        self._playbin.set_property('uri', track.uri)
        Radios().set_more_popular(track.album_artist)
        self.current_track = track
        self._current = None
        self._playbin.set_state(Gst.State.PLAYING)

    def _on_parse_finished(self, parser, result, track):
        """
            Sometimes, TotemPlparse fails to add
            the playlist URI to the end of the playlist on parse failure
            So, do the job here
            @param parser as TotemPlParser.Parser
            @param result as Gio.AsyncResult
            @param track as Track
        """
        # Only start playing if context always True
        if self._current == track:
            self._start_playback(track)

    def _on_entry_parsed(self, parser, uri, metadata, track):
        """
            Play stream
            @param parser as TotemPlParser.Parser
            @param track uri as str
            @param metadata as GLib.HastTable
            @param track as Track
        """
        # Only start playing if context always True
        if self._current == track:
            track.set_radio(track.album_artists, uri)
            self._start_playback(track)
