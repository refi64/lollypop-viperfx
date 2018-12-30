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

from gettext import gettext as _

from lollypop.logger import Logger
from lollypop.define import App


class OverlayHelper:
    """
        An overlay helper
    """
    _pixel_size = App().settings.get_value(
            "cover-size").get_int32() / 9

    def __init__(self):
        """
            Init manager
        """
        self._show_overlay = False
        self._lock_overlay = False
        self.__timeout_id = None

    def lock_overlay(self, lock):
        """
            Lock overlay
            @param lock as bool
        """
        self._lock_overlay = lock

    def show_overlay(self, set):
        """
            Set overlay
            @param set as bool
        """
        # Remove enter notify timeout
        if self.__timeout_id is not None:
            GLib.source_remove(self.__timeout_id)
            self.__timeout_id = None
        self._show_overlay_func(set)

    @property
    def is_overlay(self):
        """
            True if overlayed or going to be
        """
        return self._show_overlay

#######################
# PROTECTED           #
#######################
    def _show_overlay_func(self, show_overlay):
        """
            Set overlay
            @param show_overlay as bool
        """
        self._show_overlay = show_overlay
        self.emit("overlayed", show_overlay)

    def _on_enter_notify(self, widget, event):
        """
            Show overlay buttons after a timeout
            @param widget as Gtk.Widget
            @param event es Gdk.Event
        """
        if self._artwork is None:
            return
        self._artwork.set_opacity(0.9)
        if self.__timeout_id is None:
            self.__timeout_id = GLib.timeout_add(150,
                                                 self._on_enter_notify_timeout)

    def _on_leave_notify(self, widget, event):
        """
            Hide overlay buttons
            @param widget as Gtk.Widget
            @param event es Gdk.Event
        """
        allocation = widget.get_allocation()
        if event.x <= 0 or\
           event.x >= allocation.width or\
           event.y <= 0 or\
           event.y >= allocation.height:
            if self._artwork is not None:
                self._artwork.set_opacity(1)
            # Remove enter notify timeout
            if self.__timeout_id is not None:
                GLib.source_remove(self.__timeout_id)
                self.__timeout_id = None
            if self._show_overlay:
                self._show_overlay_func(False)

    def _on_realize(self, widget):
        """
            Set cursor on widget
            @param widget as Gtk.Widget
        """
        try:
            window = widget.get_window()
            if window is not None:
                window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))
        except:
            Logger.warning(_("You are using a broken cursor theme!"))

    def _on_enter_notify_timeout(self):
        """
            Show overlay buttons
        """
        self.__timeout_id = None
        if not self._show_overlay:
            self._show_overlay_func(True)

    def _on_popover_closed(self, widget):
        """
            Remove selected style
            @param widget as Popover
        """
        self._lock_overlay = False
        GLib.idle_add(self.show_overlay, False)


