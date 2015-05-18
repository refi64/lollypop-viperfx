#!/usr/bin/python
# Copyright (c) 2014-2015 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from lollypop.view import View
from lollypop.widgets_radio import RadioWidget
from lollypop.playlists import RadiosManager
from lollypop.popradio import PopRadio
from lollypop.define import Lp
from lollypop.track import Track

# Radios view
class RadiosView(View):
    """
        Init radios ui with a scrolled grid of radios widgets
    """
    def __init__(self):
        View.__init__(self)

        self._signal = None

        self._radios_manager = RadiosManager()
        self._radios_manager.connect('playlists-changed',
                                     self._on_radios_changed)
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/RadiosView.ui')
        builder.connect_signals(self)
        widget = builder.get_object('widget')

        self._sizegroup = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.BOTH)

        self._radiobox = Gtk.FlowBox()
        self._radiobox.set_sort_func(self._sort_radios)
        self._radiobox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._radiobox.connect("child-activated", self._on_album_activated)
        self._radiobox.set_property('column-spacing', 5)
        self._radiobox.set_property('row-spacing', 5)
        self._radiobox.set_homogeneous(True)
        self._radiobox.set_max_children_per_line(1000)
        self._radiobox.show()

        self._viewport.set_property("valign", Gtk.Align.START)
        self._viewport.set_property('margin', 5)
        self._viewport.add(self._radiobox)
        self._scrolledWindow.set_property('expand', True)

        self.add(widget)
        self.add(self._scrolledWindow)

    """
        Populate view with tracks from playlist
        Thread safe
    """
    def populate(self):
        radios_name = []
        # Get radios name
        for (i, name) in self._radios_manager.get():
            radios_name.append(name)
        GLib.idle_add(self._add_radios, radios_name)

    """
        Connect player signal
    """
    def do_show(self):
        View.do_show(self)
        self._signal = Lp.player.connect('logo-changed',
                                              self._on_logo_changed)

    """
        Disconnect player signal
    """
    def do_hide(self):
        View.do_hide(self)
        if self._signal is not None:
            Lp.player.disconnect(self._signal)

#######################
# PRIVATE             #
#######################
    """
        Return view children
        @return [RadioWidget]
    """
    def _get_children(self):
        children = []
        for child in self._radiobox.get_children():
            widget =  child.get_child()
            children.append(widget)
        return children

    """
        Sort radios
        @param a as Gtk.FlowBoxChild
        @param b as Gtk.FlowBoxChild
    """
    def _sort_radios(self, a, b):
        child1 = a.get_children()[0]
        child2 = b.get_children()[0]
        return child1.get_name().lower() > child2.get_name().lower()

    """
        Show popover
        @param widget as Gtk.Widget
    """
    def _on_new_clicked(self, widget):
        popover = PopRadio('', self._radios_manager)
        popover.set_relative_to(widget)
        popover.show()

    """
        Update radios
        @param manager as PlaylistManager
    """
    def _on_radios_changed(self, manager):
        radios_name = []
        currents = []
        new_name = None
        old_widget = None
        old_child = None

        # Get radios name
        for (i, name) in manager.get():
            radios_name.append(name)

        # Get currents widget less removed
        for child in self._radiobox.get_children():
            widget = child.get_child()
            if widget.get_name() not in radios_name:
                old_widget = widget
                old_child = child
            else:
                currents.append(widget.get_name())


        # Add the new radio
        for name in radios_name:
            if name not in currents:
                new_name = name
                break

        # Rename widget
        if new_name is not None:
            if old_widget is not None:
                old_widget.set_name(new_name)
            else:
                self._add_radios([new_name])
        # Delete widget
        elif old_widget is not None:
            self._radiobox.remove(old_child)
            old_widget.destroy()

    """
        Update radio logo
        @param player as Plyaer
        @param name as string
    """
    def _on_logo_changed(self, player, name):
        for child in self._radiobox.get_children():
            widget = child.get_child()
            if widget.get_name() == name:
                widget.update_cover()

    """
        Pop a radio and add it to the view,
        repeat operation until radio list is empty
        @param [radio names as string]
        @return new widget as RadioWidget
    """
    def _add_radios(self, radios):
        if radios and not self._stop:
            radio = radios.pop(0)
            uris = self._radios_manager.get_tracks(radio)
            if len(uris) > 0:
                widget = RadioWidget(radio,
                                     uris[0],
                                     self._radios_manager)
                widget.show()
                self._sizegroup.add_widget(widget)
                self._radiobox.insert(widget, -1)
                return widget
            GLib.idle_add(self._add_radios, radios)
        else:
            self._stop = False
        return None

    """
        Play album
        @param flowbox as Gtk.Flowbox
        @child as Gtk.FlowboxChild
    """
    def _on_album_activated(self, flowbox, child):
        name = child.get_child().get_name()
        uri =  child.get_child().get_uri()
        track = Track()
        track.set_radio(name, uri)
        Lp.player.load(track)
