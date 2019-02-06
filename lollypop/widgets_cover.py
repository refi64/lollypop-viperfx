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

from lollypop.helper_art import ArtHelperEffect
from lollypop.define import App, ArtSize


class CoverWidget(Gtk.Bin):
    """
        Widget showing current album cover
    """

    def __init__(self):
        """
            Init cover widget
        """
        Gtk.Bin.__init__(self)
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/CoverWidget.ui")
        builder.connect_signals(self)
        self.__artwork = builder.get_object("cover")
        self.add(builder.get_object("widget"))

    def update(self, album):
        """
            Update cover
            @param album as Album
        """
        App().art_helper.set_album_artwork(
                album,
                ArtSize.BIG,
                ArtSize.BIG,
                self.__artwork.get_scale_factor(),
                self.__on_album_artwork,
                ArtHelperEffect.NONE)

#######################
# PRIVATE             #
#######################
    def __on_album_artwork(self, surface):
        """
            Set album artwork
            @param surface as str
        """
        self.__artwork.set_from_surface(surface)
