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

from gi.repository import Gtk, Gio, Gdk, GLib

from lollypop.container import Container
from lollypop.define import Lp, NextContext, Shuffle, WindowSize
from lollypop.toolbar import Toolbar
from lollypop.utils import is_unity, set_loved, is_loved
from lollypop.miniplayer import MiniPlayer


class Window(Gtk.ApplicationWindow, Container):
    """
        Main window
    """

    def __init__(self, app):
        """
            Init window
        """
        Container.__init__(self)
        self._app = app
        self._signal1 = None
        self._signal2 = None
        self._timeout = None
        self._was_maximized = False
        Gtk.ApplicationWindow.__init__(self,
                                       application=app,
                                       title="Lollypop")
        self.connect('hide', self._on_hide)
        Lp().player.connect('current-changed', self._on_current_changed)
        self._timeout_configure = None
        seek_action = Gio.SimpleAction.new('seek',
                                           GLib.VariantType.new('i'))
        seek_action.connect('activate', self._on_seek_action)
        app.add_action(seek_action)
        player_action = Gio.SimpleAction.new('player',
                                             GLib.VariantType.new('s'))
        player_action.connect('activate', self._on_player_action)
        app.add_action(player_action)

        self._main_stack = Gtk.Stack()
        self._main_stack.set_transition_duration(1000)
        self._main_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._main_stack.show()

        self._setup_content()
        self.setup_window()
        self._setup_media_keys()
        self._enabled_shorcuts = False
        self.enable_global_shorcuts(True)

        self.connect('destroy', self._on_destroyed_window)
        self.connect('realize', self._on_realize)

    def setup_menu(self, menu):
        """
            Add an application menu to window
            @parma: menu as Gio.Menu
        """
        self._toolbar.setup_menu(menu)

    def enable_global_shorcuts(self, enable):
        """
            Setup global shortcuts
            @param enable as bool
        """
        if self._enabled_shorcuts == enable:
            return
        self._enabled_shorcuts = enable
        if enable:
            if Gtk.Widget.get_default_direction() == Gtk.TextDirection.RTL:
                self._app.set_accels_for_action("app.seek(10)",
                                                ["Left"])
                self._app.set_accels_for_action("app.seek(20)",
                                                ["<Control>Left"])
                self._app.set_accels_for_action("app.seek(-10)",
                                                ["Right"])
                self._app.set_accels_for_action("app.seek(-20)",
                                                ["<Control>Right"])
            else:
                self._app.set_accels_for_action("app.seek(10)",
                                                ["Right"])
                self._app.set_accels_for_action("app.seek(20)",
                                                ["<Control>Right"])
                self._app.set_accels_for_action("app.seek(-10)",
                                                ["Left"])
                self._app.set_accels_for_action("app.seek(-20)",
                                                ["<Control>Left"])

            self._app.set_accels_for_action("app.player::play_pause",
                                            ["space", "c"])
            self._app.set_accels_for_action("app.player::play",
                                            ["x"])
            self._app.set_accels_for_action("app.player::stop",
                                            ["v"])
            self._app.set_accels_for_action("app.player::next",
                                            ["n"])
            self._app.set_accels_for_action("app.player::next_album",
                                            ["<Control>n"])
            self._app.set_accels_for_action("app.player::prev",
                                            ["p"])
            self._app.set_accels_for_action("app.player::loved",
                                            ["l"])
            self._app.set_accels_for_action("app.player::locked",
                                            ["<Control>l"])
        else:
            self._app.set_accels_for_action("app.seek(10)", [None])
            self._app.set_accels_for_action("app.seek(20)", [None])
            self._app.set_accels_for_action("app.seek(-10)", [None])
            self._app.set_accels_for_action("app.seek(-20)", [None])
            self._app.set_accels_for_action("app.player::play_pause", [None])
            self._app.set_accels_for_action("app.player::play", [None])
            self._app.set_accels_for_action("app.player::stop", [None])
            self._app.set_accels_for_action("app.player::play_pause", [None])
            self._app.set_accels_for_action("app.player::play", [None])
            self._app.set_accels_for_action("app.player::stop", [None])
            self._app.set_accels_for_action("app.player::next", [None])
            self._app.set_accels_for_action("app.player::next_album", [None])
            self._app.set_accels_for_action("app.player::prev", [None])
            self._app.set_accels_for_action("app.player::loved", [None])

    def setup_window(self):
        """
            Setup window position and size, callbacks
        """
        self._setup_pos_size('window')
        if Lp().settings.get_value('window-maximized'):
            self.maximize()

        if self._signal1 is None:
            self._signal1 = self.connect("window-state-event",
                                         self._on_window_state_event)
        if self._signal2 is None:
            self._signal2 = self.connect("configure-event",
                                         self._on_configure_event)

    def responsive_design(self):
        """
            Handle responsive design
        """
        size = self.get_size()
        self._toolbar.set_content_width(size[0])
        if Lp().player.current_track.id is not None:
            self._show_miniplayer(size[0] < WindowSize.MEDIUM)
            self._show_subtoolbar(size[0] < WindowSize.MONSTER and
                                  size[0] > WindowSize.MEDIUM)

    def set_mini(self):
        """
            Set mini player on/off
        """
        if Lp().player.current_track.id is None:
            return
        was_maximized = self.is_maximized()
        if self._main_stack.get_visible_child_name() == 'main':
            if self.is_maximized():
                self.unmaximize()
                GLib.timeout_add(100, self._setup_pos_size, 'mini')
            else:
                self._setup_pos_size('mini')
        elif self._was_maximized:
            self.maximize()
        else:
            self._setup_pos_size('window')
        self._was_maximized = was_maximized

    @property
    def toolbar(self):
        """
            toolbar as Toolbar
        """
        return self._toolbar

    def do_event(self, event):
        """
            Update overlays as internal widget may not have received the signal
            @param widget as Gtk.Widget
            @param event as Gdk.event
        """
        if event.type == Gdk.EventType.FOCUS_CHANGE:
            self.disable_overlays()
        Gtk.ApplicationWindow.do_event(self, event)

