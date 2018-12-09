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

from lollypop.define import App
from lollypop.view_search import SearchView


class SearchPopover(Gtk.Popover):
    """
        Popover allowing user to search for tracks/albums
    """

    def __init__(self):
        """
            Init Popover
        """
        Gtk.Popover.__init__(self)
        self.__width = 0
        self.set_position(Gtk.PositionType.BOTTOM)
        self.connect("map", self.__on_map)
        search_view = SearchView()
        search_view.show()
        self.add(search_view)

    def set_text(self, text):
        """
            Set search text
        """
        self.__entry.set_text(text)

    def do_get_preferred_width(self):
        if self.__width == 0:
            return Gtk.Popover.do_get_preferred_width(self)
        else:
            return (self.__width, self.__width)

#######################
# PROTECTED           #
#######################

#######################
# PRIVATE             #
#######################
    def __on_map(self, widget):
        """
            Set popover size
            @param widget as Gtk.Widget
        """
        window_size = App().window.get_size()
        height = window_size[1]
        self.__width = min(500, window_size[0])
        self.set_size_request(self.__width, height * 0.7)
