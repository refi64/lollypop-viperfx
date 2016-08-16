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

    __DESTINATION = "org.gnome.SessionManager"
    __PATH = "/org/gnome/SessionManager"
    __INTERFACE = "org.gnome.SessionManager"

    def __init__(self):
        """
            Init dbus objects
        """
        # Bus to disable screenlock
        self.__bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self.__cookie = None
        self.__flags = []
        Lp().player.connect('status-changed', self.__on_status_changed)

    def uninhibit(self, flag):
        """
            Uninhibit flag
            @param flag as int
        """
        try:
            if self.__cookie is not None:
                self.__bus.call_sync(self.__DESTINATION,
                                     self.__PATH,
                                     self.__INTERFACE,
                                     'Uninhibit',
                                     GLib.Variant('(u)', (self.__cookie,)),
                                     None,
                                     Gio.DBusCallFlags.NONE,
                                     -1,
                                     None)
                self.__cookie = None
            if flag in self.__flags:
                self.__flags.remove(flag)
            self.__set_flags()
        except Exception as e:
            print("Inhibator::uninhibit:", e)

    def inhibit(self, flag):
        """
            Inhibit flag
            @param flag as int
        """
        try:
            if self.__cookie is not None:
                self.__bus.call_sync(self.__DESTINATION,
                                     self.__PATH,
                                     self.__INTERFACE,
                                     'Uninhibit',
                                     GLib.Variant('(u)', (self.__cookie,)),
                                     None,
                                     Gio.DBusCallFlags.NONE,
                                     -1,
                                     None)
                self.__cookie = None
            if flag not in self.__flags:
                self.__flags.append(flag)
            self.__set_flags()
        except Exception as e:
            print("Inhibator::inhibit:", e)

#######################
# PRIVATE             #
#######################
    def __on_status_changed(self, player):
        """
            Disallow suspend on playback
            @param player as Player
        """
        if player.is_playing():
            self.inhibit(Inhibitor.SUSPENDING)
        else:
            self.uninhibit(Inhibitor.SUSPENDING)

    def __set_flags(self):
        """
            Set inhibite flags
        """
        try:
            flags = 0
            for flag in self.__flags:
                flags += flag
            if flags > 0:
                self.__cookie = self.__bus.call_sync(
                                               self.__DESTINATION,
                                               self.__PATH,
                                               self.__INTERFACE,
                                               'Inhibit',
                                               GLib.Variant('(susu)',
                                                            ('Lollypop',
                                                             0,
                                                             'OnDemand',
                                                             flags)),
                                               GLib.VariantType.new('(u)'),
                                               Gio.DBusCallFlags.NONE,
                                               -1,
                                               None)[0]
        except Exception as e:
            print("Inhibator::__set_flags:", e)
