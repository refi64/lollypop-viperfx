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

from gi.repository import Gtk, Gdk, GLib, Gio, Gst

from datetime import datetime
from gettext import gettext as _

from lollypop.define import App, ArtSize, RowListType
from lollypop.view_albums_list import AlbumsListView
from lollypop.helper_art import ArtHelperEffect
from lollypop.controller_information import InformationController
from lollypop.controller_playback import PlaybackController
from lollypop.controller_progress import ProgressController
from lollypop.logger import Logger


class FullScreen(Gtk.Window, InformationController,
                 PlaybackController, ProgressController):
    """
        Show a fullscreen window showing current track context
    """

    def __init__(self, app):
        """
            Init window for app
            @param app as Gio.Application
        """
        Gtk.Window.__init__(self)
        self.set_title("Lollypop")
        rotate_album = App().settings.get_value("rotate-fullscreen-album")
        PlaybackController.__init__(self)
        ProgressController.__init__(self)
        if rotate_album:
            InformationController.__init__(self, False,
                                           ArtHelperEffect.ROUNDED)
        else:
            InformationController.__init__(self, False, ArtHelperEffect.NONE)
        self.set_application(app)
        self.__timeout_id = None
        self.__signal1_id = self.__signal2_id = self.__signal3_id = None
        self.set_decorated(False)

        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/FullScreen.ui")
        builder.connect_signals(self)

        # Calculate cover size
        screen = Gdk.Screen.get_default()
        monitor = screen.get_monitor_at_window(App().window.get_window())
        geometry = screen.get_monitor_geometry(monitor)
        # We want 500 and 200 in full hd
        if geometry.width > geometry.height:
            self.__artsize = int(ArtSize.FULLSCREEN * geometry.height / 1080)
        else:
            self.__artsize = int(ArtSize.FULLSCREEN * geometry.width / 1920)
        self.__font_size = int(14 * geometry.height / 1080)
        widget = builder.get_object("widget")
        grid = builder.get_object("grid")
        self._play_button = builder.get_object("play_btn")
        self._next_button = builder.get_object("next_btn")
        self._prev_button = builder.get_object("prev_btn")
        self._play_image = builder.get_object("play_image")
        self._pause_image = builder.get_object("pause_image")
        close_btn = builder.get_object("close_btn")
        preferences = Gio.Settings.new("org.gnome.desktop.wm.preferences")
        layout = preferences.get_value("button-layout").get_string()
        if layout.split(":")[0] == "close":
            grid.attach(close_btn, 0, 0, 1, 1)
            close_btn.set_property("halign", Gtk.Align.START)
        else:
            grid.attach(close_btn, 2, 0, 1, 1)
            close_btn.set_property("halign", Gtk.Align.END)
        self._artwork = builder.get_object("cover")
        if rotate_album:
            self._artwork.get_style_context().add_class("image-rotate")
        else:
            self._artwork.get_style_context().add_class("cover-frame")
        self._title_label = builder.get_object("title")
        self._artist_label = builder.get_object("artist")
        self._album_label = builder.get_object("album")
        self.__revealer = builder.get_object("reveal")
        self._datetime = builder.get_object("datetime")
        self._progress = builder.get_object("progress_scale")
        self._timelabel = builder.get_object("playback")
        self._total_time_label = builder.get_object("duration")
        self.connect("key-release-event", self.__on_key_release_event)

        # Add an AlbumListView on the right
        self.__view = AlbumsListView(RowListType.DND)
        self.__view.get_style_context().add_class("background-opacity")
        self.__view.show()
        self.__revealer.add(self.__view)
        self.add(widget)

    def do_show(self):
        """
            Init signals, set color and go party mode if nothing is playing
        """
        App().window.hide()
        self.__signal1_id = App().player.connect("current-changed",
                                                 self.on_current_changed)
        self.__signal2_id = App().player.connect("status-changed",
                                                 self.on_status_changed)
        self.__signal3_id = App().player.connect("party-changed",
                                                 self.__on_party_changed)
        self.on_status_changed(App().player)
        self.on_current_changed(App().player)
        self.__view.populate(App().player.albums)
        Gtk.Window.do_show(self)
        if self.__timeout_id is None:
            try:
                interface = Gio.Settings.new("org.gnome.desktop.interface")
                show_seconds = interface.get_value("clock-show-seconds")
            except:
                show_seconds = False
            self.__update_datetime(show_seconds)
            self.__timeout_id = GLib.timeout_add(1000,
                                                 self.__update_datetime,
                                                 show_seconds)
        self.update_position(App().player.position / Gst.SECOND)
        screen = Gdk.Screen.get_default()
        monitor = screen.get_monitor_at_window(App().window.get_window())
        self.fullscreen_on_monitor(screen, monitor)

        # Disable screensaver (idle)
        App().inhibitor.manual_inhibit(
                Gtk.ApplicationInhibitFlags.IDLE |
                Gtk.ApplicationInhibitFlags.SUSPEND)

    def do_hide(self):
        """
            Remove signals and unset color
        """
        App().window.setup()
        App().window.show()
        self.__view.stop()
        Gtk.Window.do_hide(self)
        if self.__signal1_id is not None:
            App().player.disconnect(self.__signal1_id)
            self.__signal1_id = None
        if self.__signal2_id is not None:
            App().player.disconnect(self.__signal2_id)
            self.__signal2_id = None
        if self.__signal3_id is not None:
            App().player.disconnect(self.__signal3_id)
            self.__signal3_id = None
        if self.__timeout_id is not None:
            GLib.source_remove(self.__timeout_id)
            self.__timeout_id = None
        App().inhibitor.manual_uninhibit()
        ProgressController.do_destroy(self)

    def show_hide_volume_control(self):
        """
            Show/Hide volume control
        """
        self._show_volume_control = not self._show_volume_control
        self._update_state()

    def on_status_changed(self, player):
        """
            Update controller
            @param player as Player
        """
        ProgressController.on_status_changed(self, player)
        PlaybackController.on_status_changed(self, player)
        context = self._artwork.get_style_context()
        if not App().settings.get_value("rotate-fullscreen-album"):
            return
        if player.is_playing:
            context.add_class("image-rotate")
        else:
            context.remove_class("image-rotate")

    def on_current_changed(self, player):
        """
            Update controllers
            @param player as Player
        """
        InformationController.on_current_changed(self,
                                                 self.__artsize,
                                                 self.__font_size)
        ProgressController.on_current_changed(self, player)
        if player.current_track.id is not None:
            album_name = player.current_track.album.name
            if player.current_track.year:
                album_name += " (%s)" % player.current_track.year
            self._album_label.set_markup(
                "<span font='%s'>%s</span>" %
                                        (self.__font_size - 1,
                                         GLib.markup_escape_text(album_name)))

