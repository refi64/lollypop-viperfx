# Copyright (c) 2014-2019 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from lollypop.define import App, ArtSize, ArtBehaviour, Type
from lollypop.controller_information import InformationController
from lollypop.controller_playback import PlaybackController
from lollypop.controller_progress import ProgressController
from lollypop.container import Container
from lollypop.adaptive import AdaptiveWindow
from lollypop.logger import Logger


class FullScreen(Gtk.Window, AdaptiveWindow, InformationController,
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
        AdaptiveWindow.__init__(self)
        self.set_title("Lollypop")
        self.__allocation = Gdk.Rectangle()
        self.connect("motion-notify-event", self.__on_motion_notify_event)
        self.connect("leave-notify-event", self.__on_leave_notify_event)
        rotate_album = App().settings.get_value("rotate-fullscreen-album")
        PlaybackController.__init__(self)
        ProgressController.__init__(self)
        if rotate_album:
            InformationController.__init__(self, False,
                                           ArtBehaviour.ROUNDED |
                                           ArtBehaviour.CROP_SQUARE)
        else:
            InformationController.__init__(self, False,
                                           ArtBehaviour.CROP_SQUARE)
        self.set_application(app)
        self.__timeout_id = None
        self.__signal1_id = self.__signal2_id = None
        self.set_decorated(False)

        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/FullScreen.ui")
        builder.connect_signals(self)

        # Calculate cover size
        screen = Gdk.Screen.get_default()
        monitor = screen.get_monitor_at_window(App().main_window.get_window())
        geometry = screen.get_monitor_geometry(monitor)
        # We want 500 and 200 in full hd
        if geometry.width > geometry.height:
            self.__art_size = int(ArtSize.FULLSCREEN * geometry.height / 1080)
        else:
            self.__art_size = int(ArtSize.FULLSCREEN * geometry.width / 1920)
        self.__font_size = int(14 * geometry.height / 1080)
        widget = builder.get_object("widget")
        self.__overlay_grid = builder.get_object("overlay_grid")
        self._play_button = builder.get_object("play_btn")
        self._next_button = builder.get_object("next_btn")
        self._prev_button = builder.get_object("prev_btn")
        self._play_image = builder.get_object("play_image")
        self._pause_image = builder.get_object("pause_image")
        close_btn = builder.get_object("close_btn")
        preferences = Gio.Settings.new("org.gnome.desktop.wm.preferences")
        layout = preferences.get_value("button-layout").get_string()
        if layout.split(":")[0] == "close":
            self.__overlay_grid.attach(close_btn, 0, 0, 1, 1)
            close_btn.set_property("halign", Gtk.Align.START)
        else:
            self.__overlay_grid.attach(close_btn, 2, 0, 1, 1)
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

        # Add a navigation widget on the right
        self.__back_button = Gtk.Button.new_from_icon_name(
            "go-previous-symbolic", Gtk.IconSize.BUTTON)
        self.__back_button.set_sensitive(False)
        self.__back_button.set_relief(Gtk.ReliefStyle.NONE)
        self.__back_button.set_property("valign", Gtk.Align.START)
        self.__back_button.set_property("halign", Gtk.Align.START)
        self.__back_button.connect("clicked", self.__on_back_button_clicked)
        self.__back_button.set_margin_start(5)
        self.__back_button.set_margin_end(5)
        self.__back_button.set_margin_top(5)
        self.__back_button.set_margin_bottom(5)
        self.__back_button.show()
        self.__background_artwork = builder.get_object("background_artwork")
        self.__container = Container()
        self.set_stack(self.__container.stack)
        self.add_paned(self.__container.paned_one, self.__container.list_one)
        self.add_paned(self.__container.paned_two, self.__container.list_two)
        self.__container.show()
        self.__container.show_sidebar(True)
        self.set_adaptive_stack(True)
        self.__sidebar = Gtk.Grid()
        self.__sidebar.set_orientation(Gtk.Orientation.VERTICAL)
        self.__sidebar.get_style_context().add_class("borders-left-top")
        self.__sidebar.show()
        self.__sidebar.add(self.__back_button)
        self.__sidebar.add(self.__container)
        self.__sidebar.set_size_request(450, -1)
        self.connect("can-go-back-changed", self.__on_can_go_back_changed)
        self.connect("show-can-go-back", self.__on_show_can_go_back)
        self.connect("size-allocate", self.__on_size_allocate)
        self.__sidebar.get_style_context().add_class("background-opacity")
        self.__revealer.add(self.__sidebar)
        self.add(widget)

    def do_show(self):
        """
            Setup window for current screen
        """
        App().main_window.hide()
        self.__signal1_id = App().player.connect("current-changed",
                                                 self.on_current_changed)
        self.__signal2_id = App().player.connect("status-changed",
                                                 self.on_status_changed)
        self.on_status_changed(App().player)
        self.on_current_changed(App().player)
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
        monitor = screen.get_monitor_at_window(App().main_window.get_window())
        self.fullscreen_on_monitor(screen, monitor)

        # Disable screensaver (idle)
        App().inhibitor.manual_inhibit(
                Gtk.ApplicationInhibitFlags.IDLE |
                Gtk.ApplicationInhibitFlags.SUSPEND)

    def do_hide(self):
        """
            Clean window
        """
        App().main_window.setup()
        App().main_window.show()
        Gtk.Window.do_hide(self)
        if self.__signal1_id is not None:
            App().player.disconnect(self.__signal1_id)
            self.__signal1_id = None
        if self.__signal2_id is not None:
            App().player.disconnect(self.__signal2_id)
            self.__signal2_id = None
        if self.__timeout_id is not None:
            GLib.source_remove(self.__timeout_id)
            self.__timeout_id = None
        App().inhibitor.manual_uninhibit()
        ProgressController.on_destroy(self)

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
                                                 self.__art_size,
                                                 self.__font_size)
        ProgressController.on_current_changed(self, player)
        self.__update_background()
        if player.current_track.id is not None:
            album_name = player.current_track.album.name
            if player.current_track.year:
                album_name += " (%s)" % player.current_track.year
            self._album_label.set_markup(
                "<span font='%s'>%s</span>" %
                                        (self.__font_size - 1,
                                         GLib.markup_escape_text(album_name)))

    @property
    def miniplayer(self):
        return App().main_window.miniplayer

    @property
    def toolbar(self):
        return App().main_window.toolbar

    @property
    def container(self):
        """
            Get container
            @return Container
        """
        return self.__container

