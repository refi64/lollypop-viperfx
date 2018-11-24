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

from gi.repository import Gio, GLib, Gtk

from lollypop.define import App
from lollypop.settings import SettingsDialog


class ApplicationActions:
    """
        Application actions
    """

    def __init__(self):
        """
            Init actions
        """
        settings_action = Gio.SimpleAction.new("settings", None)
        settings_action.connect("activate", self.__on_settings_activate)
        App().add_action(settings_action)

        update_action = Gio.SimpleAction.new("update_db", None)
        update_action.connect("activate", self.__on_update_db_activate)
        App().add_action(update_action)

        fullscreen_action = Gio.SimpleAction.new("fullscreen", None)
        App().player.connect("current-changed",
                             self.__on_current_changed,
                             fullscreen_action)
        fullscreen_action.set_enabled(False)
        fullscreen_action.connect("activate", self.__on_fullscreen_activate)
        App().add_action(fullscreen_action)

        show_sidebar = App().settings.get_value("show-sidebar")
        sidebar_action = Gio.SimpleAction.new_stateful(
            "sidebar",
            None,
            GLib.Variant.new_boolean(show_sidebar))
        sidebar_action.connect("change-state", self.__on_sidebar_change_state)
        App().add_action(sidebar_action)

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.__on_about_activate)
        App().add_action(about_action)

        shortcuts_action = Gio.SimpleAction.new("shortcuts", None)
        shortcuts_action.connect("activate", self.__on_shortcuts_activate)
        App().add_action(shortcuts_action)

        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda x, y: App().quit(True))
        App().add_action(quit_action)

#######################
# PRIVATE             #
#######################
    def __on_update_db_activate(self, action=None, param=None):
        """
            Search for new music
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
        """
        if App().window:
            App().task_helper.run(App().art.clean_all_cache)
            App().scanner.update()

    def __on_about_activate_response(self, dialog, response_id):
        """
            Destroy about dialog when closed
            @param dialog as Gtk.Dialog
            @param response id as int
        """
        dialog.destroy()

    def __on_sidebar_change_state(self, action, value):
        """
            Show/hide sidebar
            @param action as Gio.SimpleAction
            @param value as bool
        """
        action.set_state(value)
        App().settings.set_value("show-sidebar",
                                 GLib.Variant("b", value))
        App().window.container.show_sidebar(value)

    def __on_fullscreen_activate(self, action, param):
        """
            Show a fullscreen window with cover and artist information
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
        """
        if App().window.is_visible():
            from lollypop.fullscreen import FullScreen
            fs = FullScreen(App())
            fs.show()

    def __on_settings_activate(self, action, param):
        """
            Show settings dialog
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
        """
        dialog = SettingsDialog()
        dialog.show()

    def __on_about_activate(self, action, param):
        """
            Setup about dialog
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
        """
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/AboutDialog.ui")
        about = builder.get_object("about_dialog")
        about.set_transient_for(App().window)
        about.connect("response", self.__on_about_activate_response)
        about.show()

    def __on_shortcuts_activate(self, action, param):
        """
            Show shorctus
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
        """
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/Shortcuts.ui")
        builder.get_object("shortcuts").set_transient_for(App().window)
        builder.get_object("shortcuts").show()

    def __on_current_changed(self, player, action):
        """
            Activate action if wanted
            @param player as Player
            @param action as Gio.SimpleAction
        """
        action.set_enabled(not App().player.current_track.id is None)
