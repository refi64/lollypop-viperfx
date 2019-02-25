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

from gi.repository import Gtk

from lollypop.define import App, ViewType
from lollypop.widgets_utils import Popover
from lollypop.view_queue import QueueView


class QueuePopover(Popover):
    """
        Popover showing queue
    """

    def __init__(self):
        """
            Init Popover
        """
        Popover.__init__(self)
        self.set_position(Gtk.PositionType.BOTTOM)
        self.connect("map", self.__on_map)
        self.__view = QueueView(ViewType.POPOVER)
        self.__view.populate()
        self.__view.show()
        self.add(self.__view)

#######################
# PROTECTED           #
#######################

#######################
# PRIVATE             #
#######################
    def __on_map(self, widget):
        """
            Connect signals, populate, and resize
            @param widget as Gtk.Widget
        """
        window_size = App().window.get_size()
        height = window_size[1]
        width = min(500, window_size[0])
        self.set_size_request(width, height * 0.7)
