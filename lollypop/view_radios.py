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

from lollypop.helper_task import TaskHelper
from lollypop.view import LazyLoadingView
from lollypop.widgets_radio import RadioWidget
from lollypop.radios import Radios
from lollypop.pop_radio import RadioPopover
from lollypop.pop_tunein import TuneinPopover
from lollypop.define import Lp, Type


class RadiosView(LazyLoadingView):
    """
        Show radios in a grid
    """

    def __init__(self):
        """
            Init view
        """
        LazyLoadingView.__init__(self, True)
        self.__signal = Lp().art.connect("radio-artwork-changed",
                                         self.__on_logo_changed)

        self.__radios_manager = Radios()
        self.__radios_manager.connect("radios-changed",
                                      self.__on_radios_changed)
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/RadiosView.ui")
        builder.connect_signals(self)
        widget = builder.get_object("widget")
        self.__empty = builder.get_object("empty")

        self.__pop_tunein = TuneinPopover(self.__radios_manager)
        self.__pop_tunein.set_relative_to(builder.get_object("search_btn"))

        self._box = Gtk.FlowBox()
        self._box.set_selection_mode(Gtk.SelectionMode.NONE)
        # Allow lazy loading to not jump up and down
        self._box.set_homogeneous(True)
        self._box.set_max_children_per_line(1000)
        self._box.set_filter_func(self._filter_func)
        self._box.show()

        self.__stack = Gtk.Stack()
        self.__stack.set_transition_duration(500)
        self.__stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.__stack.add(self._scrolled)
        self.__stack.add(self.__empty)
        self.__stack.show()

        self._viewport.set_property("valign", Gtk.Align.START)
        self._viewport.set_property("margin", 5)
        self._scrolled.set_property("expand", True)

        self.add(widget)
        self.add(self.__stack)

    def populate(self):
        """
            Populate view with tracks from playlist
        """
        Lp().player.set_radios(self.__radios_manager.get())
        if Lp().player.current_track.id == Type.RADIOS:
            Lp().player.set_next()  # We force next update
            Lp().player.set_prev()  # We force prev update
        helper = TaskHelper()
        helper.run(self.__get_radios, callback=(self.__on_get_radios,))

#######################
# PROTECTED           #
#######################
    def _get_children(self):
        """
            Return view children
            @return [RadioWidget]
        """
        children = []
        for child in self._box.get_children():
            children.append(child)
        return children

    def _on_destroy(self, widget):
        """
            Disconnect signals
            @param widget as Gtk.Widget
        """
        LazyLoadingView._on_destroy(self, widget)
        if self.__signal is not None:
            Lp().art.disconnect(self.__signal)

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
            else:
                radios = [new_name]
                self.__show_stack(radios)
        # Delete widget
        elif old_child is not None:
            old_child.destroy()
            if not self._box.get_children():
                self.__show_stack([])

        # Update player state based on current view
        radios = []
        for child in self._box.get_children():
            name = child.title
            url = manager.get_url(name)
            radios.append((name, url))
        Lp().player.set_radios(radios)
        if Lp().player.current_track.id == Type.RADIOS:
            Lp().player.set_next()  # We force next update
            Lp().player.set_prev()  # We force prev update

    def __on_logo_changed(self, player, name):
        """
            Update radio logo
            @param player as Plyaer
            @param name as string
        """
        for child in self._box.get_children():
            if child.title == name:
                child.update_cover()

    def __add_radios(self, radios, first=False):
        """
            Pop a radio and add it to the view,
            repeat operation until radio list is empty
            @param [radio names as string]
            @param first as bool
        """
        if self._stop:
            self._stop = False
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

    def __on_get_radios(self, radios):
        """
            Switch empty/radios view based on radios
            @param [radio names as string]
        """
        if radios:
            self.__stack.set_visible_child(self._scrolled)
            self.__add_radios(radios, True)
        else:
            self.__stack.set_visible_child(self.__empty)
