# Copyright (c) 2014-2016 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import Gtk, Gdk, GLib, Gio, Pango
try:
    from gi.repository import Secret
except:
    Secret = None


from gettext import gettext as _
from threading import Thread
from shutil import which
from re import findall, DOTALL

from lollypop.define import Lp, SecretSchema, SecretAttributes
from lollypop.cache import InfoCache


class Settings(Gio.Settings):
    """
        Lollypop settings
    """

    def __init__(self):
        """
            Init settings
        """
        Gio.Settings.__init__(self)

    def new():
        """
            Return a new Settings object
        """
        settings = Gio.Settings.new('org.gnome.Lollypop')
        settings.__class__ = Settings
        return settings

    def get_music_paths(self):
        """
            Return music paths
            @return [str]
        """
        paths = self.get_value('music-path')
        if not paths:
            if GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_MUSIC):
                paths = [GLib.get_user_special_dir(
                    GLib.UserDirectory.DIRECTORY_MUSIC)]
            else:
                print("You need to add a music path"
                      " to org.gnome.Lollypop in dconf")
        return paths


class SettingsDialog:
    """
        Dialog showing lollypop options
    """

    def __init__(self):
        """
            Init dialog
        """
        self._choosers = []
        self._cover_tid = None
        self._mix_tid = None
        self._popover = None

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/SettingsDialog.ui')
        if Lp().lastfm and not Lp().lastfm.is_goa:
            builder.get_object('lastfm_grid').show()
        self._popover_content = builder.get_object('popover')
        duration = builder.get_object('duration')
        duration.set_range(1, 20)
        duration.set_value(Lp().settings.get_value('mix-duration').get_int32())

        self._settings_dialog = builder.get_object('settings_dialog')
        self._settings_dialog.set_transient_for(Lp().window)

        if Lp().settings.get_value('disable-csd'):
            self._settings_dialog.set_title(_("Preferences"))
        else:
            headerbar = builder.get_object('header_bar')
            headerbar.set_title(_("Preferences"))
            self._settings_dialog.set_titlebar(headerbar)

        switch_scan = builder.get_object('switch_scan')
        switch_scan.set_state(Lp().settings.get_value('auto-update'))

        switch_view = builder.get_object('switch_dark')
        switch_view.set_state(Lp().settings.get_value('dark-ui'))

        switch_background = builder.get_object('switch_background')
        switch_background.set_state(Lp().settings.get_value('background-mode'))

        switch_state = builder.get_object('switch_state')
        switch_state.set_state(Lp().settings.get_value('save-state'))

        switch_mix = builder.get_object('switch_mix')
        switch_mix.set_state(Lp().settings.get_value('mix'))

        switch_mix_party = builder.get_object('switch_mix_party')
        switch_mix_party.set_state(Lp().settings.get_value('party-mix'))

        switch_artwork_tags = builder.get_object('switch_artwork_tags')
        if which("kid3-cli") is None:
            switch_artwork_tags.set_sensitive(False)
            switch_artwork_tags.set_tooltip_text(
                                            _("You need to install kid3-cli"))
        else:
            switch_artwork_tags.set_state(
                                      Lp().settings.get_value('artwork-tags'))

        switch_genres = builder.get_object('switch_genres')
        switch_genres.set_state(Lp().settings.get_value('show-genres'))

        switch_compilations = builder.get_object('switch_compilations')
        switch_compilations.set_state(
            Lp().settings.get_value('show-compilations'))

        switch_artwork = builder.get_object('switch_artwork')
        switch_artwork.set_state(Lp().settings.get_value('artist-artwork'))

        switch_repeat = builder.get_object('switch_repeat')
        switch_repeat.set_state(not Lp().settings.get_value('repeat'))

        combo_orderby = builder.get_object('combo_orderby')
        combo_orderby.set_active(Lp().settings.get_enum(('orderby')))

        combo_preview = builder.get_object('combo_preview')

        scale_coversize = builder.get_object('scale_coversize')
        scale_coversize.set_range(150, 300)
        scale_coversize.set_value(
                            Lp().settings.get_value('cover-size').get_int32())
        self._settings_dialog.connect('destroy', self._edit_settings_close)

        builder.connect_signals(self)

        main_chooser_box = builder.get_object('main_chooser_box')
        self._chooser_box = builder.get_object('chooser_box')

        self._set_outputs(combo_preview)

        #
        # Music tab
        #
        dirs = []
        for directory in Lp().settings.get_value('music-path'):
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
        # Last.fm tab
        #
        if Lp().lastfm is not None and Secret is not None:
            self._test_img = builder.get_object('test_img')
            self._login = builder.get_object('login')
            self._password = builder.get_object('password')
            schema = Secret.Schema.new("org.gnome.Lollypop",
                                       Secret.SchemaFlags.NONE,
                                       SecretSchema)
            Secret.password_lookup(schema, SecretAttributes, None,
                                   self._on_password_lookup)
            builder.get_object('lastfm_grid').set_sensitive(True)
            builder.get_object('lastfm_error').hide()
            self._login.set_text(
                Lp().settings.get_value('lastfm-login').get_string())

    def show(self):
        """
            Show dialog
        """
        self._settings_dialog.show()

