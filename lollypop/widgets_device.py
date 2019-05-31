# Copyright (c) 2014-2019 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# Copyright (C) 2010 Jonathan Matthew (replay gain code)
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

from gi.repository import Gtk, GLib, Gio

from gi.repository.Gio import FILE_ATTRIBUTE_FILESYSTEM_SIZE, \
                              FILE_ATTRIBUTE_FILESYSTEM_FREE

from lollypop.logger import Logger


class DeviceWidget(Gtk.ListBoxRow):
    """
        A device widget for sync
    """

    def __init__(self, mount):
        """
            Init widget
            @param mount as Gio.Mount (with valid volume)
        """
        Gtk.ListBoxRow.__init__(self)
        self.__name = mount.get_name()
        self.__uri = mount.get_default_location().get_uri()
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/DeviceWidget.ui")
        self.__progress = builder.get_object("progress")
        builder.get_object("name").set_label(self.__name)
        icon = mount.get_volume().get_symbolic_icon()
        device_symbolic = builder.get_object("device-symbolic")
        device_symbolic.set_from_gicon(icon, Gtk.IconSize.MENU)
        self.add(builder.get_object("widget"))
        builder.connect_signals(self)
        self.__calculate_free_space()

    @property
    def uri(self):
        """
            Get device URI
            @return str
        """
        return self.__uri

#######################
# PROTECTED           #
#######################

#######################
# PRIVATE             #
#######################
    def __calculate_free_space(self):
        """
            Calculate free space on device
        """
        f = Gio.File.new_for_uri(self.__uri)
        f.query_filesystem_info_async("{},{}".format(
                                       FILE_ATTRIBUTE_FILESYSTEM_SIZE,
                                       FILE_ATTRIBUTE_FILESYSTEM_FREE),
                                      GLib.PRIORITY_DEFAULT,
                                      None,
                                      self.__on_filesystem_info)

    def __on_filesystem_info(self, source, result):
        """
            Show available space on disk
            @param source as GObject.Object
            @param result as Gio.AsyncResult
        """
        try:
            info = source.query_filesystem_info_finish(result)
            size = info.get_attribute_uint64(FILE_ATTRIBUTE_FILESYSTEM_SIZE)
            free = info.get_attribute_uint64(FILE_ATTRIBUTE_FILESYSTEM_FREE)
            used = size - free
            fraction = 1 * used / size
            self.__progress.set_fraction(fraction)
        except Exception as e:
            Logger.error("DeviceWiget::__on_filesystem_info(): %s", e)
