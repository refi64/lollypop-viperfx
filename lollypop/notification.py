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

from gi.repository import Gdk, GLib, Notify
from gettext import gettext as _

from lollypop.define import App


class QuitNotification:
    """
        Special notification to quit app when running in background
    """
    def __init__(self):
        """
            Init notification object with lollypop infos
        """
        self.__notification = Notify.Notification()
        self.__notification.set_category("x-gnome.music")
        self.__notification.set_hint("transient",
                                     GLib.Variant.new_boolean(False))
        self.__notification.connect("closed", self.__on_closed)
        self.__notification.update(_("Lollypop is running"),
                                   _("Click to close"),
                                   "org.gnome.Lollypop")
        try:
            self.__notification.show()
        except:
            pass

    def close(self):
        """
            Close notification
        """
        self.__notification.disconnect_by_func(self.__on_closed)
        self.__notification.close()

#######################
# PRIVATE             #
#######################
    def __on_closed(self, notification):
        App().quit()


class NotificationManager:
    """
        Freedesktop notification support
    """

    def __init__(self):
        """
            Init notification object with lollypop infos
        """
        self.__notification_handler_id = None
        self.__caps = Notify.get_server_caps()
        self.__on_notifications_settings_changed()

        App().settings.connect(
            "changed::disable-song-notifications",
            self.__on_notifications_settings_changed,
        )

        App().settings.connect(
            "changed::disable-notifications",
            self.__on_notifications_settings_changed,
        )
        self.__notification = Notify.Notification()
        self.__notification.set_category('x-gnome.music')
        self.__notification.set_hint('desktop-entry',
                                     GLib.Variant('s', 'org.gnome.Lollypop'))
        self.__set_actions()

    def send(self, message, sub=""):
        """
            Send message to user
            @param message as str
            @param sub as str
            @param transient as bool
        """
        if self.__disable_all_notifications:
            return
        self.__notification.clear_actions()
        self.__notification.clear_hints()
        self.__notification.set_hint("transient",
                                     GLib.Variant.new_boolean(True))
        self.__notification.update(message,
                                   sub,
                                   "org.gnome.Lollypop")
        try:
            self.__notification.show()
        except:
            pass
        self.__notification.clear_hints()
        self.__set_actions()

#######################
# PRIVATE             #
#######################
    def __set_actions(self):
        """
            Set notification actions
        """
        self.__notification.set_hint("transient",
                                     GLib.Variant.new_boolean(True))
        if "action-icons" in self.__caps:
            self.__notification.set_hint('action-icons',
                                         GLib.Variant('b', True))
        if "actions" in self.__caps:
            self.__notification.add_action('media-skip-backward',
                                           _("Previous"),
                                           self.__go_previous,
                                           None)
            self.__notification.add_action('media-skip-forward',
                                           _("Next"),
                                           self.__go_next,
                                           None)

    def __on_current_changed(self, player):
        """
            Update notification with track_id infos
            @param player Player
        """
        state = App().window.get_window().get_state()
        app = App().window.get_application()
        if player.current_track.id is None or (
                state & Gdk.WindowState.FOCUSED and
                App().window.is_visible()) or\
                app.is_fullscreen():
            return
        if player.current_track.album.name == '':
            self.__notification.update(
                player.current_track.title,
                # TRANSLATORS: by refers to the artist,
                _("by %s") %
                '<b>' + ", ".join(player.current_track.artists) + '</b>',
                "org.gnome.Lollypop")
        else:
            self.__notification.update(
                player.current_track.title,
                # TRANSLATORS: by refers to the artist,
                # from to the album
                _("by %s, from %s") %
                ('<b>' + ", ".join(player.current_track.artists) + '</b>',
                 '<i>' + player.current_track.album.name + '</i>'),
                "org.gnome.Lollypop")
        try:
            self.__notification.show()
        except:
            pass

    def __go_previous(self, notification, action, data):
        """
            Callback for notification prev button
        """
        App().player.prev()

    def __go_next(self, notification, action, data):
        """
            Callback for notification next button
        """
        App().player.next()

    def __on_notifications_settings_changed(self, *ignore):
        """
            Update settings
        """
        self.__disable_all_notifications = App().settings.get_value(
            "disable-notifications"
        )

        disable_song_notifications = App().settings.get_value(
            "disable-song-notifications",
        )

        if self.__notification_handler_id:
            App().player.disconnect(self.__notification_handler_id)
            self.__notification_handler_id = None

        if (not self.__disable_all_notifications and not
                disable_song_notifications):
            self.__notification_handler_id = App().player.connect(
                "current-changed",
                self.__on_current_changed,
            )
