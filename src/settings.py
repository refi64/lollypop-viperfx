#!/usr/bin/python
# Copyright (c) 2014-2015 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import Gtk, GLib, Gio, Pango
try:
    from gi.repository import Secret
except:
    Secret = None


from gettext import gettext as _
from _thread import start_new_thread

from lollypop.define import Lp, Type, SecretSchema, SecretAttributes
from lollypop.utils import use_csd


# Lollypop settings
class Settings(Gio.Settings):
    """
        Init settings
    """
    def __init__(self):
        Gio.Settings.__init__(self)

    """
        Return a new Settings object
    """
    def new():
        settings = Gio.Settings.new('org.gnome.Lollypop')
        settings.__class__ = Settings
        return settings

    """
        Return music paths
        @return [str]
    """
    def get_music_paths(self):
        paths = self.get_value('music-path')
        if not paths:
            if GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_MUSIC):
                paths = [GLib.get_user_special_dir(
                    GLib.UserDirectory.DIRECTORY_MUSIC)]
            else:
                print("You need to add a music path"
                      " to org.gnome.Lollypop in dconf")
        return paths


# Dialog showing lollypop options
class SettingsDialog:

    def __init__(self):

        self._choosers = []

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/SettingsDialog.ui')

        self._settings_dialog = builder.get_object('settings_dialog')
        self._settings_dialog.set_transient_for(Lp.window)

        if use_csd():
            self._settings_dialog.set_titlebar(
                builder.get_object('header_bar'))

        switch_scan = builder.get_object('switch_scan')
        switch_scan.set_state(Lp.settings.get_value('auto-update'))

        switch_view = builder.get_object('switch_dark')
        switch_view.set_state(Lp.settings.get_value('dark-ui'))

        switch_background = builder.get_object('switch_background')
        switch_background.set_state(Lp.settings.get_value('background-mode'))

        switch_state = builder.get_object('switch_state')
        switch_state.set_state(Lp.settings.get_value('save-state'))

        switch_autoplay = builder.get_object('switch_autoplay')
        switch_autoplay.set_state(Lp.settings.get_value('auto-play'))

        switch_genres = builder.get_object('switch_genres')
        switch_genres.set_state(Lp.settings.get_value('show-genres'))

        self._settings_dialog.connect('destroy', self._edit_settings_close)

        builder.connect_signals(self)

        main_chooser_box = builder.get_object('main_chooser_box')
        self._chooser_box = builder.get_object('chooser_box')
        party_grid = builder.get_object('party_grid')

        #
        # Music tab
        #
        dirs = []
        for directory in Lp.settings.get_value('music-path'):
            dirs.append(directory)

        # Main chooser
        self._main_chooser = ChooserWidget()
        image = Gtk.Image.new_from_icon_name("list-add-symbolic",
                                             Gtk.IconSize.MENU)
        self._main_chooser.set_icon(image)
        self._main_chooser.set_action(self._add_chooser)
        main_chooser_box.pack_start(self._main_chooser, False, True, 0)
        if len(dirs) > 0:
            path = dirs.pop(0)
        else:
            path = GLib.get_user_special_dir(
                GLib.UserDirectory.DIRECTORY_MUSIC)
        self._main_chooser.set_dir(path)

        # Others choosers
        for directory in dirs:
            self._add_chooser(directory)

        #
        # Party mode tab
        #
        genres = Lp.genres.get()
        genres.insert(0, (Type.POPULARS, _("Populars")))
        genres.insert(1, (Type.RECENTS, _("Recents")))
        ids = Lp.player.get_party_ids()
        i = 0
        x = 0
        for genre_id, genre in genres:
            label = Gtk.Label()
            label.set_property('margin-start', 10)
            label.set_property('halign', Gtk.Align.START)
            label.set_property('hexpand', True)
            label.set_ellipsize(Pango.EllipsizeMode.END)
            label.set_text(genre)
            label.show()
            switch = Gtk.Switch()
            if genre_id in ids:
                switch.set_state(True)
            switch.connect("state-set", self._party_switch_state, genre_id)
            switch.set_property('margin-end', 50)
            switch.show()
            party_grid.attach(label, x, i, 1, 1)
            party_grid.attach(switch, x+1, i, 1, 1)
            if x == 0:
                x += 2
            else:
                i += 1
                x = 0
        #
        # Last.fm tab
        #
        if Lp.lastfm is not None and Secret is not None:
            self._test_img = builder.get_object('test_img')
            self._login = builder.get_object('login')
            self._password = builder.get_object('password')
            schema = Secret.Schema.new("org.gnome.Lollypop",
                                       Secret.SchemaFlags.NONE,
                                       SecretSchema)
            Secret.password_lookup(schema, SecretAttributes, None,
                                   self._on_password_lookup)
            builder.get_object('lastfm_grid').set_sensitive(True)
            self._login.set_text(
                Lp.settings.get_value('lastfm-login').get_string())

    """
        Show dialog
    """
    def show(self):
        self._settings_dialog.show()

