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

from gi.repository import Gtk, Gio, GLib

from gettext import gettext as _

from lollypop.pop_next import NextPopover
from lollypop.define import App, Shuffle, Type, NextContext


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
        size = App().window.get_size()
        self.set_size_request(-1,
                              size[1] * 0.6)

        genres = App().genres.get()
        genres.insert(0, (Type.POPULARS, _("Populars")))
        genres.insert(1, (Type.RECENTS, _("Recently added")))
        ids = App().player.get_party_ids()
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
            party_grid.attach(switch, x + 1, i, 1, 1)
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
        ids = App().player.get_party_ids()
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
        App().settings.set_value("party-ids", GLib.Variant("ai", ids))
        App().player.set_party_ids()
        App().player.set_next()


class ToolbarEnd(Gtk.Bin):
    """
        Toolbar end
    """

    def __init__(self):
        """
            Init toolbar
        """
        Gtk.Bin.__init__(self)
        self.set_hexpand(True)
        self.__search = None
        self.__timeout_id = None
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/ToolbarEnd.ui")
        builder.connect_signals(self)

        self.add(builder.get_object("end"))

        # Map some settings to actions, can't use Gio.Settings.create_action()
        # because API does not support set_enabled()
        self.__shuffle_action = Gio.SimpleAction.new_stateful(
            "shuffle",
            GLib.VariantType.new("s"),
            GLib.Variant("s", "none"))
        self.__shuffle_action.connect("change-state",
                                      self.__on_shuffle_change_state)
        self.__playback_action = Gio.SimpleAction.new_stateful(
            "playback",
            GLib.VariantType.new("s"),
            GLib.Variant("s", "none"))
        self.__playback_action.connect("change-state",
                                       self.__on_playback_change_state)
        App().add_action(self.__shuffle_action)
        App().add_action(self.__playback_action)

        self.__shuffle_button = builder.get_object("shuffle-button")
        self.__shuffle_image = builder.get_object("shuffle-button-image")
        shuffle_button_action = Gio.SimpleAction.new("shuffle-button", None)
        shuffle_button_action.connect("activate",
                                      self.__on_shuffle_button_activate)
        App().add_action(shuffle_button_action)
        App().set_accels_for_action("app.shuffle-button", ["<Control>r"])
        App().settings.connect("changed::shuffle", self.__on_playback_changed)
        App().settings.connect("changed::playback", self.__on_playback_changed)

        self.__party_button = builder.get_object("party-button")
        party_action = Gio.SimpleAction.new_stateful(
            "party",
            None,
            GLib.Variant.new_boolean(App().player.is_party))
        party_action.connect("change-state", self.__on_party_mode_change_state)
        App().add_action(party_action)
        App().set_accels_for_action("app.party", ["<Control>p"])
        self.__next_popover = NextPopover()
        self.__next_popover.set_relative_to(self.__party_button)

        self.__search_button = builder.get_object("search-button")
        self.__gesture = Gtk.GestureLongPress.new(self.__search_button)
        self.__gesture.connect("pressed", self.__on_search_button_pressed)
        self.__gesture.connect("cancelled", self.__on_search_button_cancelled)
        search_action = Gio.SimpleAction.new("search", None)
        search_action.connect(
            "activate",
            lambda x, y: self.__on_search_button_cancelled(self.__gesture))
        App().add_action(search_action)
        App().set_accels_for_action("app.search", ["<Control>f"])

        self.__settings_button = builder.get_object("settings-button")

        self.__list_button = builder.get_object("list-button")
        self.__list_button.set_property("has-tooltip", True)
        self.__list_button.connect("query-tooltip",
                                   self.__on_list_button_query_tooltip)
        self.__list_popover = None
        App().player.connect("lock-changed", self.__on_lock_changed)

    def do_show(self):
        self.__set_shuffle_icon()
        Gtk.Bin.do_show(self)

    def do_hide(self):
        self.__next_popover.hide()
        Gtk.Bin.do_hide(self)

    def set_minimal(self, b):
        """
            Set minimal, hide some widget for minimal player
            @param b as bool
        """
        if b:
            self.__list_button.hide()
            self.__next_popover.hide()
        else:
            self.__list_button.show()
            if self.__next_popover.should_be_shown():
                self.__next_popover.show()

    def setup_menu(self, menu):
        """
            Add an application menu to menu button
            @parma: menu as Gio.Menu
        """
        self.__settings_button.set_menu_model(menu)

    def on_next_changed(self, player):
        """
            Show next popover
            @param player as Player
        """
        if self.__next_popover.should_be_shown():
            if self.__next_popover.is_visible():
                self.__next_popover.update()
            else:
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

    def show_list_popover(self, button):
        """
            Show a popover with current playlist
            @param button as Gtk.Button
        """
        if App().player.queue:
            from lollypop.pop_queue import QueuePopover
            popover = QueuePopover()
        elif App().player.get_playlist_ids():
            from lollypop.pop_playlists import PlaylistsPopover
            popover = PlaylistsPopover()
        else:
            from lollypop.pop_albums import AlbumsPopover
            popover = AlbumsPopover()
        popover.set_relative_to(button)
        popover.show()
        return popover

