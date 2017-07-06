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

from gi.repository import Gtk

from lollypop.art_widgets import ArtworkSearch
from lollypop.define import Lp


class CommonPopover(Gtk.Popover):
    """
        Resized popover
    """

    def __init__(self):
        """
            Connect map signal
        """
        Gtk.Popover.__init__(self)
        self.connect("map", self.__on_map)
        self.connect("unmap", self.__on_unmap)

#######################
# PRIVATE             #
#######################
    def __on_map(self, widget):
        """
            Resize
            @param widget as Gtk.Widget
        """
        # FIXME Not needed with GTK >= 3.18
        Lp().window.enable_global_shortcuts(False)
        size = Lp().window.get_size()
        self.set_size_request(size[0]*0.4,
                              size[1]*0.5)

    def __on_unmap(self, widget):
        """
            Stop loading
            @param widget as Gtk.Widget
        """
        # FIXME Not needed with GTK >= 3.18
        Lp().window.enable_global_shortcuts(True)
        if self._widget is not None:
            self._widget.stop()


class CoversPopover(CommonPopover):
    """
        Popover with album covers from the web
    """

    def __init__(self, album):
        """
            Init Popover
            @param album as album
        """
        CommonPopover.__init__(self)
        if not album.artist_ids:
            self._widget = None
            return
        # FIXME We only search with first artist
        self._widget = ArtworkSearch(album.artist_ids[0],
                                     album)
        self._widget.show()
        self.add(self._widget)
        self._widget.populate()


class ArtworkPopover(CommonPopover):
    """
        Popover with artist-artwork from the web
    """

    def __init__(self, artist_id):
        """
            Init Popover
            @param album as album
        """
        CommonPopover.__init__(self)
        self._widget = ArtworkSearch(artist_id, None)
        self._widget.show()
        self.add(self._widget)
        self._widget.populate()
