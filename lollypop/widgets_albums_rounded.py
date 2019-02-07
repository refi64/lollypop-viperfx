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

from lollypop.define import App, ArtSize, Type, ViewType
from lollypop.objects import Album
from lollypop.utils import get_round_surface
from lollypop.widgets_flowbox_rounded import RoundedFlowBoxWidget


class RoundedAlbumsWidget(RoundedFlowBoxWidget):
    """
        Rounded widget showing cover for 4 albums
    """
    _ALBUMS_COUNT = 4

    def __init__(self, data, name, sortname, view_type):
        """
            Init widget
            @param data as object
            @param name as str
            @param sortname as str
            @param art_size as int
        """
        if view_type & ViewType.SMALL:
            art_size = ArtSize.LARGE
        else:
            art_size = ArtSize.BIG
        RoundedFlowBoxWidget.__init__(self, data, name, sortname, art_size)
        self._genre = Type.NONE
        self._album_ids = []
        self.__cover_size = art_size / 2
        self._pixel_size = art_size / 8
        self.__cancellable = Gio.Cancellable()
        self._scale_factor = self.get_scale_factor()
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
        App().task_helper.run(self.__load_surface)

    def _create_surface(self):
        """
            Get artwork surface
            @return cairo.Surface
        """
        surface = cairo.ImageSurface(cairo.FORMAT_RGB24,
                                     self._art_size,
                                     self._art_size)
        ctx = cairo.Context(surface)
        ctx.rectangle(0, 0, self._art_size, self._art_size)
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill()
        shuffle(self._album_ids)
        positions = [(0, 0), (1, 0), (0, 1), (1, 1)]
        self.__draw_surface(surface, ctx, positions)

    def _save_surface(self, surface):
        """
            Save surface to cache
            @param surface as cairo.Surface
        """
        pixbuf = Gdk.pixbuf_get_from_surface(surface,
                                             0, 0,
                                             surface.get_width(),
                                             surface.get_height())
        string = "%s_%s" % (self._genre, self._data)
        App().task_helper.run(App().art.save_pixbuf,
                              pixbuf,
                              string)

#######################
# PRIVATE             #
#######################
    def __load_surface(self):
        """
            Load surface from art cache
        """
        string = "%s_%s" % (self._genre, self._data)
        pixbuf = App().art.load_pixbuf(string)
        if pixbuf is None:
            self._create_surface()
        else:
            GLib.idle_add(self.__set_pixbuf, pixbuf)

    def __set_pixbuf(self, pixbuf):
        """
            Set artwork from pixbuf
            @param pixbuf as Gdk.Pixbuf
        """
        surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf,
                                                       self._scale_factor,
                                                       None)
        self.__set_surface(surface)

    def __set_surface(self, surface):
        """
            Set artwork from surface
            @param surface as cairo.Surface
        """
        if self.__cancellable.is_cancelled():
            return
        self._artwork.set_from_surface(
            get_round_surface(surface, self._scale_factor, 60))
        self.emit("populated")

    def __draw_surface(self, surface, ctx, positions):
        """
            Draw surface for first available album
            @param surface as cairo.Surface
            @param ctx as Cairo.context
            @param positions as {}
            @thread safe
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
            self.__draw_surface(surface, ctx, positions)
        if self.__cancellable.is_cancelled():
            return
        elif self._album_ids and len(positions) > 0:
            album_id = self._album_ids.pop(0)
            pixbuf = App().art.get_album_artwork(Album(album_id),
                                                 self.__cover_size,
                                                 self.__cover_size,
                                                 self._scale_factor)
            if pixbuf is None:
                GLib.idle_add(self.__draw_surface, surface, ctx, positions)
            else:
                GLib.idle_add(draw_pixbuf, surface, ctx, pixbuf, positions)
        else:
            GLib.idle_add(self.__set_surface, surface)
            GLib.idle_add(self._save_surface, surface)

    def __on_unmap(self, widget):
        """
            Cancel drawing
            @param widget as Gtk.Widget
        """
        self.__cancellable.cancel()
