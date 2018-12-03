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

from gi.repository import GLib, Gdk, Gio

import cairo
from random import shuffle

from lollypop.define import App, ArtSize
from lollypop.objects import Album
from lollypop.utils import get_round_surface
from lollypop.widgets_flowbox_rounded import RoundedFlowBoxWidget


class RoundedAlbumsWidget(RoundedFlowBoxWidget):
    """
        Rounded widget showing cover for 9 albums
    """
    _ALBUMS_COUNT = 9

    def __init__(self, data, name, sortname, art_size=ArtSize.ROUNDED):
        """
            Init widget
            @param data as object
            @param name as str
            @param sortname as str
            @param art_size as int
        """
        RoundedFlowBoxWidget.__init__(self, data, name, sortname, art_size)
        self.__cover_size = art_size / 3
        self.__cancellable = Gio.Cancellable()
        self.connect("unmap", self.__on_unmap)

    def populate(self):
        """
            Populate widget content
        """
        RoundedFlowBoxWidget.populate(self)
        self._artwork.get_style_context().add_class("light-background")

#######################
# PROTECTED           #
#######################
    def _set_artwork(self):
        """
            Set artwork
        """
        self._scale_factor = self.get_scale_factor()
        App().task_helper.run(self._create_surface)

    def _set_surface(self, surface):
        """
            Set artwork from surface
            @param surface as cairo.Surface
        """
        if self.__cancellable.is_cancelled():
            return
        self._artwork.set_from_surface(
            get_round_surface(surface, self._scale_factor))
        self.emit("populated")

    def _create_surface(self):
        """
            Get artwork surface
            @return cairo.Surface
        """
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                     self._art_size,
                                     self._art_size)
        ctx = cairo.Context(surface)
        album_ids = self._get_album_ids()
        shuffle(album_ids)
        positions = [(1, 1), (0, 0), (0, 1), (0, 2),
                     (1, 0), (1, 2), (2, 0), (2, 1), (2, 2)]
        self.__draw_surface(album_ids, surface, ctx, positions)

#######################
# PRIVATE             #
#######################
    def __draw_surface(self, album_ids, surface, ctx, positions):
        """
            Draw surface for first available album
            @param album_ids as [int]
            @param surface as cairo.Surface
            @param ctx as Cairo.context
            @param positions as {}
        """
        # Workaround Gdk not being thread safe
        def draw_pixbuf(surface, ctx, pixbuf, positions):
            if self.__cancellable.is_cancelled():
                return
            (x, y) = positions.pop(0)
            x *= self.__cover_size
            y *= self.__cover_size
            subsurface = Gdk.cairo_surface_create_from_pixbuf(
                pixbuf, self._scale_factor, None)
            ctx.translate(x, y)
            ctx.set_source_surface(subsurface, 0, 0)
            ctx.paint()
            ctx.translate(-x, -y)
            self.__draw_surface(album_ids, surface, ctx, positions)
        if self.__cancellable.is_cancelled():
            return
        elif album_ids and len(positions) > 0:
            album_id = album_ids.pop(0)
            pixbuf = App().art.get_album_artwork(Album(album_id),
                                                 self.__cover_size,
                                                 self.__cover_size,
                                                 self._scale_factor)
            if pixbuf is None:
                GLib.idle_add(self.__draw_surface, album_ids,
                              surface, ctx, positions)
            else:
                GLib.idle_add(draw_pixbuf, surface, ctx, pixbuf, positions)
        else:
            GLib.idle_add(self._set_surface, surface)

    def __on_unmap(self, widget):
        """
            Cancel drawing
            @param widget as Gtk.Widget
        """
        self.__cancellable.cancel()
