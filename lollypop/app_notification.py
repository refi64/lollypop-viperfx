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


class AppNotification(Gtk.Revealer):
    """
        Show a notification to user with a button connected to an action
    """

    def __init__(self, label, button_label, action, *args):
        """
            Init notification
            @param label as str
            @param button_label as str
            @param action as callback
        """
        Gtk.Revealer.__init__(self)
        self.__action = action
        self.__args = args
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/AppNotification.ui")
        builder.connect_signals(self)
        builder.get_object("label").set_text(label)
        builder.get_object("button").set_label(button_label)
        self.add(builder.get_object("widget"))
        self.set_property("halign", Gtk.Align.CENTER)
        self.set_property("valign", Gtk.Align.START)

#######################
# PROTECTED           #
#######################
    def _on_button_clicked(self, button):
        """
            Execute action
            @param button as Gtk.Button
        """
        self.set_reveal_child(False)
        GLib.timeout_add(1000, self.destroy)
        self.__action(*self.__args)
