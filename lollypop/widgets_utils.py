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

from gi.repository import Gtk, GLib


class Popover(Gtk.Popover):
    """
        Auto destroy popover on unmap
    """

    def __init__(self):
        """
            Init widget
        """
        Gtk.Popover.__init__(self)
        # If popover is pointing to a widget, we need to destroy idle
        self.connect("unmap", lambda x: GLib.idle_add(self.destroy))
