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

from gi.repository import Gtk, Gdk, GLib, Gio, Gst

from datetime import datetime

from lollypop.define import Lp, ArtSize, Type
from lollypop.pop_next import NextPopover
from lollypop.controllers import InfoController, PlaybackController
from lollypop.controllers import ProgressController


class FullScreen(Gtk.Window, InfoController,
                 PlaybackController, ProgressController):
    """
        Show a fullscreen window showing current track context
    """

    def __init__(self, app, parent):
        """
            Init window and set transient for parent
            @param app as Gio.Application
            @param parent as Gtk.window
        """
        Gtk.Window.__init__(self)
        self.set_title("Lollypop")
        PlaybackController.__init__(self)
        ProgressController.__init__(self)
        self.set_application(app)
        self.__timeout1 = None
        self.__timeout2 = None
        self.__signal1_id = None
        self.__signal2_id = None
        self.set_decorated(False)
        self.__parent = parent

        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/FullScreen.ui")
        builder.connect_signals(self)

        # Calculate cover size
        screen = Gdk.Screen.get_default()
        monitor = screen.get_primary_monitor()
        geometry = screen.get_monitor_geometry(monitor)
        # We want 500 and 200 in full hd
        if geometry.width > geometry.height:
            artsize = int(ArtSize.FULLSCREEN*geometry.width/1920)
        else:
            artsize = int(ArtSize.FULLSCREEN*geometry.height/1920)
        InfoController.__init__(self, artsize)

        self._play_btn = builder.get_object("play_btn")
        self._next_btn = builder.get_object("next_btn")
        self._prev_btn = builder.get_object("prev_btn")
        self._next_popover = NextPopover()
        self._next_popover.set_position(Gtk.PositionType.BOTTOM)
        self._play_image = builder.get_object("play_image")
        self._pause_image = builder.get_object("pause_image")
        close_btn = builder.get_object("close_btn")
        close_btn.connect("clicked", self.__destroy)
        self._cover = builder.get_object("cover")
        self._title_label = builder.get_object("title")
        self._artist_label = builder.get_object("artist")
        self._album_label = builder.get_object("album")

        self._datetime = builder.get_object("datetime")

        self._progress = builder.get_object("progress_scale")
        self._timelabel = builder.get_object("playback")
        self._total_time_label = builder.get_object("duration")
        self.connect("key-release-event", self.__on_key_release_event)
        self.add(builder.get_object("widget"))

    def do_show(self):
        """
            Init signals, set color and go party mode if nothing is playing
        """
        self.__signal1_id = Lp().player.connect("current-changed",
                                                self.on_current_changed)
        self.__signal2_id = Lp().player.connect("status-changed",
                                                self.on_status_changed)
        if Lp().player.current_track.id is None:
            Lp().player.set_party(True)
        else:
            self.on_status_changed(Lp().player)
            self.on_current_changed(Lp().player)
        if self.__timeout1 is None:
            self.__timeout1 = GLib.timeout_add(1000, self._update_position)
        Gtk.Window.do_show(self)
        self.__parent.set_skip_pager_hint(True)
        self.__parent.set_skip_taskbar_hint(True)
        if self.__timeout2 is None:
            try:
                interface = Gio.Settings.new("org.gnome.desktop.interface")
                show_seconds = interface.get_value("clock-show-seconds")
            except:
                show_seconds = False
            self.__update_datetime(show_seconds)
            self.__timeout2 = GLib.timeout_add(1000,
                                               self.__update_datetime,
                                               show_seconds)
        self._update_position(Lp().player.position/Gst.SECOND)
        self.fullscreen()
        self._next_popover.set_relative_to(self._album_label)
        if Lp().player.next_track.id != Type.RADIOS:
            self._next_popover.show()

        # Disable screensaver (idle)
        Lp().inhibitor.manual_inhibit(suspend=False, idle=True)

    def do_hide(self):
        """
            Remove signals and unset color
        """
        self.__parent.set_skip_pager_hint(False)
        self.__parent.set_skip_taskbar_hint(False)
        Gtk.Window.do_hide(self)
        if self.__signal1_id is not None:
            Lp().player.disconnect(self.__signal1_id)
            self.__signal1_id = None
        if self.__signal2_id is not None:
            Lp().player.disconnect(self.__signal2_id)
            self.__signal2_id = None
        if self.__timeout1 is not None:
            GLib.source_remove(self.__timeout1)
            self.__timeout1 = None
        if self.__timeout2 is not None:
            GLib.source_remove(self.__timeout2)
        self._next_popover.set_relative_to(None)
        self._next_popover.hide()
        Lp().inhibitor.manual_uninhibit()

    def show_hide_volume_control(self):
        """
            Show/Hide volume control
        """
        self._show_volume_control = not self._show_volume_control
        self._update_state()

    def on_current_changed(self, player):
        """
            Update infos and show/hide popover
            @param player as Player
        """
        InfoController.on_current_changed(self, player)
        ProgressController.on_current_changed(self, player)
        if player.current_track.id is not None:
            album_name = player.current_track.album.name
            if player.current_track.year:
                album_name += " (%s)" % player.current_track.year
            self._album_label.set_text(album_name)
        # Do not show next popover non internal tracks as
        # tags will be readed on the fly
        if player.next_track.id is not None and player.next_track.id >= 0:
            self._next_popover.update()
            self._next_popover.show()
        else:
            self._next_popover.hide()

#######################
# PRIVATE             #
#######################
    def __update_datetime(self, show_seconds=False):
        """
            Update datetime in headerbar
            @param show_seconds as bool
        """
        now = datetime.now()
        if show_seconds:
            self._datetime.set_label(now.strftime("%a %d %b, %X"))
        else:
            self._datetime.set_label(now.strftime("%a %d %b, %X")[:-3])
        if self.__timeout2 is None:
            self.__timeout2 = GLib.timeout_add(60000, self.__update_datetime)
            return False
        return True

    def __destroy(self, widget):
        """
            Destroy self
            @param widget as Gtk.Button
        """
        self.destroy()

    def __on_key_release_event(self, widget, event):
        """
            Destroy window if Esc
            @param widget as Gtk.Widget
            @param event as Gdk.event
        """
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()
