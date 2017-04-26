# Copyright (c) 2014-2017 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import Gtk, Gio, GLib

from gettext import gettext as _

from lollypop.pop_next import NextPopover
from lollypop.touch_helper import TouchHelper
from lollypop.define import Lp, Shuffle, Type, NextContext


class PartyPopover(Gtk.Popover):
    """
        Show party options
    """

    def __init__(self):
        """
            Init popover
        """
        Gtk.Popover.__init__(self)

        party_grid = Gtk.Grid()
        party_grid.set_property("margin-start", 10)
        party_grid.set_property("margin-end", 10)
        party_grid.set_property("margin-bottom", 5)
        party_grid.set_property("margin-top", 5)
        party_grid.set_column_spacing(10)
        party_grid.set_row_spacing(7)
        party_grid.show()
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(party_grid)
        scrolled.show()
        self.add(scrolled)
        size = Lp().window.get_size()
        self.set_size_request(-1,
                              size[1]*0.6)

        genres = Lp().genres.get()
        genres.insert(0, (Type.POPULARS, _("Populars")))
        genres.insert(1, (Type.RECENTS, _("Recently added")))
        ids = Lp().player.get_party_ids()
        i = 0
        x = 0
        for genre_id, genre in genres:
            label = Gtk.Label()
            label.set_property("halign", Gtk.Align.START)
            # Hack as ellipsize not working as I want, help welcome ;)
            label_text = genre[0:20]
            if len(label_text) != len(genre):
                label_text += "..."
            label.set_text(label_text)
            label.set_tooltip_text(genre)
            label.show()
            switch = Gtk.Switch()
            if genre_id in ids:
                switch.set_state(True)
            switch.connect("state-set", self.__on_switch_state_set, genre_id)
            switch.show()
            party_grid.attach(label, x, i, 1, 1)
            party_grid.attach(switch, x+1, i, 1, 1)
            if x == 0:
                x += 2
            else:
                label.set_property("margin-start", 15)
                i += 1
                x = 0

#######################
# PRIVATE             #
#######################
    def __on_switch_state_set(self, widget, state, genre_id):
        """
            Update party ids when use change a switch in dialog
            @param widget as Gtk.Switch
            @param state as bool, genre id as int
        """
        ids = Lp().player.get_party_ids()
        if state:
            try:
                ids.append(genre_id)
            except:
                pass
        else:
            try:
                ids.remove(genre_id)
            except:
                pass
        Lp().settings.set_value("party-ids",  GLib.Variant("ai", ids))
        Lp().player.set_party_ids()
        Lp().player.set_next()


class ToolbarEnd(Gtk.Bin):
    """
        Toolbar end
    """

    def __init__(self):
        """
            Init toolbar
        """
        Gtk.Bin.__init__(self)
        self.connect("show", self.__on_show)
        self.connect("hide", self.__on_hide)
        self.set_hexpand(True)
        self.__next_popover = NextPopover()
        self.__search = None
        self.__next_was_inhibited = False
        self.__timeout_id = None
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/ToolbarEnd.ui")
        builder.connect_signals(self)

        self.add(builder.get_object("end"))

        self.__grid_next = builder.get_object("grid-next")

        self.__shuffle_button = builder.get_object("shuffle-button")
        self.__shuffle_image = builder.get_object("shuffle-button-image")
        shuffleAction = Gio.SimpleAction.new("shuffle-button", None)
        shuffleAction.connect("activate", self.__activate_shuffle_button)
        Lp().add_action(shuffleAction)
        Lp().set_accels_for_action("app.shuffle-button", ["<Control>r"])
        Lp().settings.connect("changed::shuffle", self.__on_playback_changed)
        Lp().settings.connect("changed::playback", self.__on_playback_changed)

        self.__party_button = builder.get_object("party-button")
        party_action = Gio.SimpleAction.new("party", None)
        party_action.connect("activate", self.__activate_party_button)
        Lp().add_action(party_action)
        Lp().set_accels_for_action("app.party", ["<Control>p"])

        self.__search_button = builder.get_object("search-button")
        self.__helper = TouchHelper(self.__search_button,
                                    "search", "<Control>f")
        self.__helper.set_long_func(self.__on_search_long)
        self.__helper.set_short_func(self.__on_search_short)

        self.__settings_button = builder.get_object("settings-button")

        self.__list_button = builder.get_object("list-button")
        self.__list_button.set_property("has-tooltip", True)
        self.__list_button.connect("query-tooltip",
                                   self.__on_list_button_query_tooltip)
        self.__list_popover = None
        Lp().player.connect("party-changed", self.__on_party_changed)
        Lp().player.connect("lock-changed", self.__on_lock_changed)

    def setup_menu(self, menu):
        """
            Add an application menu to menu button
            @parma: menu as Gio.Menu
        """
        self.__settings_button.show()
        self.__settings_button.set_menu_model(menu)

    def on_status_changed(self, player):
        """
            Update buttons on status changed
            @param player as Player
        """
        if player.is_playing:
            # Party mode can be activated
            # via Fullscreen class, so check button state
            self.__party_button.set_active(player.is_party)

    def on_next_changed(self, player, force=False):
        """
            Show next popover
            @param player as Player
            @param force to show the popover
        """
        # Do not show popover is this menu is active
        # or if we are hidden
        if self.__shuffle_button.get_active() or\
           not self.__grid_next.is_visible():
            return
        if self.__next_popover.should_be_shown() or force:
            if self.__next_popover.is_visible():
                self.__next_popover.update()
            else:
                self.__next_popover.set_relative_to(self.__grid_next)
                self.__next_popover.show()
        else:
            self.__next_popover.hide()

    def search(self, search):
        """
            Search item
            @param search as str
        """
        self.__on_search_short([])
        self.__search.set_text(search)

