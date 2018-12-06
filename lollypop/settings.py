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

from gi.repository import Gtk, Gdk, GLib, Gio, Pango

from gettext import gettext as _
from gettext import ngettext as ngettext

from lollypop.define import App
from lollypop.logger import Logger
from lollypop.database import Database
from lollypop.database_history import History


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
        settings = Gio.Settings.new("org.gnome.Lollypop")
        settings.__class__ = Settings
        return settings

    def get_music_uris(self):
        """
            Return music uris
            @return [str]
        """
        uris = self.get_value("music-uris")
        if not uris:
            filename = GLib.get_user_special_dir(
                GLib.UserDirectory.DIRECTORY_MUSIC)
            if filename:
                uris = [GLib.filename_to_uri(filename)]
            else:
                Logger.info("You need to add a music uri"
                            " to org.gnome.Lollypop in dconf")
        return list(uris)


class SettingsDialog:
    """
        Dialog showing lollypop options
    """

    def __init__(self):
        """
            Init dialog
        """
        self.__choosers = []
        self.__cover_tid = None
        self.__mix_tid = None
        self.__popover = None

        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/SettingsDialog.ui")
        self.__progress = builder.get_object("progress")
        self.__infobar = builder.get_object("infobar")
        self.__reset_button = builder.get_object("reset_button")
        if App().lastfm is not None and App().lastfm.is_goa:
            builder.get_object("lastfm_error_label").set_text(
                _('Using "GNOME Online Accounts" settings'))
        if App().scanner.is_locked():
            builder.get_object("reset_button").set_sensitive(False)
        artists = App().artists.count()
        albums = App().albums.count()
        tracks = App().tracks.count()
        builder.get_object("artists").set_text(
            ngettext("%d artist", "%d artists", artists) % artists)
        builder.get_object("albums").set_text(
            ngettext("%d album", "%d albums", albums) % albums)
        builder.get_object("tracks").set_text(
            ngettext("%d track", "%d tracks", tracks) % tracks)

        self.__popover_transitions = builder.get_object("popover-transitions")
        self.__scale_transition_duration = builder.get_object(
            "scale_transition_duration")
        self.__scale_transition_duration.set_range(1, 20)
        self.__scale_transition_duration.set_value(
            App().settings.get_value("transition-duration").get_int32())

        self.__popover_compilations = builder.get_object(
            "popover-compilations")

        self.__settings_dialog = builder.get_object("settings_dialog")
        self.__settings_dialog.set_transient_for(App().window)

        if App().settings.get_value("disable-csd"):
            self.__settings_dialog.set_title(_("Preferences"))
        else:
            headerbar = builder.get_object("header_bar")
            headerbar.set_title(_("Preferences"))
            self.__settings_dialog.set_titlebar(headerbar)

        switch_scan = builder.get_object("switch_scan")
        switch_scan.set_state(App().settings.get_value("auto-update"))

        switch_view = builder.get_object("switch_dark")
        if App().gtk_application_prefer_dark_theme:
            switch_view.set_sensitive(False)
        else:
            switch_view.set_state(App().settings.get_value("dark-ui"))

        switch_background = builder.get_object("switch_background")
        switch_background.set_state(
            App().settings.get_value("background-mode"))

        switch_state = builder.get_object("switch_state")
        switch_state.set_state(App().settings.get_value("save-state"))

        switch_network_access = builder.get_object("switch_network_access")
        network_access = App().settings.get_value("network-access")
        switch_network_access.set_state(network_access)

        switch_transitions = builder.get_object("switch_transitions")
        smooth_transitions = App().settings.get_value("smooth-transitions")
        switch_transitions.set_state(smooth_transitions)
        builder.get_object("transitions_button").set_sensitive(
            smooth_transitions)

        switch_mix_party = builder.get_object("switch_mix_party")
        switch_mix_party.set_state(App().settings.get_value("party-mix"))

        switch_artwork_tags = builder.get_object("switch_artwork_tags")
        grid_behaviour = builder.get_object("grid_behaviour")
        # Check for kid3-cli
        self.__check_for_kid3(switch_artwork_tags, grid_behaviour)

        switch_genres = builder.get_object("switch_genres")
        switch_genres.set_state(App().settings.get_value("show-genres"))

        switch_compilations_in_album_view = builder.get_object(
            "switch_compilations_in_album_view")
        switch_compilations_in_album_view.set_state(
            App().settings.get_value("show-compilations-in-album-view"))

        switch_compilations = builder.get_object("switch_compilations")
        show_compilations = App().settings.get_value("show-compilations")
        switch_compilations.set_state(show_compilations)
        builder.get_object("compilations_button").set_sensitive(
            show_compilations)

        switch_artwork = builder.get_object("switch_artwork")
        switch_artwork.set_state(App().settings.get_value("artist-artwork"))

        combo_orderby = builder.get_object("combo_orderby")
        combo_orderby.set_active(App().settings.get_enum(("orderby")))

        combo_preview = builder.get_object("combo_preview")

        scale_coversize = builder.get_object("scale_coversize")
        scale_coversize.set_range(170, 300)
        scale_coversize.set_value(
            App().settings.get_value("cover-size").get_int32())
        self.__settings_dialog.connect("destroy", self.__edit_settings_close)

        self.__flowbox = builder.get_object("flowbox")

        self.__set_outputs(combo_preview)

        builder.connect_signals(self)

        #
        # Music tab
        #
        dirs = []
        for directory in App().settings.get_value("music-uris"):
            dirs.append(directory)

        # Main chooser
        self.__main_chooser = ChooserWidget()
        image = Gtk.Image.new_from_icon_name("list-add-symbolic",
                                             Gtk.IconSize.MENU)
        self.__main_chooser.set_icon(image)
        self.__main_chooser.set_action(self.__add_chooser)
        self.__flowbox.add(self.__main_chooser)
        if len(dirs) > 0:
            uri = dirs.pop(0)
        else:
            filename = GLib.get_user_special_dir(
                GLib.UserDirectory.DIRECTORY_MUSIC)
            if filename:
                uri = GLib.filename_to_uri(filename)
            else:
                uri = "/opt"

        self.__main_chooser.set_dir(uri)

        # Others choosers
        for directory in dirs:
            self.__add_chooser(directory)

        #
        # Google tab
        #
        key = App().settings.get_value("cs-api-key").get_string() or\
            App().settings.get_default_value("cs-api-key").get_string()
        builder.get_object("cs-entry").set_text(key)

        #
        # ListenBrainz tab
        #
        token = App().settings.get_value(
            "listenbrainz-user-token").get_string()
        builder.get_object("listenbrainz_user_token_entry").set_text(token)

        from lollypop.helper_passwords import PasswordsHelper
        helper = PasswordsHelper()
        #
        # Last.fm tab
        #
        if App().lastfm is not None:
            self.__lastfm_test_image = builder.get_object("lastfm_test_image")
            self.__lastfm_login = builder.get_object("lastfm_login")
            self.__lastfm_password = builder.get_object("lastfm_password")
            helper.get("lastfm",
                       self.__on_get_password)
            if not App().lastfm.is_goa:
                builder.get_object("lastfm_grid").set_sensitive(True)
                builder.get_object("lastfm_error_label").hide()
        #
        # Libre.fm tab
        #
        if App().lastfm is not None:
            self.__librefm_test_image = builder.get_object(
                "librefm_test_image")
            self.__librefm_login = builder.get_object("librefm_login")
            self.__librefm_password = builder.get_object("librefm_password")
            helper.get("librefm",
                       self.__on_get_password)
            builder.get_object("librefm_grid").set_sensitive(True)
            builder.get_object("librefm_error_label").hide()

    def show(self):
        """
            Show dialog
        """
        self.__settings_dialog.show()

