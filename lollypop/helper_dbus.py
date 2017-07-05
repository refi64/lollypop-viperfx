# Copyright (c) 2017 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import Gio

from lollypop.define import PROXY_BUS, PROXY_PATH, PROXY_INTERFACE, Lp


class DBusHelper:
    """
        Simpler helper for DBus
    """

    def __init__(self):
        pass

    def call(self, call, args, callback, data):
        """
            Call function
            @param call as str
            @param args as GLib.Variant()/None
            @param callback as function
            @param data
        """
        try:
            bus = Lp().get_dbus_connection()
            Gio.DBusProxy.new(bus, Gio.DBusProxyFlags.NONE, None,
                              PROXY_BUS,
                              PROXY_PATH,
                              PROXY_INTERFACE, None,
                              self.__on_get_proxy, call, args, callback, data)
        except Exception as e:
            print("DBusHelper::call():", e)

#######################
# PRIVATE             #
#######################
    def __on_get_proxy(self, source, result, call, args, callback, data):
        """
            Launch call and connect it to callback
            @param source as GObject.Object
            @param result as Gio.AsyncResult
            @param call as str
            @param args as GLib.Variant()/None
            @param callback as function
            @param data
        """
        try:
            proxy = source.new_finish(result)
            proxy.call(call, args, Gio.DBusCallFlags.NO_AUTO_START,
                       500, None, callback, data)
        except Exception as e:
            print("DBusHelper::__on_get_proxy():", e)
