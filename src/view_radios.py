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

from threading import Thread

from lollypop.view import View
from lollypop.widgets_radio import RadioWidget
from lollypop.radios import Radios
from lollypop.pop_radio import RadioPopover
from lollypop.pop_tunein import TuneinPopover
from lollypop.define import Lp
from lollypop.objects import Track


class RadiosView(View):
    """
        Show radios in a grid
    """

    def __init__(self):
        """
            Init view
        """
        View.__init__(self)
        self._signal = Lp.art.connect('radio-artwork-changed',
                                      self._on_logo_changed)

        self._radios_manager = Radios()
        self._radios_manager.connect('radios-changed',
                                     self._on_radios_changed)
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/RadiosView.ui')
        builder.connect_signals(self)
        widget = builder.get_object('widget')
        self._empty = builder.get_object('empty')

        self._pop_tunein = TuneinPopover(self._radios_manager)
        self._pop_tunein.set_relative_to(builder.get_object('search_btn'))

        self._sizegroup = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.BOTH)

        self._radiobox = Gtk.FlowBox()
        self._radiobox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._radiobox.connect("child-activated", self._on_album_activated)
        self._radiobox.set_property('column-spacing', 5)
        self._radiobox.set_property('row-spacing', 5)
        self._radiobox.set_homogeneous(True)
        self._radiobox.set_max_children_per_line(1000)
        self._radiobox.show()

        self._stack = Gtk.Stack()
        self._stack.set_transition_duration(500)
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._stack.add(self._scrolledWindow)
        self._stack.add(self._empty)
        self._stack.show()

        self._viewport.set_property("valign", Gtk.Align.START)
        self._viewport.set_property('margin', 5)
        self._viewport.add(self._radiobox)
        self._scrolledWindow.set_property('expand', True)

        self.add(widget)
        self.add(self._stack)

    def populate(self):
        """
            Populate view with tracks from playlist
            Thread safe
        """
        t = Thread(target=self._populate)
        t.daemon = True
        t.start()

#######################
# PRIVATE             #
#######################
    def _populate(self):
        """
            Populate view with tracks from playlist
            Thread safe
        """
        radios = []
        # Get radios name
        for (name, url) in self._radios_manager.get():
            radios.append(name)
        GLib.idle_add(self._show_stack, radios)

    def _get_children(self):
        """
            Return view children
            @return [RadioWidget]
        """
        children = []
        for child in self._radiobox.get_children():
            widget = child.get_child()
            children.append(widget)
        return children

    def _on_destroy(self, widget):
        """
            Disconnect signals
            @param widget as Gtk.Widget
        """
        if self._signal is not None:
            Lp.art.disconnect(self._signal)

    def _on_new_clicked(self, widget):
        """
            Show popover for adding a new radio
            @param widget as Gtk.Widget
        """
        popover = RadioPopover('', self._radios_manager)
        popover.set_relative_to(widget)
        popover.show()

    def _on_search_clicked(self, widget):
        """
            Show popover for searching radios
            @param widget as Gtk.Widget
        """
        self._pop_tunein.populate()
        self._pop_tunein.show()

    def _on_radios_changed(self, manager):
        """
            Update radios
            @param manager as PlaylistManager
        """
        radios_name = []
        currents = []
        new_name = None
        old_widget = None
        old_child = None

        # Get radios name
        for (name, url) in manager.get():
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
                radios = [new_name]
                self._show_stack(radios)
        # Delete widget
        elif old_widget is not None:
            self._radiobox.remove(old_child)
            old_widget.destroy()
            if not self._radiobox.get_children():
                self._show_stack([])

    def _on_logo_changed(self, player, name):
        """
            Update radio logo
            @param player as Plyaer
            @param name as string
        """
        for child in self._radiobox.get_children():
            widget = child.get_child()
            if widget.get_name() == name:
                widget.update_cover()

    def _show_stack(self, radios):
        """
            Switch empty/radios view based on radios
            @param [radio names as string]
        """
        if radios:
            self._stack.set_visible_child(self._scrolledWindow)
            self._add_radios(radios, True)
        else:
            self._stack.set_visible_child(self._empty)

    def _add_radios(self, radios, first=False):
        """
            Pop a radio and add it to the view,
            repeat operation until radio list is empty
            @param [radio names as string]
            @param first as bool
        """
        if radios and not self._stop:
            radio = radios.pop(0)
            widget = RadioWidget(radio,
                                 self._radios_manager)
            widget.show()
            self._sizegroup.add_widget(widget)
            if first:
                self._radiobox.insert(widget, 0)
            else:
                self._radiobox.insert(widget, -1)
            GLib.idle_add(self._add_radios, radios)
        else:
            self._stop = False
        return None

    def _on_album_activated(self, flowbox, child):
        """
            Play album
            @param flowbox as Gtk.Flowbox
            @child as Gtk.FlowboxChild
        """
        name = child.get_child().get_name()
        url = self._radios_manager.get_url(name)
        if url:
            track = Track()
            track.set_radio(name, url)
            Lp.player.load(track)