#######################
# PROTECTED           #
#######################
    def _on_artwork(self, surface):
        """
            Set artwork
            @param surface as str
        """
        if surface is None:
            if App().player.current_track.id == Type.RADIOS:
                icon_name = "audio-input-microphone-symbolic"
            else:
                icon_name = "folder-music-symbolic"
            self._artwork.set_from_icon_name(icon_name,
                                             Gtk.IconSize.DIALOG)
            self._artwork.set_size_request(self.__art_size, self.__art_size)
        else:
            InformationController._on_artwork(self, surface)
            self._artwork.set_size_request(-1, -1)

    def _on_close_button_clicked(self, widget):
        """
            Destroy self
            @param widget as Gtk.Button
        """
        self.destroy()

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
                                           ArtBehaviour.ROUNDED |
                                           ArtBehaviour.CROP_SQUARE)
        else:
            context.remove_class("image-rotate")
            context.add_class("cover-frame")
            InformationController.__init__(self, False,
                                           ArtBehaviour.CROP_SQUARE)
        InformationController.on_current_changed(self,
                                                 self.__art_size,
                                                 self.__font_size)

#######################
# PRIVATE             #
#######################
    def __update_background(self):
        """
            Update window background
        """
        allocation = self.get_allocation()
        if allocation.width <= 1 or allocation.height <= 1:
            return
        behaviour = ArtBehaviour.BLUR_HARD | ArtBehaviour.CROP
        settings = Gtk.Settings.get_default()
        if settings.get_property("gtk-application-prefer-dark-theme"):
            behaviour |= ArtBehaviour.DARKER
        else:
            behaviour |= ArtBehaviour.LIGHTER
        if App().settings.get_value("artist-artwork"):
            App().art_helper.set_artist_artwork(
                                        App().player.current_track.artists[0],
                                        allocation.width,
                                        allocation.height,
                                        self.get_scale_factor(),
                                        behaviour,
                                        self.__on_artwork,)
        else:
            App().art_helper.set_album_artwork(
                                        App().player.current_track.album,
                                        allocation.width,
                                        allocation.height,
                                        self.get_scale_factor(),
                                        behaviour,
                                        self.__on_artwork,)

    def __update_datetime(self, show_seconds=False):
        """
            Update datetime in headerbar
            @param show_seconds as bool
        """
        now = datetime.now()
        if show_seconds:
            self._datetime.set_label(now.strftime("%a %d %b %X"))
        else:
            self._datetime.set_label(now.strftime("%a %d %b %X")[:-3])
        if self.__timeout_id is None:
            self.__timeout_id = GLib.timeout_add(60000, self.__update_datetime)
            return False
        return True

    def __on_artwork(self, surface):
        """
            Set background artwork
            @param surface as str
        """
        self.__background_artwork.set_from_surface(surface)

    def __on_leave_notify_event(self, widget, event):
        """
            Hide tracks
            @param widget as Gtk.Widget
            @param event as Gdk.EventCrossing
        """
        allocation = widget.get_allocation()
        if event.x <= 0 or\
           event.x >= allocation.width or\
           event.y <= 0 or\
           event.y >= allocation.height:
            self.__revealer.set_reveal_child(False)

    def __on_motion_notify_event(self, widget, event):
        """
            Show/Hide track list if mouse on the right
            @param widget as Gtk.Widget
            @param event as Gdk.EventMotion
        """
        if event.window == widget.get_window():
            reveal = event.x > widget.get_allocated_width() -\
                self.__sidebar.get_allocated_width() - 100
            self.__revealer.set_reveal_child(reveal)

    def __on_key_release_event(self, widget, event):
        """
            Destroy window if Esc
            @param widget as Gtk.Widget
            @param event as Gdk.event
        """
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()

    def __on_back_button_clicked(self, button):
        """
            Go back in container stack
            @param button as Gtk.Button
        """
        self.go_back()

    def __on_show_can_go_back(self, window, back):
        """
            Show back button
            @param window as Gtk.Window
            @param back as bool
        """
        if back:
            self.__back_button.show()
        else:
            self.__back_button.hide()

    def __on_can_go_back_changed(self, window, back):
        """
            Make button sensitive
            @param window as Gtk.Window
            @param back as bool
        """
        if back:
            self.__back_button.set_sensitive(True)
        else:
            self.__back_button.set_sensitive(False)

    def __on_size_allocate(self, widget, allocation):
        """
            Update background if needed
            @param widget as Gtk.Widget
            @param allocation as Gtk.Allocation
        """
        if allocation.width <= 1 or\
                allocation.height <= 1 or\
                allocation.width == self.__allocation.width or\
                allocation.height == self.__allocation.height:
            return
        self.__allocation = allocation
        self.__update_background()
