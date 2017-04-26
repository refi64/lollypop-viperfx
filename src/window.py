# Copyright (c) 2014-2017 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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
from lollypop.define import Lp, WindowSize
from lollypop.toolbar import Toolbar
from lollypop.utils import is_unity, set_loved, is_loved


class Window(Gtk.ApplicationWindow, Container):
    """
        Main window
    """

    def __init__(self):
        """
            Init window
        """
        Container.__init__(self)
        self.__signal1 = None
        self.__signal2 = None
        self.__timeout = None
        self.__was_maximized = False
        Gtk.ApplicationWindow.__init__(self,
                                       application=Lp(),
                                       title="Lollypop")
        self.connect("hide", self.__on_hide)
        Lp().player.connect("current-changed", self.__on_current_changed)
        self.__timeout_configure = None
        seek_action = Gio.SimpleAction.new("seek",
                                           GLib.VariantType.new("i"))
        seek_action.connect("activate", self.__on_seek_action)
        Lp().add_action(seek_action)
        player_action = Gio.SimpleAction.new("shortcut",
                                             GLib.VariantType.new("s"))
        player_action.connect("activate", self.__on_player_action)
        Lp().add_action(player_action)

        self.__setup_global_shortcuts()

        self.__main_stack = Gtk.Stack()
        self.__main_stack.set_transition_duration(1000)
        self.__main_stack.set_transition_type(
                                             Gtk.StackTransitionType.CROSSFADE)
        self.__main_stack.show()

        self.__setup_content()
        self.setup_window()
        self.__setup_media_keys()
        self.__enabled_shortcuts = False
        self.enable_global_shortcuts(True)

        self.connect("destroy", self.__on_destroyed_window)
        self.connect("realize", self.__on_realize)

    def setup_menu(self, menu):
        """
            Add an application menu to window
            @parma: menu as Gio.Menu
        """
        self.__toolbar.setup_menu(menu)

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
                Lp().set_accels_for_action("app.seek(10)", ["Left"])
                Lp().set_accels_for_action("app.seek(20)", ["<Control>Left"])
                Lp().set_accels_for_action("app.seek(-10)", ["Right"])
                Lp().set_accels_for_action("app.seek(-20)", ["<Control>Right"])
            else:
                Lp().set_accels_for_action("app.seek(10)", ["Right"])
                Lp().set_accels_for_action("app.seek(20)", ["<Control>Right"])
                Lp().set_accels_for_action("app.seek(-10)", ["Left"])
                Lp().set_accels_for_action("app.seek(-20)", ["<Control>Left"])

            Lp().set_accels_for_action("app.shortcut::play_pause",
                                       ["space", "c"])
            Lp().set_accels_for_action("app.shortcut::play", ["x"])
            Lp().set_accels_for_action("app.shortcut::stop", ["v"])
            Lp().set_accels_for_action("app.shortcut::next", ["n"])
            Lp().set_accels_for_action("app.shortcut::prev", ["p"])
            Lp().set_accels_for_action("app.shortcut::loved", ["l"])
        else:
            Lp().set_accels_for_action("app.seek(10)", [None])
            Lp().set_accels_for_action("app.seek(20)", [None])
            Lp().set_accels_for_action("app.seek(-10)", [None])
            Lp().set_accels_for_action("app.seek(-20)", [None])
            Lp().set_accels_for_action("app.shortcut::play_pause", [None])
            Lp().set_accels_for_action("app.shortcut::play", [None])
            Lp().set_accels_for_action("app.shortcut::stop", [None])
            Lp().set_accels_for_action("app.shortcut::play_pause", [None])
            Lp().set_accels_for_action("app.shortcut::play", [None])
            Lp().set_accels_for_action("app.shortcut::stop", [None])
            Lp().set_accels_for_action("app.shortcut::next", [None])
            Lp().set_accels_for_action("app.shortcut::next_album", [None])
            Lp().set_accels_for_action("app.shortcut::prev", [None])
            Lp().set_accels_for_action("app.shortcut::loved", [None])

    def setup_window(self):
        """
            Setup window position and size, callbacks
        """
        self.__setup_pos_size("window")
        if Lp().settings.get_value("window-maximized"):
            self.maximize()

        if self.__signal1 is None:
            self.__signal1 = self.connect("window-state-event",
                                          self.__on_window_state_event)
        if self.__signal2 is None:
            self.__signal2 = self.connect("configure-event",
                                          self.__on_configure_event)

    def responsive_design(self):
        """
            Handle responsive design
        """
        size = self.get_size()
        self.__toolbar.set_content_width(size[0])
        self.__show_miniplayer(size[0] < WindowSize.MEDIUM)
        self.__show_subtoolbar(size[0] < WindowSize.MONSTER and
                               size[0] > WindowSize.MEDIUM)

    def set_mini(self):
        """
            Set mini player on/off
        """
        if Lp().player.current_track.id is None:
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
        if event.type == Gdk.EventType.FOCUS_CHANGE and self.view is not None:
            self.view.disable_overlay()
            Lp().player.preview.set_state(Gst.State.NULL)
        Gtk.ApplicationWindow.do_event(self, event)

