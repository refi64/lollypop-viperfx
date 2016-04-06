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

from gi.repository import Gio, GLib

from lollypop.define import Lp


class Inhibitor:
    """
        Inhibitor for gnome session manager
    """

    SUSPENDING = 4
    IDLE = 8

    _DESTINATION = "org.gnome.SessionManager"
    _PATH = "/org/gnome/SessionManager"
    _INTERFACE = "org.gnome.SessionManager"

    def __init__(self):
        """
            Init dbus objects
        """
        # Bus to disable screenlock
        self._bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self._cookie = None
        self._flags = []
        Lp().player.connect('status-changed', self._on_status_changed)

    def uninhibit(self, flag):
        """
            Uninhibit flag
            @param flag as int
        """
        try:
            if self._cookie is not None:
                self._bus.call_sync(self._DESTINATION,
                                    self._PATH,
                                    self._INTERFACE,
                                    'Uninhibit',
                                    GLib.Variant('(u)', (self._cookie,)),
                                    None,
                                    Gio.DBusCallFlags.NONE,
                                    -1,
                                    None)
                self._cookie = None
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
        try:
            if self._cookie is not None:
                self._bus.call_sync(self._DESTINATION,
                                    self._PATH,
                                    self._INTERFACE,
                                    'Uninhibit',
                                    GLib.Variant('(u)', (self._cookie,)),
                                    None,
                                    Gio.DBusCallFlags.NONE,
                                    -1,
                                    None)
                self._cookie = None
            if flag not in self._flags:
                self._flags.append(flag)
            self._set_flags()
        except Exception as e:
            print("Inhibator::inhibit:", e)

#######################
# PRIVATE             #
#######################
    def _on_status_changed(self, player):
        """
            Disallow suspend on playback
            @param player as Player
        """
        if player.is_playing():
            self.inhibit(Inhibitor.SUSPENDING)
        else:
            self.uninhibit(Inhibitor.SUSPENDING)

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
                self._cookie = self._bus.call_sync(
                                               self._DESTINATION,
                                               self._PATH,
                                               self._INTERFACE,
                                               'Inhibit',
                                               GLib.Variant('(susu)',
                                                            ('Lollypop',
                                                             xid,
                                                             'OnDemand',
                                                             flags)),
                                               GLib.VariantType.new('(u)'),
                                               Gio.DBusCallFlags.NONE,
                                               -1,
                                               None)[0]
        except Exception as e:
            print("Inhibator::_set_flags:", e)
