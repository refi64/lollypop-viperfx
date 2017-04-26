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

from gi.repository import Gio, GLib

from lollypop.define import Lp
from lollypop.utils import is_audio
from lollypop.lio import Lio


class Inotify:
    """
        Inotify support
    """
    # 10 second before updating database
    __TIMEOUT = 10000

    def __init__(self):
        """
            Init inode notification
        """
        self.__monitors = []
        self.__timeout = None

    def add_monitor(self, uri):
        """
            Add a monitor for uri
            @param uri as string
        """
        # Check if there is already a monitor for this uri
        if uri in self.__monitors:
            return
        try:
            f = Lio.File.new_for_uri(uri)
            monitor = f.monitor_directory(Gio.FileMonitorFlags.NONE,
                                          None)
            if monitor is not None:
                monitor.connect("changed", self.__on_dir_changed)
                self.__monitors.append(uri)
        except Exception as e:
            print("Inotify::add_monitor():", e)

#######################
# PRIVATE             #
#######################
    def __on_dir_changed(self, monitor, changed_file, other_file, event):
        """
            Prepare thread to handle changes
        """
        update = False
        # Stop collection scanner and wait
        if Lp().scanner.is_locked():
            Lp().scanner.stop()
            GLib.timeout_add(self.__TIMEOUT,
                             self.__on_dir_changed,
                             monitor,
                             changed_file,
                             other_file,
                             event)
        # Run update delayed
        else:
            uri = changed_file.get_uri()
            d = Lio.File.new_for_uri(uri)
            if d.query_exists():
                # If a directory, monitor it
                if changed_file.query_file_type(
                                            Gio.FileQueryInfoFlags.NONE,
                                            None) == Gio.FileType.DIRECTORY:
                    self.add_monitor(uri)
                # If not an audio file, exit
                elif is_audio(changed_file):
                    update = True
            else:
                update = True
            if update:
                if self.__timeout is not None:
                    GLib.source_remove(self.__timeout)
                    self.__timeout = None
                self.__timeout = GLib.timeout_add(self.__TIMEOUT,
                                                  self.__run_collection_update)

    def __run_collection_update(self):
        """
            Run a collection update
        """
        self.__timeout = None
        Lp().window.update_db()
