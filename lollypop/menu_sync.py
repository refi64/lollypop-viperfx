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

from gi.repository import Gio, GLib

from gettext import gettext as _

from lollypop.define import App
from lollypop.utils import is_device


class SyncMenu(Gio.Menu):
    """
        Sync menu for album
    """

    def __init__(self, album):
        """
            Init menu
            @param album as Album
        """
        Gio.Menu.__init__(self)
        self.__album = album
        self.__vm = Gio.VolumeMonitor.get()
        self.__vm.connect("mount-added", self.__on_mount_added)
        self.__set_sync_action()

#######################
# PRIVATE             #
#######################
    def __add_sync_action(self, mount):
        """
            Add sync action for mount
            @param mount as Gio.Mount
        """
        if not is_device(mount):
            return
        devices = list(App().settings.get_value("devices"))
        name = mount.get_name()
        action_name = "sync_%s" % name
        try:
            index = devices.index(name) + 1
            synced = self.__album.synced & (1 << index)
        except:
            synced = False
        sync_action = Gio.SimpleAction.new_stateful(
                                          action_name,
                                          None,
                                          GLib.Variant.new_boolean(synced))
        App().add_action(sync_action)
        sync_action.connect("change-state",
                            self.__on_sync_action_change_state,
                            name)
        self.append(_("Sync with %s" % name), "app.%s" % action_name)

    def __set_sync_action(self):
        """
            Set sync action
        """
        for mount in self.__vm.get_mounts():
            self.__add_sync_action(mount)

    def __on_mount_added(self, vm, mount):
        """
            On volume mounter
            @param vm as Gio.VolumeMonitor
            @param mount as Gio.Mount
        """
        self.__add_sync_action(mount)

    def __on_sync_action_change_state(self, action, variant, name):
        """
            Save album to collection
            @param Gio.SimpleAction
            @param GLib.Variant
            @param name as str
        """
        action.set_state(variant)
        devices = list(App().settings.get_value("devices"))
        if name not in devices:
            devices.append(name)
            App().settings.set_value("devices", GLib.Variant("as", devices))
        index = devices.index(name) + 1
        synced = self.__album.synced | (1 << index)
        App().albums.set_synced(self.__album.id, synced)
