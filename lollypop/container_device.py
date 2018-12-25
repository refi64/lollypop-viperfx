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

from gi.repository import Gio

from gettext import gettext as _

from urllib.parse import urlparse

from lollypop.define import App, Type
from lollypop.view import MessageView


# This is a multimedia device
class Device:
    id = None
    name = None
    uri = None


class DeviceContainer:
    """
        Devices management for main view
    """

    def __init__(self):
        """
            Init container
        """
        # Index will start at -VOLUMES
        self.__devices = {}
        self.__devices_index = Type.DEVICES

        # Volume manager
        self.__vm = Gio.VolumeMonitor.get()
        self.__vm.connect("mount-added", self.__on_mount_added)
        self.__vm.connect("mount-removed", self.__on_mount_removed)
        for mount in self.__vm.get_mounts():
            self.__add_device(mount, False)

    def add_fake_phone(self):
        """
            Emulate an Android Phone
        """
        self.__devices_index -= 1
        dev = Device()
        dev.id = self.__devices_index
        dev.name = "Android phone"
        dev.uri = "file:///tmp/android/"
        d = Gio.File.new_for_uri(dev.uri + "Internal Memory")
        if not d.query_exists():
            d.make_directory_with_parents()
        d = Gio.File.new_for_uri(dev.uri + "SD Card")
        if not d.query_exists():
            d.make_directory_with_parents()
        self.__devices[self.__devices_index] = dev

    @property
    def devices(self):
        """
            Get devices
            @return {}
        """
        return self.__devices

############
# PRIVATE  #
############
    def _get_view_device(self, device_id):
        """
            Get device view for id
            Use existing view if available
            @param device id as int
            @return View
        """
        from lollypop.view_device import DeviceView
        device = self.__devices[device_id]
        device_view = None

        # Search a device child with uri
        for child in self._stack.get_children():
            if isinstance(child, DeviceView):
                if child.device.uri == device.uri:
                    device_view = child
                    break

        # If no view available, get a new one
        if device_view is None:
            files = DeviceView.get_files(device.uri)
            if files:
                device_view = DeviceView(device)
                self._stack.add_named(device_view, device.uri)
            else:
                device_view = MessageView(_("Please unlock your device"))
                self._stack.add(device_view)
            device_view.populate()
            device_view.show()
        return device_view

    def __add_device(self, mount, show=False):
        """
            Add a device
            @param mount as Gio.Mount
            @param show as bool
        """
        if mount.get_volume() is None:
            return
        uri = mount.get_default_location().get_uri()
        drive = mount.get_drive()
        if uri is None:
            return
        parsed = urlparse(uri)
        is_removable = drive is not None and drive.is_removable() and\
            Type.USB_DISKS in App().settings.get_value("shown-album-lists")
        if is_removable or parsed.scheme == "mtp":
            self.__devices_index -= 1
            dev = Device()
            dev.id = self.__devices_index
            dev.name = mount.get_name()
            dev.uri = uri
            self.__devices[self.__devices_index] = dev
            if show:
                if App().settings.get_value("show-sidebar"):
                    self._list_one.add_value((dev.id, dev.name, dev.name))
                else:
                    self._rounded_artists_view.add_value((dev.id,
                                                         dev.name,
                                                         dev.name))

    def __remove_device(self, mount):
        """
            Remove volume from device list
            @param mount as Gio.Mount
        """
        uri = mount.get_default_location().get_uri()
        for dev in self.__devices.values():
            if dev.uri == uri:
                if App().settings.get_value("show-sidebar"):
                    self._list_one.remove_value(dev.id)
                else:
                    self._rounded_artists_view.remove_value(dev.id)
                child = self._stack.get_child_by_name(uri)
                if child is not None:
                    child.destroy()
                del self.__devices[dev.id]
                break

    def __on_mount_added(self, vm, mount):
        """
            On volume mounter
            @param vm as Gio.VolumeMonitor
            @param mount as Gio.Mount
        """
        self.__add_device(mount, True)

    def __on_mount_removed(self, vm, mount):
        """
            On volume removed, clean selection list
            @param vm as Gio.VolumeMonitor
            @param mount as Gio.Mount
        """
        self.__remove_device(mount)
