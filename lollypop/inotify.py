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

from gi.repository import Gio, GLib

from lollypop.define import App, ScanType
from lollypop.utils import is_audio
from lollypop.logger import Logger


class Inotify:
    """
        Inotify support
    """
    # 2 seconds before updating database
    __TIMEOUT = 2000

    def __init__(self):
        """
            Init inode notification
        """
        self.__monitors = {}
        self.__timeout_id = None

    def add_monitor(self, uri):
        """
            Add a monitor for uri
            @param uri as string
        """
        # Check if there is already a monitor for this uri
        if uri in self.__monitors.keys():
            return
        try:
            f = Gio.File.new_for_uri(uri)
            monitor = f.monitor_directory(Gio.FileMonitorFlags.NONE,
                                          None)
            if monitor is not None:
                monitor.connect("changed", self.__on_dir_changed)
                self.__monitors[uri] = monitor
        except Exception as e:
            Logger.error("Inotify::add_monitor(): %s" % e)

#######################
# PRIVATE             #
#######################
    def __on_dir_changed(self, monitor, changed_file, other_file, event):
        """
            Stop collection scanner if running
            Delayed update by default
            @param monitor as Gio.FileMonitor
            @param changed_file as Gio.File/None
            @param other_file as Gio.File/None
            @param event as Gio.FileMonitorEvent
        """
        changed_uri = changed_file.get_uri()
        # Do not monitor our self
        if changed_uri in self.__monitors.keys() and\
                self.__monitors[changed_uri] == monitor:
            return
        # Ignore non audio/dir
        if not is_audio(changed_file) and\
            changed_file.query_file_type(Gio.FileQueryInfoFlags.NONE,
                                         None) != Gio.FileType.DIRECTORY:
            return

        # Stop collection scanner and wait
        if App().scanner.is_locked():
            App().scanner.stop()
            GLib.timeout_add(self.__timeout_id,
                             self.__on_dir_changed,
                             monitor,
                             changed_file,
                             other_file,
                             event)
        # Run update delayed
        else:
            if changed_file.has_parent():
                uris = [changed_file.get_parent().get_uri()]
            else:
                uris = [changed_uri]
            self.__timeout_id = GLib.timeout_add(self.__TIMEOUT,
                                                 self.__run_collection_update,
                                                 uris)

    def __run_collection_update(self, uris=[]):
        """
            Run a collection update
            @param uris as [str]
        """
        self.__timeout_id = None
        App().scanner.update(ScanType.NEW_FILES, uris)
