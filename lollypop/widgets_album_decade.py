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

from lollypop.helper_task import TaskHelper
from lollypop.define import App, ArtSize
from lollypop.objects import Album


class AlbumDecadeWidget(Gtk.FlowBoxChild):
    """
        Decade widget showing cover for 5 albums
    """

    __ALBUMS_COUNT = 9

    def __init__(self, decade):
        """
            Init widget
            @param decade as [int]
        """
        # We do not use Gtk.Builder for speed reasons
        Gtk.FlowBoxChild.__init__(self)
        self.__decade = decade
        self.__cover_size = App().settings.get_value("cover-size").get_int32()
        self.set_size_request(ArtSize.YEAR, ArtSize.YEAR)

    def populate(self):
        """
            Populate widget content
        """
        self.__widget = Gtk.EventBox()
        self.__widget.connect("button-press-event",
                              self.__on_eventbox_button_press_event)
        self.__widget.connect("realize", self.__on_eventbox_realize)
        grid = Gtk.Grid()
        grid.set_orientation(Gtk.Orientation.VERTICAL)
        decade_label = Gtk.Label()
        decade_label.set_ellipsize(Pango.EllipsizeMode.END)
        decade_label.set_property("halign", Gtk.Align.CENTER)
        decade_str = "%s - %s" % (self.__decade[0], self.__decade[-1])
        decade_label.set_markup("<b>" +
                                GLib.markup_escape_text(decade_str) +
                                "</b>")
        self.__widget.set_property("has-tooltip", True)
        self.__widget.add(grid)
        cover = Gtk.Image.new()
        task_helper = TaskHelper()
        task_helper.run(self.__get_surface,
                        callback=(cover.set_from_surface,))
        cover.set_size_request(ArtSize.YEAR, ArtSize.YEAR)
        cover.show()
        grid.add(cover)
        grid.add(decade_label)
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

#######################
# PRIVATE             #
#######################
    def __get_surface(self):
        """
            Draw covers
            @return cairo.Surface
        """
        cover = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                   ArtSize.YEAR,
                                   ArtSize.YEAR)
        ctx = cairo.Context(cover)
        width = ArtSize.YEAR - 4
        ctx.translate(2, 2)
        ctx.new_sub_path()
        radius = width / 2
        ctx.arc(width / 2, width / 2, radius, 0, 2 * pi)
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill_preserve()
        ctx.clip()
        ctx.scale(0.5, 0.5)
        album_ids = []
        for year in self.__decade:
            album_ids += App().albums.get_albums_for_year(year,
                                                          self.__ALBUMS_COUNT)
            l = len(album_ids)
            if l < self.__ALBUMS_COUNT:
                album_ids += App().albums.get_compilations_for_year(
                                                       year,
                                                       self.__ALBUMS_COUNT - l)
        x = 0
        while album_ids:
            album_id = album_ids.pop(0)
            surface = App().art.get_album_artwork(Album(album_id),
                                                  self.__cover_size,
                                                  self.get_scale_factor())
            if surface is not None:
                ctx.set_source_surface(surface, 0, 0)
                ctx.paint()
            if x < ArtSize.YEAR:
                x += self.__cover_size
                ctx.translate(self.__cover_size, 0)
            else:
                ctx.translate(-x, self.__cover_size)
                x = 0
        return cover

    def __on_eventbox_button_press_event(self, eventbox, event):
        """
            Select decade in list
        """
        App().window.container.list_two.select_ids(self.__decade)

    def __on_eventbox_realize(self, eventbox):
        """
            Change cursor over eventbox
            @param eventbox as Gdk.Eventbox
        """
        window = eventbox.get_window()
        if window is not None:
            window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))
