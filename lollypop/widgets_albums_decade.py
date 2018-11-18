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

from lollypop.define import App, Type
from lollypop.widgets_albums_rounded import RoundedAlbumsWidget
from lollypop.helper_overlay import OverlayHelper


class AlbumsDecadeWidget(RoundedAlbumsWidget, OverlayHelper):
    """
        Decade widget showing cover for 9 albums
    """

    def __init__(self, item_ids):
        """
            Init widget
            @param decade as [int]
        """
        OverlayHelper.__init__(self)
        RoundedAlbumsWidget.__init__(self, item_ids)

    def populate(self):
        """
            Populate widget content
        """
        self._lock_overlay = False
        decade_str = "%s - %s" % (self._data[0], self._data[-1])
        RoundedAlbumsWidget.populate(self, decade_str)
        self._widget.connect("enter-notify-event", self._on_enter_notify)
        self._widget.connect("leave-notify-event", self._on_leave_notify)

    @property
    def filter(self):
        return "%s - %s" % (self._data[0], self._data[-1])

#######################
# PROTECTED           #
#######################
    def _get_album_ids(self):
        """
            Get ids for widget
            @return [int]
        """
        album_ids = []
        for year in self._data:
            album_ids += App().albums.get_albums_for_year(year,
                                                          self._ALBUMS_COUNT)
            l = len(album_ids)
            if l < self._ALBUMS_COUNT:
                album_ids += App().albums.get_compilations_for_year(
                                                       year,
                                                       self._ALBUMS_COUNT)
        return album_ids

    def _show_overlay_func(self, set):
        """
            Set overlay
            @param set as bool
        """
        if self._lock_overlay or\
           self._show_overlay == set:
            return
        OverlayHelper._show_overlay_func(self, set)
        if set:
            # Play button
            self.__play_event = Gtk.EventBox()
            self.__play_event.set_property("has-tooltip", True)
            self.__play_event.set_hexpand(True)
            self.__play_event.set_property("valign", Gtk.Align.CENTER)
            self.__play_event.set_property("halign", Gtk.Align.CENTER)
            self.__play_event.connect("realize", self.__on_eventbox_realize)
            self.__play_event.connect("button-press-event",
                                      self._on_play_press_event)
            self.__play_button = Gtk.Image.new_from_icon_name(
                "media-playback-start-symbolic",
                Gtk.IconSize.DND)
            self.__play_event.set_tooltip_text(_("Play"))
            self.__play_button.set_opacity(1)
            # Open button
            self.__open_event = Gtk.EventBox()
            self.__open_event.set_property("has-tooltip", True)
            self.__open_event.set_tooltip_text(_("Open"))
            self.__open_event.set_property("halign", Gtk.Align.END)
            self.__open_event.connect("realize", self._on_eventbox_realize)
            self.__open_event.connect("button-press-event",
                                      self._on_open_press_event)
            self.__open_event.set_property("valign", Gtk.Align.END)
            self.__open_event.set_margin_bottom(5)
            self.__open_event.set_property("halign", Gtk.Align.CENTER)
            self.__open_button = Gtk.Image.new_from_icon_name(
                "folder-open-symbolic",
                Gtk.IconSize.BUTTON)
            self.__open_button.set_opacity(1)
            self.__play_event.add(self.__play_button)
            self.__open_event.add(self.__open_button)
            self._overlay.add_overlay(self.__play_event)
            self._overlay.add_overlay(self.__open_event)
            self._overlay.show_all()
            self.__play_button.get_style_context().add_class("rounded-icon")
            self.__open_button.get_style_context().add_class(
                "squared-icon-small")
        else:
            self.__play_event.destroy()
            self.__play_event = None
            self.__play_button.destroy()
            self.__play_button = None
            self.__open_event.destroy()
            self.__open_event = None
            self.__open_button.destroy()
            self.__open_button = None

    def _on_play_press_event(self, widget, event):
        """
            Play decade
            @param: widget as Gtk.EventBox
            @param: event as Gdk.Event
        """
        if App().player.is_locked:
            return True
        if App().player.is_party:
            App().lookup_action("party").change_state(GLib.Variant("b", False))
        App().player.play_albums(None, [Type.YEARS], self._data)
        return True

    def _on_open_press_event(self, widget, event):
        """
            Open decade
            @param: widget as Gtk.EventBox
            @param: event as Gdk.Event
        """
        if App().player.is_locked:
            return True
        if App().settings.get_value("show-sidebar"):
            App().window.container.list_two.select_ids(self._data)
        else:
            App().window.container.show_view(Type.YEARS, self._data)

#######################
# PRIVATE             #
#######################
    def __on_eventbox_realize(self, eventbox):
        """
            Change cursor over eventbox
            @param eventbox as Gdk.Eventbox
        """
        window = eventbox.get_window()
        if window is not None:
            window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))
