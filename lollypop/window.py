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

from gi.repository import Gtk, Gio, Gdk, GLib, Gst

from lollypop.container import Container
from lollypop.define import App, WindowSize
from lollypop.toolbar import Toolbar
from lollypop.helper_task import TaskHelper
from lollypop.logger import Logger
from lollypop.utils import is_unity


class Window(Gtk.ApplicationWindow):
    """
        Main window
    """

    def __init__(self):
        """
            Init window
        """
        self.__signal1 = None
        self.__signal2 = None
        self.__timeout = None
        self.__miniplayer = None
        self.__mediakeys = None
        self.__media_keys_busnames = []
        self.__was_maximized = False
        Gtk.ApplicationWindow.__init__(self,
                                       application=App(),
                                       title="Lollypop",
                                       icon_name="org.gnome.Lollypop")
        self.connect("hide", self.__on_hide)
        App().player.connect("current-changed", self.__on_current_changed)
        self.__timeout_configure = None
        seek_action = Gio.SimpleAction.new("seek",
                                           GLib.VariantType.new("i"))
        seek_action.connect("activate", self.__on_seek_action)
        App().add_action(seek_action)
        player_action = Gio.SimpleAction.new("shortcut",
                                             GLib.VariantType.new("s"))
        player_action.connect("activate", self.__on_player_action)
        App().add_action(player_action)

        self.__setup_global_shortcuts()

        self.__main_stack = Gtk.Stack()
        self.__main_stack.set_transition_duration(1000)
        self.__main_stack.set_transition_type(
            Gtk.StackTransitionType.CROSSFADE)
        self.__main_stack.show()

        self.__setup_content()
        # FIXME Remove this, handled by MPRIS in GNOME 3.26
        self.__setup_media_keys()
        self.__enabled_shortcuts = False
        self.enable_global_shortcuts(True)
        self.set_auto_startup_notification(False)
        self.connect("destroy", self.__on_destroyed_window)
        self.connect("realize", self.__on_realize)

    def enable_global_shortcuts(self, enable):
        """
            Enable/Disable special global shortcuts
            @param enable as bool
        """
        if self.__enabled_shortcuts == enable:
            return
        self.__enabled_shortcuts = enable
        if enable:
            if Gtk.Widget.get_default_direction() == Gtk.TextDirection.RTL:
                App().set_accels_for_action("app.seek(10)", ["Left"])
                App().set_accels_for_action("app.seek(20)", ["<Control>Left"])
                App().set_accels_for_action("app.seek(-10)", ["Right"])
                App().set_accels_for_action("app.seek(-20)",
                                            ["<Control>Right"])
            else:
                App().set_accels_for_action("app.seek(10)", ["Right"])
                App().set_accels_for_action("app.seek(20)", ["<Control>Right"])
                App().set_accels_for_action("app.seek(-10)", ["Left"])
                App().set_accels_for_action("app.seek(-20)", ["<Control>Left"])

            App().set_accels_for_action("app.shortcut::play_pause",
                                        ["space", "c"])
            App().set_accels_for_action("app.shortcut::play", ["x"])
            App().set_accels_for_action("app.shortcut::stop", ["v"])
            App().set_accels_for_action("app.shortcut::next", ["n"])
            App().set_accels_for_action("app.shortcut::prev", ["p"])
            App().set_accels_for_action("app.shortcut::loved", ["l"])
        else:
            App().set_accels_for_action("app.seek(10)", [None])
            App().set_accels_for_action("app.seek(20)", [None])
            App().set_accels_for_action("app.seek(-10)", [None])
            App().set_accels_for_action("app.seek(-20)", [None])
            App().set_accels_for_action("app.shortcut::play_pause", [None])
            App().set_accels_for_action("app.shortcut::play", [None])
            App().set_accels_for_action("app.shortcut::stop", [None])
            App().set_accels_for_action("app.shortcut::play_pause", [None])
            App().set_accels_for_action("app.shortcut::play", [None])
            App().set_accels_for_action("app.shortcut::stop", [None])
            App().set_accels_for_action("app.shortcut::next", [None])
            App().set_accels_for_action("app.shortcut::next_album", [None])
            App().set_accels_for_action("app.shortcut::prev", [None])
            App().set_accels_for_action("app.shortcut::loved", [None])

    def setup_window(self):
        """
            Setup window position and size, callbacks
        """
        self.__setup_pos_size("window")
        if App().settings.get_value("window-maximized"):
            # Lets resize happen
            GLib.idle_add(self.maximize)

    def responsive_design(self):
        """
            Handle responsive design
        """
        size = self.get_size()
        self.__toolbar.set_content_width(size[0])
        if size[0] < WindowSize.BIG:
            self.__container.paned_stack(True)
        else:
            self.__container.paned_stack(False)
        if size[0] < WindowSize.XXLARGE:
            self.__show_miniplayer(True)
            self.__main_stack.show()
            self.__miniplayer.set_vexpand(False)
            self.__toolbar.title.hide()
            self.__toolbar.info.hide()
            self.__toolbar.end.set_minimal(True)
        else:
            self.__main_stack.show()
            self.__show_miniplayer(False)
            self.__toolbar.title.show()
            self.__toolbar.info.show()
            self.__toolbar.end.set_minimal(False)
        if size[1] < WindowSize.MEDIUM and\
                self.__miniplayer is not None and\
                self.__miniplayer.is_visible():
            self.__main_stack.hide()
            self.__miniplayer.set_vexpand(True)

    def set_mini(self):
        """
            Set mini player on/off
        """
        if App().player.current_track.id is None:
            return
        was_maximized = self.is_maximized()
        if self.__main_stack.get_visible_child_name() == "main":
            if self.is_maximized():
                self.unmaximize()
                GLib.timeout_add(100, self.__setup_pos_size, "mini")
            else:
                self.__setup_pos_size("mini")
        elif self.__was_maximized:
            self.maximize()
        else:
            self.__setup_pos_size("window")
        self.__was_maximized = was_maximized

    @property
    def toolbar(self):
        """
            toolbar as Toolbar
        """
        return self.__toolbar

    def do_event(self, event):
        """
            Update overlays as internal widget may not have received the signal
            @param widget as Gtk.Widget
            @param event as Gdk.event
        """
        if event.type == Gdk.EventType.FOCUS_CHANGE and\
                self.__container.view is not None:
            if hasattr(self.__container.view, "disable_overlay"):
                self.__container.view.disable_overlay()
            App().player.preview.set_state(Gst.State.NULL)
        Gtk.ApplicationWindow.do_event(self, event)

    @property
    def container(self):
        """
            Get container
            @return Container
        """
        return self.__container

