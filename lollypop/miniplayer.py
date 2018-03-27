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

from gi.repository import Gtk, Gdk

from lollypop.controllers import InfoController, ProgressController
from lollypop.define import App, WindowSize


class MiniPlayer(Gtk.Bin, InfoController, ProgressController):
    """
        Toolbar end
    """

    def __init__(self, width):
        """
            Init toolbar
            @param width as int
        """
        self.__width = width
        Gtk.Bin.__init__(self)
        InfoController.__init__(self, width)
        ProgressController.__init__(self)
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/MiniPlayer.ui")
        builder.connect_signals(self)

        self._progress = builder.get_object("progress_scale")
        self._progress.set_sensitive(False)
        self._progress.set_hexpand(True)
        self._timelabel = builder.get_object("playback")
        self._total_time_label = builder.get_object("duration")

        self.__grid = builder.get_object("grid")
        self._title_label = builder.get_object("title")
        self._artist_label = builder.get_object("artist")
        self._cover = builder.get_object("cover")
        self.__signal_id1 = App().player.connect("current-changed",
                                                 self.__on_current_changed)
        self.__signal_id2 = App().player.connect("status-changed",
                                                 self.__on_status_changed)
        self.__on_current_changed(App().player)
        if App().player.current_track.id is not None:
            self._update_position()
            self.__on_status_changed(App().player)
        self.add(builder.get_object("widget"))

    def update_cover(self, width):
        """
            Update cover for width
            @param width as int
        """
        self.__width = width
        InfoController.__init__(self, width)
        InfoController.on_current_changed(self, App().player)

    def do_get_preferred_width(self):
        """
            Force preferred width
        """
        (min, nat) = Gtk.Bin.do_get_preferred_width(self)
        # Allow resizing
        return (0, 0)

    def do_get_preferred_height(self):
        """
            Force preferred height
        """
        return self.__grid.get_preferred_height()

    def do_destroy(self):
        """
            Remove signal
        """
        Gtk.Bin.do_destroy(self)
        ProgressController.do_destroy(self)
        App().player.disconnect(self.__signal_id1)
        App().player.disconnect(self.__signal_id2)

#######################
# PROTECTED           #
#######################
    def _on_button_release_event(self, button, event):
        """
            Show track menu
            @param button as Gtk.Button
            @param event as Gdk.Event
        """
        height = App().window.get_size()[1]
        if App().player.current_track.id is not None and\
                height > WindowSize.MEDIUM:
            if event.button == 1:
                App().window.toolbar.end.show_list_popover(button)
            elif App().player.current_track.id >= 0:
                from lollypop.pop_menu import TrackMenuPopover, ToolbarMenu
                popover = TrackMenuPopover(
                    App().player.current_track,
                    ToolbarMenu(App().player.current_track))
                popover.set_relative_to(self)
                popover.show()
        return True

    def _on_labels_realize(self, eventbox):
        """
            Set mouse cursor
            @param eventbox as Gtk.EventBox
        """
        eventbox.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))

#######################
# PRIVATE             #
#######################
    def __on_current_changed(self, player):
        """
            Update controllers
            @param player as Player
        """
        if App().player.current_track.id is not None:
            self.show()
        InfoController.on_current_changed(self, player)
        ProgressController.on_current_changed(self, player)

    def __on_status_changed(self, player):
        """
            Update controllers
            @param player as Player
        """
        ProgressController.on_status_changed(self, player)