#######################
# PROTECTED           #
#######################
    def _on_shuffle_button_toggled(self, button):
        """
            Hide next popover
            @param button as Gtk.Button
        """
        if button.get_active():
            self.__next_popover.hide()
            self.__next_popover.inhibit(True)
        else:
            self.__next_popover.inhibit(False)
            if self.__next_popover.should_be_shown():
                self.__next_popover.show()

    def _on_party_button_toggled(self, button):
        """
            Set party mode on if party button active
            @param obj as Gtk.button
        """
        active = self.__party_button.get_active()
        self.__shuffle_button.set_sensitive(not active)
        if not Lp().settings.get_value("dark-ui"):
            settings = Gtk.Settings.get_default()
            settings.set_property("gtk-application-prefer-dark-theme", active)
        Lp().player.set_party(active)
        self.on_next_changed(Lp().player)

    def _on_party_press_event(self, eventbox, event):
        """
            Show party popover
            @param eventbox as Gtk.EventBox
            @param event as Gdk.Event
        """
        if event.button == 3:
            popover = PartyPopover()
            popover.set_relative_to(eventbox)
            self.__next_popover.hide()
            popover.connect("closed", self.__on_popover_closed)
            self.__next_popover.inhibit(True)
            popover.show()
            return True

    def _on_list_button_clicked(self, widget, unused=None):
        """
            Show current playback context popover
            @param widget as Gtk.Widget
        """
        if self.__list_popover is not None:
            return
        self.__next_was_inhibited = self.__next_popover.inhibited
        self.__next_popover.hide()
        self.__next_popover.inhibit(True)
        if Lp().player.current_track.id == Type.EXTERNALS:
            from lollypop.pop_externals import ExternalsPopover
            self.__list_popover = ExternalsPopover()
            self.__list_popover.set_relative_to(self.__list_button)
            self.__list_popover.populate()
            self.__list_popover.show()
        elif Lp().player.queue:
            from lollypop.pop_queue import QueuePopover
            self.__list_popover = QueuePopover()
            self.__list_popover.set_relative_to(self.__list_button)
            self.__list_popover.show()
        elif Lp().player.get_user_playlist_ids():
            from lollypop.pop_playlists import PlaylistsPopover
            self.__list_popover = PlaylistsPopover()
            self.__list_popover.set_relative_to(self.__list_button)
            self.__list_popover.show()
        else:
            from lollypop.pop_albums import AlbumsPopover
            self.__list_popover = AlbumsPopover()
            self.__list_popover.set_relative_to(self.__list_button)
            self.__list_popover.show()
        self.__list_popover.connect("closed", self.__on_list_popover_closed)
        return True

