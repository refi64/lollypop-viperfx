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

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gst", "1.0")
gi.require_version("GstAudio", "1.0")
gi.require_version("GstPbutils", "1.0")
gi.require_version("Notify", "0.7")
gi.require_version("TotemPlParser", "1.0")
from gi.repository import Gtk, Gio, GLib, Gdk, Notify, TotemPlParser

from pickle import dump
from gettext import gettext as _


try:
    from lollypop.lastfm import LastFM
except Exception as e:
    print(e)
    print(_("    - Scrobbler disabled\n"
            "    - Auto cover download disabled\n"
            "    - Artist information disabled"))
    print("$ sudo pip3 install pylast")
    LastFM = None

from lollypop.utils import is_gnome, is_unity, set_proxy_from_gnome
from lollypop.define import Type, LOLLYPOP_DATA_PATH
from lollypop.window import Window
from lollypop.database import Database
from lollypop.player import Player
from lollypop.inhibitor import Inhibitor
from lollypop.art import Art
from lollypop.sqlcursor import SqlCursor
from lollypop.settings import Settings, SettingsDialog
from lollypop.database_albums import AlbumsDatabase
from lollypop.database_artists import ArtistsDatabase
from lollypop.database_genres import GenresDatabase
from lollypop.database_tracks import TracksDatabase
from lollypop.notification import NotificationManager
from lollypop.playlists import Playlists
from lollypop.objects import Album, Track
from lollypop.helper_task import TaskHelper
from lollypop.collectionscanner import CollectionScanner


