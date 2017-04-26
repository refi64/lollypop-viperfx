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

from gi.repository import Gtk, Gdk

from lollypop.controllers import InfosController
from lollypop.define import Lp, WindowSize


class MiniPlayer(Gtk.Bin, InfosController):
    """
        Toolbar end
    """

    def __init__(self):
        """
            Init toolbar
        """
        Gtk.Bin.__init__(self)
        InfosController.__init__(self, WindowSize.SMALL)
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/MiniPlayer.ui")
        builder.connect_signals(self)
        self.__grid = builder.get_object("grid")
        self._title_label = builder.get_object("title")
        self._artist_label = builder.get_object("artist")
        self._cover = builder.get_object("cover")
        self._signal_id = Lp().player.connect("current-changed",
                                              self.on_current_changed)
        self.on_current_changed(Lp().player)
        self.add(builder.get_object("widget"))

    def do_get_preferred_height(self):
        """
            Grid height
        """
        return self.__grid.get_preferred_height()

    def do_hide(self):
        """
            Remove signal
        """
        Gtk.Bin.do_hide(self)
        Lp().player.disconnect(self._signal_id)

#######################
# PROTECTED           #
#######################
    def _on_button_press(self, button, event):
        """
            Show track menu
            @param button as Gtk.Button
            @param event as Gdk.Event
        """
        if Lp().player.current_track.id is not None:
            if event.button != 1 and Lp().player.current_track.id >= 0:
                from lollypop.pop_menu import TrackMenuPopover, PlaylistsMenu
                popover = TrackMenuPopover(
                            Lp().player.current_track,
                            PlaylistsMenu(Lp().player.current_track))
                popover.set_relative_to(self)
                press_rect = Gdk.Rectangle()
                press_rect.x = event.x
                press_rect.y = event.y
                press_rect.width = press_rect.height = 1
                popover.set_pointing_to(press_rect)
                popover.show()
        return True
