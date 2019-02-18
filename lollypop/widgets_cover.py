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

from gi.repository import Gtk

from lollypop.helper_art import ArtHelperEffect
from lollypop.define import App, ArtSize
from lollypop.utils import on_realize


class CoverWidget(Gtk.EventBox):
    """
        Widget showing current album cover
    """

    def __init__(self, editable=False):
        """
            Init cover widget
        """
        Gtk.EventBox.__init__(self)
        self.__album = None
        if editable:
            self.connect("realize", on_realize)
            self.connect("button-release-event",
                         self.__on_button_release_event)
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/CoverWidget.ui")
        builder.connect_signals(self)
        self.__artwork = builder.get_object("cover")
        self.add(builder.get_object("widget"))
        self.connect("destroy", self.__on_destroy)
        self.__signal = App().art.connect("album-artwork-changed",
                                          self.__on_album_artwork_changed)

    def update(self, album):
        """
            Update cover
            @param album as Album
        """
        self.__album = album
        App().art_helper.set_album_artwork(
                album,
                ArtSize.BANNER,
                ArtSize.BANNER,
                self.__artwork.get_scale_factor(),
                self.__on_album_artwork,
                ArtHelperEffect.NONE)

#######################
# PRIVATE             #
#######################
    def __on_destroy(self, widget):
        """
            Disconnect signal
            @param widget as Gtk.Widget
        """
        if self.__signal is not None:
            App().art.disconnect(self.__signal)

    def __on_album_artwork_changed(self, art, album_id):
        """
            Update cover for album_id
            @param art as Art
            @param album id as int
        """
        if self.__album is None:
            return
        if album_id == self.__album.id:
            self.update(self.__album)

    def __on_button_release_event(self, eventbox, event):
        """
            Show Covers popover
            @param eventbox as Gtk.EventBox
            @param event as Gdk.Event
        """
        if self.__album is None:
            return
        from lollypop.pop_artwork import CoversPopover
        popover = CoversPopover(self.__album)
        popover.set_relative_to(eventbox)
        popover.popup()

    def __on_album_artwork(self, surface):
        """
            Set album artwork
            @param surface as str
        """
        self.__artwork.set_from_surface(surface)
