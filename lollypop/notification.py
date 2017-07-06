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

from gi.repository import Gdk, GLib
from gettext import gettext as _

from lollypop.GioNotify import GioNotify

from lollypop.define import Lp, ArtSize, Type
from lollypop.utils import is_gnome


class NotificationManager:
    """
        Freedesktop notification support
    """

    def __init__(self):
        """
            Init notification object with lollypop infos
        """
        self.__inhibitor = False
        self.__fully_initted = False
        self.__supports_actions = False
        self.__is_gnome = is_gnome()
        self.__notification = GioNotify.async_init("Lollypop",
                                                   self.__on_init_finish)

    def send(self, message, sub=""):
        """
            Send message to user
            @param message as str
            @param sub as str
        """
        if not self.__fully_initted:
            return

        if self.__supports_actions:
            self.__notification.clear_actions()

        self.__notification.show_new(
            message,
            sub,
            "org.gnome.Lollypop",
        )

        if self.__supports_actions:
            self.__set_actions()

    def inhibit(self):
        """
            Inhibit notifications for one shot
        """
        self.__inhibitor = True

#######################
# PRIVATE             #
#######################

    def __on_init_finish(self, caps):
        """
            Set actions and connect signals
            @param caps as [str]
        """
        self.__notification.set_hint(
            "category",
            GLib.Variant("s", "x-gnome.music"),
        )

        self.__notification.set_hint(
            "desktop-entry",
            GLib.Variant("s", "org.gnome.Lollypop"),
        )

        if "action-icons" in caps:
            self.__notification.set_hint(
                "action-icons",
                GLib.Variant("b", True),
            )

        if "persistence" in caps:
            self.__notification.set_hint(
                "transient",
                GLib.Variant("b", True),
            )

        if "actions" in caps:
            self.__supports_actions = True
            self.__set_actions()

        Lp().player.connect(
            "current-changed",
            self.__on_current_changed,
        )

        self.__fully_initted = True

    def __set_actions(self):
        """
            Set notification actions
        """

        self.__notification.add_action(
            "media-skip-backward",
            _("Previous"),
            Lp().player.prev,
        )

        self.__notification.add_action(
            "media-skip-forward",
            _("Next"),
            Lp().player.next,
        )

    def __on_current_changed(self, player):
        """
            Send notification with track_id infos
            @param player Player
        """
        if player.current_track.title == "" or self.__inhibitor:
            self.__inhibitor = False
            return
        state = Lp().window.get_window().get_state()
        if player.current_track.id is None or\
                state & Gdk.WindowState.FOCUSED or\
                Lp().is_fullscreen():
            return
        # Since GNOME 3.24, using album cover looks bad
        if self.__is_gnome:
            cover_path = "org.gnome.Lollypop-symbolic"
        else:
            if player.current_track.id == Type.RADIOS:
                cover_path = Lp().art.get_radio_cache_path(
                    player.current_track.album_artists[0], ArtSize.BIG)
            else:
                cover_path = Lp().art.get_album_cache_path(
                    player.current_track.album, ArtSize.BIG)
            if cover_path is None:
                cover_path = "org.gnome.Lollypop-symbolic"

        if player.current_track.album.name == "":
            self.__notification.show_new(
                player.current_track.title,
                # TRANSLATORS: by refers to the artist,
                _("by %s") %
                "<b>" + ", ".join(player.current_track.artists) + "</b>",
                cover_path)
        else:
            self.__notification.show_new(
                player.current_track.title,
                # TRANSLATORS: by refers to the artist,
                # from to the album
                _("by %s, from %s") %
                ("<b>" + ", ".join(player.current_track.artists) + "</b>",
                 "<i>" + player.current_track.album.name + "</i>"),
                cover_path)
