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

from lollypop.define import App


class ViewController:
    """
        Update view for registered signals
        Should be herited by a Gtk.Widget
    """

    def __init__(self):
        """
            Init controller
        """
        self.__signals_ids = {}
        self.connect("destroy", self.__on_destroy)

    def connect_current_changed_signal(self):
        """
            Connect to current-changed signal
        """
        player = App().player
        self.__signals_ids[
            player.connect("current-changed",
                           self._on_current_changed)] = player

    def connect_artwork_changed_signal(self, type):
        """
            Connect to cover-changed signal
            @param type as str ("album", "radio")
        """
        artwork = App().art
        self.__signals_ids[
            artwork.connect("%s-artwork-changed" % type,
                            self._on_artwork_changed)] = artwork

#######################
# PROTECTED           #
#######################
    def _on_current_changed(self, player):
        pass

    def _on_artwork_changed(self, artwork, *args):
        pass

#######################
# PRIVATE             #
#######################
    def __on_destroy(self, widget):
        """
            Remove signals
            @param widget as Gtk.Widget
        """
        for signal_id in self.__signals_ids.keys():
            self.__signals_ids[signal_id].disconnect(signal_id)
