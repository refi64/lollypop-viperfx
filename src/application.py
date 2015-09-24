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

from gi.repository import Gtk, Gio, GLib, Gdk, Gst, Notify, TotemPlParser

from locale import getlocale
from gettext import gettext as _
from threading import Thread
import os


try:
    from lollypop.lastfm import LastFM
except Exception as e:
    print(e)
    print(_("    - Scrobbler disabled\n"
            "    - Auto cover download disabled\n"
            "    - Artist informations disabled"))
    print("$ sudo pip3 install pylast")
    LastFM = None

from lollypop.utils import is_gnome, is_unity
from lollypop.define import Lp, ArtSize
from lollypop.window import Window
from lollypop.database import Database
from lollypop.player import Player
from lollypop.art import Art
from lollypop.settings import Settings, SettingsDialog
from lollypop.mpris import MPRIS
from lollypop.notification import NotificationManager
from lollypop.database_albums import AlbumsDatabase
from lollypop.database_artists import ArtistsDatabase
from lollypop.database_genres import GenresDatabase
from lollypop.database_tracks import TracksDatabase
from lollypop.playlists import PlaylistsManager
from lollypop.collectionscanner import CollectionScanner
from lollypop.fullscreen import FullScreen

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
gi.require_version('Notify', '0.7')
gi.require_version('TotemPlParser', '1.0')


