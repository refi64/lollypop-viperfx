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

from gi.repository import Gtk, GObject

from gettext import gettext as _

from lollypop.define import App, ArtSize, ArtHelperEffect
from lollypop.helper_overlay_album import OverlayAlbumHelper
from lollypop.utils import on_realize


class CoverWidget(Gtk.EventBox, OverlayAlbumHelper):
    """
        Widget showing current album cover
    """
    __gsignals__ = {
        "overlayed": (GObject.SignalFlags.RUN_FIRST, None, (bool,))
    }

    def __init__(self, album, art_size=ArtSize.BANNER):
        """
            Init cover widget
            @param art_size as int
        """
        Gtk.EventBox.__init__(self)
        self.set_property("halign", Gtk.Align.CENTER)
        self.set_property("valign", Gtk.Align.CENTER)
        self._album = None
        self.__image_button = None
        self.__art_size = art_size
        self._artwork = App().art_helper.get_image(self.__art_size,
                                                   self.__art_size,
                                                   "small-cover-frame")
        self._artwork.show()
        App().art_helper.set_album_artwork(
                album,
                self.__art_size,
                self.__art_size,
                self._artwork.get_scale_factor(),
                self.__on_album_artwork,
                ArtHelperEffect.NONE)
        self._overlay = Gtk.Overlay.new()
        self._overlay.show()
        OverlayAlbumHelper.__init__(self)
        self._overlay.add(self._artwork)
        self.add(self._overlay)
        self.connect("enter-notify-event", self._on_enter_notify)
        self.connect("leave-notify-event", self._on_leave_notify)
        self.connect("destroy", self.__on_destroy)
        self.__art_signal_id = App().art.connect(
                                              "album-artwork-changed",
                                              self.__on_album_artwork_changed)

#######################
# PROTECTED           #
#######################
    def _show_overlay_func(self, show_overlay):
        """
            Set overlay
            @param show_overlay as bool
        """
        if self._lock_overlay or self._show_overlay == show_overlay:
            return
        OverlayAlbumHelper._show_overlay_func(self, show_overlay)
        if show_overlay:
            # Image button
            self.__image_button = Gtk.Button.new_from_icon_name(
                "image-x-generic-symbolic",
                Gtk.IconSize.INVALID)
            self.__image_button.set_property("has-tooltip", True)
            self.__image_button.set_tooltip_text(_("Change artwork"))
            self.__image_button.connect("realize", on_realize)
            self.__image_button.connect("clicked", self.__on_artwork_clicked)
            self.__image_button.get_image().set_pixel_size(self._pixel_size)
            self.__image_button.show()
            self._small_grid.add(self.__image_button)
            self.__image_button.get_style_context().add_class(
                "overlay-button")
        else:
            self.__image_button.destroy()
            self.__image_button = None

#######################
# PRIVATE             #
#######################
    def __on_destroy(self, widget):
        """
            Disconnect signal
            @param widget as Gtk.Widget
        """
        if self.__art_signal_id is not None:
            App().art.disconnect(self.__art_signal_id)

    def __on_album_artwork_changed(self, art, album_id):
        """
            Update cover for album_id
            @param art as Art
            @param album id as int
        """
        if self._album is None:
            return
        if album_id == self._album.id:
            self.update(self._album)

    def __on_album_artwork(self, surface):
        """
            Set album artwork
            @param surface as str
        """
        self._artwork.set_from_surface(surface)

    def __on_artwork_clicked(self, button):
        """
            Popover with album art downloaded from the web (in fact google :-/)
            @param button as Gtk.Button
        """
        from lollypop.pop_artwork import CoversPopover
        popover = CoversPopover(self._album)
        popover.set_relative_to(button)
        popover.connect("closed", self._on_popover_closed)
        self._lock_overlay = True
        popover.popup()
        return True