############
# Private  #
############
    def __setup_global_shortcuts(self):
        """
            Setup global shortcuts
        """
        Lp().set_accels_for_action("app.shortcut::locked", ["<Control>l"])
        Lp().set_accels_for_action("app.shortcut::filter", ["<Control>i"])
        Lp().set_accels_for_action("app.shortcut::volume", ["<Alt>v"])
        Lp().set_accels_for_action("app.shortcut::next_album", ["<Control>n"])
        Lp().set_accels_for_action("app.shortcut::show_genres", ["<Control>g"])
        Lp().set_accels_for_action("app.shortcut::hide_pane", ["<Control>h"])
        Lp().set_accels_for_action("app.update_db", ["<Control>u"])
        Lp().set_accels_for_action("app.settings", ["<Control>s"])
        Lp().set_accels_for_action("app.fullscreen", ["F11", "F7"])
        Lp().set_accels_for_action("app.mini", ["<Control>m"])
        Lp().set_accels_for_action("app.about", ["F3"])
        Lp().set_accels_for_action("app.shortcuts", ["F2"])
        Lp().set_accels_for_action("app.help", ["F1"])
        Lp().set_accels_for_action("app.quit", ["<Control>q"])

    def __show_subtoolbar(self, show):
        """
            Show/hide subtoolbar
            @param show as bool
        """
        is_visible = self.__subtoolbar.is_visible()
        if show and not is_visible:
            from lollypop.miniplayer import MiniPlayer
            mini = MiniPlayer()
            mini.show()
            self.__subtoolbar.add(mini)
            self.__subtoolbar.show()
        elif not show and is_visible:
            children = self.__subtoolbar.get_children()
            if children:
                children[0].destroy()
            self.__subtoolbar.hide()

    def __show_miniplayer(self, show):
        """
            Show/hide miniplayer
            @param show as bool
        """
        mini = self.__main_stack.get_child_by_name("mini")
        if show:
            if mini is not None:
                if self.__timeout is not None:
                    GLib.source_remove(self.__timeout)
            else:
                from lollypop.miniplayer import MiniPlayer
                mini = MiniPlayer()
                self.__main_stack.add_named(mini, "mini")
            self.__timeout = None
            mini.show()
            self.__main_stack.set_visible_child_name("mini")
            self.__toolbar.set_show_close_button(False)
        elif mini is not None and not show and self.__timeout is None:
            self.__main_stack.set_visible_child_name("main")
            self.__toolbar.set_show_close_button(
                                not Lp().settings.get_value("disable-csd") and
                                not is_unity())
            self.__timeout = GLib.timeout_add(1000, mini.destroy)

    def __setup_pos_size(self, name):
        """
            Set window pos and size based on name
            @param name as str
        """
        size_setting = Lp().settings.get_value("%s-size" % name)
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
        position_setting = Lp().settings.get_value("%s-position" % name)
        if len(position_setting) == 2 and\
           isinstance(position_setting[0], int) and\
           isinstance(position_setting[1], int):
            self.move(position_setting[0], position_setting[1])

    def __setup_media_keys(self):
        """
            Setup media player keys
        """
        self.__proxy = Gio.DBusProxy.new_sync(Gio.bus_get_sync(Gio.BusType.
                                                               SESSION, None),
                                              Gio.DBusProxyFlags.NONE,
                                              None,
                                              "org.gnome.SettingsDaemon",
                                              "/org/gnome/SettingsDaemon/"
                                              "MediaKeys",
                                              "org.gnome.SettingsDaemon."
                                              "MediaKeys",
                                              None)
        self.__grab_media_player_keys()
        try:
            self.__proxy.connect("g-signal", self.__handle_media_keys)
        except GLib.GError:
            # We cannot grab media keys if no settings daemon is running
            pass

    def __grab_media_player_keys(self):
        """
            Do key grabbing
        """
        try:
            self.__proxy.call_sync("GrabMediaPlayerKeys",
                                   GLib.Variant("(su)", ("Lollypop", 0)),
                                   Gio.DBusCallFlags.NONE,
                                   -1,
                                   None)
        except GLib.GError:
            # We cannot grab media keys if no settings daemon is running
            pass

    def __handle_media_keys(self, proxy, sender, signal, parameters):
        """
            Do player actions in response to media key pressed
        """
        if signal != "MediaPlayerKeyPressed":
            print("Received an unexpected signal\
                   \"%s\" from media player".format(signal))
            return
        response = parameters.get_child_value(1).get_string()
        if "Play" in response:
            Lp().player.play_pause()
        elif "Stop" in response:
            Lp().player.stop()
        elif "Next" in response:
            Lp().player.next()
        elif "Previous" in response:
            Lp().player.prev()

    def __setup_content(self):
        """
            Setup window content
        """
        self.set_default_icon_name("lollypop")
        vgrid = Gtk.Grid()
        vgrid.set_orientation(Gtk.Orientation.VERTICAL)
        vgrid.show()
        self.__toolbar = Toolbar()
        self.__toolbar.show()
        self.__subtoolbar = Gtk.Grid()
        if Lp().settings.get_value("disable-csd") or is_unity():
            vgrid.add(self.__toolbar)
        else:
            self.set_titlebar(self.__toolbar)
            self.__toolbar.set_show_close_button(
                                    not Lp().settings.get_value("disable-csd"))
        vgrid.add(self.__main_stack)
        vgrid.add(self.__subtoolbar)
        self.add(vgrid)
        self.__main_stack.add_named(self._paned_main_list, "main")
        self.__main_stack.set_visible_child_name("main")

    def __on_hide(self, window):
        """
            Remove callbacks (we don"t want to save an invalid value on hide
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
        if size[0] > WindowSize.MEDIUM:
            name = "window"
        else:
            name = "mini"
        Lp().settings.set_value("%s-size" % name,
                                GLib.Variant("ai", [size[0], size[1]]))

        position = widget.get_position()
        Lp().settings.set_value("%s-position" % name,
                                GLib.Variant("ai",
                                             [position[0], position[1]]))

    def __on_window_state_event(self, widget, event):
        """
            Save maximised state
        """
        Lp().settings.set_boolean("window-maximized",
                                  "GDK_WINDOW_STATE_MAXIMIZED" in
                                  event.new_window_state.value_names)

    def __on_destroyed_window(self, widget):
        """
            Save paned widget width
            @param widget as unused, data as unused
        """
        if self.__was_maximized and\
           self.__main_stack.get_visible_child_name() == "mini":
            Lp().settings.set_boolean("window-maximized", True)
        main_pos = self._paned_main_list.get_position()
        listview_pos = self._paned_list_view.get_position()
        listview_pos = listview_pos if listview_pos > 100 else 100
        Lp().settings.set_value("paned-mainlist-width",
                                GLib.Variant("i",
                                             main_pos))
        Lp().settings.set_value("paned-listview-width",
                                GLib.Variant("i",
                                             listview_pos))

    def __on_seek_action(self, action, param):
        """
            Seek in stream
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
        """
        seconds = param.get_int32()
        position = Lp().player.position
        seek = position/1000000/60+seconds
        if seek < 0:
            seek = 0
        if seek > Lp().player.current_track.duration:
            seek = Lp().player.current_track.duration - 2
        Lp().player.seek(seek)
        if Lp().player.current_track.id is not None:
            self.__toolbar.update_position(seek*60)

    def __on_player_action(self, action, param):
        """
            Change player state
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
        """
        string = param.get_string()
        if string == "play_pause":
            Lp().player.play_pause()
        elif string == "play":
            Lp().player.play()
        elif string == "stop":
            Lp().player.stop()
        elif string == "next":
            Lp().player.next()
        elif string == "next_album":
            Lp().player.skip_album()
        elif string == "prev":
            Lp().player.prev()
        elif string == "locked":
            Lp().player.lock()
        elif string == "hide_pane":
            self._hide_pane()
        elif string == "filter":
            if self.view is not None:
                self.view.set_search_mode()
        elif string == "volume":
            self.__toolbar.show_hide_volume_control()
        elif string == "show_genres":
            state = not Lp().settings.get_value("show-genres")
            Lp().settings.set_value("show-genres",
                                    GLib.Variant("b", state))
            Lp().window.show_genres(state)
        elif string == "loved":
            if Lp().player.current_track.id is not None and\
                    Lp().player.current_track.id >= 0:
                isloved = is_loved(Lp().player.current_track.id)
                set_loved(Lp().player.current_track.id, not isloved)
                if Lp().notify is not None:
                    if isloved:
                        heart = "♡"
                    else:
                        heart = "❤"
                    Lp().notify.send("%s - %s: %s" % (
                                ", ".join(Lp().player.current_track.artists),
                                Lp().player.current_track.name,
                                heart))

    def __on_realize(self, widget):
        """
            Run scanner on realize
            @param widget as Gtk.Widget
        """
        if Lp().settings.get_value("auto-update") or Lp().tracks.is_empty():
            # Delayed, make python segfault on sys.exit() otherwise
            # No idea why, maybe scanner using Gstpbutils before Gstreamer
            # initialisation is finished...
            GLib.timeout_add(2000, self.update_db)

    def __on_current_changed(self, player):
        """
            Update toolbar
            @param player as Player
        """
        if Lp().player.current_track.id is None:
            self.set_title("Lollypop")
        else:
            self.set_title(", ".join(player.current_track.artists) + " - " +
                           player.current_track.title + " - Lollypop")
