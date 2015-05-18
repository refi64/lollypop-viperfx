#!/usr/bin/python
# Copyright (c) 2014-2015 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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
        Init notification object with lollypop infos
    """
    def __init__(self):
        self._caps = Notify.get_server_caps()

        self._notification = Notify.Notification()
        self._notification.set_category('x-gnome.music')
        self._notification.set_hint('desktop-entry',
                                    GLib.Variant('s', 'lollypop'))
        self._set_actions()
        Lp.player.connect('current-changed',
                          self._on_current_changed)

    """
        Send message to user
        @param message as str
    """
    def send(self, message):
        self._notification.clear_actions()
        self._notification.clear_hints()
        self._notification.update(message,
                                  None,
                                  "lollypop")
        try:
            self._notification.show()
        except:
            pass
        self._set_actions()

#######################
# PRIVATE             #
#######################
    """
        Set notification actions
    """
    def _set_actions(self):
        if "action-icons" in self._caps:
            self._notification.set_hint('action-icons',
                                        GLib.Variant('b', True))
        if "actions" in self._caps:
            self._notification.add_action('media-skip-backward',
                                          _("Previous"),
                                          self._go_previous,
                                          None)
            self._notification.add_action('media-skip-forward',
                                          _("Next"),
                                          self._go_next,
                                          None)

    """
        Update notification with track_id infos
        @param player Player
    """
    def _on_current_changed(self, player):
        state = Lp.window.get_window().get_state()
        app = Lp.window.get_application()
        if player.current_track.id is None or state & Gdk.WindowState.FOCUSED\
                                     or app.is_fullscreen():
            return
        if player.current_track.id == Type.RADIOS:
            cover_path = Lp.art.get_radio_cache_path(
                                                   player.current_track.artist,
                                                   ArtSize.BIG)
        else:
            cover_path = Lp.art.get_album_cache_path(
                                                   player.current_track.album_id,
                                                   ArtSize.BIG)
        if cover_path is not None:
            self._notification.set_hint('image-path',
                                        GLib.Variant('s', cover_path))
        else:
            self._notification.set_hint('image-path',
                                        GLib.Variant('s', ''))

        self._notification.update(player.current_track.title,
                                  # TRANSLATORS: by refers to the artist,
                                  # from to the album
                                  _("by %s, from %s") %
                                  ('<b>' + player.current_track.artist + '</b>',
                                   '<i>' + player.current_track.album + '</i>'),
                                  'lollypop')
        try:
            self._notification.show()
        except:
            pass

    """
        Callback for notification prev button
    """
    def _go_previous(self, notification, action, data):
        Lp.player.prev()

    """
        Callback for notification next button
    """
    def _go_next(self, notification, action, data):
        Lp.player.next()
