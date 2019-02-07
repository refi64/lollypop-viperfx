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

from gi.repository import Gdk, Gtk, GLib

from gettext import gettext as _

from lollypop.logger import Logger
from lollypop.define import App, Type, SidebarContent
from lollypop.widgets_albums_rounded import RoundedAlbumsWidget
from lollypop.helper_overlay import OverlayHelper


class AlbumsGenreWidget(RoundedAlbumsWidget, OverlayHelper):
    """
        Genre widget showing cover for 4 albums
    """

    def __init__(self, genre_id, view_type):
        """
            Init widget
            @param Genre as [int]
            @param view_type as ViewType
        """
        OverlayHelper.__init__(self)
        name = sortname = App().genres.get_name(genre_id)
        RoundedAlbumsWidget.__init__(self, genre_id, name, sortname, view_type)
        self._genre = Type.GENRES

    def populate(self):
        """
            Populate widget content
        """
        self._lock_overlay = False
        self._album_ids = App().albums.get_ids([], [self._data])
        RoundedAlbumsWidget.populate(self)
        self._widget.connect("enter-notify-event", self._on_enter_notify)
        self._widget.connect("leave-notify-event", self._on_leave_notify)

#######################
# PROTECTED           #
#######################
    def _show_overlay_func(self, show_overlay):
        """
            Set overlay
            @param show_overlay as bool
        """
        if self._lock_overlay or\
                self._show_overlay == show_overlay or\
                App().player.is_locked:
            return
        OverlayHelper._show_overlay_func(self, show_overlay)
        if show_overlay:
            # Play button
            self.__play_button = Gtk.Button.new_from_icon_name(
                "media-playback-start-symbolic",
                Gtk.IconSize.INVALID)
            self.__play_button.set_tooltip_text(_("Play"))
            self.__play_button.set_relief(Gtk.ReliefStyle.NONE)
            self.__play_button.get_image().set_pixel_size(self._pixel_size +
                                                          20)
            self.__play_button.set_property("has-tooltip", True)
            self.__play_button.set_hexpand(True)
            self.__play_button.set_property("valign", Gtk.Align.END)
            self.__play_button.set_property("halign", Gtk.Align.START)
            self.__play_button.connect("realize", self._on_realize)
            self.__play_button.connect("clicked", self.__on_play_clicked)
            self.__play_button.set_margin_bottom(10)
            self.__play_button.set_margin_start(10)
            self.__overlay_grid = Gtk.Grid()
            self.__overlay_grid.set_property("halign", Gtk.Align.END)
            self.__overlay_grid.set_property("valign", Gtk.Align.END)
            self.__overlay_grid.set_margin_bottom(10)
            self.__overlay_grid.set_margin_end(10)
            self._overlay.add_overlay(self.__overlay_grid)
            self._overlay.add_overlay(self.__play_button)
            self._overlay.show_all()
            self.__play_button.get_style_context().add_class("rounded-icon")
            self.__overlay_grid.get_style_context().add_class(
                "squared-icon-small")
        else:
            self.__play_button.destroy()
            self.__play_button = None
            self.__overlay_grid.destroy()
            self.__overlay_grid = None

#######################
# PRIVATE             #
#######################
    def __on_play_clicked(self, button):
        """
            Play Genre
            @param button as Gtk.Button
        """
        if App().player.is_locked:
            return True
        if App().player.is_party:
            App().lookup_action("party").change_state(GLib.Variant("b", False))
        App().player.play_albums(None, [self._data], [])
        return True

    def __on_open_clicked(self, button):
        """
            Open Genre
            @param button as Gtk.Button
        """
        sidebar_content = App().settings.get_enum("sidebar-content")
        if sidebar_content != SidebarContent.GENRES:
            App().window.emit("show-can-go-back", True)
            App().window.emit("can-go-back-changed", True)
        App().window.container.show_view(Type.GENRES, self._data)

    def __on_eventbox_realize(self, eventbox):
        """
            Change cursor over eventbox
            @param eventbox as Gdk.Eventbox
        """
        try:
            window = eventbox.get_window()
            if window is not None:
                window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))
        except:
            Logger.warning(_("You are using a broken cursor theme!"))
