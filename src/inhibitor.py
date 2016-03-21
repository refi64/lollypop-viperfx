# Copyright (c) 2014-2016 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

import gi
gi.require_version('GdkX11', '3.0')
from gi.repository import GdkX11

import dbus

from lollypop.define import Lp


class Inhibitor:
    """
        Inhibitor for gnome session manager
    """

    SUSPENDING = 4
    IDLE = 8

    def __init__(self):
        """
            Init dbus objects
        """
        # Just to make pep8/flake8 happy
        GdkX11.x11_get_default_root_xwindow()
        # Dbus interface to disable screenlock
        bus = dbus.SessionBus()
        self._sm = None
        self._cookie = None
        self._flags = []
        try:
            bus_object = bus.get_object('org.gnome.SessionManager',
                                        '/org/gnome/SessionManager')
            self._sm = dbus.Interface(bus_object,
                                      'org.gnome.SessionManager')
        except:
            self._sm = None

    def uninhibit(self, flag):
        """
            Uninhibit flag
            @param flag as int
        """
        if self._sm is None:
            return
        try:
            if self._cookie is not None:
                self._sm.Uninhibit(self._cookie)
            if flag in self._flags:
                self._flags.remove(flag)
            self._set_flags()
        except Exception as e:
            print("Inhibator::uninhibit:", e)

    def inhibit(self, flag):
        """
            Inhibit flag
            @param flag as int
        """
        if self._sm is None:
            return
        try:
            if self._cookie is not None:
                self._sm.Uninhibit(self._cookie)
            if flag not in self._flags:
                self._flags.append(flag)
            self._set_flags()
        except Exception as e:
            print("Inhibator::inhibit:", e)

#######################
# PRIVATE             #
#######################
    def _set_flags(self):
        """
            Set inhibite flags
        """
        try:
            xid = Lp().window.get_window().get_xid()
            flags = 0
            for flag in self._flags:
                flags += flag
            if flags > 0:
                self._cookie = self._sm.Inhibit("Lollypop", xid,
                                                "OnDemand", flags)
        except Exception as e:
            print("Inhibator::_set_flags:", e)
