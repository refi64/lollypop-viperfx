# Copyright (c) 2014-2018 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import Gdk, Gtk, GLib, Gio, GdkPixbuf

from gettext import gettext as _
from random import shuffle

from lollypop.define import App, STATIC_ALBUM_NAME
from lollypop.utils import get_icon_name
from lollypop.objects import Album
from lollypop.information_store import InformationStore
from lollypop.widgets_flowbox_rounded import RoundedFlowBoxWidget


class RoundedArtistWidget(RoundedFlowBoxWidget):
    """
        Artist photo or artist's albums in a rounded widget
    """

    def __init__(self, artist_id, art_size):
        """
            Init widget
            @param artist_id as int
            @param art_size as int
        """
        self.__artist_name = ""
        RoundedFlowBoxWidget.__init__(self, artist_id, art_size)
        self.connect("realize", self.__on_realize)

    def populate(self):
        """
            Populate widget content
        """
        if self._data < 0:
            self.__artist_name = _(STATIC_ALBUM_NAME[self._data])
        else:
            self.__artist_name = App().artists.get_name(self._data)
        RoundedFlowBoxWidget.populate(self, self.__artist_name)

    def show_overlay(self, show):
        """
            Show overlay
            @param show as bool
        """
        pass

    @property
    def is_overlay(self):
        """
            True if widget is overlayed
            @return bool
        """
        return False

    @property
    def filter(self):
        return "%s - %s" % (self._data[0], self._data[-1])

#######################
# PROTECTED           #
#######################
    def _get_album_ids(self):
        """
            Get ids for widget
            @return [int]
        """
        App().albums.get_ids([], [self._data])

    def _set_surface(self, pixbuf):
        """
            Set artwork from pixbuf
            @param pixbuf as GdkPixbuf.Pixbuf
        """
        if pixbuf is None:
            icon = get_icon_name(self._data) or "avatar-default-symbolic"
            surface = Gtk.IconTheme.get_default().load_surface(
                                             icon,
                                             self._art_size,
                                             self._scale_factor,
                                             None,
                                             Gtk.IconLookupFlags.USE_BUILTIN)
        else:
            surface = Gdk.cairo_surface_create_from_pixbuf(
                                                    pixbuf,
                                                    self.get_scale_factor(),
                                                    None)
        RoundedFlowBoxWidget._set_surface(self, surface)
        self.emit("populated")

    def _get_surface(self):
        """
            Get surface for artist
            @return GdkPixbuf.Pixbuf
        """
        if self._data < 0:
            return None
        pixbuf = None
        if App().settings.get_value("artist-artwork"):
            path = InformationStore.get_artwork_path(
                                            self.__artist_name, self._art_size)
            if path is not None:
                f = Gio.File.new_for_path(path)
                (status, data, tag) = f.load_contents(None)
                if status:
                    bytes = GLib.Bytes(data)
                    stream = Gio.MemoryInputStream.new_from_bytes(bytes)
                    pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(
                        stream,
                        self._art_size,
                        self._art_size,
                        True,
                        None)
                    stream.close()
        else:
            album_ids = App().albums.get_ids([self._data], [])
            shuffle(album_ids)
            pixbuf = App().art.get_album_artwork_pixbuf(Album(album_ids[0]),
                                                        self._art_size,
                                                        self._scale_factor)
        return pixbuf

#######################
# PRIVATE             #
#######################
    def __on_realize(self, widget):
        """
            Change cursor over eventbox
            @param widget as Gtk.Widget
        """
        window = widget.get_window()
        if window is not None:
            window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))