#######################
# PROTECTED           #
#######################
    def _on_enable_network_access_state_set(self, widget, state):
        """
            Save network access state
            @param widget as Gtk.Switch
            @param state as bool
        """
        App().settings.set_value("network-access",
                                 GLib.Variant("b", state))

    def _on_scale_coversize_value_changed(self, widget):
        """
            Delayed update cover size
            @param widget as Gtk.Range
        """
        if self.__cover_tid is not None:
            GLib.source_remove(self.__cover_tid)
            self.__cover_tid = None
        self.__cover_tid = GLib.timeout_add(500,
                                            self.__really_update_coversize,
                                            widget)

    def _on_switch_dark_state_set(self, widget, state):
        """
            Update view setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        App().settings.set_value("dark-ui", GLib.Variant("b", state))
        if not App().player.is_party:
            settings = Gtk.Settings.get_default()
            settings.set_property("gtk-application-prefer-dark-theme", state)

    def _on_switch_scan_state_set(self, widget, state):
        """
            Update scan setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        App().settings.set_value("auto-update",
                                 GLib.Variant("b", state))

    def _on_switch_background_state_set(self, widget, state):
        """
            Update background mode setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        App().settings.set_value("background-mode",
                                 GLib.Variant("b", state))

    def _on_switch_state_state_set(self, widget, state):
        """
            Update save state setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        App().settings.set_value("save-state",
                                 GLib.Variant("b", state))

    def _on_switch_genres_state_set(self, widget, state):
        """
            Update show genre setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        App().settings.set_value("show-genres",
                                 GLib.Variant("b", state))
        App().window.container.show_genres(state)

    def _on_transitions_button_clicked(self, widget):
        """
            Show popover
            @param widget as Gtk.Button
        """
        self.__popover_transitions.popup()
        # https://gitlab.gnome.org/GNOME/pango/issues/309
        self.__scale_transition_duration.set_draw_value(True)

    def _on_switch_transitions_state_set(self, widget, state):
        """
            Update smooth transitions setting
            @param widget as Gtk.Button
            @param state as bool
        """
        widget.set_sensitive(state)
        App().settings.set_value("smooth-transitions",
                                 GLib.Variant("b", state))
        App().player.update_crossfading()

    def _on_switch_mix_party_state_set(self, widget, state):
        """
            Update party mix setting
            @param widget as Gtk.Range
        """
        App().settings.set_value("party-mix", GLib.Variant("b", state))
        App().player.update_crossfading()

    def _on_scale_transition_duration_value_changed(self, widget):
        """
            Update mix duration setting
            @param widget as Gtk.Range
        """
        value = widget.get_value()
        App().settings.set_value("transition-duration",
                                 GLib.Variant("i", value))

    def _on_switch_artwork_tags_state_set(self, widget, state):
        """
            Update artwork in tags setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        App().settings.set_value("save-to-tags", GLib.Variant("b", state))

    def _on_compilations_button_clicked(self, widget):
        """
            Show compilations popover
            @param widget as Gtk.Button
        """
        self.__popover_compilations.popup()

    def _on_switch_compilations_state_set(self, widget, state):
        """
            Update show compilations setting
            @param widget as Gtk.Button
            @param state as bool
        """
        widget.set_sensitive(state)
        App().settings.set_value("show-compilations",
                                 GLib.Variant("b", state))

    def _on_switch_compilations_in_album_view_state_set(self, widget, state):
        """
            Update show compilations in album view setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        App().settings.set_value("show-compilations-in-album-view",
                                 GLib.Variant("b", state))

    def _on_switch_artwork_state_set(self, widget, state):
        """
            Update artist artwork setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        App().settings.set_value("artist-artwork",
                                 GLib.Variant("b", state))
        if App().settings.get_value("show-sidebar"):
            App().window.container.list_one.redraw()
            App().window.container.list_two.redraw()
        else:
            from lollypop.view_artists_rounded import RoundedArtistsView
            for child in App().window.container.stack.get_children():
                if isinstance(child, RoundedArtistsView):
                    child.destroy()
                    break
            App().window.container.reload_view()
        if state:
            App().art.cache_artists_info()

    def _on_combo_order_by_changed(self, widget):
        """
            Update orderby setting
            @param widget as Gtk.ComboBoxText
        """
        App().settings.set_enum("orderby", widget.get_active())

    def _on_entry_cs_changed(self, entry):
        """
            Save key
            @param entry as Gtk.Entry
        """
        value = entry.get_text().strip()
        App().settings.set_value("cs-api-key", GLib.Variant("s", value))

    def _on_entry_listenbrainz_token_changed(self, entry):
        """
            Save listenbrainz token
            @param entry as Gtk.Entry
        """
        value = entry.get_text().strip()
        App().settings.set_value("listenbrainz-user-token",
                                 GLib.Variant("s", value))
        App().load_listenbrainz()

    def _on_combo_preview_changed(self, combo):
        """
            Update preview setting
            @param combo as Gtk.ComboBoxText
        """
        App().settings.set_value("preview-output",
                                 GLib.Variant("s", combo.get_active_id()))
        App().player.set_preview_output()

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

    def _on_key_press_event(self, widget, event):
        """
            Destroy window if Esc
            @param widget as Gtk.Widget
            @param event as Gdk.event
        """
        if event.keyval == Gdk.KEY_Escape:
            self.__settings_dialog.destroy()

    def _on_lastfm_test_btn_clicked(self, button):
        """
            Test lastfm connection
            @param button as Gtk.Button
        """
        App().settings.set_value("lastfm-loved-status",
                                 GLib.Variant("b", False))
        self.__update_fm_settings("lastfm")
        if not Gio.NetworkMonitor.get_default().get_network_available():
            self.__lastfm_test_image.set_from_icon_name(
                "computer-fail-symbolic",
                Gtk.IconSize.MENU)
            return

    def _on_librefm_test_btn_clicked(self, button):
        """
            Test librefm connection
            @param button as Gtk.Button
        """
        self.__update_fm_settings("librefm")
        if not Gio.NetworkMonitor.get_default().get_network_available():
            self.__librefm_test_image.set_from_icon_name(
                "computer-fail-symbolic",
                Gtk.IconSize.MENU)
            return

    def _hide_popover(self, widget):
        """
            Hide popover
            @param widget as Gtk.Widget
        """
        self.__popover_transitions.popdown()
        self.__popover_compilations.popdown()

    def _on_response(self, infobar, response_id):
        """
            Hide infobar
            @param widget as Gtk.Infobar
            @param reponse id as int
        """
        if response_id == Gtk.ResponseType.CLOSE:
            infobar.hide()

    def _on_confirm_button_clicked(self, button):
        """
            Reset database
            @param button as Gtk.Button
        """
        try:
            App().player.stop()
            App().player.reset_pcn()
            App().player.emit("current-changed")
            App().player.emit("prev-changed")
            App().player.emit("next-changed")
            App().cursors = {}
            track_ids = App().tracks.get_ids()
            self.__progress.show()
            history = History()
            self.__reset_button.get_toplevel().set_deletable(False)
            self.__reset_button.set_sensitive(False)
            self.__infobar.hide()
            self.__reset_database(track_ids, len(track_ids), history)
        except Exception as e:
            Logger.error("SettingsDialog::_on_confirm_button_clicked(): %s" %
                         e)

    def _on_reset_button_clicked(self, widget):
        """
            Show infobar
            @param widget as Gtk.Widget
        """
        self.__infobar.show()
        # GTK 3.20 https://bugzilla.gnome.org/show_bug.cgi?id=710888
        self.__infobar.queue_resize()

