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

from lollypop.view_artist_albums import ArtistAlbumsView
from lollypop.define import Lp


class AlbumPopover(Gtk.Popover):
    """
        An ArtistAlbumsView in a popover
    """

    def __init__(self, album_id, genre_ids,
                 artist_ids, width=None, height=None, show_cover=True):
        """
            Init popover
            @param album id as int
            @param genre ids as [int]
            @param artist ids as [int]
            @param width as int (None)
            @param height as int (None)
            @param show cover as bool
        """
        Gtk.Popover.__init__(self)
        # Get width/height from main window if None
        if height is None:
            height = Lp().window.get_size()[1] * 0.8
        if width is None:
            self.__width = Lp().window.get_size()[0] * 0.8
        else:
            self.__width = width

        self.get_style_context().add_class('box-shadow')
        view = ArtistAlbumsView(artist_ids, genre_ids, show_cover)
        view.populate([album_id])
        wanted_height = min(400, min(height, view.requested_height))
        view.set_property('height-request', wanted_height)
        view.show()
        self.add(view)

    def do_get_preferred_width(self):
        """
            Set maximum width
        """
        width = min(900, self.__width * 0.8)
        return (width, width)

#######################
# PRIVATE             #
#######################
