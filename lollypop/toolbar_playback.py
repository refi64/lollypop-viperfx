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

from gi.repository import Gtk

from lollypop.define import App
from lollypop.controller_playback import PlaybackController


class ToolbarPlayback(Gtk.Bin, PlaybackController):
    """
        Playback toolbar
    """

    def __init__(self):
        """
            Init toolbar
        """
        Gtk.Bin.__init__(self)
        PlaybackController.__init__(self)
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/ToolbarPlayback.ui")
        builder.connect_signals(self)

        self.add(builder.get_object("playback"))

        self._prev_btn = builder.get_object("previous_button")
        self._play_btn = builder.get_object("play_button")
        self._next_btn = builder.get_object("next_button")
        self.__back_btn = builder.get_object("back_button")
        self._play_image = builder.get_object("play_image")
        self._pause_image = builder.get_object("pause_image")

        App().player.connect("lock-changed", self.__on_lock_changed)

    def show_back(self, b, sensitive=False):
        """
            Show/hide back button
            @param b as bool
        """
        if b:
            self.__back_btn.show()
            self.__back_btn.set_sensitive(sensitive)
        else:
            self.__back_btn.hide()

#######################
# PRIVATE             #
#######################
    def _on_back_btn_clicked(self, button):
        """
            Go back in container stack
            @param button as Gtk.Button
        """
        App().window.container.go_back()

#######################
# PRIVATE             #
#######################
    def __on_lock_changed(self, player):
        """
            Lock toolbar
            @param player as Player
        """
        self._prev_btn.set_sensitive(not player.locked)
        self._next_btn.set_sensitive(not player.locked)
