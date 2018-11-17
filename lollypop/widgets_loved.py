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

from gi.repository import Gtk

from lollypop.define import App
from lollypop.objects import Track


class LovedWidget(Gtk.Bin):
    """
        Loved widget
    """

    def __init__(self, object):
        """
            Init widget
            @param object as Album/Track
        """
        Gtk.Bin.__init__(self)
        self.__object = object
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/LovedWidget.ui")
        builder.connect_signals(self)

        self.add(builder.get_object("widget"))
        self.set_property("valign", Gtk.Align.CENTER)
        self.set_opacity(0.8 if object.loved else 0.2)

#######################
# PROTECTED           #
#######################
    def _on_enter_notify_event(self, widget, event):
        """
            Update love opacity
            @param widget as Gtk.EventBox
            @param event as Gdk.Event
        """
        self.set_opacity(0.2 if self.__object.loved else 0.8)

    def _on_leave_notify_event(self, widget, event):
        """
            Update love opacity
            @param widget as Gtk.EventBox (can be None)
            @param event as Gdk.Event (can be None)
        """
        self.set_opacity(0.8 if self.__object.loved else 0.2)

    def _on_button_release_event(self, widget, event):
        """
            Toggle loved status
            @param widget as Gtk.EventBox
            @param event as Gdk.Event
        """
        loved = not self.__object.loved
        self.__object.set_loved(loved)
        if App().lastfm is not None and isinstance(self.__object, Track):
            App().lastfm.set_loved(self.__object, loved)
        self.set_opacity(0.8 if loved else 0.2)
        return True
