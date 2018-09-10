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

from gi.repository import GLib, Gtk, Pango, GObject

import cairo
from math import pi
from random import sample

from lollypop.helper_task import TaskHelper
from lollypop.define import App, ArtSize
from lollypop.objects import Album


class RoundedFlowBoxWidget(Gtk.FlowBoxChild):
    """
        Rounded widget showing cover for 9 albums
    """

    _ALBUMS_COUNT = 9
    __gsignals__ = {
        "overlayed": (GObject.SignalFlags.RUN_FIRST, None, (bool,))
    }

    def __init__(self, item_ids):
        """
            Init widget
            @param data as [int]
        """
        # We do not use Gtk.Builder for speed reasons
        Gtk.FlowBoxChild.__init__(self)
        self._data = item_ids
        self.__cover_size = App().settings.get_value("cover-size").get_int32()
        self.set_size_request(ArtSize.ROUNDED, ArtSize.ROUNDED)

    def populate(self, text):
        """
            Populate widget content
            @param text as str
        """
        self._widget = Gtk.EventBox()
        self._widget.connect("button-press-event",
                             self._on_eventbox_button_press_event)
        self._widget.connect("realize", self._on_eventbox_realize)
        grid = Gtk.Grid()
        grid.set_orientation(Gtk.Orientation.VERTICAL)
        label = Gtk.Label()
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_property("halign", Gtk.Align.CENTER)
        label.set_markup("<b>" + GLib.markup_escape_text(text) + "</b>")
        self._widget.set_property("has-tooltip", True)
        self._widget.add(grid)
        cover = Gtk.Image.new()
        self._overlay = Gtk.Overlay()
        self._overlay.add(cover)
        task_helper = TaskHelper()
        task_helper.run(self.__get_surface,
                        callback=(cover.set_from_surface,))
        cover.set_size_request(ArtSize.ROUNDED, ArtSize.ROUNDED)
        cover.show()
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

#######################
# PROTECTED           #
#######################
    def _get_album_ids(self):
        """
            Get ids for widget
            @return [int]
        """
        return []

    def _on_eventbox_button_press_event(self, eventbox, event):
        """
            @param eventbox as Gtk.EventBox
            @param event as Gdk.Event
        """
        pass

    def _on_eventbox_realize(self, eventbox):
        """
            @param eventbox as Gtk.Eventbox
        """
        pass

#######################
# PRIVATE             #
#######################
    def __draw_surface(self, album_ids, ctx):
        """
            Draw surface for first available album
            @param album_ids as [int]
            @param ctx as Cairo.context
        """
        if album_ids:
            album_id = album_ids.pop(0)
            surface = App().art.get_album_artwork(Album(album_id),
                                                  self.__cover_size,
                                                  self.get_scale_factor())
            if surface is not None:
                ctx.set_source_surface(surface, 0, 0)
                ctx.paint()

    def __get_surface(self):
        """
            Get artwork surface
            @return cairo.Surface
        """
        cover = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                   ArtSize.ROUNDED,
                                   ArtSize.ROUNDED)
        ctx = cairo.Context(cover)
        ctx.new_sub_path()
        radius = ArtSize.ROUNDED / 2
        ctx.arc(ArtSize.ROUNDED / 2, ArtSize.ROUNDED / 2, radius, 0, 2 * pi)
        ctx.set_source_rgb(0, 0, 0)
        ctx.fill_preserve()
        ctx.scale(0.5, 0.5)
        ctx.clip()
        album_ids = self._get_album_ids()
        if len(album_ids) >= self._ALBUMS_COUNT:
            album_ids = sample(album_ids, self._ALBUMS_COUNT)
        x = self.__cover_size
        y = self.__cover_size
        max_value = self.__cover_size * 3
        ctx.translate(x, y)
        # Draw centered cover
        self.__draw_surface(album_ids, ctx)
        ctx.translate(-x, -y)
        # Draw other covers
        for i in [1, 2, 3]:
            for h in [1, 2, 3]:
                # Ignore centered
                if i == 2 and h == 2:
                    ctx.translate(0, y)
                    continue
                self.__draw_surface(album_ids, ctx)
                ctx.translate(0, y)
            ctx.translate(x, 0)
            ctx.translate(0, -max_value)
        return cover
