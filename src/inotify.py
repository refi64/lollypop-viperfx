#!/usr/bin/python
# Copyright (c) 2014-2015 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

import os

from lollypop.define import Objects


class Inotify:
    # 20 second before updating database
    _TIMEOUT = 20000
    """
        Init inode notification
    """
    def __init__(self):
        self._monitors = {}
        self._timeout = None

    """
        Add a monitor for path
        @param path as string
    """
    def add_monitor(self, path):
        # Check if there is no monitor for this path
        if path in self._monitors.keys():
            return

        f = Gio.File.new_for_path(path)
        monitor = f.monitor_directory(Gio.FileMonitorFlags.NONE,
                                      None)
        if monitor is not None:
            monitor.connect('changed', self._on_dir_changed)
            self._monitors[path] = monitor

#######################
# PRIVATE             #
#######################
    """
        Prepare thread to handle changes
    """
    def _on_dir_changed(self, monitor, changed_file, other_file, event):
        # Stop collection scanner and wait
        if Objects.scanner.is_locked():
            Objects.scanner.stop()
            GLib.timeout_add(1000,
                             self._on_dir_changed,
                             monitor,
                             changed_file,
                             other_file,
                             event)
        # Run update delayed
        else:
            path = changed_file.get_path()
            # If a directory, monitor it
            if os.path.exists(path) and\
               changed_file.query_file_type(Gio.FileQueryInfoFlags.NONE,
                                            None) == Gio.FileType.DIRECTORY:
                self.add_monitor(path)
            if self._timeout is not None:
                GLib.source_remove(self._timeout)
                self._timeout = None
            self._timeout = GLib.timeout_add(self._TIMEOUT,
                                             self._run_collection_update)

    """
        Run a collection update
    """
    def _run_collection_update(self):
        self._timeout = None
        Objects.scanner.update(True, None)
