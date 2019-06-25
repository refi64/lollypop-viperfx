# Copyright (c) 2014-2019 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from lollypop.define import App
from lollypop.widgets_utils import Popover


class CommonPopover(Popover):
    """
        Resized popover
    """

    def __init__(self):
        """
            Connect map signal
        """
        Popover.__init__(self)
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
        size = App().window.get_size()
        self.set_size_request(size[0] * 0.6,
                              size[1] * 0.6)

    def __on_unmap(self, widget):
        """
            Stop loading
            @param widget as Gtk.Widget
        """
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
        from lollypop.widgets_artwork_album import AlbumArtworkSearchWidget
        CommonPopover.__init__(self)
        if not album.artist_ids:
            self._widget = None
            return
        self._widget = AlbumArtworkSearchWidget(album)
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
        from lollypop.widgets_artwork_artist import ArtistArtworkSearchWidget
        CommonPopover.__init__(self)
        self._widget = ArtistArtworkSearchWidget(artist_id)
        self._widget.show()
        self.add(self._widget)
        self._widget.populate()
