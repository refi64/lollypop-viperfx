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

from gi.repository import GObject, Gio

from lollypop.search_spotify import SpotifySearch


class NetworkSearch(SpotifySearch, GObject.GObject):
    """
        Search provider over network
    """
    __gsignals__ = {
        'item-found': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        """
            Init provider
        """
        GObject.GObject.__init__(self)
        SpotifySearch.__init__(self)
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

    def do(self, name):
        """
            Return tracks containing name
            @param name as str
            @return tracks as [SearchItem]
        """
        SpotifySearch.albums(self, name)
        SpotifySearch.tracks(self, name)
        self._finished = True
        self.emit('item-found')
