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
from lollypop.widgets_flowbox_rounded import RoundedFlowBoxWidget
from lollypop.widgets_album import AlbumBaseWidget


class AlbumsDecadeWidget(RoundedFlowBoxWidget, AlbumBaseWidget):
    """
        Decade widget showing cover for 9 albums
    """

    def __init__(self, item_ids):
        """
            Init widget
            @param decade as [int]
        """
        AlbumBaseWidget.__init__(self)
        RoundedFlowBoxWidget.__init__(self, item_ids)

    def populate(self):
        """
            Populate widget content
        """
        self._lock_overlay = False
        decade_str = "%s - %s" % (self._data[0], self._data[-1])
        RoundedFlowBoxWidget.populate(self, decade_str)
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
        if set:
            # Play button
            self._play_event = Gtk.EventBox()
            self._play_event.set_property("has-tooltip", True)
            self._play_event.set_hexpand(True)
            self._play_event.set_property("valign", Gtk.Align.CENTER)
            self._play_event.set_property("halign", Gtk.Align.CENTER)
            self._play_event.connect("realize", self.__on_eventbox_realize)
            self._play_event.connect("button-press-event",
                                     self._on_play_press_event)
            self._play_button = Gtk.Image.new_from_icon_name(
                "media-playback-start-symbolic",
                Gtk.IconSize.DND)
            self._play_event.set_tooltip_text(_("Play"))
            self._play_button.set_opacity(0)
            # Open button
            self._action2_event = Gtk.EventBox()
            self._action2_event.set_property("has-tooltip", True)
            self._action2_event.set_tooltip_text(_("Open"))
            self._action2_event.set_property("halign", Gtk.Align.END)
            self._action2_event.connect("realize", self._on_eventbox_realize)
            self._action2_event.connect("button-press-event",
                                        self._on_open_press_event)
            self._action2_event.set_property("valign", Gtk.Align.END)
            self._action2_event.set_margin_bottom(5)
            self._action2_event.set_property("halign", Gtk.Align.CENTER)
            self._action2_button = Gtk.Image.new_from_icon_name(
                "folder-open-symbolic",
                Gtk.IconSize.BUTTON)
            self._action2_button.set_opacity(0)
            self._play_event.add(self._play_button)
            self._action2_event.add(self._action2_button)
            self._overlay.add_overlay(self._play_event)
            self._overlay.add_overlay(self._action2_event)
            self._overlay.show_all()
            AlbumBaseWidget._show_overlay_func(self, True)
        else:
            AlbumBaseWidget._show_overlay_func(self, False)
            self._play_event.destroy()
            self._play_event = None
            self._play_button.destroy()
            self._play_button = None
            self._action2_event.destroy()
            self._action2_event = None
            self._action2_button.destroy()
            self._action2_button = None

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
        # FIXME
        if isinstance(self._data, list):
            App().window.container.list_two.select_ids(self._data)
        else:
            App().window.container.list_two.select_ids([self._data])

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