class Application(Gtk.Application):
    """
        Lollypop application:
            - Handle appmenu
            - Handle command line
            - Create main window
    """

    def __init__(self):
        """
            Create application
        """
        Gtk.Application.__init__(self,
                                 application_id='org.gnome.Lollypop',
                                 flags=Gio.ApplicationFlags.FLAGS_NONE)
        self._init_proxy()
        GLib.set_application_name('lollypop')
        GLib.set_prgname('lollypop')
        self.set_flags(Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        # TODO: Remove this test later
        if Gtk.get_minor_version() > 12:
            self.add_main_option("debug", b'd', GLib.OptionFlags.NONE,
                                 GLib.OptionArg.NONE, "Debug lollypop", None)
            self.add_main_option("set-rating", b'r', GLib.OptionFlags.NONE,
                                 GLib.OptionArg.INT, "Rate the current track",
                                 None)
        self.connect('handle-local-options', self._on_handle_local_options)
        self.connect('command-line', self._on_command_line)
        cssProviderFile = Gio.File.new_for_uri(
            'resource:///org/gnome/Lollypop/application.css')
        cssProvider = Gtk.CssProvider()
        cssProvider.load_from_file(cssProviderFile)
        screen = Gdk.Screen.get_default()
        monitor = screen.get_primary_monitor()
        geometry = screen.get_monitor_geometry(monitor)
        # We want 500 and 200 in full hd
        # Do not upscale on HiDPI
        ArtSize.BIG = int(200*geometry.width/1920)
        ArtSize.MONSTER = int(500*geometry.width/1920)

        styleContext = Gtk.StyleContext()
        styleContext.add_provider_for_screen(screen, cssProvider,
                                             Gtk.STYLE_PROVIDER_PRIORITY_USER)
        Lp.settings = Settings.new()
        if LastFM is not None:
            Lp.lastfm = LastFM()
        Lp.db = Database()
        # We store a cursor for the main thread
        Lp.sql = Lp.db.get_cursor()
        Lp.albums = AlbumsDatabase()
        Lp.artists = ArtistsDatabase()
        Lp.genres = GenresDatabase()
        Lp.tracks = TracksDatabase()
        Lp.player = Player()
        Lp.playlists = PlaylistsManager()
        Lp.scanner = CollectionScanner()
        Lp.art = Art()
        if not Lp.settings.get_value('disable-mpris'):
            MPRIS(self)
        if not Lp.settings.get_value('disable-notifications'):
            Lp.notify = NotificationManager()

        settings = Gtk.Settings.get_default()
        dark = Lp.settings.get_value('dark-ui')
        settings.set_property('gtk-application-prefer-dark-theme', dark)

        self._parser = TotemPlParser.Parser.new()
        self._parser.connect('entry-parsed', self._on_entry_parsed)

        self.add_action(Lp.settings.create_action('shuffle'))
        self._externals_count = 0
        self._is_fs = False

        self.register(None)
        if self.get_is_remote():
            Gdk.notify_startup_complete()

    def do_startup(self):
        """
            Add startup notification and
            build gnome-shell menu after Gtk.Application startup
        """
        Gtk.Application.do_startup(self)
        Notify.init("Lollypop")

        # Check locale, we want unicode!
        (code, encoding) = getlocale()
        if encoding is None or encoding != "UTF-8":
            builder = Gtk.Builder()
            builder.add_from_resource('/org/gnome/Lollypop/Unicode.ui')
            Lp.window = builder.get_object('unicode')
            Lp.window.set_application(self)
            Lp.window.show()
        elif not Lp.window:
            menu = self._setup_app_menu()
            # If GNOME/Unity, add appmenu
            if is_gnome() or is_unity():
                self.set_app_menu(menu)
            Lp.window = Window(self)
            # If not GNOME add menu to toolbar
            if not is_gnome() and not is_unity():
                Lp.window.setup_menu(menu)
            Lp.window.connect('delete-event', self._hide_on_delete)
            Lp.window.init_list_one()
            Lp.window.show()
            Lp.player.restore_state()

    def do_activate(self):
        """
            Activate window
        """
        if Lp.window is not None:
            Lp.window.present()
        Gtk.Application.do_activate(self)

    def do_open(self, files, hint, data):
        """
            Play specified files
            @param app as Gio.Application
            @param files as [Gio.Files]
            @param hint as str
            @param data as unused
        """
        Lp.player.clear_externals()
        for f in files:
            self._parser.parse_async(f.get_uri(), True,
                                     None, self._on_parsing_finished,
                                     f.get_uri())
        if Lp.window is not None and Lp.window.is_visible():
            Lp.window.present()

    def prepare_to_exit(self, action=None, param=None):
        """
            Save window position and view
        """
        if Lp.settings.get_value('save-state'):
            Lp.window.save_view_state()
            if Lp.player.current_track.id is None:
                track_id = -1
            else:
                track_id = Lp.player.current_track.id
            Lp.settings.set_value('track-id', GLib.Variant('i',
                                                           track_id))
        Lp.player.stop()
        if Lp.window:
            Lp.window.stop_all()
        self.quit()

    def quit(self):
        """
            Quit lollypop
        """
        if Lp.scanner.is_locked():
            Lp.scanner.stop()
            GLib.idle_add(self.quit)
            return
        try:
            Lp.sql.execute("VACUUM")
        except Exception as e:
            print("Application::quit(): ", e)
        Lp.window.destroy()
        Lp.sql.close()
        Gst.deinit()

    def is_fullscreen(self):
        """
            Return True if application is fullscreen
        """
        return self._is_fs

#######################
# PRIVATE             #
#######################
    def _init_proxy(self):
        """
            Init proxy setting env
        """
        try:
            settings = Gio.Settings.new('org.gnome.system.proxy.http')
            h = settings.get_value('host').get_string()
            p = settings.get_value('port').get_int32()
            if h != '' and p != 0:
                os.environ['HTTP_PROXY'] = "%s:%s" % (h, p)
        except:
            pass

    def _on_handle_local_options(self, app, options):
        """
            Handle command line
            @param app as Gio.Application
            @param options as GLib.VariantDict
        """
        if options.contains("debug"):
            Lp.debug = True
        return -1

    def _on_command_line(self, app, app_cmd_line):
        """
            Handle command line
            @param app as Gio.Application
            @param options as Gio.ApplicationCommandLine
        """
        options = app_cmd_line.get_options_dict()
        if options.contains("set-rating"):
            value = options.lookup_value("set-rating").get_int32()
            if value < 0 or value > 5:
                return 1
            if Lp.player.current_track.id is not None:
                Lp.player.current_track.set_popularity(value)
            else:
                return 1
        return 0

    def _on_entry_parsed(self, parser, uri, metadata):
        """
            Add playlist entry to external files
            @param parser as TotemPlParser.Parser
            @param track uri as str
            @param metadata as GLib.HastTable
        """
        Lp.player.load_external(uri)
        if self._externals_count == 0:
            Lp.player.set_party(False)
            Lp.player.play_first_external()
        self._externals_count += 1

    def _on_parsing_finished(self, source, result, uri):
        """
            Reset parsed count and play uri if not a playlist
            @param source as GObject.Object
            @param result as Gio.AsyncResult
            @param uri as string
        """
        if self._externals_count == 0:
            Lp.player.load_external(uri)
            Lp.player.set_party(False)
            Lp.player.play_first_external()
        else:
            self._externals_count = 0

    def _hide_on_delete(self, widget, event):
        """
            Hide window
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        if not Lp.settings.get_value('background-mode'):
            GLib.timeout_add(500, self.prepare_to_exit)
            Lp.scanner.stop()
        return widget.hide_on_delete()

    def _update_db(self, action=None, param=None):
        """
            Search for new music
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
        """
        if Lp.window:
            t = Thread(target=Lp.art.clean_all_cache)
            t.daemon = True
            t.start()
            Lp.window.update_db()

    def _fullscreen(self, action=None, param=None):
        """
            Show a fullscreen window with cover and artist informations
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
        """
        if Lp.window and not self._is_fs:
            fs = FullScreen(self, Lp.window)
            fs.connect("destroy", self._on_fs_destroyed)
            self._is_fs = True
            fs.show()

    def _on_fs_destroyed(self, widget):
        """
            Mark fullscreen as False
            @param widget as Fullscreen
        """
        self._is_fs = False

    def _settings_dialog(self, action=None, param=None):
        """
            Show settings dialog
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
        """
        dialog = SettingsDialog()
        dialog.show()

    def _about(self, action, param):
        """
            Setup about dialog
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
        """
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/AboutDialog.ui')
        about = builder.get_object('about_dialog')
        about.set_transient_for(Lp.window)
        about.connect("response", self._about_response)
        about.show()

    def _help(self, action, param):
        """
            Show help in yelp
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
        """
        try:
            Gtk.show_uri(None, "help:lollypop", Gtk.get_current_event_time())
        except:
            print(_("Lollypop: You need to install yelp."))

    def _about_response(self, dialog, response_id):
        """
            Destroy about dialog when closed
            @param dialog as Gtk.Dialog
            @param response id as int
        """
        dialog.destroy()

    def _setup_app_menu(self):
        """
            Setup application menu
            @return menu as Gio.Menu
        """
        builder = Gtk.Builder()

        builder.add_from_resource('/org/gnome/Lollypop/Appmenu.ui')

        menu = builder.get_object('app-menu')

        # TODO: Remove this test later
        if Gtk.get_minor_version() > 12:
            settingsAction = Gio.SimpleAction.new('settings', None)
            settingsAction.connect('activate', self._settings_dialog)
            self.set_accels_for_action('app.settings', ["<Control>s"])
            self.add_action(settingsAction)

        updateAction = Gio.SimpleAction.new('update_db', None)
        updateAction.connect('activate', self._update_db)
        self.set_accels_for_action('app.update_db', ["<Control>u"])
        self.add_action(updateAction)

        fsAction = Gio.SimpleAction.new('fullscreen', None)
        fsAction.connect('activate', self._fullscreen)
        self.set_accels_for_action('app.fullscreen', ["F11", "<Control>m"])
        self.add_action(fsAction)

        aboutAction = Gio.SimpleAction.new('about', None)
        aboutAction.connect('activate', self._about)
        self.add_action(aboutAction)

        helpAction = Gio.SimpleAction.new('help', None)
        helpAction.connect('activate', self._help)
        self.set_accels_for_action('app.help', ["F1"])
        self.add_action(helpAction)

        quitAction = Gio.SimpleAction.new('quit', None)
        quitAction.connect('activate', self.prepare_to_exit)
        self.set_accels_for_action('app.quit', ["<Control>q"])
        self.add_action(quitAction)

        return menu
