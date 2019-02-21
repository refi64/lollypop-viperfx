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

from random import shuffle

from lollypop.define import App, SelectionListMask
from lollypop.utils import get_icon_name
from lollypop.objects import Album
from lollypop.widgets_flowbox_rounded import RoundedFlowBoxWidget
from lollypop.helper_art import ArtHelperEffect


class RoundedArtistWidget(RoundedFlowBoxWidget):
    """
        Artist photo or artist's albums in a rounded widget
    """

    def __init__(self, item, art_size):
        """
            Init widget
            @param item as (int, str, str)
            @param art_size as int
        """
        RoundedFlowBoxWidget.__init__(self, item[0], item[1],
                                      item[1], art_size)

    def populate(self):
        """
            Populate widget content
        """
        RoundedFlowBoxWidget.populate(self)
        self.connect("destroy", self.__on_destroy)
        self.connect("button-release-event", self.__on_button_release_event)
        self.__gesture = Gtk.GestureLongPress.new(self)
        self.__gesture.connect("pressed", self.__on_gesture_pressed)
        # We want to get release event after gesture
        self.__gesture.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.__gesture.set_button(0)

    def show_overlay(self, show):
        """
            Show overlay
            @param show as bool
        """
        pass

    def set_artwork(self):
        """
            Set artist artwork
        """
        self._set_artwork()

    @property
    def is_overlay(self):
        """
            True if widget is overlayed
            @return bool
        """
        return False

#######################
# PROTECTED           #
#######################
    def _set_artwork(self):
        """
            Set artist artwork
        """
        if self._artwork is None:
            return

        def set_icon_name():
            icon_name = get_icon_name(self._data) or "avatar-default-symbolic"
            self._artwork.set_from_icon_name(icon_name, Gtk.IconSize.DIALOG)
            self.emit("populated")
            self._artwork.get_style_context().add_class("artwork-icon-large")

        if self._data < 0:
            set_icon_name()
        elif App().settings.get_value("artist-artwork"):
            App().art_helper.set_artist_artwork(
                                            self.name,
                                            self._art_size,
                                            self._art_size,
                                            self._artwork.get_scale_factor(),
                                            self.__on_artist_artwork)
        else:
            album_ids = App().albums.get_ids([self._data], [])
            if album_ids:
                shuffle(album_ids)
                App().art_helper.set_album_artwork(
                                            Album(album_ids[0]),
                                            self._art_size,
                                            self._art_size,
                                            self._artwork.get_scale_factor(),
                                            self.__on_artist_artwork,
                                            ArtHelperEffect.ROUNDED)
            else:
                set_icon_name()

#######################
# PRIVATE             #
#######################
    def __popup_menu(self, widget):
        """
            Popup menu for track
            @param widget as Gtk.Widget
        """
        if App().settings.get_value("show-sidebar"):
            return
        from lollypop.pop_menu_views import ViewsMenuPopover
        from lollypop.view_artists_rounded import RoundedArtistsView
        popover = ViewsMenuPopover(self.get_ancestor(RoundedArtistsView),
                                   self.data,
                                   SelectionListMask.ARTISTS_VIEW)
        popover.set_relative_to(widget)
        popover.popup()

    def __on_artist_artwork(self, surface):
        """
            Finish widget initialisation
            @param surface as cairo.Surface
        """
        if self._artwork is None:
            return
        if surface is None:
            self._artwork.set_from_icon_name("avatar-default-symbolic",
                                             Gtk.IconSize.DIALOG)
        else:
            self._artwork.set_from_surface(surface)
        if self._artwork.props.surface is None:
            self._artwork.get_style_context().add_class("artwork-icon")
        self.emit("populated")

    def __on_gesture_pressed(self, gesture, x, y):
        """
            Show current track menu
            @param gesture as Gtk.GestureLongPress
            @param x as float
            @param y as float
        """
        self.__popup_menu(self)

    def __on_button_release_event(self, widget, event):
        """
            Handle button release event
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        if event.button == 1:
            self.activate()
        elif event.button == 3:
            self.__popup_menu(self)
        return True

    def __on_destroy(self, widget):
        """
            Destroyed widget
            @param widget as Gtk.Widget
        """
        self.__artwork = None
