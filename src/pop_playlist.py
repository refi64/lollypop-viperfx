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

from gi.repository import Gtk

from lollypop.loader import Loader
from lollypop.define import Lp
from lollypop.view_playlists import PlaylistView


class PlaylistPopover(Gtk.Popover):
    """
        Popover showing current albums
        @Warning: destroy it self on close
    """

    def __init__(self):
        """
            Init Popover
        """
        Gtk.Popover.__init__(self)
        self.set_position(Gtk.PositionType.BOTTOM)
        self.connect('map', self._on_map)
        self.connect('unmap', self._on_unmap)
        self._widget = PlaylistView(Lp().player.get_user_playlist_ids(), True)
        self._widget.show()
        self.add(self._widget)

    def do_show(self):
        """
            Set widget size
        """
        height = Lp().window.get_size()[1]
        self.set_size_request(500, height*0.7)
        Gtk.Popover.do_show(self)

    def populate(self):
        """
            Populate view
        """
        def load():
            return Lp().player.get_user_playlist()
        loader = Loader(target=load, view=self._widget)
        loader.start()

#######################
# PRIVATE             #
#######################
    def _on_map(self, widget):
        """
            Connect signals
            @param widget as Gtk.Widget
        """
        self._stop = False
        self.populate()

    def _on_unmap(self, widget):
        """
            Disconnect signals, clear view
            @param widget as Gtk.Widget
        """
        self._stop = True
        self.destroy()
