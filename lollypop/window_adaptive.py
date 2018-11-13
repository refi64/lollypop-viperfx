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

from gi.repository import GObject, Gtk, GLib


class AdaptiveWindow:
    """
        Handle window resizing and window's children workflow
        This class needs a stack and n paned
    """
    _ADAPTIVE_STACK = 750
    _TRANSITION_TYPE = Gtk.StackTransitionType.CROSSFADE

    gsignals = {
        "adaptive-changed": (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
        "show-can-go-back": (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
        "can-go-back-changed": (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
    }
    for signal in gsignals:
        args = gsignals[signal]
        GObject.signal_new(signal, Gtk.Window,
                           args[0], args[1], args[2])

    def __init__(self):
        """
            Init adaptive mode, Gtk.Window should be initialised
        """
        self._adaptive_stack = None
        self.__configure_timeout_id = None
        self.__stack = None
        self.__paned = []

    def add_stack(self, stack):
        """
            Add stack to adaptive mode
            @param stack as Gtk.Stack
        """
        self.__stack = stack
        self.__stack.set_transition_type(self._TRANSITION_TYPE)

    def add_paned(self, paned, child):
        """
            Add paned to adaptive mode
            @param paned as Gtk.Paned
            @param child as Gtk.Widget
        """
        self.__paned.append((paned, child))

    def go_back(self):
        """
            Go back in stack
        """
        visible_child = self.__stack.get_visible_child()
        previous_child = tmp = None
        for (p, c) in self.__paned:
            if c == visible_child:
                previous_child = tmp
                break
            tmp = c
        if previous_child is None:
            for (p, c) in reversed(self.__paned):
                if c.is_visible():
                    self.__stack.set_visible_child(c)
                    break
        else:
            self.__stack.set_visible_child(previous_child)
        if self.__stack.get_visible_child() == self.__paned[0][1]:
            self.emit("can-go-back-changed", False)

    def set_initial_view(self):
        """
            Set initial view
        """
        if self._adaptive_stack:
            self.__stack.set_visible_child(self.__paned[0][1])

    def do_adaptive_mode(self, width):
        """
            Handle basic adaptive mode
            Will start to listen to configure event
            @param width as int
        """
        if width < self._ADAPTIVE_STACK:
            self._set_adaptive_stack(True)
        else:
            self._set_adaptive_stack(False)
        # We delay connect to ignore initial configure events
        if self.__configure_timeout_id is None:
            self.__configure_timeout_id = GLib.timeout_add(
                                                 1000,
                                                 self.connect,
                                                 "configure-event",
                                                 self.__on_configure_event)

    @property
    def adaptive_is_on(self):
        """
            True if adaptive is on
            @return bool
        """
        return self._adaptive_stack is True

#############
# Protected #
#############
    def _set_adaptive_stack(self, b):
        """
            Move paned child to stack
            @param b as bool
        """
        # Do adaptive on init
        if self._adaptive_stack is None:
            self._adaptive_stack = not b
        if b and not self._adaptive_stack:
            self.__stack.set_transition_type(Gtk.StackTransitionType.NONE)
            self._adaptive_stack = True
            child = []
            for (p, c) in self.__paned:
                child.append(p.get_child1())
                p.remove(c)
                self.__stack.add(c)
            self.__stack.set_visible_child(self.__paned[0][1])
            self.emit("can-go-back-changed", False)
            self.emit("adaptive-changed", True)
            self.emit("show-can-go-back", True)
            self.__stack.set_transition_type(self._TRANSITION_TYPE)
        elif not b and self._adaptive_stack:
            self.__stack.set_transition_type(Gtk.StackTransitionType.NONE)
            self._adaptive_stack = False
            for child in self.__stack.get_children():
                # Move wanted child to paned
                for (p, c) in self.__paned:
                    if c == child:
                        self.__stack.remove(child)
                        p.add1(child)
                        break
            self.emit("adaptive-changed", False)
            self.emit("show-can-go-back", False)
            self.__stack.set_transition_type(self._TRANSITION_TYPE)

############
# Private  #
############
    def __on_configure_event(self, widget, event):
        """
            Delay event
            @param widget as Gtk.Window
            @param event as Gdk.EventConfigure
        """
        self.do_adaptive_mode(widget.get_size()[0])
