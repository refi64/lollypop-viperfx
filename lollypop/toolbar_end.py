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
from lollypop.define import App, Shuffle, NextContext, Type


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
        self.__search_popover = None
        self.__timeout_id = None
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/ToolbarEnd.ui")
        builder.connect_signals(self)

        self.__party_submenu = builder.get_object("party_submenu")
        self.add(builder.get_object("end"))

        # Map some settings to actions, can't use Gio.Settings.create_action()
        # because API does not support set_enabled()
        self.__shuffle_action = Gio.SimpleAction.new_stateful(
            "shuffle",
            GLib.VariantType.new("s"),
            GLib.Variant("s", "none"))
        self.__shuffle_action.set_state(App().settings.get_value("shuffle"))
        self.__shuffle_action.connect("change-state",
                                      self.__on_shuffle_change_state)
        self.__playback_action = Gio.SimpleAction.new_stateful(
            "playback",
            GLib.VariantType.new("s"),
            GLib.Variant("s", "none"))
        self.__playback_action.set_state(App().settings.get_value("playback"))
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

        party_action = Gio.SimpleAction.new_stateful(
            "party",
            None,
            GLib.Variant.new_boolean(App().player.is_party))
        party_action.connect("change-state", self.__on_party_mode_change_state)
        App().add_action(party_action)
        App().set_accels_for_action("app.party", ["<Control>p"])

        scrobbling_disabled = App().settings.get_value("disable-scrobbling")
        scrobbling_action = Gio.SimpleAction.new_stateful(
            "scrobbling",
            None,
            GLib.Variant.new_boolean(not scrobbling_disabled))
        scrobbling_action.connect("change-state",
                                  self.__on_scrobbling_mode_change_state)
        App().add_action(scrobbling_action)
        App().set_accels_for_action("app.scrobbling", ["<Control><Shift>s"])

        self.__next_popover = NextPopover()
        self.__next_popover.set_relative_to(self.__shuffle_button)

        search_action = Gio.SimpleAction.new("search", None)
        self.__search_button = builder.get_object("search-button")
        search_action.connect("activate", self.__on_search_activate)
        App().add_action(search_action)
        App().set_accels_for_action("app.search", ["<Control>f"])

        builder_menu = Gtk.Builder()
        builder_menu.add_from_resource("/org/gnome/Lollypop/Appmenu.ui")
        builder.get_object("settings-button").set_menu_model(
            builder_menu.get_object("app-menu"))

        self.__list_button = builder.get_object("list-button")
        self.__list_button.set_property("has-tooltip", True)
        self.__list_button.connect("query-tooltip",
                                   self.__on_list_button_query_tooltip)
        self.__list_popover = None
        App().player.connect("playlist-changed", self.__on_playlist_changed)
        self.__set_shuffle_icon()

    def on_next_changed(self, player):
        """
            Show next popover
            @param player as Player
        """
        if self.__next_popover.should_be_shown():
            if self.__next_popover.is_visible():
                self.__next_popover.update()
            else:
                self.__next_popover.popup()
        else:
            self.__next_popover.hide()

    def set_mini(self, mini):
        """
            Set mini mode
            @param mini as bool
        """
        if mini:
            self.__search_button.hide()
            self.__list_button.hide()
        else:
            self.__search_button.show()
            self.__list_button.show()

    def search(self, search):
        """
            Search item
            @param search as str
        """
        self.__on_search_button_cancelled()
        self.__search_popover.set_text(search)

    @property
    def next_popover(self):
        """
            Get next popover
            @return popover
        """
        return self.__next_popover

#######################
# PROTECTED           #
#######################
    def _on_list_button_toggled(self, button):
        """
            Show current playback context popover
            @param button as Gtk.MenuButton
        """
        if not button.get_active():
            return
        self.__next_popover.hide()
        self.__next_popover.inhibit(True)
        if App().player.queue:
            from lollypop.pop_queue import QueuePopover
            popover = QueuePopover()
        elif App().player.playlist_ids:
            from lollypop.pop_playlists import PlaylistsPopover
            popover = PlaylistsPopover()
        else:
            from lollypop.pop_albums import AlbumsPopover
            popover = AlbumsPopover()
        popover.set_relative_to(button)
        popover.popup()
        popover.connect("closed", self.__on_popover_closed, button)
        return True

    def _on_search_button_toggled(self, button):
        """
            Show search popover
            @param button as Gtk.Button
        """
        if not button.get_active():
            self.__search_popover.popdown()
            return
        self.__next_popover.hide()
        self.__next_popover.inhibit(True)
        if self.__search_popover is None:
            from lollypop.pop_search import SearchPopover
            self.__search_popover = SearchPopover()
            self.__search_popover.connect("closed",
                                          self.__on_popover_closed,
                                          button)
        self.__search_popover.set_relative_to(button)
        self.__search_popover.popup()
        return True

    def _on_shuffle_button_toggled(self, button):
        """
           Create submenu
           @param button as Gtk.MenuButton
        """
        if button.get_active():
            # Create submenu "Configure party mode"
            self.__party_submenu.remove_all()
            self.__init_party_submenu()
            self.__next_popover.hide()
            self.__next_popover.inhibit(True)
        else:
            self.__next_popover.inhibit(False)
            if self.__next_popover.should_be_shown():
                self.__next_popover.popup()

    def _on_settings_button_toggled(self, button):
        """
           Create submenu
           @param button as Gtk.MenuButton
        """
        if button.get_active():
            self.__next_popover.hide()
            self.__next_popover.inhibit(True)
        else:
            self.__next_popover.inhibit(False)
            if self.__next_popover.should_be_shown():
                self.__next_popover.popup()

