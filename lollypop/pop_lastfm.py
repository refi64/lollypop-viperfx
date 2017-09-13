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

from gi.repository import Gtk, GLib, Pango

from lollypop.define import Lp
from lollypop.utils import get_network_available


class LastfmPopover(Gtk.Popover):
    """
        A lastfm popover with similar artists
    """

    def __init__(self):
        """
            Init popover
        """
        Gtk.Popover.__init__(self)
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/LastfmPopover.ui")
        self.connect("map", self.__on_map)
        self.__stack = builder.get_object("stack")
        self.__spinner = builder.get_object("spinner")
        self.__spinner.start()
        self.__view = Gtk.ListBox()
        self.__view.get_style_context().add_class("trackswidget")
        self.__view.set_vexpand(True)
        self.__view.set_selection_mode(Gtk.SelectionMode.NONE)
        self.__view.set_activate_on_single_click(True)
        self.__view.connect("row-activated", self.__on_row_activated)
        self.__view.show()
        self.__stack.add(self.__view)
        self.add(builder.get_object("widget"))

    def populate(self, artist_ids):
        """
            Populate view artist ids
            @param artist ids as int
        """
        if get_network_available():
            artists = []
            for artist_id in artist_ids:
                artists.append(Lp().artists.get_name(artist_id))
            GLib.idle_add(self.__populate, artists)

#######################
# PRIVATE             #
#######################
    def __on_map(self, widget):
        """
            Resize
            @param widget as Gtk.Widget
        """
        self.set_size_request(300, 400)

    def __populate(self, artists):
        """
            Populate view with artists
            @param artists as [str]
        """
        if artists:
            artist = artists.pop(0)
            similars = Lp().lastfm.get_similars(artist)
            for similar in similars:
                label = Gtk.Label.new(similar)
                label.set_ellipsize(Pango.EllipsizeMode.END)
                label.show()
                self.__view.add(label)
            GLib.idle_add(self.__populate, artists)
        else:
            self.__spinner.stop()
            self.__stack.set_visible_child(self.__view)

    def __on_row_activated(self, widget, row):
        """
            Play searched item when selected
            @param widget as Gtk.ListBox
            @param row as AlbumRow
        """
        Lp().window.toolbar.search(row.get_child().get_text())
