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


class FlowBoxView(LazyLoadingView):
    """
        Lazy loading FlowBox
    """

    def __init__(self):
        """
            Init decade view
        """
        LazyLoadingView.__init__(self, True)
        self._widget_class = None
        self.__overlayed = None
        self._box = Gtk.FlowBox()
        self._box.set_filter_func(self._filter_func)
        self._box.set_selection_mode(Gtk.SelectionMode.NONE)
        # Allow lazy loading to not jump up and down
        self._box.set_homogeneous(True)
        self._box.set_max_children_per_line(1000)
        self._box.show()

        self._viewport.set_property("valign", Gtk.Align.START)
        self._viewport.set_property("margin", 5)
        self._scrolled.set_property("expand", True)

        self.add(self._scrolled)

    def populate(self, items):
        """
            Populate items
            @param items
        """
        GLib.idle_add(self._add_items, items)

    def disable_overlay(self):
        """
            Disable overlay widget
        """
        if self.__overlayed is not None:
            self.__overlayed.show_overlay(False)

#######################
# PROTECTED           #
#######################
    def _add_items(self, items, *args):
        """
            Add decade to the view
            Start lazy loading
            @param items as [int]
            @return added widget
        """
        if self._lazy_queue is None:
            return
        if items:
            widget = self._widget_class(items.pop(0), *args)
            self._box.insert(widget, -1)
            widget.show()
            self._lazy_queue.append(widget)
            GLib.idle_add(self._add_items, items)
            return widget
        else:
            GLib.idle_add(self.lazy_loading)
            if self._viewport.get_child() is None:
                self._viewport.add(self._box)
        return None

    def _on_overlayed(self, widget, value):
        """
            Keep overlayed widget, clean previously overlayed
            @param widget as AlbumWidget
            @param value as bool
        """
        if value:
            if self.__overlayed is not None:
                self.__overlayed.show_overlay(False)
            self.__overlayed = widget
        elif self.__overlayed == widget:
            self.__overlayed = None
#######################
# PRIVATE             #
#######################
