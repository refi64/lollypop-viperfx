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

from gi.repository import Gtk

from lollypop.define import App
from lollypop.widgets_utils import Popover


class AppMenuPopover(Popover):
    """
        Configure defaults items
    """

    def __init__(self):
        """
            Init popover
        """
        Popover.__init__(self)
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/Appmenu.ui")
        self.add(builder.get_object("widget"))
        self.__volume = builder.get_object("volume")
        self.__volume.set_value(App().player.volume)
        builder.connect_signals(self)
        self.connect("map", self.__on_map)
        self.connect("unmap", self.__on_unmap)

#######################
# PROTECTED           #
#######################
    def _on_button_clicked(self, button):
        self.hide()

    def _on_volume_value_changed(self, scale):
        """
            Set volume
            @param scale as Gtk.Scale
        """
        new_volume = scale.get_value()
        if new_volume != App().player.volume:
            App().player.set_volume(scale.get_value())

#######################
# PRIVATE             #
#######################
    def __on_volume_changed(self, player):
        """
            Set scale value
            @param player as Player
        """
        volume = self.__volume.get_value()
        if player.volume != volume:
            self.__volume.set_value(player.volume)

    def __on_map(self, widget):
        """
            Connect signals
            @param widget as Gtk.Widget
        """
        App().player.connect("volume-changed", self.__on_volume_changed)

    def __on_unmap(self, widget):
        """
            Disconnect signals
            @param widget as Gtk.Widget
        """
        App().player.disconnect_by_func(self.__on_volume_changed)
