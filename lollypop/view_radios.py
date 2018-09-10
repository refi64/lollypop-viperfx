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

from lollypop.helper_task import TaskHelper
from lollypop.view_flowbox import FlowBoxView
from lollypop.widgets_radio import RadioWidget
from lollypop.radios import Radios
from lollypop.pop_radio import RadioPopover
from lollypop.pop_tunein import TuneinPopover
from lollypop.controller_view import ViewController


class RadiosView(FlowBoxView, ViewController):
    """
        Show radios flow box
    """

    def __init__(self):
        """
            Init view
        """
        FlowBoxView.__init__(self)
        ViewController.__init__(self)

        self.__radios_manager = Radios()
        self.__radios_manager.connect("radios-changed",
                                      self.__on_radios_changed)
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/RadiosView.ui")
        builder.connect_signals(self)
        self.__widget = builder.get_object("widget")
        self.__empty = builder.get_object("empty")
        self._viewport.add(self.__empty)

        self.__pop_tunein = TuneinPopover(self.__radios_manager)
        self.__pop_tunein.set_relative_to(builder.get_object("search_btn"))

        self.connect_artwork_changed_signal("radio")

    def populate(self):
        """
            Populate view with tracks from playlist
        """
        helper = TaskHelper()
        helper.run(self.__get_radios, callback=(self.__on_get_radios,))

#######################
# PROTECTED           #
#######################
    def _on_new_clicked(self, widget):
        """
            Show popover for adding a new radio
            @param widget as Gtk.Widget
        """
        popover = RadioPopover("", self.__radios_manager)
        popover.set_relative_to(widget)
        popover.show()

    def _on_search_clicked(self, widget):
        """
            Show popover for searching radios
            @param widget as Gtk.Widget
        """
        self.__pop_tunein.populate()
        self.__pop_tunein.show()

    def _on_artwork_changed(self, artwork, name):
        """
            Update children artwork if matching name
            @param artwork as Artwork
            @param name as str
        """
        for child in self._box.get_children():
            child.set_artwork(name)

#######################
# PRIVATE             #
#######################
    def __get_radios(self):
        """
            Get radios
            @return [name]
        """
        radios = []
        # Get radios name
        for (name, url) in self.__radios_manager.get():
            radios.append(name)
        return radios

    def __on_radios_changed(self, manager):
        """
            Update radios
            @param manager as PlaylistManager
        """
        radios_name = []
        currents = []
        new_name = None
        old_child = None

        # Get radios name
        for (name, url) in manager.get():
            radios_name.append(name)

        # Get currents widget less removed
        for child in self._box.get_children():
            if child.title not in radios_name:
                old_child = child
            else:
                currents.append(child.title)

        # Add the new radio
        for name in radios_name:
            if name not in currents:
                new_name = name
                break

        # Rename widget
        if new_name is not None:
            if old_child is not None:
                old_child.set_name(new_name)
        # Delete widget
        elif old_child is not None:
            old_child.destroy()

    def __add_radios(self, radios, first=False):
        """
            Pop a radio and add it to the view,
            repeat operation until radio list is empty
            @param [radio names as string]
            @param first as bool
        """
        if self._lazy_queue is None:
            return
        if radios:
            radio = radios.pop(0)
            widget = RadioWidget(radio,
                                 self.__radios_manager)
            widget.connect("overlayed", self._on_overlayed)
            widget.show()
            self._lazy_queue.append(widget)
            if first:
                self._box.insert(widget, 0)
            else:
                self._box.insert(widget, -1)
            GLib.idle_add(self.__add_radios, radios)
        else:
            GLib.idle_add(self.lazy_loading)
            if self._viewport.get_child() is None:
                self._viewport.add(self._box)

    def __on_logo_changed(self, player, name):
        """
            Update radio logo
            @param player as Plyaer
            @param name as string
        """
        for child in self._box.get_children():
            if child.title == name:
                child.update_cover()

    def __on_get_radios(self, radios):
        """
            Switch empty/radios view based on radios
            @param [radio names as string]
        """
        if radios:
            self._viewport.get_child().destroy()
            self.__add_radios(radios, True)