class OverlayAlbumHelper(OverlayHelper):
    """
        Special album case
    """

    def __init__(self):
        """
            Init overlay
        """
        OverlayHelper.__init__(self)

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
                (App().player.is_locked and show_overlay):
            return
        OverlayHelper._show_overlay_func(self, show_overlay)
        if show_overlay:
            self._play_button = Gtk.Button.new_from_icon_name(
                "media-playback-start-symbolic",
                Gtk.IconSize.INVALID)
            self._play_button.set_relief(Gtk.ReliefStyle.NONE)
            self._play_button.get_image().set_pixel_size(
                OverlayAlbumHelper._pixel_size + 20)
            self._play_button.set_property("has-tooltip", True)
            self._play_button.set_tooltip_text(_("Play"))
            self._play_button.connect("realize", self._on_realize)
            self._play_button.connect("clicked", self.__on_play_clicked)
            self._play_button.set_property("halign", Gtk.Align.START)
            self._play_button.set_property("valign", Gtk.Align.END)
            self._play_button.set_margin_start(6)
            self._play_button.set_margin_bottom(6)
            self._play_button.show()
            # Artwork button
            self._artwork_button = Gtk.Button.new_from_icon_name(
                "image-x-generic-symbolic",
                Gtk.IconSize.INVALID)
            self._artwork_button.set_relief(Gtk.ReliefStyle.NONE)
            self._artwork_button.set_property("has-tooltip", True)
            self._artwork_button.set_tooltip_text(_("Change artwork"))
            self._artwork_button.set_property("halign", Gtk.Align.END)
            self._artwork_button.set_property("valign", Gtk.Align.END)
            self._artwork_button.connect("realize", self._on_realize)
            self._artwork_button.connect("clicked", self.__on_artwork_clicked)
            self._artwork_button.get_image().set_pixel_size(
                OverlayAlbumHelper._pixel_size)
            self._artwork_button.show()
            # Action button
            self._action_button = Gtk.Button.new()
            self._action_button.set_relief(Gtk.ReliefStyle.NONE)
            self._action_button.set_property("has-tooltip", True)
            self._action_button.set_property("halign", Gtk.Align.END)
            self._action_button.set_property("valign", Gtk.Align.END)
            self._action_button.connect("realize", self._on_realize)
            self._action_button.connect("clicked", self.__on_action_clicked)
            self._action_button.set_image(Gtk.Image())
            self._action_button.get_image().set_pixel_size(
                OverlayAlbumHelper._pixel_size)
            self._action_button.show()
            self._show_append(self._album.id not in App().player.album_ids)
            self._overlay.add_overlay(self._play_button)
            self._overlay_grid = Gtk.Grid()
            self._overlay_grid.set_margin_bottom(6)
            self._overlay_grid.set_margin_end(6)
            self._overlay_grid.set_property("halign", Gtk.Align.END)
            self._overlay_grid.set_property("valign", Gtk.Align.END)
            self._overlay.add_overlay(self._overlay_grid)
            self._overlay_grid.add(self._action_button)
            self._overlay_grid.add(self._artwork_button)
            self._overlay_grid.show_all()
            self._play_button.get_style_context().add_class("rounded-icon")
            self._overlay_grid.get_style_context().add_class(
                    "squared-icon-small")
            self._artwork_button.get_style_context().add_class(
                    "overlay-button")
            self._action_button.get_style_context().add_class(
                    "overlay-button")
        else:
            self._play_button.destroy()
            self._play_button = None
            self._action_button.destroy()
            self._action_button = None
            self._artwork_button.destroy()
            self._artwork_button = None
            self._overlay_grid.destroy()
            self._overlay_grid = None

    def _show_append(self, append):
        """
            Show append button if append, else remove button
        """
        if append:
            self._action_button.get_image().set_from_icon_name(
                                                  "list-add-symbolic",
                                                  Gtk.IconSize.INVALID)
            self._action_button.set_tooltip_text(_("Add to current playlist"))
        else:
            self._action_button.get_image().set_from_icon_name(
                                                   "list-remove-symbolic",
                                                   Gtk.IconSize.INVALID)
            self._action_button.set_tooltip_text(
                _("Remove from current playlist"))

#######################
# PRIVATE             #
#######################
    def __on_play_clicked(self, button):
        """
            Play album
            @param button as Gtk.Button
        """
        if App().player.is_locked:
            return True
        if App().player.is_party:
            action = App().lookup_action("party")
            action.change_state(GLib.Variant("b", False))
        App().player.play_album(self._album.clone(True))
        self._show_append(False)
        return True

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

    def __on_action_clicked(self, button):
        """
            Append album to current list if not present
            Remove it if present
            @param button as Gtk.Button
        """
        if App().player.is_locked:
            return True
        if self._album.id in App().player.album_ids:
            if App().player.current_track.album.id == self._album.id:
                # If not last album, skip it
                if len(App().player.albums) > 1:
                    App().player.skip_album()
                    App().player.remove_album_by_id(self._album.id)
                # remove it and stop playback by going to next track
                else:
                    App().player.remove_album_by_id(self._album.id)
                    App().player.stop()
            else:
                App().player.remove_album_by_id(self._album.id)
            self._show_append(True)
        else:
            if App().player.is_playing and not App().player.albums:
                App().player.play_album(self._album.clone(True))
            else:
                App().player.add_album(self._album.clone(True))
            self._show_append(False)
        return True
