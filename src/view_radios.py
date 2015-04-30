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

from gi.repository import Gtk

from _thread import start_new_thread

from lollypop.view import View
from lollypop.define import Objects


# Radios view
class RadiosView(View):
    """
        Init radios ui with a scrolled grid of radios widgets
    """
    def __init__(self, playlist_name, parent):
        View.__init__(self)
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/RadiosView.ui')
#       builder.connect_signals(self)
        widget = builder.get_object('widget')

        self._radiobox = Gtk.FlowBox()
        self._radiobox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._radiobox.connect("child-activated", self._on_album_activated)
        self._radiobox.set_max_children_per_line(100)
        self._radiobox.show()

        widget.add(self._radiobox)

        self._viewport.set_property("valign", Gtk.Align.START)
        self._viewport.add(widget)
        self._scrolledWindow.set_property('expand', True)

        self.add(self._scrolledWindow)

    """
        Populate view with tracks from playlist
        Thread safe
    """
    def populate(self):
        pass

#######################
# PRIVATE             #
#######################
    """
        Current song changed
        @param player as Player
    """
    def _on_current_changed(self, player):
        pass
