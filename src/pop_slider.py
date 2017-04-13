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

from gi.repository import Gtk, GLib


class SliderPopover(Gtk.Popover):
    """
        Popover with next track
    """

    def __init__(self):
        """
            Init popover
        """
        Gtk.Popover.__init__(self)
        self._timeout_id = None
        self.set_modal(False)
        self.set_position(Gtk.PositionType.BOTTOM)
        self._past = Gtk.Label()
        self._past.show()
        self.add(self._past)

    def set(self, past):
        """
            Set values and start an auto hide timer
            @param past as string
        """
        if self._timeout_id is not None:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = None
        self._past.set_text(past)

    def delayed_hide(self):
        """
            Delayed hide
        """
        if self._timeout_id is not None:
            GLib.source_remove(self._timeout_id)
        self._timeout_id = GLib.timeout_add(250, self._hide)

#######################
# PRIVATE             #
#######################
    def _hide(self):
        """
            Hide and unset timeout id
        """
        self._timeout_id = None
        self.hide()
