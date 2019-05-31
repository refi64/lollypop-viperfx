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

from gi.repository import Gtk, Gio

from lollypop.define import App
from lollypop.utils import is_device
from lollypop.widgets_device import DeviceWidget


class AppMenuPopover(Gtk.Popover):
    """
        Application menu with some extra widgets (sync, volume, ...)
    """

    def __init__(self):
        """
            Init popover
        """
        Gtk.Popover.__init__(self)
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/Appmenu.ui")
        self.__volume = builder.get_object("volume")
        self.__volume.set_value(App().player.volume)
        self.__listbox = builder.get_object("listbox")
        builder.connect_signals(self)
        # Volume manager
        self.__vm = Gio.VolumeMonitor.get()
        self.__vm.connect("mount-added", self.__on_mount_added)
        self.__vm.connect("mount-removed", self.__on_mount_removed)
        for mount in self.__vm.get_mounts():
            self.__add_device(mount)
        self.add(builder.get_object("widget"))

#######################
# PROTECTED           #
#######################
    def _on_button_clicked(self, button):
        """
            Hide popover
            @param button as Gtk.Button
        """
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
    def __add_device(self, mount):
        """
            Add a device
            @param mount as Gio.Mount
        """
        if is_device(mount):
            widget = DeviceWidget(mount)
            widget.show()
            self.__listbox.add(widget)
            self.__listbox.show()

    def __remove_device(self, mount):
        """
            Remove volume from device list
            @param mount as Gio.Mount
        """
        uri = mount.get_default_location().get_uri()
        for widget in self.__listbox.get_children():
            if widget.uri == uri:
                widget.destroy()
        if not self.__listbox.get_children():
            self.__listbox.hide()

    def __on_mount_added(self, vm, mount):
        """
            On volume mounter
            @param vm as Gio.VolumeMonitor
            @param mount as Gio.Mount
        """
        self.__add_device(mount)

    def __on_mount_removed(self, vm, mount):
        """
            On volume removed, clean selection list
            @param vm as Gio.VolumeMonitor
            @param mount as Gio.Mount
        """
        self.__remove_device(mount)

    def __on_volume_changed(self, player):
        """
            Set scale value
            @param player as Player
        """
        volume = self.__volume.get_value()
        if player.volume != volume:
            self.__volume.set_value(player.volume)