############
# Private  #
############
    def __setup_global_shortcuts(self):
        """
            Setup global shortcuts
        """
        App().set_accels_for_action("app.shortcut::locked", ["<Control>l"])
        App().set_accels_for_action("app.shortcut::filter", ["<Control>i"])
        App().set_accels_for_action("app.shortcut::volume", ["<Alt>v"])
        App().set_accels_for_action("app.shortcut::lyrics", ["<Alt>l"])
        App().set_accels_for_action("app.shortcut::next_album", ["<Control>n"])
        App().set_accels_for_action("app.shortcut::current_artist",
                                    ["<Alt>a"])
        App().set_accels_for_action("app.shortcut::show_genres",
                                    ["<Control>g"])
        App().set_accels_for_action("app.shortcut::show_sidebar", ["F9"])
        App().set_accels_for_action("app.update_db", ["<Control>u"])
        App().set_accels_for_action("app.settings", ["<Control>s"])
        App().set_accels_for_action("app.fullscreen", ["F11", "F7"])
        App().set_accels_for_action("app.mini", ["<Control>m"])
        App().set_accels_for_action("app.about", ["F3"])
        App().set_accels_for_action("app.shortcuts", ["F2"])
        App().set_accels_for_action("app.help", ["F1"])
        App().set_accels_for_action("app.quit", ["<Control>q"])

    def __show_miniplayer(self, show):
        """
            Show/hide subtoolbar
            @param show as bool
        """
        if show and self.__miniplayer is None:
            from lollypop.miniplayer import MiniPlayer
            self.__miniplayer = MiniPlayer(self.get_size()[0])
            self.__vgrid.add(self.__miniplayer)
        elif not show and self.__miniplayer is not None:
            self.__miniplayer.destroy()
            self.__miniplayer = None

    def __setup_pos_size(self, name):
        """
            Set window pos and size based on name
            @param name as str
        """
        size_setting = App().settings.get_value("%s-size" % name)
        if len(size_setting) == 2 and\
           isinstance(size_setting[0], int) and\
           isinstance(size_setting[1], int):
            self.resize(size_setting[0], size_setting[1])
        if name == "window":
            self.__setup_pos(name)
        else:
            # We need position to happen after resize as previous
            # may be refused by window manager => mini player as bottom
            GLib.idle_add(self.__setup_pos, name)

    def __setup_pos(self, name):
        """
            Set window position
            @param name as str
        """
        position_setting = App().settings.get_value("%s-position" % name)
        if len(position_setting) == 2 and\
           isinstance(position_setting[0], int) and\
           isinstance(position_setting[1], int):
            self.move(position_setting[0], position_setting[1])

    # FIXME Remove this, handled by MPRIS in GNOME 3.26
    def __setup_media_keys(self):
        """
            Setup media player keys
        """
        self.__media_keys_busnames = [
            "org.gnome.SettingDaemon.MediaKeys",
            "org.gnome.SettingsDaemon",
        ]

        self.__get_media_keys_proxy()

    # FIXME Remove this, handled by MPRIS in GNOME 3.26
    def __get_media_keys_proxy(self):
        if self.__media_keys_busnames:
            bus_name = self.__media_keys_busnames.pop(0)
            try:
                bus = App().get_dbus_connection()
                Gio.DBusProxy.new(
                    bus,
                    Gio.DBusProxyFlags.DO_NOT_LOAD_PROPERTIES,
                    None,
                    bus_name,
                    "/org/gnome/SettingsDaemon/MediaKeys",
                    "org.gnome.SettingsDaemon.MediaKeys",
                    None,
                    self.__on_get_proxy,
                )

            except Exception as e:
                Logger.error("Window::__setup_media_keys(): %s" % e)

    # FIXME Remove this, handled by MPRIS in GNOME 3.26
    def __on_get_proxy(self, source, result):
        try:
            self.__mediakeys = source.new_finish(result)
        except Exception as e:
            self.__mediakeys = None
            Logger.error("Window::__on_get_proxy(): %s" % e)
        else:
            if self.__mediakeys.get_name_owner():
                self.__grab_media_keys()
                self.__mediakeys.connect('g-signal', self.__mediakey_signal)
            else:
                self.__mediakeys = None
                self.__get_media_keys_proxy()

    # FIXME Remove this, handled by MPRIS in GNOME 3.26
    def __grab_media_keys(self):
        if not self.__mediakeys:
            return
        self.__mediakeys.call(
            "GrabMediaPlayerKeys",
            GLib.Variant("(su)", ("org.gnome.Lollypop", 0)),
            Gio.DBusCallFlags.NONE,
            -1,
            None,
            None,
        )

    def __mediakey_signal(self, proxy, sender, signal, param, userdata=None):
        if signal != "MediaPlayerKeyPressed":
            return

        app, action = param.unpack()
        if app == "org.gnome.Lollypop":
            if action == "Play":
                App().player.play_pause()
            elif action == "Next":
                App().player.next()
            elif action == "Stop":
                App().player.stop()
            elif action == "Previous":
                App().player.prev()

    def __setup_content(self):
        """
            Setup window content
        """
        self.__container = Container()
        self.__container.show()
        self.__vgrid = Gtk.Grid()
        self.__vgrid.set_orientation(Gtk.Orientation.VERTICAL)
        self.__vgrid.show()
        self.__toolbar = Toolbar()
        self.__toolbar.show()
        if App().settings.get_value("disable-csd") or is_unity():
            self.__vgrid.add(self.__toolbar)
        else:
            self.set_titlebar(self.__toolbar)
            self.__toolbar.set_show_close_button(
                not App().settings.get_value("disable-csd"))
        self.__vgrid.add(self.__main_stack)
        self.add(self.__vgrid)
        self.__main_stack.add_named(self.__container, "main")
        self.__main_stack.set_visible_child_name("main")
        self.drag_dest_set(Gtk.DestDefaults.DROP | Gtk.DestDefaults.MOTION,
                           [], Gdk.DragAction.MOVE)
        self.drag_dest_add_text_targets()
        self.connect("drag-data-received", self.__on_drag_data_received)
        self.connect("drag-leave", self.__on_drag_leave)

    def __on_drag_data_received(self, widget, context, x, y, data, info, time):
        """
            Import values
            @param widget as Gtk.Widget
            @param context as Gdk.DragContext
            @param x as int
            @param y as int
            @param data as Gtk.SelectionData
            @param info as int
            @param time as int
        """
        try:
            from lollypop.collectionimporter import CollectionImporter
            from urllib.parse import urlparse
            importer = CollectionImporter()
            uris = []
            for uri in data.get_text().strip("\n").split("\r"):
                parsed = urlparse(uri)
                if parsed.scheme in ["file", "sftp", "smb", "webdav"]:
                    uris.append(uri)
            if uris:
                task_helper = TaskHelper()
                task_helper.run(importer.add, uris,
                                callback=(App().scanner.update,))
        except:
            pass

    def __on_drag_leave(self, widget, context, time):
        """
            Remove style
            @param widget as Gtk.Widget
            @param context as Gdk.DragContext
            @param time as int
        """
        self.__main_stack.set_visible_child_name("main")

    def __on_hide(self, window):
        """
            Remove callbacks we don"t want to save an invalid value on hide
            @param window as GtkApplicationWindow
        """
        if self.__signal1 is not None:
            self.disconnect(self.__signal1)
            self.__signal1 = None
        if self.__signal2 is not None:
            self.disconnect(self.__signal2)
            self.__signal2 = None

    def __on_configure_event(self, widget, event):
        """
            Delay event
            @param: widget as Gtk.Window
            @param: event as Gdk.Event
        """
        if self.__timeout_configure:
            GLib.source_remove(self.__timeout_configure)
            self.__timeout_configure = None
        self.responsive_design()
        if not self.is_maximized():
            self.__timeout_configure = GLib.timeout_add(
                1000,
                self.__save_size_position,
                widget)

    def __save_size_position(self, widget):
        """
            Save window state, update current view content size
            @param: widget as Gtk.Window
        """
        self.__timeout_configure = None
        size = widget.get_size()
        if self.__main_stack.is_visible():
            name = "window"
        else:
            name = "mini"
        if self.__miniplayer is not None:
            self.__miniplayer.update_cover(size[0])
        App().settings.set_value("%s-size" % name,
                                 GLib.Variant("ai", [size[0], size[1]]))

        position = widget.get_position()
        App().settings.set_value("%s-position" % name,
                                 GLib.Variant("ai",
                                              [position[0], position[1]]))

    def __connect_state_signals(self):
        """
            Connect state signals
        """
        self.responsive_design()
        if self.__signal1 is None:
            self.__signal1 = self.connect("window-state-event",
                                          self.__on_window_state_event)
        if self.__signal2 is None:
            self.__signal2 = self.connect("configure-event",
                                          self.__on_configure_event)

    def __on_window_state_event(self, widget, event):
        """
            Save maximised state
        """
        App().settings.set_boolean("window-maximized",
                                   "GDK_WINDOW_STATE_MAXIMIZED" in
                                   event.new_window_state.value_names)
        if event.changed_mask & Gdk.WindowState.FOCUSED and \
           event.new_window_state & Gdk.WindowState.FOCUSED:
            # FIXME Remove this, handled by MPRIS in GNOME 3.26
            self.__grab_media_keys()

    def __on_destroyed_window(self, widget):
        """
            Save paned widget width
            @param widget as unused, data as unused
        """
        if self.__was_maximized and\
           self.__main_stack.get_visible_child_name() == "mini":
            App().settings.set_boolean("window-maximized", True)
        self.__container.save_internals()

    def __on_seek_action(self, action, param):
        """
            Seek in stream
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
        """
        seconds = param.get_int32()
        position = App().player.position
        seek = position / Gst.SECOND + seconds
        if seek < 0:
            seek = 0
        if seek > App().player.current_track.duration:
            seek = App().player.current_track.duration - 2
        App().player.seek(seek)
        if App().player.current_track.id is not None:
            self.__toolbar.update_position(seek)

    def __on_player_action(self, action, param):
        """
            Change player state
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
        """
        string = param.get_string()
        if string == "play_pause":
            App().player.play_pause()
        elif string == "play":
            App().player.play()
        elif string == "stop":
            App().player.stop()
        elif string == "next":
            App().player.next()
        elif string == "next_album":
            App().player.skip_album()
        elif string == "prev":
            App().player.prev()
        elif string == "locked":
            App().player.lock()
        elif string == "lyrics":
            App().window.container.show_lyrics()
        elif string == "show_sidebar":
            value = App().settings.get_value("show-sidebar")
            App().settings.set_value("show-sidebar",
                                     GLib.Variant("b", not value))
            self.__container.show_sidebar(not value)
        elif string == "filter":
            if self.container.view is not None:
                self.container.view.enable_filter()
        elif string == "volume":
            self.__toolbar.title.show_hide_volume_control()
        elif string == "current_artist":
            if App().player.current_track.id is not None and\
                    App().player.current_track.id > 0:
                artist_ids = App().player.current_track.album.artist_ids
                self.container.show_artists_albums(artist_ids)
        elif string == "show_genres":
            state = not App().settings.get_value("show-genres")
            App().settings.set_value("show-genres",
                                     GLib.Variant("b", state))
            self.__container.show_genres(state)
        elif string == "loved":
            track = App().player.current_track
            if track.id is not None and track.id >= 0:
                track.set_loved(not track.loved)
                if App().notify is not None:
                    if track.loved:
                        heart = "❤"
                    else:
                        heart = "♡"
                    App().notify.send("%s - %s: %s" %
                                      (", ".join(track.artists),
                                       track.name,
                                       heart))

    def __on_realize(self, widget):
        """
            Run scanner on realize
            @param widget as Gtk.Widget
        """
        self.setup_window()
        if App().settings.get_value("auto-update") or App().tracks.is_empty():
            # Delayed, make python segfault on sys.exit() otherwise
            # No idea why, maybe scanner using Gstpbutils before Gstreamer
            # initialisation is finished...
            GLib.timeout_add(2000, App().scanner.update)
        # We delay update_list_one() to be sure inital stacked mode is set
        GLib.timeout_add(200, self.__container.update_list_one)
        # Here we ignore initial configure events
        GLib.timeout_add(200, self.__connect_state_signals)

    def __on_current_changed(self, player):
        """
            Update toolbar
            @param player as Player
        """
        if App().player.current_track.id is None:
            self.set_title("Lollypop")
        else:
            artists = ", ".join(player.current_track.artists)
            self.set_title("%s - %s" % (artists, "Lollypop"))
