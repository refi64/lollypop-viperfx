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


class ArtistBannerWidget(Gtk.Overlay):
    """
        Banner for artist
    """

    def __init__(self, artist_id):
        """
            Init artist banner
            @param artist_id as int
        """
        Gtk.Overlay.__init__(self)
        self.__width = 0
        self.__artist_id = artist_id
        self.__allocation_timeout_id = None
        self.__artwork = Gtk.Image()
        self.__artwork.get_style_context().add_class("black")
        self.__artwork.show()
        self.add(self.__artwork)
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
        return (ArtSize.BIG + 40, ArtSize.BIG + 40)

#######################
# PROTECTED           #
#######################

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
        artist = App().artists.get_name(self.__artist_id)
        App().art_helper.set_artist_artwork(
                                    artist,
                                    allocation.width,
                                    allocation.width,
                                    self.get_scale_factor(),
                                    self.__on_artist_artwork,
                                    ArtHelperEffect.BLUR)

    def __on_artist_artwork(self, surface):
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
