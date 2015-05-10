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

from gi.repository import TotemPlParser

from gettext import gettext as _

from lollypop.playlists import RadiosManager
from lollypop.player_base import BasePlayer
from lollypop.define import Navigation

# This class neeed the parent object to be a BinPlayer
class RadioPlayer(BasePlayer):
    """
        Init radio player
    """
    def __init__(self):
        BasePlayer.__init__(self)
        self._radio_name = None
        self._radio_uri = None
        self._bus.connect("message::tag", self._on_bus_message_tag)

    """
        Load radio at uri
        @param name as string
        @param uri as string
    """
    def load(self, name, uri):
        self.current.id = Navigation.RADIOS
        self._radio_name = name
        self._radio_uri = uri
        try:
            parser = TotemPlParser.Parser.new()
            parser.parse_async(uri, False, None, self._on_entry_parsed, name)
        except Exception as e:
            print("RadioPlayer::load(): ", e)
            return False
        self.set_party(False)
        self._albums = []
        return True

    """
        Return next radio name, uri
        @return (name, uri)
    """
    def next(self):
        radios_manager = RadiosManager()
        radios = radios_manager.get()
        i = 0
        for (radio_id, name) in radios:
            if name == self._radio_name:
                break
            i += 1
        # Get next radio
        if i + 1 >= len(radios):
            i = 0
        else:
            i += 1
        name = radios[i][1]
        uris = radios_manager.get_tracks(name)
        if len(uris) > 0:
            return (name, uris[0])
        else:
            return (None, None)

    """
        Return prev radio name, uri
        @return (name, uri)
    """
    def prev(self):
        radios_manager = RadiosManager()
        radios = radios_manager.get()
        i = 0
        for (radio_id, name) in radios:
            if name == self._radio_name:
                break
            i += 1
        # Get prev radio
        if i - 1 <= 0:
            i = len(radios) - 1
        else:
            i -= 1
        name = radios[i][1]
        uris = radios_manager.get_tracks(name)
        if len(uris) > 0:
            return (name, uris[0])
        else:
            return (None, None)

#######################
# PRIVATE             #
#######################
    """
        Set current state on radio
    """
    def _set_current(self):
        string = _("Radio")
        if self._radio_name is not None:
            self.current.artist = self._radio_name
        if self._radio_uri is not None:
            self.current.path = self._radio_uri
        self.current.title = string
        self.current.album_id = None
        self.current.album = string
        self.current.aartist_id = None
        self.current.aartist = string
        self.current.genre = string
        self.current.duration = 0.0
        self.current.number = 0

    """
        Read title from stream
        @param bus as Gst.Bus
        @param message as Gst.Message
    """
    def _on_bus_message_tag(self, bus, message):
        if self.current.id != Navigation.RADIOS:
            return
        tags = message.parse_tag()
        (exist, title) = tags.get_string_index('title', 0)
        if exist and title != self.current.title:
            self.current.title = title
            self.emit('current-changed')

    """
        Play stream
        @param parser as TotemPlParser.Parser
        @param result as Gio.AsyncResult
        @param radio name as string
    """
    def _on_entry_parsed(self, parser, result, name):
        # Only start playing if context always True
        if self._radio_name == name:
            self._stop()
            self._playbin.set_property('uri', self._radio_uri)
            self._set_current()
            self.play()
