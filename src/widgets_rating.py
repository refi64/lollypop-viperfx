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

from lollypop.define import Lp


class RatingWidget(Gtk.Bin):
    """
        Init widget
        @param object id as int
        @param is album as bool
    """
    # FIXME is_album unused in this class as we need Gtk.ModelButton introduced
    # in Gtk 3.16 to add this to a menu. FIXME later
    def __init__(self, object_id, is_album):
        Gtk.Bin.__init__(self)
        self._object_id = object_id
        self._is_album = is_album
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
    """
        On enter notify, change star opacity
        @param widget as Gtk.EventBox
        @param event as Gdk.Event
    """
    def _on_enter_notify(self, widget, event):
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

    """
        On leave notify, change star opacity
        @param widget as Gtk.EventBox (can be None)
        @param event as Gdk.Event (can be None)
    """
    def _on_leave_notify(self, widget, event):
        if self._is_album:
            avg_popularity = Lp.albums.get_avg_popularity()
        else:
            avg_popularity = Lp.tracks.get_avg_popularity()

        if avg_popularity > 0:
            if self._is_album:
                popularity = Lp.albums.get_popularity(self._object_id)
            else:
                popularity = Lp.tracks.get_popularity(self._object_id)

            stars = popularity*5/avg_popularity+0.5
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
        else:
            for i in range(5):
                self._stars[i].set_property("opacity", 0.2)

    """
        On button press, set album popularity
        @param widget as Gtk.EventBox
        @param event as Gdk.Event
    """
    def _on_button_press(self, widget, event):
        if Lp.scanner.is_locked():
            return
        event_star = widget.get_children()[0]
        try:
            position = self._stars.index(event_star)
            if self._is_album:
                avg_popularity = Lp.albums.get_avg_popularity()
            else:
                avg_popularity = Lp.tracks.get_avg_popularity()
            popularity = int(((position+1)*avg_popularity/5)+0.5)
            if self._is_album:
                Lp.albums.set_popularity(self._object_id, popularity)
            else:
                Lp.tracks.set_popularity(self._object_id, popularity)
        except:
            if self._is_album:
                Lp.albums.set_popularity(self._object_id, 0)
            else:
                Lp.tracks.set_popularity(self._object_id, 0)
        Lp.sql.commit()