#######################
# PRIVATE             #
#######################

    """
        Add a new chooser widget
        @param directory path as string
    """
    def _add_chooser(self, directory=None):
        chooser = ChooserWidget()
        image = Gtk.Image.new_from_icon_name("list-remove-symbolic",
                                             Gtk.IconSize.MENU)
        chooser.set_icon(image)
        if directory:
            chooser.set_dir(directory)
        self._chooser_box.add(chooser)

    """
        Update view setting
        @param widget as unused, state as widget state
    """
    def _update_ui_setting(self, widget, state):
        Lp.settings.set_value('dark-ui', GLib.Variant('b', state))
        if not Lp.player.is_party():
            settings = Gtk.Settings.get_default()
            settings.set_property("gtk-application-prefer-dark-theme", state)
            Lp.window.update_view()

    """
        Update scan setting
        @param widget as unused, state as widget state
    """
    def _update_scan_setting(self, widget, state):
        Lp.settings.set_value('auto-update',
                              GLib.Variant('b', state))

    """
        Update background mode setting
        @param widget as unused, state as widget state
    """
    def _update_background_setting(self, widget, state):
        Lp.settings.set_value('background-mode',
                              GLib.Variant('b', state))

    """
        Update save state setting
        @param widget as unused, state as widget state
    """
    def _update_state_setting(self, widget, state):
        Lp.settings.set_value('save-state',
                              GLib.Variant('b', state))
    """
        Update show genre setting
        @param widget as unused, state as widget state
    """
    def _update_genres_setting(self, widget, state):
        Lp.window.show_genres(state)
        Lp.settings.set_value('show-genres',
                              GLib.Variant('b', state))

    """
        Update auto play setting
        @param widget as unused, state as widget state
    """
    def _update_autoplay_setting(self, widget, state):
        Lp.settings.set_value('auto-play',
                              GLib.Variant('b', state))

    """
        Update lastfm settings
        @param sync as bool
    """
    def _update_lastfm_settings(self, sync=False):
        if Lp.lastfm is not None and Secret is not None:
            schema = Secret.Schema.new("org.gnome.Lollypop",
                                       Secret.SchemaFlags.NONE,
                                       SecretSchema)
            Secret.password_store_sync(schema, SecretAttributes,
                                       Secret.COLLECTION_DEFAULT,
                                       "org.gnome.Lollypop.lastfm.login %s" %
                                       self._login.get_text(),
                                       self._password.get_text(),
                                       None)
            Lp.settings.set_value('lastfm-login',
                                  GLib.Variant('s', self._login.get_text()))
            if sync:
                Lp.lastfm.connect_sync(self._password.get_text())
            else:
                Lp.lastfm.connect(self._password.get_text())

    """
        Close edit party dialog
        @param widget as Gtk.Window
    """
    def _edit_settings_close(self, widget):
        # Music path
        paths = []
        main_path = self._main_chooser.get_dir()
        choosers = self._chooser_box.get_children()
        if main_path == GLib.get_user_special_dir(
            GLib.UserDirectory.DIRECTORY_MUSIC)\
           and not choosers:
            paths = []
        else:
            paths.append(main_path)
            for chooser in choosers:
                path = chooser.get_dir()
                if path is not None and path not in paths:
                    paths.append(path)

        previous = Lp.settings.get_value('music-path')
        Lp.settings.set_value('music-path', GLib.Variant('as', paths))

        # Last.fm
        self._update_lastfm_settings()

        self._settings_dialog.hide()
        self._settings_dialog.destroy()
        if set(previous) != set(paths):
            Lp.window.update_db()

    """
        Update party ids when use change a switch in dialog
        @param widget as unused, state as widget state, genre id as int
    """
    def _party_switch_state(self, widget, state, genre_id):
        ids = Lp.player.get_party_ids()
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
        Lp.settings.set_value('party-ids',  GLib.Variant('ai', ids))

    """
        Test lastfm connection
        @param button as Gtk.Button
    """
    def _on_test_btn_clicked(self, button):
        self._update_lastfm_settings(True)
        if not Gio.NetworkMonitor.get_default().get_network_available():
            self._test_img.set_from_icon_name('computer-fail-symbolic',
                                              Gtk.IconSize.MENU)
            return
        start_new_thread(self._test_lastfm_connection, ())

    """
        Test lastfm connection
        @thread safe
    """
    def _test_lastfm_connection(self):
        try:
            u = Lp.lastfm.get_authenticated_user()
            u.get_id()
            GLib.idle_add(self._test_img.set_from_icon_name,
                          'object-select-symbolic',
                          Gtk.IconSize.MENU)
        except:
            GLib.idle_add(self._test_img.set_from_icon_name,
                          'computer-fail-symbolic',
                          Gtk.IconSize.MENU)

    """
        Set password entry
        @param source as GObject.Object
        @param result Gio.AsyncResult
    """
    def _on_password_lookup(self, source, result):
        password = None
        if result is not None:
            password = Secret.password_lookup_finish(result)
        if password is not None:
            self._password.set_text(password)


