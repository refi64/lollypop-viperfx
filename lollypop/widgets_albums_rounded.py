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

from gi.repository import GLib, Gdk, Gtk, Pango

import cairo
from math import pi
from random import sample

from lollypop.helper_task import TaskHelper
from lollypop.define import App, ArtSize
from lollypop.objects import Album


class RoundedAlbumsWidget(Gtk.FlowBoxChild):
    """
        Rounded widget showing cover for 9 albums
    """

    _ALBUMS_COUNT = 9

    def __init__(self, item_ids):
        """
            Init widget
            @param item_ids as [int]
        """
        # We do not use Gtk.Builder for speed reasons
        Gtk.FlowBoxChild.__init__(self)
        self._item_ids = item_ids
        self.__cover_size = App().settings.get_value("cover-size").get_int32()
        self.set_size_request(ArtSize.ROUNDED, ArtSize.ROUNDED)

    def populate(self, text):
        """
            Populate widget content
            @param text as str
        """
        self.__widget = Gtk.EventBox()
        self.__widget.connect("button-press-event",
                              self.__on_eventbox_button_press_event)
        self.__widget.connect("realize", self.__on_eventbox_realize)
        grid = Gtk.Grid()
        grid.set_orientation(Gtk.Orientation.VERTICAL)
        label = Gtk.Label()
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_property("halign", Gtk.Align.CENTER)
        label.set_markup("<b>" + GLib.markup_escape_text(text) + "</b>")
        self.__widget.set_property("has-tooltip", True)
        self.__widget.add(grid)
        cover = Gtk.Image.new()
        task_helper = TaskHelper()
        task_helper.run(self.__get_surface,
                        callback=(cover.set_from_surface,))
        cover.set_size_request(ArtSize.ROUNDED, ArtSize.ROUNDED)
        cover.show()
        grid.add(cover)
        grid.add(label)
        self.add(self.__widget)
        self.__widget.set_property("halign", Gtk.Align.CENTER)
        self.__widget.set_property("valign", Gtk.Align.CENTER)
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

#######################
# PRIVATE             #
#######################
    def __get_surface(self):
        """
            Draw covers
            @return cairo.Surface
        """
        cover = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                   ArtSize.ROUNDED,
                                   ArtSize.ROUNDED)
        ctx = cairo.Context(cover)
        width = ArtSize.ROUNDED - 4
        ctx.translate(2, 2)
        ctx.new_sub_path()
        radius = width / 2
        ctx.arc(width / 2, width / 2, radius, 0, 2 * pi)
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill_preserve()
        ctx.clip()
        ctx.scale(0.5, 0.5)
        album_ids = self._get_album_ids()
        x = 0
        album_ids = sample(album_ids, self._ALBUMS_COUNT)
        while album_ids:
            album_id = album_ids.pop(0)
            surface = App().art.get_album_artwork(Album(album_id),
                                                  self.__cover_size,
                                                  self.get_scale_factor())
            if surface is not None:
                ctx.set_source_surface(surface, 0, 0)
                ctx.paint()
            if x < ArtSize.ROUNDED:
                x += self.__cover_size
                ctx.translate(self.__cover_size, 0)
            else:
                ctx.translate(-x, self.__cover_size)
                x = 0
        return cover

    def __on_eventbox_button_press_event(self, eventbox, event):
        """
            Select items in list
        """
        App().window.container.list_two.select_ids(self._item_ids)

    def __on_eventbox_realize(self, eventbox):
        """
            Change cursor over eventbox
            @param eventbox as Gdk.Eventbox
        """
        window = eventbox.get_window()
        if window is not None:
            window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))