#######################
# PRIVATE             #
#######################
    def __init_party_submenu(self):
        """
            Init party submenu with current ids
        """
        def on_change_state(action, value, genre_id):
            action.set_state(value)
            ids = list(App().settings.get_value("party-ids"))
            genre_ids = App().genres.get_ids()
            # Select all
            if genre_id is None:
                # Update others
                for genre_id in genre_ids:
                    action = App().lookup_action("genre_%s" % genre_id)
                    if action.get_state() != value:
                        action.set_state(value)
                ids = []
            # Party id added
            elif value:
                ids.append(genre_id)
            # Party id removed
            elif ids and len(party_ids) > 1:
                ids.remove(genre_id)
            # Initial value
            else:
                genre_ids.remove(genre_id)
            App().settings.set_value("party-ids", GLib.Variant("ai", ids))
            App().player.set_party_ids()
            App().player.set_next()

        party_ids = App().settings.get_value("party-ids")
        all_ids = App().genres.get_ids()
        all_selected = len(set(all_ids) & set(party_ids)) == len(all_ids) or\
            not party_ids
        action = Gio.SimpleAction.new_stateful(
                    "all_party_ids",
                    None,
                    GLib.Variant.new_boolean(all_selected))
        action.connect("change-state", on_change_state, None)
        App().add_action(action)
        item = Gio.MenuItem.new(_("All genres"), "app.all_party_ids")
        self.__party_submenu.append_item(item)
        i = 0
        # Hack, hack, hack
        submenu_name = _("Next")
        menu = self.__party_submenu
        for (genre_id, name, sortname) in App().genres.get():
            in_party_ids = not party_ids or genre_id in party_ids
            action_name = "genre_%s" % genre_id
            action = Gio.SimpleAction.new_stateful(
                action_name,
                None,
                GLib.Variant.new_boolean(in_party_ids))
            action.connect("change-state", on_change_state, genre_id)
            App().add_action(action)
            item = Gio.MenuItem.new(name, "app.%s" % action_name)
            menu.append_item(item)
            if i > 10:
                submenu = Gio.Menu()
                item = Gio.MenuItem.new(submenu_name, None)
                submenu_name += " "
                item.set_submenu(submenu)
                menu.append_item(item)
                menu = submenu
                i = 0
            i += 1

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
        App().player.set_party(value.get_boolean())
        action.set_state(value)
        self.__shuffle_action.set_enabled(not value)
        self.__playback_action.set_enabled(not value)
        self.on_next_changed(App().player)

    def __on_scrobbling_mode_change_state(self, action, value):
        """
            Change scrobbling option
            @param action as Gio.SimpleAction
            @param value as bool
        """
        action.set_state(value)
        App().settings.set_value("disable-scrobbling",
                                 GLib.Variant("b", not value))

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

    def __on_playback_changed(self, settings, value):
        """
            Update shuffle icon
            @param settings as Gio.Settings, value as str
        """
        self.__set_shuffle_icon()
        self.__next_popover.hide()

    def __on_popover_closed(self, popover, button):
        """
            Restore next popover if needed
            @param popover as Popover
            @param button as Gtk.Button
        """
        button.set_active(False)
        self.__next_popover.inhibit(False)
        if self.__next_popover.should_be_shown():
            self.__next_popover.popup()

    def __on_search_activate(self, action, variant):
        """
            @param action as Gio.SimpleAction
            @param variant as GLib.Variant
        """
        if self.__search_button.get_visible():
            self.__search_button.set_active(
                not self.__search_button.get_active())
        else:
            App().window.container.show_view(Type.SEARCH)

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
        elif App().player.playlist_ids:
            widget.set_tooltip_text(_("Playing playlists"))
        else:
            widget.set_tooltip_text(_("Playing albums"))

    def __on_playlist_changed(self, player):
        """
            Update playback button status
            @param player as Player
        """
        if player.albums or player.playlist_ids or player.queue:
            self.__list_button.set_sensitive(True)
        else:
            self.__list_button.set_sensitive(False)
