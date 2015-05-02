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

from lollypop.player_base import BasePlayer
from lollypop.define import Navigation

# This class neeed the parent object to be a BinPlayer
class RadioPlayer(BasePlayer):
    """
        Init radio player
    """
    def __init__(self):
        BasePlayer.__init__(self)
        self._name = None
        self._uri = None

    """
        Load radio at uri
        @param name as string
        @param uri as string
    """
    def load(self, name, uri):
        self._name = name
        self._uri = uri
        try:
            parser = TotemPlParser.Parser.new()
            if parser.can_parse_from_uri(uri, False):
                parser.connect("entry-parsed", self._on_entry_parsed)
                parser.parse(uri, False)
            else:
                self._playbin.set_property('uri', uri)
                self._set_current()
        except Exception as e:
            print("RadioPlayer::load(): ", e)
            return False
        return True

#######################
# PRIVATE             #
#######################
    """
        Set current state on radio
    """
    def _set_current(self):
        string = _("Radio")
        self.current.id = Navigation.RADIOS
        if self._name is not None:
            self.current.artist = self._name
        if self._uri is not None:
            self.current.path = self._uri
        self.current.title = string
        self.current.album_id = None
        self.current.album = string
        self.current.aartist_id = None
        self.current.aartist = string
        self.current.genre = string
        self.current.duration = 0.0
        self.current.number = 0
        if self._bus is not None and self._message_tag is None:
            self._message_tag =  self._bus.connect("message::tag",
                                                   self._on_bus_message_tag)

    """
        Play stream
        @param parser as TotemPlParser.Parser
        @param track uri as str
        @param metadata as GLib.HastTable
    """
    def _on_entry_parsed(self, parser, uri, metadata):
        self._playbin.set_property('uri', uri)
        self._set_current()
