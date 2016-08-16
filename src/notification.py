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

from lollypop.define import Lp, ArtSize, Type


class NotificationManager:
    """
        Freedesktop notification support
    """

    def __init__(self):
        """
            Init notification object with lollypop infos
        """
        self.__caps = Notify.get_server_caps()
        self.__inhibitor = False
        self.__notification = Notify.Notification()
        self.__notification.set_category('x-gnome.music')
        self.__notification.set_hint('desktop-entry',
                                     GLib.Variant('s', 'lollypop'))
        self.__set_actions()
        Lp().player.connect('current-changed',
                            self.__on_current_changed)

    def send(self, message):
        """
            Send message to user
            @param message as str
        """
        self.__notification.clear_actions()
        self.__notification.clear_hints()
        self.__notification.update(message,
                                   None,
                                   "lollypop")
        try:
            self.__notification.show()
        except:
            pass
        self.__set_actions()

    def inhibit(self):
        """
            Inhibit notifications for one shot
        """
        self.__inhibitor = True

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
        if player.current_track.title == '' or self.__inhibitor:
            self.__inhibitor = False
            return
        state = Lp().window.get_window().get_state()
        app = Lp().window.get_application()
        if player.current_track.id is None or\
                state & Gdk.WindowState.FOCUSED or\
                app.is_fullscreen():
            return
        if player.current_track.id == Type.RADIOS:
            cover_path = Lp().art.get_radio_cache_path(
                player.current_track.album_artists[0], ArtSize.BIG)
        else:
            cover_path = Lp().art.get_album_cache_path(
                player.current_track.album, ArtSize.BIG)
        if cover_path is None:
            cover_path = 'lollypop'
        else:
            self.__notification.set_hint('image-path',
                                         GLib.Variant('s', cover_path))
        if player.current_track.album.name == '':
            self.__notification.update(
                player.current_track.title,
                # TRANSLATORS: by refers to the artist,
                _("by %s") %
                '<b>' + ", ".join(player.current_track.artists) + '</b>',
                cover_path)
        else:
            self.__notification.update(
                player.current_track.title,
                # TRANSLATORS: by refers to the artist,
                # from to the album
                _("by %s, from %s") %
                ('<b>' + ", ".join(player.current_track.artists) + '</b>',
                 '<i>' + player.current_track.album.name + '</i>'),
                cover_path)
        try:
            self.__notification.show()
        except:
            pass

    def __go_previous(self, notification, action, data):
        """
            Callback for notification prev button
        """
        Lp().player.prev()

    def __go_next(self, notification, action, data):
        """
            Callback for notification next button
        """
        Lp().player.next()
