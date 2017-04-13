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

from gi.repository import Gtk


class ProgressBar(Gtk.ProgressBar):
    """
        A smart progress bar
    """

    def __init__(self):
        """
            Init progress bar
        """
        Gtk.ProgressBar.__init__(self)
        self.__callers = []

    def add(self, caller):
        """
            Add caller
            @param caller as Instance
        """
        if caller not in self.__callers:
            self.__callers.insert(0, caller)

    def set_fraction(self, fraction, caller):
        """
            Set fraction if caller is on top.
        """
        if not self.__callers:
            return
        if caller == self.__callers[0]:
            self.show()
            Gtk.ProgressBar.set_fraction(self, fraction)
            if fraction == 1:
                self.__callers.remove(caller)
                self.hide()
                Gtk.ProgressBar.set_fraction(self, 0.0)
