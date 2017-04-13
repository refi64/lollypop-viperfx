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

from gi.repository import GLib

from threading import Thread, Lock


class Loader(Thread):
    """
        Helper to load data on a separate thread and
        dispatch it to the UI thread
    """
    active = {}
    active_lock = Lock()

    def __init__(self, target, view=None, on_finished=None):
        Thread.__init__(self)
        self.daemon = True
        self._target = target
        self._view = view
        self._on_finished = on_finished
        self._invalidated = False
        self._invalidated_lock = Lock()

    def is_invalidated(self):
        with self._invalidated_lock:
            return self._invalidated

    def invalidate(self):
        with self._invalidated_lock:
            self._invalidated = True

    def run(self):
        with Loader.active_lock:
            active = Loader.active.get(self._view, None)
            if active:
                active.invalidate()
            Loader.active[self._view] = self
        result = self._target()
        if not self.is_invalidated():
            if self._on_finished:
                GLib.idle_add(self._on_finished, (result))
            elif self._view:
                GLib.idle_add(self._view.populate, (result))
            with Loader.active_lock:
                Loader.active.pop(self._view, None)
