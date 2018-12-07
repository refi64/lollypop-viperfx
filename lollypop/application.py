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
gi.require_version("TotemPlParser", "1.0")
from gi.repository import Gtk, Gio, GLib, Gdk, Gst
Gst.init(None)

from threading import current_thread
from pickle import dump
from gettext import gettext as _
from signal import signal, SIGINT, SIGTERM


try:
    from lollypop.lastfm import LastFM
except Exception as e:
    print(e)
    print(_("    - Scrobbler disabled\n"
            "    - Auto cover download disabled\n"
            "    - Artist information disabled"))
    print("$ sudo pip3 install pylast")
    LastFM = None

from lollypop.utils import set_proxy_from_gnome
from lollypop.application_actions import ApplicationActions
from lollypop.utils import is_audio, is_pls
from lollypop.define import Type, LOLLYPOP_DATA_PATH
from lollypop.window import Window
from lollypop.database import Database
from lollypop.player import Player
from lollypop.inhibitor import Inhibitor
from lollypop.art import Art
from lollypop.logger import Logger
from lollypop.sqlcursor import SqlCursor
from lollypop.settings import Settings
from lollypop.database_albums import AlbumsDatabase
from lollypop.database_artists import ArtistsDatabase
from lollypop.database_genres import GenresDatabase
from lollypop.database_tracks import TracksDatabase
from lollypop.notification import NotificationManager
from lollypop.playlists import Playlists
from lollypop.objects import Album, Track
from lollypop.helper_task import TaskHelper
from lollypop.helper_art import ArtHelper
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
        self.set_property("register-session", True)
        signal(SIGINT, lambda a, b: self.quit())
        signal(SIGTERM, lambda a, b: self.quit())
        # Set main thread name
        # We force it to current python 3.6 name, to be sure in case of
        # change in python
        current_thread().setName("MainThread")
        set_proxy_from_gnome()
        GLib.setenv("PULSE_PROP_media.role", "music", True)
        GLib.setenv("PULSE_PROP_application.icon_name",
                    "org.gnome.Lollypop", True)
        # Fix proxy for python
        proxy = GLib.environ_getenv(GLib.get_environ(), "all_proxy")
        if proxy is not None and proxy.startswith("socks://"):
            proxy = proxy.replace("socks://", "socks4://")
            from os import environ
            environ["all_proxy"] = proxy
            environ["ALL_PROXY"] = proxy
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
        self.shown_sidebar_tooltip = False
        self.__fs = None
        GLib.set_application_name("Lollypop")
        GLib.set_prgname("lollypop")
        self.add_main_option("play-ids", b"a", GLib.OptionFlags.NONE,
                             GLib.OptionArg.STRING, "Play ids", None)
        self.add_main_option("debug", b"d", GLib.OptionFlags.NONE,
                             GLib.OptionArg.NONE, "Debug Lollypop", None)
        self.add_main_option("set-rating", b"r", GLib.OptionFlags.NONE,
                             GLib.OptionArg.STRING, "Rate the current track",
                             None)
        self.add_main_option("play-pause", b"t", GLib.OptionFlags.NONE,
                             GLib.OptionArg.NONE, "Toggle playback",
                             None)
        self.add_main_option("stop", b"s", GLib.OptionFlags.NONE,
                             GLib.OptionArg.NONE, "Stop playback",
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
        self.add_main_option("version", b"v", GLib.OptionFlags.NONE,
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
            Logger.error("Application::init(): %s" % e)

        cssProviderFile = Gio.File.new_for_uri(
            "resource:///org/gnome/Lollypop/application.css")
        cssProvider = Gtk.CssProvider()
        cssProvider.load_from_file(cssProviderFile)
        screen = Gdk.Screen.get_default()
        styleContext = Gtk.StyleContext()
        styleContext.add_provider_for_screen(screen, cssProvider,
                                             Gtk.STYLE_PROVIDER_PRIORITY_USER)
        self.db = Database()
        self.playlists = Playlists()
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
        self.task_helper = TaskHelper()
        self.art_helper = ArtHelper()
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
        ApplicationActions()
        startup_one_ids = self.settings.get_value("startup-one-ids")
        startup_two_ids = self.settings.get_value("startup-two-ids")
        if startup_one_ids:
            self.settings.set_value("state-one-ids", startup_one_ids)
        if startup_two_ids:
            self.settings.set_value("state-two-ids", startup_two_ids)

    def do_startup(self):
        """
            Init application
        """
        Gtk.Application.do_startup(self)

        if self.window is None:
            self.init()
            self.window = Window()
            self.window.connect("delete-event", self.__hide_on_delete)
            self.window.show()
            self.player.restore_state()

    def quit(self, vacuum=False):
        """
            Quit Lollypop
            @param vacuum as bool
        """
        if not self.settings.get_value("save-state"):
            self.settings.set_value("state-one-ids", GLib.Variant("ai", []))
            self.settings.set_value("state-two-ids", GLib.Variant("ai", []))
        self.window.container.save_internals()
        # Then vacuum db
        if vacuum:
            self.__vacuum()
        self.window.hide()
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
                    with open(LOLLYPOP_DATA_PATH + "/Albums.bin", "wb") as f:
                        dump(list(self.player.albums), f)
                except Exception as e:
                    Logger.error("Application::__save_state(): %s" % e)
            dump(track_id, open(LOLLYPOP_DATA_PATH + "/track_id.bin", "wb"))
            dump([self.player.is_playing, self.player.is_party],
                 open(LOLLYPOP_DATA_PATH + "/player.bin", "wb"))
            dump(self.player.queue,
                 open(LOLLYPOP_DATA_PATH + "/queue.bin", "wb"))
            # Save current playlist
            if self.player.current_track.id == Type.RADIOS:
                playlist_ids = [Type.RADIOS]
            elif not self.player.playlist_ids:
                playlist_ids = []
            else:
                playlist_ids = self.player.playlist_ids
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
        self.db.del_tracks(self.tracks.get_non_persistent())
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
            Logger.error("Application::__vacuum(): %s" % e)

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
                Logger.error("Application::__on_command_line(): %s", e)
                pass
        elif options.contains("play-pause"):
            self.player.play_pause()
        elif options.contains("stop"):
            self.player.stop()
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
                Logger.error("Application::__on_command_line(): %s", e)
                pass
        elif options.contains("next"):
            self.player.next()
        elif options.contains("prev"):
            self.player.prev()
        elif options.contains("emulate-phone"):
            self.window.container.add_fake_phone()
        elif len(args) > 1:
            uris = []
            pls = []
            for uri in args[1:]:
                try:
                    uri = GLib.filename_to_uri(uri)
                except:
                    pass
                f = Gio.File.new_for_uri(uri)
                if is_audio(f):
                    uris.append(uri)
                elif is_pls(f):
                    pls.append(uri)
            if pls:
                from gi.repository import TotemPlParser
                parser = TotemPlParser.Parser.new()
                parser.connect("entry-parsed", self.__on_entry_parsed, uris)
                parser.parse_async(uri, True, None,
                                   self.__on_parse_finished, uris)
            else:
                self.__on_parse_finished(None, None, uris)
        elif self.window is not None:
            self.window.setup()
            if not self.window.is_visible():
                # https://bugzilla.gnome.org/show_bug.cgi?id=766284
                monotonic_time = int(GLib.get_monotonic_time() / 1000)
                self.window.present_with_time(monotonic_time)
                self.player.emit("status-changed")
                self.player.emit("current-changed")
        Gdk.notify_startup_complete()
        return 0

    def __on_parse_finished(self, parser, result, uris):
        """
            Play stream
            @param parser as TotemPlParser.Parser
            @param result as Gio.AsyncResult
            @param uris as [str]
        """
        GLib.timeout_add(500, self.scanner.update, uris, False)

    def __on_entry_parsed(self, parser, uri, metadata, uris):
        """
            Add playlist entry to external files
            @param parser as TotemPlParser.Parser
            @param uri as str
            @param metadata as GLib.HastTable
            @param uris as str
        """
        uris.append(uri)

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

    def __on_activate(self, application):
        """
            Call default handler
            @param application as Gio.Application
        """
        # https://bugzilla.gnome.org/show_bug.cgi?id=766284
        monotonic_time = int(GLib.get_monotonic_time() / 1000)
        self.window.present_with_time(monotonic_time)
