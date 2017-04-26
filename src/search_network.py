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

from gi.repository import GObject, Gio, GLib

from lollypop.search_spotify import SpotifySearch
from lollypop.search_itunes import ItunesSearch
from lollypop.utils import get_network_available
from lollypop.define import Lp


class NetworkSearch(SpotifySearch, ItunesSearch, GObject.GObject):
    """
        Search provider over network
    """
    __gsignals__ = {
        "item-found": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        """
            Init provider
        """
        GObject.GObject.__init__(self)
        SpotifySearch.__init__(self)
        ItunesSearch.__init__(self)
        self._cancel = Gio.Cancellable.new()
        self._items = []
        self._finished = False

    @property
    def finished(self):
        """
            True if search finished
        """
        return self._finished

    @property
    def items(self):
        """
            Get items
            @return items as [SearchItems]
        """
        return self._items

    def stop(self):
        self._cancel.cancel()

    def do_tracks(self, name):
        """
            Populate items with tracks containing name
            @param name as str
            @return tracks/albums as [SearchItem]
        """
        if get_network_available():
            if Lp().settings.get_value("search-itunes"):
                ItunesSearch.tracks(self, name)
            if Lp().settings.get_value("search-spotify"):
                SpotifySearch.tracks(self, name)
        self._finished = True
        GLib.idle_add(self.emit, "item-found")

    def do(self, name):
        """
            Populate items with albums/tracks containing name
            @param name as str
            @return tracks/albums as [SearchItem]
        """
        if get_network_available():
            if Lp().settings.get_value("search-itunes"):
                ItunesSearch.albums(self, name)
                ItunesSearch.tracks(self, name)
            if Lp().settings.get_value("search-spotify"):
                SpotifySearch.albums(self, name)
                SpotifySearch.tracks(self, name)
        self._finished = True
        GLib.idle_add(self.emit, "item-found")