#######################
# PROTECTED           #
#######################
    def _on_list_button_clicked(self, widget, unused=None):
        """
            Show current playback context popover
            @param widget as Gtk.Widget
        """
        if self.__list_popover is not None:
            return
        self.__next_popover.hide()
        self.__next_popover.inhibit(True)
        self.__list_popover = self.show_list_popover(widget)
        self.__list_popover.connect("closed", self.__on_list_popover_closed)
        return True

#######################
# PRIVATE             #
#######################
    def __on_search_button_pressed(self, gesture, x, y):
        """
            Show filtering
            @param gesture as Gtk.GestureLongPress
            @param x as float
            @param y as float
        """
        if App().window.container.view is not None:
            App().window.container.view.enable_filter()

    def __on_search_button_cancelled(self, gesture):
        """
            Show search popover
            @param gesture as Gtk.GestureLongPress
        """
        self.__next_popover.hide()
        self.__next_popover.inhibit(True)
        if self.__search is None:
            from lollypop.pop_search import SearchPopover
            self.__search = SearchPopover()
            self.__search.connect("closed", self.__on_popover_closed)
        self.__search.set_relative_to(self.__search_button)
        self.__search.show()

    def __set_shuffle_icon(self):
        """
            Set shuffle icon
        """
        shuffle = App().settings.get_enum("shuffle")
        repeat = App().settings.get_enum("playback")
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

    def __on_party_mode_change_state(self, action, value):
        """
            Activate party mode
            @param action as Gio.SimpleAction
            @param value as bool
        """
        if not App().gtk_application_prefer_dark_theme and\
                not App().settings.get_value("dark-ui"):
            settings = Gtk.Settings.get_default()
            settings.set_property("gtk-application-prefer-dark-theme", value)
        App().player.set_party(value)
        action.set_state(value)
        self.__shuffle_action.set_enabled(not value)
        self.__playback_action.set_enabled(not value)
        self.on_next_changed(App().player)

    def __on_shuffle_change_state(self, action, value):
        """
            Update shuffle setting
            @param action as Gio.SimpleAction
            @param value as bool
        """
        App().settings.set_value("shuffle", value)
        action.set_state(value)

    def __on_playback_change_state(self, action, value):
        """
            Update playback setting
            @param action as Gio.SimpleAction
            @param value as bool
        """
        App().settings.set_value("playback", value)
        action.set_state(value)

    def __on_shuffle_button_activate(self, action, param):
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
        self.__set_shuffle_icon()
        self.__next_popover.hide()

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
        self.__next_popover.inhibit(False)
        if self.__next_popover.should_be_shown():
            self.__next_popover.show()

    def __on_list_button_query_tooltip(self, widget, x, y, keyboard, tooltip):
        """
            Show tooltip
            @param widget as Gtk.Widget
            @param x as int
            @param y as int
            @param keyboard as bool
            @param tooltip as Gtk.Tooltip
        """
        if App().player.queue:
            widget.set_tooltip_text(_("Queue"))
        elif App().player.get_playlist_ids():
            widget.set_tooltip_text(_("Playing playlists"))
        else:
            widget.set_tooltip_text(_("Playing albums"))