#######################
# PROTECTED           #
#######################
    def _on_close_button_clicked(self, widget):
        """
            Destroy self
            @param widget as Gtk.Button
        """
        self.__view.stop()
        self.destroy()

    def _on_motion_notify_event(self, widget, event):
        """
            Show/Hide track list if mouse on the right
            @param widget as Gtk.Widget
            @param event as Gdk.EventMotion
        """
        if event.window == widget.get_window():
            allocated_width = widget.get_allocated_width()
            reveal = event.x > allocated_width -\
                self.__view.get_allocated_width() - 100 and\
                event.x < allocated_width + 100
            self.__revealer.set_reveal_child(reveal)

    def _on_image_realize(self, eventbox):
        """
            Set cursor
            @param eventbox as Gtk.EventBox
        """
        try:
            eventbox.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))
        except:
            Logger.warning(_("You are using a broken cursor theme!"))

    def _on_image_button_release_event(self, widget, event):
        """
            Change artwork type
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        rotate_album = not App().settings.get_value("rotate-fullscreen-album")
        App().settings.set_value("rotate-fullscreen-album",
                                 GLib.Variant("b", rotate_album))
        context = self._artwork.get_style_context()
        if rotate_album:
            context.add_class("image-rotate")
            context.remove_class("cover-frame")
            InformationController.__init__(self, False,
                                           ArtHelperEffect.ROUNDED)
        else:
            context.remove_class("image-rotate")
            context.add_class("cover-frame")
            InformationController.__init__(self, False, ArtHelperEffect.NONE)
        InformationController.on_current_changed(self,
                                                 self.__artsize,
                                                 self.__font_size)

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
        if self.__timeout_id is None:
            self.__timeout_id = GLib.timeout_add(60000, self.__update_datetime)
            return False
        return True

    def __on_party_changed(self, player, party):
        """
            Populate view again
            @param player as Player
            @param party as bool
        """
        self.__view.populate(player.albums)

    def __on_key_release_event(self, widget, event):
        """
            Destroy window if Esc
            @param widget as Gtk.Widget
            @param event as Gdk.event
        """
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()
