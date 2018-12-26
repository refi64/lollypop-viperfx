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

from lollypop.define import App
from lollypop.view import View
from lollypop.adaptive import AdaptiveStack
from lollypop.container_device import DeviceContainer
from lollypop.container_donation import DonationContainer
from lollypop.container_progress import ProgressContainer
from lollypop.container_scanner import ScannerContainer
from lollypop.container_playlists import PlaylistsContainer
from lollypop.container_lists import ListsContainer
from lollypop.container_views import ViewsContainer


class Container(Gtk.Overlay, DeviceContainer, DonationContainer,
                ProgressContainer, ScannerContainer, PlaylistsContainer,
                ListsContainer, ViewsContainer):
    """
        Main view management
    """

    def __init__(self):
        """
            Init container
        """
        Gtk.Overlay.__init__(self)
        DeviceContainer.__init__(self)
        DonationContainer.__init__(self)
        ProgressContainer.__init__(self)
        ScannerContainer.__init__(self)
        PlaylistsContainer.__init__(self)
        ListsContainer.__init__(self)
        ViewsContainer.__init__(self)
        self._rounded_artists_view = None
        self._stack = AdaptiveStack()
        self._stack.show()
        self.__setup_view()
        self.add(self.__paned_one)

    def stop_all(self):
        """
            Stop current view from processing
        """
        view = self._stack.get_visible_child()
        if view is not None:
            view.stop()

    def show_genres(self, show):
        """
            Show/Hide genres
            @param bool
        """
        def select_list_one(selection_list):
            self._list_one.select_first()
            self._list_one.disconnect_by_func(select_list_one)
        if App().settings.get_value("show-sidebar"):
            self._list_two.hide()
            self.update_list_one()
            self._list_one.connect("populated", select_list_one)

    def reload_view(self):
        """
            Reload current view
        """
        if App().settings.get_value("show-sidebar"):
            self._reload_list_view()
        else:
            self._reload_navigation_view()

    def save_internals(self):
        """
            Save paned position
        """
        main_pos = self.__paned_one.get_position()
        listview_pos = self.__paned_two.get_position()
        listview_pos = listview_pos if listview_pos > 100 else 100
        App().settings.set_value("paned-mainlist-width",
                                 GLib.Variant("i",
                                              main_pos))
        App().settings.set_value("paned-listview-width",
                                 GLib.Variant("i",
                                              listview_pos))

    def show_sidebar(self, show):
        """
            Show/Hide navigation sidebar
            @param show as bool
        """
        def select_list_one(selection_list):
            self._reload_list_view()
            self._list_one.disconnect_by_func(select_list_one)

        adaptive_window = App().window.is_adaptive
        self._stack.set_navigation_enabled(not show or adaptive_window)
        if self._rounded_artists_view is not None:
            self._rounded_artists_view.destroy()
            self._rounded_artists_view = None
        if show or adaptive_window:
            if not adaptive_window:
                App().window.emit("show-can-go-back", False)
            self._list_one.show()
            if self._list_one.count == 0:
                self._list_one.connect("populated", select_list_one)
                self.update_list_one()
            else:
                self._reload_list_view()
        elif not adaptive_window:
            if self._list_one.get_visible():
                self._list_two.hide()
                self._list_one.hide()
            for child in self._stack.get_children():
                child.destroy()
            self._reload_navigation_view()

    @property
    def view(self):
        """
            Get current view
            @return View
        """
        view = self._stack.get_visible_child()
        if view is not None and isinstance(view, View):
            return view
        return None

    @property
    def stack(self):
        """
            Container stack
            @return stack as Gtk.Stack
        """
        return self._stack

    @property
    def paned_one(self):
        """
            Get first paned (list_one)
        """
        return self.__paned_one

    @property
    def paned_two(self):
        """
            Get second paned (list_two)
        """
        return self.__paned_two

############
# PRIVATE  #
############
    def __setup_view(self):
        """
            Setup window main view:
                - genre list
                - artist list
                - main view as artist view or album view
        """
        self.__paned_one = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        self.__paned_two = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)

        vgrid = Gtk.Grid()
        vgrid.set_orientation(Gtk.Orientation.VERTICAL)

        vgrid.add(self._stack)
        vgrid.add(self._progress)
        vgrid.show()

        self.__paned_two.add1(self._list_two)
        self.__paned_two.add2(vgrid)
        self.__paned_one.add1(self._list_one)
        self.__paned_one.add2(self.__paned_two)
        self.__paned_one.set_position(
            App().settings.get_value("paned-mainlist-width").get_int32())
        self.__paned_two.set_position(
            App().settings.get_value("paned-listview-width").get_int32())
        self.__paned_one.show()
        self.__paned_two.show()