#######################
# PRIVATE             #
#######################
    def __update_fm_settings(self, name):
        """
            Update *fm settings
            @param name as str (librefm/lastfm)
        """
        if App().lastfm is None:
            return
        from pylast import LastFMNetwork, LibreFMNetwork
        fm = None
        for scrobbler in App().scrobblers:
            if (isinstance(scrobbler, LibreFMNetwork) and
                name == "librefm") or\
                    (isinstance(scrobbler, LastFMNetwork) and
                     name != "librefm"):
                fm = scrobbler
                break
        if name == "librefm":
            callback = self.__test_librefm_connection
            login = self.__librefm_login.get_text()
            password = self.__librefm_password.get_text()
        elif App().lastfm is not None:
            callback = self.__test_lastfm_connection
            login = self.__lastfm_login.get_text()
            password = self.__lastfm_password.get_text()
        try:
            if fm is not None and login and password:
                from lollypop.helper_passwords import PasswordsHelper
                helper = PasswordsHelper()
                helper.clear(name,
                             helper.store,
                             name,
                             login,
                             password,
                             self.__on_password_store,
                             fm,
                             callback)
        except Exception as e:
            Logger.error("SettingsDialog::__update_fm_settings(): %s" % e)

    def __set_outputs(self, combo):
        """
            Set outputs in combo
            @parma combo as Gtk.ComboxBoxText
        """
        renderer = combo.get_cells()[0]
        renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
        renderer.set_property("max-width-chars", 60)
        if GLib.find_program_in_path("flatpak-spawn") is not None:
            argv = ["flatpak-spawn", "--host", "pacmd", "list-sinks"]
        else:
            argv = ["pacmd", "list-sinks"]
        try:
            (pid, stdin, stdout, stderr) = GLib.spawn_async(
                argv, flags=GLib.SpawnFlags.SEARCH_PATH |
                GLib.SpawnFlags.DO_NOT_REAP_CHILD,
                standard_input=False,
                standard_output=True,
                standard_error=False
            )
            GLib.child_watch_add(GLib.PRIORITY_DEFAULT_IDLE, pid,
                                 self.__on_pacmd_result, stdout, combo)
        except Exception as e:
            Logger.error("SettingsDialog::__set_outputs(): %s" % e)

    def __add_chooser(self, directory=None):
        """
            Add a new chooser widget
            @param directory uri as string
        """
        chooser = ChooserWidget()
        image = Gtk.Image.new_from_icon_name("list-remove-symbolic",
                                             Gtk.IconSize.MENU)
        chooser.set_icon(image)
        if directory is not None:
            chooser.set_dir(directory)
        self.__flowbox.add(chooser)

    def __really_update_coversize(self, widget):
        """
            Update cover size
            @param widget as Gtk.Range
        """
        self.__cover_tid = None
        value = widget.get_value()
        App().settings.set_value("cover-size", GLib.Variant("i", value))
        App().art.update_art_size()
        App().window.container.reload_view()

    def __edit_settings_close(self, widget):
        """
            Close edit party dialog
            @param widget as Gtk.Window
        """
        # Music uris
        uris = []
        default = GLib.get_user_special_dir(
            GLib.UserDirectory.DIRECTORY_MUSIC)
        if default is not None:
            default_uri = GLib.filename_to_uri(default)
        else:
            default_uri = None
        main_uri = self.__main_chooser.get_dir()
        choosers = self.__flowbox.get_children()
        if main_uri != default_uri or choosers:
            uris.append(main_uri)
            for chooser in choosers:
                uri = chooser.get_dir()
                if uri is not None and uri not in uris:
                    uris.append(uri)

        previous = App().settings.get_value("music-uris")
        App().settings.set_value("music-uris", GLib.Variant("as", uris))

        self.__settings_dialog.hide()
        self.__settings_dialog.destroy()
        if set(previous) != set(uris):
            App().scanner.update()

    def __test_lastfm_connection(self, result, fm):
        """
            Test lastfm connection
            @param result as None
            @param fm as LastFM
        """
        if fm.available:
            self.__lastfm_test_image.set_from_icon_name(
                "object-select-symbolic",
                Gtk.IconSize.MENU)
        else:
            self.__lastfm_test_image.set_from_icon_name(
                "computer-fail-symbolic",
                Gtk.IconSize.MENU)

    def __test_librefm_connection(self, result, fm):
        """
            Test librefm connection
            @param result as None
            @param fm as LastFM
        """
        if fm.available:
            self.__librefm_test_image.set_from_icon_name(
                "object-select-symbolic",
                Gtk.IconSize.MENU)
        else:
            self.__librefm_test_image.set_from_icon_name(
                "computer-fail-symbolic",
                Gtk.IconSize.MENU)

    def __on_pacmd_result(self, pid, status, stdout, combo):
        """
            Read output and set combobox
            @param pid as int
            @param status as bool
            @param stdout as int
            @param combo as Gtk.ComboBox
        """
        from re import findall, DOTALL
        GLib.spawn_close_pid(pid)
        io = GLib.IOChannel.unix_new(stdout)
        [status, data] = io.read_to_end()
        if data:
            string = data.decode("utf-8")
            current = App().settings.get_value("preview-output").get_string()
            devices = findall('name: <([^>]*)>', string, DOTALL)
            names = findall('device.description = "([^"]*)"', string, DOTALL)
            if names:
                for i in range(0, len(names)):
                    combo.append(devices[i], names[i])
                    if devices[i] == current:
                        combo.set_active_id(devices[i])
            else:
                combo.set_sensitive(False)

    def __on_password_store(self, source, result, fm, callback):
        """
            Connect service
            @param source as GObject.Object
            @param result as Gio.AsyncResult
            @param fm as LastFM
            @param callback as function
        """
        fm.connect(True, callback, fm)

    def __check_for_kid3(self, switch, grid):
        """
            Update grid/switch based on result
            @param switch as Gtk.Switch
            @param grid as Gtk.Grid
        """
        if not App().art.kid3_available:
            h = grid.child_get_property(switch, "height")
            w = grid.child_get_property(switch, "width")
            l = grid.child_get_property(switch, "left-attach")
            t = grid.child_get_property(switch, "top-attach")
            switch.destroy()
            label = Gtk.Label.new(_("You need to install kid3-cli"))
            label.get_style_context().add_class("dim-label")
            label.set_property("halign", Gtk.Align.END)
            label.show()
            grid.attach(label, l, t, w, h)
        else:
            switch.set_state(App().settings.get_value("save-to-tags"))

    def __on_get_password(self, attributes, password, name):
        """
             Set password label
             @param attributes as {}
             @param password as str
             @param name as str
        """
        if attributes is None:
            return
        if name == "librefm":
            self.__librefm_login.set_text(attributes["login"])
            self.__librefm_password.set_text(password)
        else:
            self.__lastfm_login.set_text(attributes["login"])
            self.__lastfm_password.set_text(password)

    def __reset_database(self, track_ids, count, history):
        """
            Backup database and reset
            @param track ids as [int]
            @param count as int
            @param history as History
        """
        if track_ids:
            track_id = track_ids.pop(0)
            uri = App().tracks.get_uri(track_id)
            f = Gio.File.new_for_uri(uri)
            name = f.get_basename()
            album_id = App().tracks.get_album_id(track_id)
            popularity = App().tracks.get_popularity(track_id)
            rate = App().tracks.get_rate(track_id)
            ltime = App().tracks.get_ltime(track_id)
            mtime = App().tracks.get_mtime(track_id)
            duration = App().tracks.get_duration(track_id)
            loved_track = App().tracks.get_loved(track_id)
            loved_album = App().albums.get_loved(album_id)
            album_popularity = App().albums.get_popularity(album_id)
            album_rate = App().albums.get_rate(album_id)
            history.add(name, duration, popularity, rate,
                        ltime, mtime, loved_track, loved_album,
                        album_popularity, album_rate)
            self.__progress.set_fraction((count - len(track_ids)) / count)
            GLib.idle_add(self.__reset_database, track_ids,
                          count, history)
        else:
            self.__progress.hide()
            App().player.stop()
            App().db.drop_db()
            App().db = Database()
            App().window.container.show_genres(
                App().settings.get_value("show-genres"))
            App().scanner.update()
            self.__progress.get_toplevel().set_deletable(True)


