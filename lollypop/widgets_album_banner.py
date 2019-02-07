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

from gi.repository import Gtk, GLib

from lollypop.helper_art import ArtHelperEffect
from lollypop.define import App, ArtSize
from lollypop.widgets_cover import CoverWidget
from lollypop.utils import get_human_duration


class AlbumBannerWidget(Gtk.Bin):
    """
        Banner for album
    """

    def __init__(self, album):
        """
            Init cover widget
            @param album
        """
        Gtk.Bin.__init__(self)
        self.__width = 0
        self.__allocation_timeout_id = None
        self.__album = album
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/AlbumBannerWidget.ui")
        builder.connect_signals(self)
        name_label = builder.get_object("name_label")
        year_label = builder.get_object("year_label")
        duration_label = builder.get_object("duration_label")
        name_label.set_text(album.name)
        year_label.set_text(str(album.year))
        duration = App().albums.get_duration(self.__album.id,
                                             self.__album.genre_ids)
        duration_label.set_text(get_human_duration(duration))
        self.__artwork = builder.get_object("artwork")
        self.__grid = builder.get_object("grid")
        self.__widget = builder.get_object("widget")
        cover_widget = CoverWidget()
        cover_widget.update(album)
        cover_widget.set_margin_start(20)
        cover_widget.set_margin_top(18)
        cover_widget.show()
        self.__grid.attach(cover_widget, 0, 0, 1, 3)
        self.add(self.__widget)
        self.connect("size-allocate", self.__on_size_allocate)

    def do_get_preferred_width(self):
        """
            Force preferred width
        """
        (min, nat) = Gtk.Bin.do_get_preferred_width(self)
        # Allow resizing
        return (0, 0)

    def do_get_preferred_height(self):
        """
            Force preferred height
        """
        return (ArtSize.BANNER + 40, ArtSize.BANNER + 40)

#######################
# PROTECTED           #
#######################
    def _on_menu_button_clicked(self, button):
        """
            Show album menu
            @param button as Gtk.Button
        """
        from lollypop.pop_menu import AlbumMenu
        menu = AlbumMenu(self.__album, True)
        popover = Gtk.Popover.new_from_model(button, menu)
        popover.popup()

#######################
# PRIVATE             #
#######################
    def __handle_size_allocate(self, allocation):
        """
            Change box max/min children
            @param allocation as Gtk.Allocation
        """
        self.__allocation_timeout_id = None
        if allocation.width == 1 or self.__width == allocation.width:
            return
        self.__width = allocation.width
        App().art_helper.set_album_artwork(
                self.__album,
                allocation.width,
                allocation.width,
                self.__artwork.get_scale_factor(),
                self.__on_album_artwork,
                ArtHelperEffect.BLUR)

    def __on_album_artwork(self, surface):
        """
            Set album artwork
            @param surface as str
        """
        self.__artwork.set_from_surface(surface)

    def __on_size_allocate(self, widget, allocation):
        """
            Change box max/min children
            @param widget as Gtk.Widget
            @param allocation as Gtk.Allocation
        """
        if self.__allocation_timeout_id is not None:
            GLib.source_remove(self.__allocation_timeout_id)
        self.__allocation_timeout_id = GLib.idle_add(
            self.__handle_size_allocate, allocation)
