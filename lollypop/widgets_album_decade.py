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

from random import sample
import cairo
from math import pi

from lollypop.define import App, ArtSize
from lollypop.objects import Album


class AlbumDecadeWidget(Gtk.FlowBoxChild):
    """
        Decade widget showing cover for 5 albums
    """

    def __init__(self, decade):
        """
            Init widget
            @param decade as [int]
        """
        # We do not use Gtk.Builder for speed reasons
        Gtk.FlowBoxChild.__init__(self)
        self.__decade = decade
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
        self.__cover = Gtk.Image.new_from_surface(self.__get_surface())
        self.__cover.set_size_request(ArtSize.YEAR, ArtSize.YEAR)
        self.__cover.show()
        grid.add(self.__cover)
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

    def stop(self):
        pass

    def update_cover(self):
        pass

    def update_state(self):
        pass

    def update_playing_indicator(self):
        pass

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
            album_ids += App().albums.get_albums_for_year(year, 4)
        if len(album_ids) >= 4:
            album_ids = sample(album_ids, 4)
        while album_ids:
            album_id = album_ids.pop(0)
            surface = App().art.get_album_artwork(Album(album_id),
                                                  ArtSize.YEAR,
                                                  self.get_scale_factor())
            if surface is not None:
                ctx.set_source_surface(surface, 0, 0)
                ctx.paint()
            if len(album_ids) in [3, 1]:
                ctx.translate(ArtSize.YEAR, 0)
            elif len(album_ids) == 2:
                ctx.translate(-ArtSize.YEAR, ArtSize.YEAR)
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
