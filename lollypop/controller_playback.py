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

from gi.repository import GLib

from gettext import gettext as _

from lollypop.define import Type, App


class PlaybackController:
    """
        Button controller (for toolbars)
    """

    def __init__(self):
        """
            Init controller
        """
        pass

    def on_current_changed(self, player):
        """
            Update toolbar
            @param player as Player
        """
        is_radio = App().player.current_track.id == Type.RADIOS
        self._play_btn.set_sensitive(True)
        self._prev_btn.set_sensitive(not App().player.locked and not is_radio)
        self._next_btn.set_sensitive(not App().player.locked and not is_radio)

    def on_prev_changed(self, player):
        """
            Update prev button
            @param player as Player
        """
        if player.prev_track.id == Type.RADIOS:
            self._prev_btn.set_tooltip_text(
                ", ".join(player.prev_track.album_artists))
        elif player.prev_track.id is not None:
            prev_artists = GLib.markup_escape_text(
                ", ".join(player.prev_track.artists))
            prev_title = GLib.markup_escape_text(player.prev_track.title)
            self._prev_btn.set_tooltip_markup("<b>%s</b> - %s" %
                                              (prev_artists,
                                               prev_title))
        else:
            self._prev_btn.set_tooltip_text("")

    def on_next_changed(self, player):
        """
            Update toolbar
            @param player as Player
        """
        if player.next_track.id == Type.RADIOS:
            self._next_btn.set_tooltip_text(
                ", ".join(player.next_track.album_artists))
        elif player.next_track.id is not None:
            next_artists = GLib.markup_escape_text(
                ", ".join(player.next_track.artists))
            next_title = GLib.markup_escape_text(player.next_track.title)
            self._next_btn.set_tooltip_markup("<b>%s</b> - %s" %
                                              (next_artists,
                                               next_title))
        else:
            self._prev_btn.set_tooltip_text("")

    def on_status_changed(self, player):
        """
            Update buttons and progress bar
            @param player as Player
        """
        # GTK bug, should not be needed, see #1214
        self._play_btn.set_sensitive(True)
        if player.is_playing:
            self.__change_play_btn_status(self._pause_image, _("Pause"))
        else:
            self.__change_play_btn_status(self._play_image, _("Play"))

#######################
# PROTECTED           #
#######################
    def _on_prev_btn_clicked(self, button):
        """
            Previous track on prev button clicked
            @param button as Gtk.Button
        """
        App().player.prev()

    def _on_play_btn_clicked(self, button):
        """
            Play/Pause on play button clicked
            @param button as Gtk.Button
        """
        if App().player.is_playing:
            App().player.pause()
            self.__change_play_btn_status(self._play_image, _("Play"))
        else:
            App().player.play()
            self.__change_play_btn_status(self._pause_image, _("Pause"))

    def _on_next_btn_clicked(self, button):
        """
            Next track on next button clicked
            @param button as Gtk.Button
        """
        App().player.next()

#######################
# PRIVATE             #
#######################
    def __change_play_btn_status(self, image, status):
        """
            Update play button with image and status as tooltip
            @param image as Gtk.Image
            @param status as str
        """
        self._play_btn.set_image(image)
        self._play_btn.set_tooltip_text(status)