class Application(Gtk.Application):
    """
        Lollypop application:
            - Handle appmenu
            - Handle command line
            - Create main window
    """

    def __init__(self, version):
        """
            Create application
            @param version as str
        """
        Gtk.Application.__init__(
                            self,
                            application_id="org.gnome.Lollypop",
                            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.__version = version
        set_proxy_from_gnome()
        self.set_property("register-session", True)
        GLib.setenv("PULSE_PROP_media.role", "music", True)
        GLib.setenv("PULSE_PROP_application.icon_name",
                    "org.gnome.Lollypop", True)

        # Ideally, we will be able to delete this once Flatpak has a solution
        # for SSL certificate management inside of applications.
        if GLib.file_test("/app", GLib.FileTest.EXISTS):
            paths = ["/etc/ssl/certs/ca-certificates.crt",
                     "/etc/pki/tls/cert.pem",
                     "/etc/ssl/cert.pem"]
            for path in paths:
                if GLib.file_test(path, GLib.FileTest.EXISTS):
                    GLib.setenv("SSL_CERT_FILE", path, True)
                    break

        self.cursors = {}
        self.window = None
        self.notify = None
        self.scrobblers = []
        self.debug = False
        self.__fs = None
        self.__externals_count = 0
        GLib.set_application_name("Lollypop")
        GLib.set_prgname("lollypop")
        self.add_main_option("play-ids", b"a", GLib.OptionFlags.NONE,
                             GLib.OptionArg.STRING, "Play ids", None)
        self.add_main_option("debug", b"d", GLib.OptionFlags.NONE,
                             GLib.OptionArg.NONE, "Debug lollypop", None)
        self.add_main_option("set-rating", b"r", GLib.OptionFlags.NONE,
                             GLib.OptionArg.STRING, "Rate the current track",
                             None)
        self.add_main_option("play-pause", b"t", GLib.OptionFlags.NONE,
                             GLib.OptionArg.NONE, "Toggle playback",
                             None)
        self.add_main_option("next", b"n", GLib.OptionFlags.NONE,
                             GLib.OptionArg.NONE, "Go to next track",
                             None)
        self.add_main_option("prev", b"p", GLib.OptionFlags.NONE,
                             GLib.OptionArg.NONE, "Go to prev track",
                             None)
        self.add_main_option("emulate-phone", b"e", GLib.OptionFlags.NONE,
                             GLib.OptionArg.NONE,
                             "Emulate an Android Phone",
                             None)
        self.add_main_option("version", b"V", GLib.OptionFlags.NONE,
                             GLib.OptionArg.NONE,
                             "Lollypop version",
                             None)
        self.connect("command-line", self.__on_command_line)
        self.connect("handle-local-options", self.__on_handle_local_options)
        self.connect("activate", self.__on_activate)
        self.connect("shutdown", lambda a: self.__save_state())
        self.register(None)
        if self.get_is_remote():
            Gdk.notify_startup_complete()

    def init(self):
        """
            Init main application
        """
        self.settings = Settings.new()
        # Mount enclosing volume as soon as possible
        uris = self.settings.get_music_uris()
        try:
            for uri in uris:
                if uri.startswith("file:/"):
                    continue
                f = Gio.File.new_for_uri(uri)
                f.mount_enclosing_volume(Gio.MountMountFlags.NONE,
                                         None,
                                         None,
                                         None)
        except Exception as e:
            print("Application::init():", e)

        if Gtk.get_minor_version() > 18:
            cssProviderFile = Gio.File.new_for_uri(
                 "resource:///org/gnome/Lollypop/application.css")
        else:
            cssProviderFile = Gio.File.new_for_uri(
                 "resource:///org/gnome/Lollypop/application-legacy.css")
        cssProvider = Gtk.CssProvider()
        cssProvider.load_from_file(cssProviderFile)
        screen = Gdk.Screen.get_default()
        styleContext = Gtk.StyleContext()
        styleContext.add_provider_for_screen(screen, cssProvider,
                                             Gtk.STYLE_PROVIDER_PRIORITY_USER)
        self.db = Database()
        self.playlists = Playlists()
        # We store cursors for main thread
        SqlCursor.add(self.db)
        SqlCursor.add(self.playlists)
        self.albums = AlbumsDatabase()
        self.artists = ArtistsDatabase()
        self.genres = GenresDatabase()
        self.tracks = TracksDatabase()
        self.player = Player()
        self.inhibitor = Inhibitor()
        self.scanner = CollectionScanner()
        self.art = Art()
        self.notify = NotificationManager()
        self.art.update_art_size()
        if self.settings.get_value("artist-artwork"):
            GLib.timeout_add(5000, self.art.cache_artists_info)
        # Load lastfm if support available
        if LastFM is not None:
            self.scrobblers = [LastFM("lastfm"),
                               LastFM("librefm")]
        self.load_listenbrainz()
        if not self.settings.get_value("disable-mpris"):
            from lollypop.mpris import MPRIS
            MPRIS(self)

        settings = Gtk.Settings.get_default()
        self.__gtk_dark = settings.get_property(
                                           "gtk-application-prefer-dark-theme")
        if not self.__gtk_dark:
            dark = self.settings.get_value("dark-ui")
            settings.set_property("gtk-application-prefer-dark-theme", dark)

        # Map some settings to actions
        self.add_action(self.settings.create_action("playback"))
        self.add_action(self.settings.create_action("shuffle"))

    def do_startup(self):
        """
            Init application
        """
        Gtk.Application.do_startup(self)
        Notify.init("Lollypop")

        if not self.window:
            self.init()
            menu = self.__setup_app_menu()
            # If GNOME/Unity, add appmenu
            if is_gnome() or is_unity():
                self.set_app_menu(menu)
            self.window = Window()
            # If not GNOME/Unity add menu to toolbar
            if not is_gnome() and not is_unity():
                self.window.setup_menu(menu)
            self.window.connect("delete-event", self.__hide_on_delete)
            self.window.container.init_list_one()
            self.window.show()
            self.player.restore_state()
            # We add to mainloop as we want to run
            # after player::restore_state() signals
            GLib.idle_add(self.window.toolbar.set_mark)
            self.__preload_portal()

    def quit(self, vacuum=False):
        """
            Quit Lollypop
            @param vacuum as bool
        """
        if self.settings.get_value("save-state"):
            self.window.container.save_view_state()
        # Then vacuum db
        if vacuum:
            self.__vacuum()
        self.window.destroy()
        Gio.Application.quit(self)

    def is_fullscreen(self):
        """
            Return True if application is fullscreen
        """
        return self.__fs is not None

    def set_mini(self, action, param):
        """
            Set mini player on/off
            @param dialog as Gtk.Dialog
            @param response id as int
        """
        if self.window is not None:
            self.window.set_mini()

    def load_listenbrainz(self):
        """
            Load listenbrainz support if needed
        """
        if self.settings.get_value("listenbrainz-user-token").get_string():
            from lollypop.listenbrainz import ListenBrainz
            for scrobbler in self.scrobblers:
                if isinstance(scrobbler, ListenBrainz):
                    return
            listenbrainz = ListenBrainz()
            self.scrobblers.append(listenbrainz)
            self.settings.bind("listenbrainz-user-token", listenbrainz,
                               "user_token", 0)

    @property
    def lastfm(self):
        """
            Get lastfm provider from scrobbler
            @return LastFM/None
        """
        if LastFM is None:
            return None
        from pylast import LastFMNetwork
        for scrobbler in self.scrobblers:
            if isinstance(scrobbler, LastFMNetwork):
                return scrobbler
        return None

    @property
    def gtk_application_prefer_dark_theme(self):
        """
            Return default gtk value
            @return bool
        """
        return self.__gtk_dark

#######################
# PRIVATE             #
#######################
    def __save_state(self):
        """
            Save window position and view
        """
        if self.settings.get_value("save-state"):
            # Save current track
            if self.player.current_track.id is None:
                track_id = -1
            elif self.player.current_track.id == Type.RADIOS:
                from lollypop.radios import Radios
                radios = Radios()
                track_id = radios.get_id(
                                    self.player.current_track.album_artists[0])
            else:
                track_id = self.player.current_track.id
                # Save albums context
                try:
                    self.player.shuffle_albums(False)
                    with open(LOLLYPOP_DATA_PATH + "/Albums.bin", "wb") as f:
                        dump(list(self.player.albums), f)
                except Exception as e:
                    print("Application::__save_state()", e)
            dump(track_id, open(LOLLYPOP_DATA_PATH + "/track_id.bin", "wb"))
            dump([self.player.is_playing, self.player.is_party],
                 open(LOLLYPOP_DATA_PATH + "/player.bin", "wb"))
            # Save current playlist
            if self.player.current_track.id == Type.RADIOS:
                playlist_ids = [Type.RADIOS]
            elif not self.player.get_playlist_ids():
                playlist_ids = []
            else:
                playlist_ids = self.player.get_playlist_ids()
            dump(playlist_ids,
                 open(LOLLYPOP_DATA_PATH + "/playlist_ids.bin", "wb"))
        if self.player.current_track.id is not None:
            position = self.player.position
        else:
            position = 0
        dump(position, open(LOLLYPOP_DATA_PATH + "/position.bin", "wb"))
        self.player.stop_all()
        self.window.container.stop_all()

    def __vacuum(self):
        """
            VACUUM DB
        """
        if self.scanner.is_locked():
            self.scanner.stop()
            GLib.idle_add(self.__vacuum)
            return
        try:
            from lollypop.radios import Radios
            with SqlCursor(self.db) as sql:
                sql.isolation_level = None
                sql.execute("VACUUM")
                sql.isolation_level = ""
            with SqlCursor(self.playlists) as sql:
                sql.isolation_level = None
                sql.execute("VACUUM")
                sql.isolation_level = ""
            with SqlCursor(Radios()) as sql:
                sql.isolation_level = None
                sql.execute("VACUUM")
                sql.isolation_level = ""
        except Exception as e:
            print("Application::__vacuum(): ", e)

    def __preload_portal(self):
        """
            Preload lollypop portal
        """
        try:
            bus = self.get_dbus_connection()
            Gio.DBusProxy.new(bus, Gio.DBusProxyFlags.NONE, None,
                              "org.gnome.Lollypop.Portal",
                              "/org/gnome/LollypopPortal",
                              "org.gnome.Lollypop.Portal", None, None)
        except Exception as e:
            print("You are missing lollypop-portal: "
                  "https://github.com/gnumdk/lollypop-portal")
            print("Application::__preload_portal():", e)

    def __on_handle_local_options(self, app, options):
        """
            Handle local options
            @param app as Gio.Application
            @param options as GLib.VariantDict
        """
        if options.contains("version"):
            print("Lollypop %s" % self.__version)
            exit(0)
        return -1

    def __on_command_line(self, app, app_cmd_line):
        """
            Handle command line
            @param app as Gio.Application
            @param options as Gio.ApplicationCommandLine
        """
        self.__externals_count = 0
        args = app_cmd_line.get_arguments()
        options = app_cmd_line.get_options_dict()
        if options.contains("debug"):
            self.debug = True
        if options.contains("set-rating"):
            value = options.lookup_value("set-rating").get_string()
            try:
                value = min(max(0, int(value)), 5)
                if self.player.current_track.id is not None:
                    self.player.current_track.set_rate(value)
            except Exception as e:
                print(e)
                pass
        elif options.contains("play-pause"):
            self.player.play_pause()
        elif options.contains("play-ids"):
            try:
                value = options.lookup_value("play-ids").get_string()
                ids = value.split(";")
                tracks = []
                for id in ids:
                    if id[0:2] == "a:":
                        album = Album(int(id[2:]))
                        tracks += album.tracks
                    else:
                        tracks.append(Track(int(id[2:])))
                self.player.load(tracks[0])
                self.player.populate_playlist_by_tracks(tracks,
                                                        [Type.SEARCH])
            except Exception as e:
                print(e)
                pass
        elif options.contains("next"):
            self.player.next()
        elif options.contains("prev"):
            self.player.prev()
        elif options.contains("emulate-phone"):
            self.window.container.add_fake_phone()
        elif len(args) > 1:
            self.player.clear_externals()
            for uri in args[1:]:
                try:
                    uri = GLib.filename_to_uri(uri)
                except:
                    pass
                parser = TotemPlParser.Parser.new()
                parser.connect("entry-parsed", self.__on_entry_parsed)
                parser.parse_async(uri, True, None, None)
        elif self.window is not None and self.window.is_visible():
            self.window.present_with_time(Gtk.get_current_event_time())
        elif self.window is not None:
            # self.window.setup_window()
            # self.window.present()
            # Horrible HACK: https://bugzilla.gnome.org/show_bug.cgi?id=774130
            self.window.container.save_view_state()
            self.window.destroy()
            self.window = Window()
            # If not GNOME/Unity add menu to toolbar
            if not is_gnome() and not is_unity():
                menu = self.__setup_app_menu()
                self.window.setup_menu(menu)
            self.window.connect("delete-event", self.__hide_on_delete)
            self.window.container.init_list_one()
            self.window.show()
            self.player.emit("status-changed")
            self.player.emit("current-changed")
        return 0

    def __on_entry_parsed(self, parser, uri, metadata):
        """
            Add playlist entry to external files
            @param parser as TotemPlParser.Parser
            @param track uri as str
            @param metadata as GLib.HastTable
        """
        self.player.load_external(uri)
        if self.__externals_count == 0:
            if self.player.is_party:
                self.player.set_party(False)
            self.player.play_first_external()
        self.__externals_count += 1

    def __hide_on_delete(self, widget, event):
        """
            Hide window
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        if not self.settings.get_value("background-mode") or\
                not self.player.is_playing:
            GLib.timeout_add(500, self.quit, True)
        return widget.hide_on_delete()

    def __update_db(self, action=None, param=None):
        """
            Search for new music
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
        """
        if self.window:
            helper = TaskHelper()
            helper.run(self.art.clean_all_cache)
            self.scanner.update()

    def __fullscreen(self, action=None, param=None):
        """
            Show a fullscreen window with cover and artist information
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
        """
        if self.window and not self.is_fullscreen():
            from lollypop.fullscreen import FullScreen
            self.__fs = FullScreen(self, self.window)
            self.__fs.connect("destroy", self.__on_fs_destroyed)
            self.__fs.show()
        elif self.window and self.is_fullscreen():
            self.__fs.destroy()

    def __on_fs_destroyed(self, widget):
        """
            Mark fullscreen as False
            @param widget as Fullscreen
        """
        self.__fs = None
        if not self.window.is_visible():
            self.quit(True)

    def __on_activate(self, application):
        """
            Call default handler
            @param application as Gio.Application
        """
        self.window.present()

    def __settings_dialog(self, action=None, param=None):
        """
            Show settings dialog
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
        """
        dialog = SettingsDialog()
        dialog.show()

    def __about(self, action, param):
        """
            Setup about dialog
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
        """
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/AboutDialog.ui")
        about = builder.get_object("about_dialog")
        about.set_transient_for(self.window)
        about.connect("response", self.__about_response)
        about.show()

    def __shortcuts(self, action, param):
        """
            Show shorctus
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
        """
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/Shortcuts.ui")
        builder.get_object("shortcuts").set_transient_for(self.window)
        builder.get_object("shortcuts").show()

    def __about_response(self, dialog, response_id):
        """
            Destroy about dialog when closed
            @param dialog as Gtk.Dialog
            @param response id as int
        """
        dialog.destroy()

    def __setup_app_menu(self):
        """
            Setup application menu
            @return menu as Gio.Menu
        """
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/Appmenu.ui")
        menu = builder.get_object("app-menu")

        settingsAction = Gio.SimpleAction.new("settings", None)
        settingsAction.connect("activate", self.__settings_dialog)
        self.add_action(settingsAction)

        updateAction = Gio.SimpleAction.new("update_db", None)
        updateAction.connect("activate", self.__update_db)
        self.add_action(updateAction)

        fsAction = Gio.SimpleAction.new("fullscreen", None)
        fsAction.connect("activate", self.__fullscreen)
        self.add_action(fsAction)

        mini_action = Gio.SimpleAction.new("mini", None)
        mini_action.connect("activate", self.set_mini)
        self.add_action(mini_action)

        aboutAction = Gio.SimpleAction.new("about", None)
        aboutAction.connect("activate", self.__about)
        self.add_action(aboutAction)

        shortcutsAction = Gio.SimpleAction.new("shortcuts", None)
        shortcutsAction.connect("activate", self.__shortcuts)
        self.add_action(shortcutsAction)

        quitAction = Gio.SimpleAction.new("quit", None)
        quitAction.connect("activate", lambda x, y: self.quit(True))
        self.add_action(quitAction)

        return menu
