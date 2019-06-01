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

    def __init__(self, name, uri, icon=None):
        """
            Init widget
            @param name as str
            @param uri as str
            @param icon as Gio.Icon
        """
        Gtk.ListBoxRow.__init__(self)
        self.get_style_context().add_class("background")
        self.__name = name
        self.__uri = uri
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/DeviceWidget.ui")
        self.__progress = builder.get_object("progress")
        builder.get_object("name").set_label(self.__name)
        if icon is not None:
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
    def _on_sync_button_clicked(self, button):
        """
            Sync music on device
            @param button as Gtk.Button
        """
        uri = self.__get_best_uri_for_sync()
        if uri is None:
            return

#######################
# PRIVATE             #
#######################
    def __get_best_uri_for_sync(self):
        """
            Get best URI for synchronization:
                - A folder with lollypop sync DB
                - A SD Card
            @return str
        """
        uris = []
        try:
            # First test we have a normal Music folder at root
            # We try to create one, MTP will fail
            music_uri = "%s/Music" % self.__uri
            music_dir = Gio.File.new_for_uri(music_uri)
            try:
                music_dir.make_directory_with_parents()
            except:
                pass
            if music_dir.query_exists():
                return music_uri

            # Search for previous sync or for SD CARD
            d = Gio.File.new_for_uri(self.__uri)
            infos = d.enumerate_children(
                "standard::name,standard::type",
                Gio.FileQueryInfoFlags.NONE,
                None)

            for info in infos:
                if info.get_file_type() != Gio.FileType.DIRECTORY:
                    continue
                f = infos.get_child(info)
                uri = f.get_uri() + "/Music"
                previous_sync = Gio.File.new_for_uri("%s/unsync" % uri)
                if previous_sync.query_exists():
                    uris.insert(0, uri)
                elif info.get_name().lower().startswith("SD"):
                    sync = Gio.File.new_for_uri(uri)
                    sync.make_directory_with_parents()
                    uris.append(uri)
            infos.close(None)
            return uris
        except Exception as e:
            Logger.error("DeviceManagerView::_get_files: %s: %s" % (uri, e))
        return uris[0] if uris else None

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