############
# Private  #
############
    def _show_subtoolbar(self, show):
        """
            Show/hide subtoolbar
            @param show as bool
        """
        is_visible = self._subtoolbar.is_visible()
        if show and not is_visible:
            mini = MiniPlayer()
            mini.show()
            self._subtoolbar.add(mini)
            self._subtoolbar.show()
        elif not show and is_visible:
            children = self._subtoolbar.get_children()
            if children:
                children[0].destroy()
            self._subtoolbar.hide()

    def _show_miniplayer(self, show):
        """
            Show/hide miniplayer
            @param show as bool
        """
        mini = self._main_stack.get_child_by_name('mini')
        if show:
            if mini is not None:
                if self._timeout is not None:
                    GLib.source_remove(self._timeout)
            else:
                mini = MiniPlayer()
                self._main_stack.add_named(mini, 'mini')
            self._timeout = None
            mini.show()
            self._main_stack.set_visible_child_name('mini')
            self._toolbar.set_show_close_button(False)
        elif mini is not None and not show and self._timeout is None:
            self._main_stack.set_visible_child_name('main')
            self._toolbar.set_show_close_button(
                                    not Lp().settings.get_value('disable-csd'))
            self._timeout = GLib.timeout_add(1000, mini.destroy)

    def _setup_pos_size(self, name):
        """
            Set window pos and size based on name
            @param name as str
        """
        size_setting = Lp().settings.get_value('%s-size' % name)
        if len(size_setting) == 2 and\
           isinstance(size_setting[0], int) and\
           isinstance(size_setting[1], int):
            self.resize(size_setting[0], size_setting[1])
        if name == 'window':
            self._setup_pos(name)
        else:
            # We need position to happen after resize as previous
            # may be refused by window manager => mini player as bottom
            GLib.idle_add(self._setup_pos, name)

    def _setup_pos(self, name):
        """
            Set window position
            @param name as str
        """
        position_setting = Lp().settings.get_value('%s-position' % name)
        if len(position_setting) == 2 and\
           isinstance(position_setting[0], int) and\
           isinstance(position_setting[1], int):
            self.move(position_setting[0], position_setting[1])

    def _setup_media_keys(self):
        """
            Setup media player keys
        """
        self._proxy = Gio.DBusProxy.new_sync(Gio.bus_get_sync(Gio.BusType.
                                                              SESSION, None),
                                             Gio.DBusProxyFlags.NONE,
                                             None,
                                             'org.gnome.SettingsDaemon',
                                             '/org/gnome/SettingsDaemon/'
                                             'MediaKeys',
                                             'org.gnome.SettingsDaemon.'
                                             'MediaKeys',
                                             None)
        self._grab_media_player_keys()
        try:
            self._proxy.connect('g-signal', self._handle_media_keys)
        except GLib.GError:
            # We cannot grab media keys if no settings daemon is running
            pass

    def _grab_media_player_keys(self):
        """
            Do key grabbing
        """
        try:
            self._proxy.call_sync('GrabMediaPlayerKeys',
                                  GLib.Variant('(su)', ('Lollypop', 0)),
                                  Gio.DBusCallFlags.NONE,
                                  -1,
                                  None)
        except GLib.GError:
            # We cannot grab media keys if no settings daemon is running
            pass

    def _handle_media_keys(self, proxy, sender, signal, parameters):
        """
            Do player actions in response to media key pressed
        """
        if signal != 'MediaPlayerKeyPressed':
            print('Received an unexpected signal\
                   \'%s\' from media player'.format(signal))
            return
        response = parameters.get_child_value(1).get_string()
        if 'Play' in response:
            Lp().player.play_pause()
        elif 'Stop' in response:
            Lp().player.stop()
        elif 'Next' in response:
            Lp().player.next()
        elif 'Previous' in response:
            Lp().player.prev()

    def _setup_content(self):
        """
            Setup window content
        """
        self.set_default_icon_name('lollypop')
        vgrid = Gtk.Grid()
        vgrid.set_orientation(Gtk.Orientation.VERTICAL)
        vgrid.show()
        self._toolbar = Toolbar(self.get_application())
        self._toolbar.show()
        self._subtoolbar = Gtk.Grid()
        if Lp().settings.get_value('disable-csd') or is_unity():
            vgrid.add(self._toolbar)
        else:
            self.set_titlebar(self._toolbar)
            self._toolbar.set_show_close_button(
                                    not Lp().settings.get_value('disable-csd'))
        vgrid.add(self._main_stack)
        vgrid.add(self._subtoolbar)
        self.add(vgrid)
        self._main_stack.add_named(self.main_widget(), 'main')
        self._main_stack.set_visible_child_name('main')

    def _on_hide(self, window):
        """
            Remove callbacks (we don't want to save an invalid value on hide
            @param window as GtkApplicationWindow
        """
        if self._signal1 is not None:
            self.disconnect(self._signal1)
            self._signal1 = None
        if self._signal2 is not None:
            self.disconnect(self._signal2)
            self._signal2 = None

    def _on_configure_event(self, widget, event):
        """
            Delay event
            @param: widget as Gtk.Window
            @param: event as Gdk.Event
        """
        if self._timeout_configure:
            GLib.source_remove(self._timeout_configure)
            self._timeout_configure = None
        self.responsive_design()
        if not self.is_maximized():
            self._timeout_configure = GLib.timeout_add(
                                                   1000,
                                                   self._save_size_position,
                                                   widget)

    def _save_size_position(self, widget):
        """
            Save window state, update current view content size
            @param: widget as Gtk.Window
        """
        self._timeout_configure = None
        size = widget.get_size()
        if size[0] > WindowSize.MEDIUM:
            name = 'window'
        else:
            name = 'mini'
        Lp().settings.set_value('%s-size' % name,
                                GLib.Variant('ai', [size[0], size[1]]))

        position = widget.get_position()
        Lp().settings.set_value('%s-position' % name,
                                GLib.Variant('ai',
                                             [position[0], position[1]]))

    def _on_window_state_event(self, widget, event):
        """
            Save maximised state
        """
        Lp().settings.set_boolean('window-maximized',
                                  'GDK_WINDOW_STATE_MAXIMIZED' in
                                  event.new_window_state.value_names)

    def _on_destroyed_window(self, widget):
        """
            Save paned widget width
            @param widget as unused, data as unused
        """
        if self._was_maximized and\
           self._main_stack.get_visible_child_name() == 'mini':
            Lp().settings.set_boolean('window-maximized', True)
        Lp().settings.set_value('paned-mainlist-width',
                                GLib.Variant('i',
                                             self._paned_main_list.
                                             get_position()))
        Lp().settings.set_value('paned-listview-width',
                                GLib.Variant('i',
                                             self._paned_list_view.
                                             get_position()))

    def _on_seek_action(self, action, param):
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
            self._toolbar.update_position(seek*60)

    def _on_player_action(self, action, param):
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
            # In party or shuffle, just update next track
            if Lp().player.is_party() or\
                    Lp().settings.get_enum('shuffle') == Shuffle.TRACKS:
                Lp().player.set_next()
                # We send this signal to update next popover
                Lp().player.emit('queue-changed')
            else:
                Lp().player.set_next_context(NextContext.START_NEW_ALBUM)
                Lp().player.set_next()
                Lp().player.next()
        elif string == "prev":
            Lp().player.prev()
        elif string == "locked":
            Lp().player.lock()
        elif string == "loved":
            if Lp().player.current_track.id is not None:
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

    def _on_realize(self, widget):
        """
            Run scanner on realize
            @param widget as Gtk.Widget
        """
        if Lp().settings.get_value('auto-update') or Lp().tracks.is_empty():
            # Delayed, make python segfault on sys.exit() otherwise
            # No idea why, maybe scanner using Gstpbutils before Gstreamer
            # initialisation is finished...
            GLib.timeout_add(2000, self.update_db)

    def _on_current_changed(self, player):
        """
            Update toolbar
            @param player as Player
        """
        if Lp().player.current_track.id is None:
            self.set_title("Lollypop")
        else:
            self.set_title(", ".join(player.current_track.artists) + " - " +
                           player.current_track.title + " - Lollypop")
