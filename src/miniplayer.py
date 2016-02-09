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

from lollypop.controller import InfosController
from lollypop.define import Lp, Mini


class MiniPlayer(Gtk.Bin, InfosController):
    """
        Toolbar end
    """

    def __init__(self):
        """
            Init toolbar
        """
        Gtk.Bin.__init__(self)
        InfosController.__init__(self, Mini.SMALL)
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/MiniPlayer.ui')
        self._title_label = builder.get_object('title')
        self._artist_label = builder.get_object('artist')
        self._cover_frame = builder.get_object('frame')
        self._cover = builder.get_object('cover')
        self._signal_id = Lp().player.connect('current-changed',
                                              self.on_current_changed)
        self.on_current_changed(Lp().player)
        self.add(builder.get_object('widget'))

    def do_hide(self):
        """
            Remove signal
        """
        Gtk.Bin.do_hide(self)
        Lp().player.disconnect(self._signal_id)
