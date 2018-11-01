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

from gi.repository import GLib, Gtk, Gdk, Pango, GObject

import cairo
from random import shuffle

from lollypop.helper_task import TaskHelper
from lollypop.define import App, ArtSize
from lollypop.utils import draw_rounded_image
from lollypop.objects import Album


class RoundedFlowBoxWidget(Gtk.FlowBoxChild):
    """
        Rounded widget showing cover for 9 albums
    """

    _ALBUMS_COUNT = 9
    __gsignals__ = {
        "populated": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "overlayed": (GObject.SignalFlags.RUN_FIRST, None, (bool,))
    }

    def __init__(self, data, art_size=ArtSize.ROUNDED):
        """
            Init widget
            @param data as object
        """
        # We do not use Gtk.Builder for speed reasons
        Gtk.FlowBoxChild.__init__(self)
        self._art_size = art_size
        self.__covers_count = 0
        self._data = data
        self.__cover_size = App().settings.get_value("cover-size").get_int32()
        self.__scale = art_size / self.__cover_size / 3
        self.set_size_request(art_size, art_size)

    def populate(self, text):
        """
            Populate widget content
            @param text as str
        """
        self._widget = Gtk.EventBox()
        self._widget.connect("button-press-event",
                             self._on_eventbox_button_press_event)
        grid = Gtk.Grid()
        grid.set_orientation(Gtk.Orientation.VERTICAL)
        label = Gtk.Label()
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_property("halign", Gtk.Align.CENTER)
        label.set_markup("<b>" + GLib.markup_escape_text(text) + "</b>")
        self._widget.set_property("has-tooltip", True)
        self._widget.add(grid)
        self._artwork = Gtk.Image.new()
        self._artwork.connect("draw", self.__on_artwork_draw)
        self.__set_artwork()
        self._overlay = Gtk.Overlay()
        self._overlay.add(self._artwork)
        self._artwork.set_size_request(self._art_size, self._art_size)
        self._artwork.show()
        grid.add(self._overlay)
        grid.add(label)
        self.add(self._widget)
        self._widget.set_property("halign", Gtk.Align.CENTER)
        self._widget.set_property("valign", Gtk.Align.CENTER)
        self.show_all()

    def do_get_preferred_width(self):
        """
            Return preferred width
            @return (int, int)
        """
        width = Gtk.FlowBoxChild.do_get_preferred_width(self)[0]
        return (width, width)

    @property
    def data(self):
        """
            Get associated data
            @return object
        """
        return self._data

    @property
    def is_populated(self):
        """
            True if album populated
        """
        return True

#######################
# PROTECTED           #
#######################
    def _get_album_ids(self):
        """
            Get ids for widget
            @return [int]
        """
        return []

    def _set_surface(self, surface):
        """
            Set artwork from surface
            @param surface as cairo.Surface
        """
        self._artwork.set_from_surface(surface)

    def _get_surface(self):
        """
            Get artwork surface
            @return cairo.Surface
        """
        cover = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                   self._art_size,
                                   self._art_size)
        ctx = cairo.Context(cover)
        ctx.scale(self.__scale, self.__scale)
        album_ids = self._get_album_ids()
        shuffle(album_ids)
        x = self.__cover_size
        y = self.__cover_size
        # Draw centered cover
        self.__draw_surface(album_ids, ctx, x, y)
        # Draw other covers
        for i in [0, 1, 2]:
            for h in [0, 1, 2]:
                # Ignore centered
                if i == 1 and h == 1:
                    continue
                self.__draw_surface(album_ids, ctx, x * i, y * h)
        GLib.idle_add(self.emit, "populated")
        return cover

    def _on_eventbox_button_press_event(self, eventbox, event):
        """
            @param eventbox as Gtk.EventBox
            @param event as Gdk.Event
        """
        pass

#######################
# PRIVATE             #
#######################
    def __set_artwork(self):
        """
            Set artwork
        """
        self._scale_factor = self.get_scale_factor()
        task_helper = TaskHelper()
        task_helper.run(self._get_surface,
                        callback=(self._set_surface,))

    def __draw_surface(self, album_ids, ctx, x, y):
        """
            Draw surface for first available album
            @param album_ids as [int]
            @param ctx as Cairo.context
            @param x as int
            @param y as int
        """
        # Workaround Gdk not being thread safe
        def draw_pixbuf(ctx, pixbuf):
            surface = Gdk.cairo_surface_create_from_pixbuf(
                pixbuf, self._scale_factor, None)
            ctx.translate(x, y)
            ctx.set_source_surface(surface, 0, 0)
            ctx.paint()
            ctx.translate(-x, -y)
        if album_ids:
            album_id = album_ids.pop(0)
            pixbuf = App().art.get_album_artwork_pixbuf(
                                                  Album(album_id),
                                                  self.__cover_size,
                                                  self._scale_factor)
            if pixbuf is None:
                GLib.idle_add(self.__draw_surface, album_ids, ctx, x, y)
            else:
                self.__covers_count += 1
                GLib.idle_add(draw_pixbuf, ctx, pixbuf)

    def __on_artwork_draw(self, image, ctx):
        """
            Draw rounded image
            @param image as Gtk.Image
            @param ctx as cairo.Context
        """
        if image.props.surface is None:
            return
        # Update image if scale factor changed
        if self._scale_factor != image.get_scale_factor():
            self._scale_factor = image.get_scale_factor()
            self.__set_artwork()
        draw_rounded_image(image, ctx)
        return True
