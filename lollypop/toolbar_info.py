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

from gi.repository import Gtk, Gdk, GLib

from lollypop.controllers import InfoController
from lollypop.define import App, Type


class ToolbarInfo(Gtk.Bin, InfoController):
    """
        Informations toolbar
    """

    def __init__(self):
        """
            Init toolbar
        """
        Gtk.Bin.__init__(self)
        InfoController.__init__(self)
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/ToolbarInfo.ui")
        builder.connect_signals(self)
        self.__timeout_id = None
        self.__width = 0

        self._infobox = builder.get_object("info")
        self._infobox.connect("button-press-event",
                              self.__on_infobox_button_press_event)
        self._infobox.connect("button-release-event",
                              self.__on_infobox_button_release_event)
        self.add(self._infobox)

        self.__gesture = Gtk.GestureLongPress.new(self._infobox)
        self.__gesture.connect("pressed", self.__on_infobox_pressed)

        self._spinner = builder.get_object("spinner")

        self.__labels = builder.get_object("nowplaying_labels")
        self.__labels.connect("query-tooltip", self.__on_query_tooltip)
        self.__labels.set_property("has-tooltip", True)

        self._title_label = builder.get_object("title")
        self._artist_label = builder.get_object("artist")
        self._cover = builder.get_object("cover")
        self._cover.set_property("has-tooltip", True)
        # Since GTK 3.20, we can set cover full height
        if Gtk.get_minor_version() > 18:
            self._cover.get_style_context().add_class("toolbar-cover-frame")
        else:
            self._cover.get_style_context().add_class("small-cover-frame")

        self.connect("realize", self.__on_realize)
        App().player.connect("loading-changed", self.__on_loading_changed)
        App().art.connect("album-artwork-changed", self.__update_cover)
        App().art.connect("radio-artwork-changed", self.__update_logo)

    def do_get_preferred_width(self):
        """
            We force preferred width
            @return (int, int)
        """
        return (self.__width, self.__width)

    def get_preferred_height(self):
        """
            Return preferred height
            @return (int, int)
        """
        return self.__labels.get_preferred_height()

    def set_width(self, width):
        """
            Set widget width
            @param width as int
        """
        self.__width = width
        self.set_property("width-request", width)

    def on_current_changed(self, player):
        """
            Update widgets
            player as Player
        """
        InfoController.on_current_changed(self, self.artsize, None)

#######################
# PROTECTED           #
#######################
    def _on_eventbox_realize(self, eventbox):
        """
            Show hand cursor over
        """
        eventbox.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))

#######################
# PRIVATE             #
#######################
    def __update_cover(self, art, album_id):
        """
            Update cover for album_id
            @param art as Art
            @param album id as int
        """
        if App().player.current_track.album.id == album_id:
            surface = App().art.get_album_artwork(
                App().player.current_track.album,
                self.artsize,
                self._cover.get_scale_factor())
            self._cover.set_from_surface(surface)

    def __update_logo(self, art, name):
        """
            Update logo for name
            @param art as Art
            @param name as str
        """
        if App().player.current_track.album_artist == name:
            pixbuf = App().art.get_radio_artwork(name, self.artsize)
            self._cover.set_from_surface(pixbuf)

    def __on_infobox_pressed(self, gesture, x, y):
        """
            Show current track menu
            @param gesture as Gtk.GestureLongPress
            @param x as float
            @param y as float
        """
        from lollypop.pop_menu import ToolbarMenu
        menu = ToolbarMenu(App().player.current_track)
        if App().player.current_track.id >= 0:
            from lollypop.pop_menu import TrackMenuPopover
            popover = TrackMenuPopover(App().player.current_track, menu)
            popover.set_relative_to(self._infobox)
        elif App().player.current_track.id == Type.RADIOS:
            popover = Gtk.Popover.new_from_model(self._infobox, menu)
        popover.show()

    def __on_infobox_button_press_event(self, eventbox, event):
        """
            Block event if button is not left click
            @param eventbox as Gtk.EventBox
            @param event as Gdk.Event
        """
        if event.button != 1:
            return True

    def __on_infobox_button_release_event(self, eventbox, event):
        """
            Show track information popover
            @param eventbox as Gtk.EventBox
            @param event as Gdk.Event
        """
        if event.button == 1:
            if App().player.current_track.id == Type.RADIOS:
                from lollypop.pop_tunein import TuneinPopover
                popover = TuneinPopover()
                popover.populate()
            elif App().player.current_track.id is not None:
                from lollypop.pop_information import InformationPopover
                popover = InformationPopover()
                popover.populate()
            popover.set_relative_to(self._infobox)
            popover.show()
        else:
            self.__on_infobox_pressed(self.__gesture, 0, 0)

    def __on_loading_changed(self, player, show):
        """
            Show spinner based on loading status
            @param player as player
            @param show as bool
        """
        if show:
            self._title_label.hide()
            self._artist_label.hide()
            self._cover.hide()
            self._spinner.show()
            self._spinner.start()
            self._infobox.show()
        else:
            self._spinner.hide()
            self._spinner.stop()

    def __on_realize(self, toolbar):
        """
            Calculate art size
            @param toolbar as ToolbarInfos
        """
        style = self.get_style_context()
        padding = style.get_padding(style.get_state())
        artsize = self.get_allocated_height()\
            - padding.top - padding.bottom
        # Since GTK 3.20, we can set cover full height
        if Gtk.get_minor_version() < 20:
            artsize -= 2
        self.set_artsize(artsize)

    def __on_query_tooltip(self, widget, x, y, keyboard, tooltip):
        """
            Show tooltip if needed
            @param widget as Gtk.Widget
            @param x as int
            @param y as int
            @param keyboard as bool
            @param tooltip as Gtk.Tooltip
        """
        layout_title = self._title_label.get_layout()
        layout_artist = self._artist_label.get_layout()
        if layout_title.is_ellipsized() or layout_artist.is_ellipsized():
            artist = GLib.markup_escape_text(self._artist_label.get_text())
            title = GLib.markup_escape_text(self._title_label.get_text())
            tooltip.set_markup("<b>%s</b> - %s" % (artist, title))
        else:
            return False
        return True
