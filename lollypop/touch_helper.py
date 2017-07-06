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

from gi.repository import GObject, Gio, GLib

from lollypop.define import Lp, Type


class TouchHelper(GObject.GObject):
    """
        Allow to launch a function after a long click
        Can't get touch gtk support to work with python
    """

    def __init__(self, widget, action, shortcut):
        """
            Init touch helper
            @param widget as Gtk.Widget
            @param action as str/None
            @param shortcut as str/None
        """
        GObject.GObject.__init__(self)
        self.__timeout_id = None
        widget.connect("button-press-event", self.__on_button_press)
        widget.connect("button-release-event", self.__on_button_release)
        if action is not None:
            new_action = Gio.SimpleAction.new(action, None)
            new_action.connect("activate", self.__on_action_activate)
            Lp().add_action(new_action)
            Lp().set_accels_for_action("app.%s" % action, [shortcut])

    def set_short_func(self, short_func, *args):
        """
            @param short func as function
            @param short args
        """
        self.__short_func = short_func
        self.__short_args = args

    def set_long_func(self, long_func, *args):
        """
            @param long func as function
            @param long args
        """
        self.__long_func = long_func
        self.__long_args = args

#######################
# PRIVATE             #
#######################
    def __launch_long_func(self):
        """
            Launch long func
        """
        self.__timeout_id = Type.NONE
        self.__long_func(self.__long_args)

    def __on_action_activate(self, action, param):
        """
            Launch short func
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
        """
        self.__short_func(self.__short_args)

    def __on_button_press(self, widget, event):
        """
            Launch long func
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        self.__timeout_id = GLib.timeout_add(500,
                                             self.__launch_long_func)
        return True

    def __on_button_release(self, widget, event):
        """
            Launch short func if needed
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        # Ignore this release event, long func called
        if self.__timeout_id == Type.NONE:
            self.__timeout_id = None
            return True
        elif self.__timeout_id is not None:
            GLib.source_remove(self.__timeout_id)
            self.__timeout_id = None
        if event is None or event.button == 1:
            self.__short_func(self.__short_args)
        else:
            self.__long_func(self.__long_args)
        return True