#######################
# PRIVATE             #
#######################
    def __on_search_long(self, args):
        """
            Show current track menu
            @param args as []
        """
        if Lp().window.view is not None:
            Lp().window.view.set_search_mode()

    def __on_search_short(self, args):
        """
            Show search popover
            @param args as []
        """
        self.__next_was_inhibited = self.__next_popover.inhibited
        self.__next_popover.hide()
        self.__next_popover.inhibit(True)
        if self.__search is None:
            from lollypop.pop_search import SearchPopover
            self.__search = SearchPopover()
            self.__search.connect("closed", self.__on_popover_closed)
        self.__search.set_relative_to(self.__search_button)
        self.__search.show()

    def __set_icon(self):
        """
            Set shuffle icon
        """
        shuffle = Lp().settings.get_enum("shuffle")
        repeat = Lp().settings.get_enum("playback")
        if repeat == NextContext.REPEAT_TRACK:
            self.__shuffle_image.get_style_context().remove_class("selected")
            self.__shuffle_image.set_from_icon_name(
                "media-playlist-repeat-song-symbolic",
                Gtk.IconSize.SMALL_TOOLBAR)
        elif shuffle == Shuffle.NONE:
            self.__shuffle_image.get_style_context().remove_class("selected")
            if repeat == NextContext.NONE:
                self.__shuffle_image.set_from_icon_name(
                    "media-playlist-repeat-symbolic",
                    Gtk.IconSize.SMALL_TOOLBAR)
            else:
                self.__shuffle_image.set_from_icon_name(
                    "media-playlist-consecutive-symbolic",
                    Gtk.IconSize.SMALL_TOOLBAR)
        else:
            self.__shuffle_image.set_from_icon_name(
                "media-playlist-shuffle-symbolic",
                Gtk.IconSize.SMALL_TOOLBAR)
            if shuffle == Shuffle.TRACKS:
                self.__shuffle_image.get_style_context().add_class("selected")
            else:
                self.__shuffle_image.get_style_context().remove_class(
                                                                    "selected")

    def __activate_party_button(self, action=None, param=None):
        """
            Activate party button
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
        """
        self.__party_button.set_active(not self.__party_button.get_active())
        Lp().window.responsive_design()

    def __activate_shuffle_button(self, action=None, param=None):
        """
            Activate shuffle button
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
        """
        self.__shuffle_button.set_active(
            not self.__shuffle_button.get_active())

    def __on_lock_changed(self, player):
        """
            Lock toolbar
            @param player as Player
        """
        self.__party_button.set_sensitive(not player.locked)
        self.__list_button.set_sensitive(not player.locked)
        self.__shuffle_button.set_sensitive(not player.locked)

    def __on_playback_changed(self, settings, value):
        """
            Update shuffle icon
            @param settings as Gio.Settings, value as str
        """
        self.__set_icon()
        self.__next_popover.hide()

    def __on_party_changed(self, player, is_party):
        """
            On party change, sync toolbar
            @param player as Player
            @param is party as bool
        """
        if self.__party_button.get_active() != is_party:
            self.__activate_party_button()

    def __on_list_popover_closed(self, popover):
        """
            Reset variable
            @param popover as Gtk.Popover
        """
        self.__list_popover = None
        self.__on_popover_closed(popover)

    def __on_popover_closed(self, popover):
        """
            Restore next popover if needed
            @param popover as Gtk.Popover
        """
        if not self.__next_was_inhibited:
            self.__next_popover.inhibit(False)
        if self.__next_popover.should_be_shown():
            self.__next_popover.set_relative_to(self.__grid_next)
            self.__next_popover.show()

    def __on_show(self, widget):
        """
            Show popover if needed
            @param widget as Gtk.Widget
        """
        self.__set_icon()

    def __on_hide(self, widget):
        """
            Hide popover
            @param widget as Gtk.Widget
        """
        self.__next_popover.hide()

    def __on_list_button_query_tooltip(self, widget, x, y, keyboard, tooltip):
        """
            Show tooltip
            @param widget as Gtk.Widget
            @param x as int
            @param y as int
            @param keyboard as bool
            @param tooltip as Gtk.Tooltip
        """
        if Lp().player.current_track.id == Type.EXTERNALS:
            widget.set_tooltip_text(_("External tracks"))
        elif Lp().player.queue:
            widget.set_tooltip_text(_("Queue"))
        elif Lp().player.get_user_playlist_ids():
            widget.set_tooltip_text(_("Playing playlists"))
        else:
            widget.set_tooltip_text(_("Playing albums"))
