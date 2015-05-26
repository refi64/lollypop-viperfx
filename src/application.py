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

from gi.repository import Gtk, Gio, GLib, Gdk, Notify, TotemPlParser

from locale import getlocale
from gettext import gettext as _
from _thread import start_new_thread

try:
    from lollypop.lastfm import LastFM
    PYLAST = True
except Exception as e:
    print(e)
    print(_("    - Scrobbler disabled\n"
            "    - Auto cover download disabled\n"
            "    - Artist informations disabled"))
    PYLAST = False

from lollypop.utils import is_audio, is_gnome, is_unity
from lollypop.define import Lp, ArtSize
from lollypop.window import Window
from lollypop.database import Database
from lollypop.player import Player
from lollypop.art import Art
from lollypop.settings import Settings, SettingsDialog
from lollypop.mpris import MPRIS
from lollypop.notification import NotificationManager
from lollypop.database_albums import DatabaseAlbums
from lollypop.database_artists import DatabaseArtists
from lollypop.database_genres import DatabaseGenres
from lollypop.database_tracks import DatabaseTracks
from lollypop.playlists import PlaylistsManager
from lollypop.collectionscanner import CollectionScanner
from lollypop.fullscreen import FullScreen


class Application(Gtk.Application):

    """
        Create application with a custom css provider
    """
    def __init__(self):
        Gtk.Application.__init__(self,
                                 application_id='org.gnome.Lollypop',
                                 flags=Gio.ApplicationFlags.FLAGS_NONE)
        GLib.set_application_name('lollypop')
        GLib.set_prgname('lollypop')
        self.set_flags(Gio.ApplicationFlags.HANDLES_OPEN)
        self.add_main_option("debug", b'd', GLib.OptionFlags.NONE,
                             GLib.OptionArg.NONE, "Debug lollypop", None)
        self.connect('handle-local-options', self._on_handle_local_options)
        cssProviderFile = Gio.File.new_for_uri(
                            'resource:///org/gnome/Lollypop/application.css'
                                              )
        cssProvider = Gtk.CssProvider()
        cssProvider.load_from_file(cssProviderFile)
        screen = Gdk.Screen.get_default()
        monitor = screen.get_primary_monitor()
        geometry = screen.get_monitor_geometry(monitor)
        # We want 500 and 200 in full hd
        ArtSize.BIG = int(200*geometry.width/1920)
        ArtSize.MONSTER = int(500*geometry.width/1920)

        styleContext = Gtk.StyleContext()
        styleContext.add_provider_for_screen(screen, cssProvider,
                                             Gtk.STYLE_PROVIDER_PRIORITY_USER)
        if PYLAST:
            Lp.lastfm = LastFM()
        Lp.settings = Settings.new()
        Lp.db = Database()
        # We store a cursor for the main thread
        Lp.sql = Lp.db.get_cursor()
        Lp.player = Player()
        Lp.albums = DatabaseAlbums()
        Lp.artists = DatabaseArtists()
        Lp.genres = DatabaseGenres()
        Lp.tracks = DatabaseTracks()
        Lp.playlists = PlaylistsManager()
        Lp.scanner = CollectionScanner()
        Lp.art = Art()
        if not Lp.settings.get_value('disable-mpris'):
            MPRIS(self)
        if not Lp.settings.get_value('disable-notifications'):
            Lp.notify = NotificationManager()

        settings = Gtk.Settings.get_default()
        dark = Lp.settings.get_value('dark-ui')
        settings.set_property("gtk-application-prefer-dark-theme", dark)

        self._parser = TotemPlParser.Parser.new()
        self._parser.connect("entry-parsed", self._on_entry_parsed)

        self.add_action(Lp.settings.create_action('shuffle'))
        self._externals_count = 0
        self._is_fs = False

        self.register(None)
        if self.get_is_remote():
            Gdk.notify_startup_complete()

    """
        Add startup notification and
        build gnome-shell menu after Gtk.Application startup
    """
    def do_startup(self):
        Gtk.Application.do_startup(self)
        Notify.init("Lollypop")

        # Check locale, we want unicode!
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

    """
        Activate window
    """
    def do_activate(self):
        if Lp.window:
            Lp.window.present()

    """
        Play specified files
        @param app as Gio.Application
        @param files as [Gio.Files]
        @param hint as str
        @param data as unused
    """
    def do_open(self, files, hint, data):
        Lp.player.clear_externals()
        for f in files:
            self._parser.parse_async(f.get_uri(), True,
                                     None, self._on_parsing_finished)
        if not Lp.window.is_visible():
            self.do_activate()

    """
        Save window position and view
    """
    def prepare_to_exit(self, action=None, param=None):
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

    """
        Quit lollypop
    """
    def quit(self):
        if Lp.scanner.is_locked():
            Lp.scanner.stop()
            GLib.idle_add(self.quit)
            return
        try:
            Lp.sql.execute("VACUUM")
        except Exception as e:
            print("Application::quit(): ", e)
        Lp.sql.close()
        Lp.window.destroy()

    """
        Return True if application is fullscreen
    """
    def is_fullscreen(self):
        return self._is_fs