class ChooserWidget(Gtk.FlowBoxChild):
    """
        Widget used to let user select a collection folder
    """

    def __init__(self):
        """
            Init widget
        """
        Gtk.FlowBoxChild.__init__(self)
        self.__action = None
        grid = Gtk.Grid()
        grid.set_property("orientation", Gtk.Orientation.HORIZONTAL)
        grid.show()
        self.__chooser_btn = Gtk.FileChooserButton()
        self.__chooser_btn.set_local_only(False)
        self.__chooser_btn.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        self.__chooser_btn.set_property("margin", 5)
        self.__chooser_btn.show()
        for child in self.__chooser_btn.get_children():
            if isinstance(child, Gtk.ComboBox):
                child.connect("scroll-event", self.__on_scroll_event)
                break
        grid.add(self.__chooser_btn)
        self.__action_btn = Gtk.Button()
        self.__action_btn.set_property("margin", 5)
        self.__action_btn.show()
        grid.add(self.__action_btn)
        self.__action_btn.connect("clicked", self.___do_action)
        self.show()
        self.add(grid)

    def set_dir(self, uri):
        """
            Set current selected uri for chooser
            @param directory uri as string
        """
        if uri:
            self.__chooser_btn.set_uri(uri)

    def set_icon(self, image):
        """
            Set image for action button
            @param Gtk.Image
        """
        self.__action_btn.set_image(image)

    def set_action(self, action):
        """
            Set action callback for button clicked signal
            @param func
        """
        self.__action = action

    def get_dir(self):
        """
            Return select directory uri
            @return uri as string
        """
        return self.__chooser_btn.get_uri()

#######################
# PRIVATE             #
#######################
    def __on_scroll_event(self, widget, event):
        """
            Block scroll event on combobox
            @param widget as Gtk.ComboBox
            @param event as Gdk.ScrollEvent
        """
        return True

    def ___do_action(self, widget):
        """
            If action defined, execute, else, remove widget
        """
        if self.__action:
            self.__action()
        else:
            self.destroy()
