#
# Copyright (C) 2016 Jason Gray <jasonlevigray3@gmail.com>
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
# END LICENSE

# See <https://developer.gnome.org/notification-spec/> and
# <https://github.com/JasonLG1979/possibly-useful-scraps/wiki/GioNotify>
# for documentation.

from gi.repository import GLib, Gio


class GioNotify(Gio.DBusProxy):

    __gtype_name__ = "GioNotify"

    def __init__(self, **kwargs):
        super().__init__(
            g_bus_type=Gio.BusType.SESSION,
            g_interface_name="org.freedesktop.Notifications",
            g_name="org.freedesktop.Notifications",
            g_object_path="/org/freedesktop/Notifications",
            **kwargs
        )

        self._replace_id = 0
        self._actions = []
        self._callbacks = {}
        self._hints = {}

    @classmethod
    def async_init(cls, app_name, callback):
        def on_init_finish(self, result, data):
            try:
                self.init_finish(result)
            except GLib.Error as e:
                callback(None, None, error=e)
            else:
                if not self.get_name_owner():
                    callback(None, None,
                             error='Notification service is unowned')
                else:
                    self.call(
                        'GetCapabilities',
                        None,
                        Gio.DBusCallFlags.NONE,
                        -1,
                        None,
                        on_GetCapabilities_finish,
                        None,
                    )

        def on_GetCapabilities_finish(self, result, data):
            try:
                caps = self.call_finish(result).unpack()[0]

                self._app_name = app_name

                callback(self, caps)
            except Exception as e:
                callback(None, None, error=e)

        self = cls()
        self.init_async(GLib.PRIORITY_DEFAULT, None, on_init_finish, None)

    def show_new(self, summary, body, icon):
        def on_Notify_finish(self, result):
            self._replace_id = self.call_finish(result).unpack()[0]

        args = GLib.Variant("(susssasa{sv}i)", (self._app_name,
                                                self._replace_id,
                                                icon, summary, body,
                                                self._actions, self._hints,
                                                -1))

        self.call(
            "Notify",
            args,
            Gio.DBusCallFlags.NONE,
            -1,
            None,
            on_Notify_finish,
        )

    def add_action(self, action_id, label, callback):
        self._actions += [action_id, label]
        self._callbacks[action_id] = callback

    def clear_actions(self):
        self._actions.clear()
        self._callbacks.clear()

    def set_hint(self, key, value):
        if value is None:
            if key in self._hints:
                del self._hints[key]
        else:
            self._hints[key] = value

    def do_g_signal(self, sender_name, signal_name, parameters):
        id, signal_value = parameters.unpack()
        # We only care about our notifications.
        if id != self._replace_id:
            return
        if signal_name == "ActionInvoked":
            self._callbacks[signal_value]()