# Widget used to let user select a collection folder
class ChooserWidget(Gtk.Grid):
    def __init__(self):
        Gtk.Grid.__init__(self)
        self._action = None
        self.set_property("orientation", Gtk.Orientation.HORIZONTAL)
        self.set_property("halign", Gtk.Align.CENTER)
        self._chooser_btn = Gtk.FileChooserButton()
        self._chooser_btn.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        self._chooser_btn.set_property("margin", 5)
        self._chooser_btn.show()
        self.add(self._chooser_btn)
        self._action_btn = Gtk.Button()
        self._action_btn.set_property("margin", 5)
        self._action_btn.show()
        self.add(self._action_btn)
        self._action_btn.connect("clicked", self._do_action)
        self.show()

    """
        Set current selected path for chooser
        @param directory path as string
    """
    def set_dir(self, path):
        if path:
            self._chooser_btn.set_uri("file://"+path)

    """
        Set image for action button
        @param Gtk.Image
    """
    def set_icon(self, image):
        self._action_btn.set_image(image)

    """
        Set action callback for button clicked signal
        @param func
    """
    def set_action(self, action):
        self._action = action

    """
        Return select directory path
        @return path as string
    """
    def get_dir(self):
        path = None
        uri = self._chooser_btn.get_uri()
        if uri is not None:
            path = GLib.uri_unescape_string(uri, None)
        if path is not None:
            return path[7:]
        else:
            return None

#######################
# PRIVATE             #
#######################
    """
        If action defined, execute, else, remove widget
    """
    def _do_action(self, widget):
        if self._action:
            self._action()
        else:
            self.destroy()