#######################
# PRIVATE             #
#######################
    def _get_pa_outputs(self):
        """
            Get PulseAudio outputs
            @return name/device as [(str, str)]
        """
        ret = []
        argv = ["pacmd", "list-sinks", None]
        try:
            (s, out, err, e) = GLib.spawn_sync(None, argv, None,
                                               GLib.SpawnFlags.SEARCH_PATH,
                                               None)
            string = out.decode('utf-8')
            devices = findall('name: <([^>]*)>', string, DOTALL)
            names = findall('device.description = "([^"]*)"', string, DOTALL)
            for name in names:
                ret.append((name, devices.pop(0)))
        except Exception as e:
            print("SettingsDialog::_get_pa_outputse()", e)
        return ret

    def _set_outputs(self, combo):
        """
            Set outputs in combo
            @parma combo as Gtk.ComboxBoxText
        """
        current = Lp().settings.get_value('preview-output').get_string()
        renderer = combo.get_cells()[0]
        renderer.set_property('ellipsize', Pango.EllipsizeMode.END)
        renderer.set_property('max-width-chars', 60)
        outputs = self._get_pa_outputs()
        if outputs:
            for output in outputs:
                combo.append(output[1], output[0])
                if output[1] == current:
                    combo.set_active_id(output[1])
        else:
            combo.set_sensitive(False)

    def _add_chooser(self, directory=None):
        """
            Add a new chooser widget
            @param directory path as string
        """
        chooser = ChooserWidget()
        image = Gtk.Image.new_from_icon_name("list-remove-symbolic",
                                             Gtk.IconSize.MENU)
        chooser.set_icon(image)
        if directory:
            chooser.set_dir(directory)
        self._chooser_box.add(chooser)

    def _update_coversize(self, widget):
        """
            Delayed update cover size
            @param widget as Gtk.Range
        """
        if self._cover_tid is not None:
            GLib.source_remove(self._cover_tid)
            self._cover_tid = None
        self._cover_tid = GLib.timeout_add(500,
                                           self._really_update_coversize,
                                           widget)

    def _really_update_coversize(self, widget):
        """
            Update cover size
            @param widget as Gtk.Range
        """
        self._cover_tid = None
        value = widget.get_value()
        Lp().settings.set_value('cover-size', GLib.Variant('i', value))
        Lp().art.update_art_size()
        for suffix in ["lastfm", "wikipedia", "spotify"]:
            for artist in Lp().artists.get([]):
                InfoCache.uncache_artwork(artist[1], suffix,
                                          widget.get_scale_factor())
                Lp().art.emit('artist-artwork-changed', artist[1])
        Lp().window.reload_view()

    def _update_ui_setting(self, widget, state):
        """
            Update view setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        Lp().settings.set_value('dark-ui', GLib.Variant('b', state))
        if not Lp().player.is_party():
            settings = Gtk.Settings.get_default()
            settings.set_property("gtk-application-prefer-dark-theme", state)

    def _update_scan_setting(self, widget, state):
        """
            Update scan setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        Lp().settings.set_value('auto-update',
                                GLib.Variant('b', state))

    def _update_background_setting(self, widget, state):
        """
            Update background mode setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        Lp().settings.set_value('background-mode',
                                GLib.Variant('b', state))

    def _update_state_setting(self, widget, state):
        """
            Update save state setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        Lp().settings.set_value('save-state',
                                GLib.Variant('b', state))

    def _update_genres_setting(self, widget, state):
        """
            Update show genre setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        Lp().window.show_genres(state)
        Lp().settings.set_value('show-genres',
                                GLib.Variant('b', state))

    def _update_mix_setting(self, widget, state):
        """
            Update mix setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        Lp().settings.set_value('mix', GLib.Variant('b', state))
        Lp().player.update_crossfading()
        if state:
            if self._popover is None:
                self._popover = Gtk.Popover.new(widget)
                self._popover.set_modal(False)
                self._popover.add(self._popover_content)
            self._popover.show_all()
        elif self._popover is not None:
            self._popover.hide()

    def _update_party_mix_setting(self, widget, state):
        """
            Update party mix setting
            @param widget as Gtk.Range
        """
        Lp().settings.set_value('party-mix', GLib.Variant('b', state))
        Lp().player.update_crossfading()

    def _update_mix_duration_setting(self, widget):
        """
            Update mix duration setting
            @param widget as Gtk.Range
        """
        value = widget.get_value()
        Lp().settings.set_value('mix-duration', GLib.Variant('i', value))

    def _update_artwork_tags(self, widget, state):
        """
            Update artwork in tags setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        Lp().settings.set_value('artwork-tags', GLib.Variant('b', state))

    def _update_compilations_setting(self, widget, state):
        """
            Update compilations setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        Lp().settings.set_value('show-compilations',
                                GLib.Variant('b', state))

    def _update_artwork_setting(self, widget, state):
        """
            Update artist artwork setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        Lp().settings.set_value('artist-artwork',
                                GLib.Variant('b', state))
        Lp().window.reload_view()
        if state:
            Lp().art.cache_artists_art()

    def _update_repeat_setting(self, widget, state):
        """
            Update repeat setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        Lp().settings.set_value('repeat',
                                GLib.Variant('b', not state))

    def _update_orderby_setting(self, widget):
        """
            Update orderby setting
            @param widget as Gtk.ComboBoxText
        """
        Lp().settings.set_enum('orderby', widget.get_active())

    def _update_lastfm_settings(self, sync=False):
        """
            Update lastfm settings
            @param sync as bool
        """
        try:
            if Lp().lastfm is not None and Secret is not None:
                schema = Secret.Schema.new("org.gnome.Lollypop",
                                           Secret.SchemaFlags.NONE,
                                           SecretSchema)
                Secret.password_store_sync(schema, SecretAttributes,
                                           Secret.COLLECTION_DEFAULT,
                                           "org.gnome.Lollypop"
                                           ".lastfm.login %s" %
                                           self._login.get_text(),
                                           self._password.get_text(),
                                           None)
                Lp().settings.set_value('lastfm-login',
                                        GLib.Variant('s',
                                                     self._login.get_text()))
                if sync:
                    Lp().lastfm.connect_sync(self._password.get_text())
                else:
                    Lp().lastfm.connect(self._password.get_text())
        except Exception as e:
            print("Settings::_update_lastfm_settings(): %s" % e)

    def _edit_settings_close(self, widget):
        """
            Close edit party dialog
            @param widget as Gtk.Window
        """
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

        previous = Lp().settings.get_value('music-path')
        Lp().settings.set_value('music-path', GLib.Variant('as', paths))

        # Last.fm
        try:
            if not Lp().lastfm.is_goa:
                self._update_lastfm_settings()
        except:
            pass

        self._settings_dialog.hide()
        self._settings_dialog.destroy()
        if set(previous) != set(paths):
            Lp().window.update_db()
        Lp().window.update_view()

    def _show_mix_popover(self, widget):
        """
            Show mix popover
            @param widget as Gtk.Widget
        """
        self._mix_tid = None
        if Lp().settings.get_value('mix'):
            if self._popover is None:
                self._popover = Gtk.Popover.new(widget)
                self._popover.set_modal(False)
                self._popover.add(self._popover_content)
            self._popover.show_all()

    def _on_preview_changed(self, combo):
        """
            Update preview setting
            @param combo as Gtk.ComboBoxText
        """
        Lp().settings.set_value('preview-output',
                                GLib.Variant('s', combo.get_active_id()))
        Lp().player.set_preview_output()

    def _on_preview_query_tooltip(self, combo, x, y, keyboard, tooltip):
        """
            Show tooltip if needed
            @param combo as Gtk.ComboBoxText
            @param x as int
            @param y as int
            @param keyboard as bool
            @param tooltip as Gtk.Tooltip
        """
        combo.set_tooltip_text(combo.get_active_text())

    def _on_mix_button_press(self, widget, event):
        """
            Show mix popover on long press
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        self._mix_tid = GLib.timeout_add(500, self._show_mix_popover, widget)

    def _on_mix_button_release(self, widget, event):
        """
            If no popover shown, pass event
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        if self._mix_tid is None:
            return True
        else:
            GLib.source_remove(self._mix_tid)
            self._mix_tid = None

    def _on_key_release_event(self, widget, event):
        """
            Destroy window if Esc
            @param widget as Gtk.Widget
            @param event as Gdk.event
        """
        if event.keyval == Gdk.KEY_Escape:
            self._settings_dialog.destroy()

    def _on_test_btn_clicked(self, button):
        """
            Test lastfm connection
            @param button as Gtk.Button
        """
        self._update_lastfm_settings(True)
        if not Gio.NetworkMonitor.get_default().get_network_available():
            self._test_img.set_from_icon_name('computer-fail-symbolic',
                                              Gtk.IconSize.MENU)
            return
        t = Thread(target=self._test_lastfm_connection)
        t.daemon = True
        t.start()

    def _test_lastfm_connection(self):
        """
            Test lastfm connection
            @thread safe
        """
        try:
            u = Lp().lastfm.get_authenticated_user()
            u.get_id()
            GLib.idle_add(self._test_img.set_from_icon_name,
                          'object-select-symbolic',
                          Gtk.IconSize.MENU)
        except:
            GLib.idle_add(self._test_img.set_from_icon_name,
                          'computer-fail-symbolic',
                          Gtk.IconSize.MENU)

    def _on_password_lookup(self, source, result):
        """
            Set password entry
            @param source as GObject.Object
            @param result Gio.AsyncResult
        """
        try:
            password = None
            if result is not None:
                password = Secret.password_lookup_finish(result)
            if password is not None:
                self._password.set_text(password)
        except:
            pass

    def _hide_popover(self, widget):
        """
            Hide popover
            @param widget as Gtk.Widget
        """
        self._popover.hide()


class ChooserWidget(Gtk.Grid):
    """
        Widget used to let user select a collection folder
    """

    def __init__(self):
        """
            Init widget
        """
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

    def set_dir(self, path):
        """
            Set current selected path for chooser
            @param directory path as string
        """
        if path:
            self._chooser_btn.set_uri("file://"+path)

    def set_icon(self, image):
        """
            Set image for action button
            @param Gtk.Image
        """
        self._action_btn.set_image(image)

    def set_action(self, action):
        """
            Set action callback for button clicked signal
            @param func
        """
        self._action = action

    def get_dir(self):
        """
            Return select directory path
            @return path as string
        """
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
    def _do_action(self, widget):
        """
            If action defined, execute, else, remove widget
        """
        if self._action:
            self._action()
        else:
            self.destroy()
