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

from lollypop.define import Lp


class RatingWidget(Gtk.Bin):
    """
        Rate widget
    """

    def __init__(self, object):
        """
            Init widget
            @param object id as int
            @param is album as bool
        """
        Gtk.Bin.__init__(self)
        self._object = object
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/RatingWidget.ui')
        builder.connect_signals(self)

        self._stars = []
        self._stars.append(builder.get_object('star0'))
        self._stars.append(builder.get_object('star1'))
        self._stars.append(builder.get_object('star2'))
        self._stars.append(builder.get_object('star3'))
        self._stars.append(builder.get_object('star4'))
        self._on_leave_notify(None, None)
        self.add(builder.get_object('widget'))

#######################
# PRIVATE             #
#######################
    def _on_enter_notify(self, widget, event):
        """
            On enter notify, change star opacity
            @param widget as Gtk.EventBox
            @param event as Gdk.Event
        """
        event_star = widget.get_children()[0]
        # First star is hidden (used to clear score)
        if event_star.get_property("opacity") == 0.0:
            found = True
        else:
            found = False
        for star in self._stars:
            if found:
                star.set_property("opacity", 0.2)
            else:
                star.set_property("opacity", 0.8)
            if star == event_star:
                found = True

    def _on_leave_notify(self, widget, event):
        """
            On leave notify, change star opacity
            @param widget as Gtk.EventBox (can be None)
            @param event as Gdk.Event (can be None)
        """
        stars = self._object.get_popularity()
        if stars < 1:
            for i in range(5):
                self._stars[i].set_property("opacity", 0.2)
        else:
            if stars >= 1:
                self._stars[0].set_property("opacity", 0.8)
            else:
                self._stars[0].set_property("opacity", 0.2)
            if stars >= 2:
                self._stars[1].set_property("opacity", 0.8)
            else:
                self._stars[1].set_property("opacity", 0.2)
            if stars >= 3:
                self._stars[2].set_property("opacity", 0.8)
            else:
                self._stars[2].set_property("opacity", 0.2)
            if stars >= 4:
                self._stars[3].set_property("opacity", 0.8)
            else:
                self._stars[3].set_property("opacity", 0.2)
            if stars >= 4.75:
                self._stars[4].set_property("opacity", 0.8)
            else:
                self._stars[4].set_property("opacity", 0.2)

    def _on_button_press(self, widget, event):
        """
            On button press, set album popularity
            @param widget as Gtk.EventBox
            @param event as Gdk.Event
        """
        if Lp.scanner.is_locked():
            return
        event_star = widget.get_children()[0]
        position = self._stars.index(event_star)
        self._object.set_popularity(position + 1)