#######################
# PRIVATE             #
#######################
    """
        Handle command line
        @param app as Gio.Application
        @param options as GLib.VariantDict
    """
    def _on_handle_local_options(self, app, options):
        if options.contains("debug"):
            Lp.debug = True
        return 0

    """
        Add playlist entry to external files
        @param parser as TotemPlParser.Parser
        @param track uri as str
        @param metadata as GLib.HastTable
    """
    def _on_entry_parsed(self, parser, uri, metadata):
        Lp.player.load_external(uri)
        if self._externals_count == 0:
            Lp.player.load_first_external()
        self._externals_count += 1

    """
        Reset parsed count
        @param source as GObject.Object)
        @param result as Gio.AsyncResult
    """
    def _on_parsing_finished(self, source, result):
        self._externals_count = 0

    """
        Hide window
        @param widget as Gtk.Widget
        @param event as Gdk.Event
    """
    def _hide_on_delete(self, widget, event):
        if not Lp.settings.get_value('background-mode'):
            GLib.timeout_add(500, self.prepare_to_exit)
            Lp.scanner.stop()
        return widget.hide_on_delete()

    """
        Search for new music
        @param action as Gio.SimpleAction
        @param param as GLib.Variant
    """
    def _update_db(self, action=None, param=None):
        if Lp.window:
            start_new_thread(Lp.art.clean_all_cache, ())
            Lp.window.update_db()

    """
        Show a fullscreen window with cover and artist informations
        @param action as Gio.SimpleAction
        @param param as GLib.Variant
    """
    def _fullscreen(self, action=None, param=None):
        if Lp.window:
            fs = FullScreen(Lp.window)
            fs.connect("destroy", self._on_fs_destroyed)
            self._is_fs = True
            fs.show()
        else:
            self._is_fs = False

    """
        Mark fullscreen as False
        @param widget as Fullscreen
    """
    def _on_fs_destroyed(self, widget):
        self._is_fs = False

    """
        Show settings dialog
        @param action as Gio.SimpleAction
        @param param as GLib.Variant
    """
    def _settings_dialog(self, action=None, param=None):
        dialog = SettingsDialog()
        dialog.show()

    """
        Setup about dialog
    """
    def _about(self, action, param):
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/AboutDialog.ui')
        about = builder.get_object('about_dialog')
        about.set_transient_for(Lp.window)
        about.connect("response", self._about_response)
        about.show()

    """
        Show help in yelp
    """
    def _help(self, action, param):
        try:
            Gtk.show_uri(None, "help:lollypop", Gtk.get_current_event_time())
        except:
            print(_("Lollypop: You need to install yelp."))

    """
        Destroy about dialog when closed
    """
    def _about_response(self, dialog, response):
        dialog.destroy()

    """
        Setup application menu
        @return menu as Gio.Menu
    """
    def _setup_app_menu(self):
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
