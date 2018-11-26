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


class ViewControllerType:
    RADIO = "radio"
    ALBUM = "album"


class ViewController:
    """
        Update view for registered signals
        Should be herited by a Gtk.Widget
    """

    def __init__(self, controller_type):
        """
            Init controller
            @param controller_type as ViewControllerType
        """
        self.__signals_ids = {}
        self.__type = controller_type
        self.connect("map", self.__on_map)
        self.connect("unmap", self.__on_unmap)

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
    def __on_map(self, widget):
        """
            Connect signals
            @param widget as Gtk.Widget
        """
        self.__signals_ids[
            App().player.connect("current-changed",
                                 self._on_current_changed)] = App().player
        self.__signals_ids[
            App().art.connect("%s-artwork-changed" % self.__type,
                              self._on_artwork_changed)] = App().art

    def __on_unmap(self, widget):
        """
            Disconnect signals
            @param widget as Gtk.Widget
        """
        for signal_id in self.__signals_ids.keys():
            self.__signals_ids[signal_id].disconnect(signal_id)
        self.__signals_ids = {}
