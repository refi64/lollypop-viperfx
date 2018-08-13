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

from gi.repository import Gtk, GLib

from lollypop.view import LazyLoadingView
from lollypop.widgets_album_decade import AlbumDecadeWidget


class AlbumsDecadeBoxView(LazyLoadingView):
    """
        Show decades in a box
    """

    def __init__(self):
        """
            Init album view
        """
        LazyLoadingView.__init__(self, True)
        self.__signal = None
        self.__current = None
        self.__context_album_id = None
        self.__press_rect = None

        self._box = Gtk.FlowBox()
        self._box.set_filter_func(self._filter_func)
        self._box.set_selection_mode(Gtk.SelectionMode.NONE)
        self._box.connect("child-activated", self.__on_decade_activated)
        # Allow lazy loading to not jump up and down
        self._box.set_homogeneous(True)
        self._box.set_max_children_per_line(1000)
        self._box.show()

        self._viewport.set_property("valign", Gtk.Align.START)
        self._viewport.set_property("margin", 5)
        self._scrolled.set_property("expand", True)

        self.add(self._scrolled)

    def populate(self, decades):
        """
            Populate decades
            @param decades as [[int]]
        """
        GLib.idle_add(self.__add_decade, decades)

    @property
    def children(self):
        """
            Return view children
            @return [AlbumWidget]
        """
        children = []
        for child in self._box.get_children():
            children.append(child)
        return children

#######################
# PROTECTED           #
#######################

#######################
# PRIVATE             #
#######################
    def __add_decade(self, decades):
        """
            Add decade to the view
            Start lazy loading
            @param decades as [[int]]
        """
        if self._stop:
            self._stop = False
            return
        if decades:
            widget = AlbumDecadeWidget(decades.pop(0))
            self._box.insert(widget, -1)
            widget.show()
            self._lazy_queue.append(widget)
            GLib.idle_add(self.__add_decade, decades)
        else:
            GLib.idle_add(self.lazy_loading)
            if self._viewport.get_child() is None:
                self._viewport.add(self._box)
