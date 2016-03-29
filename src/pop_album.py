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


class AlbumPopover(Gtk.Popover):
    """
        An ArtistAlbumsView in a popover
    """

    def __init__(self, album_id, genre_ids,
                 artist_ids, width=1125, show_cover=True):
        """
            Init popover
            @param album id as int
            @param genre ids as [int]
            @param artist ids as [int]
            @param show cover as bool
        """
        Gtk.Popover.__init__(self)
        self._width = width
        self.get_style_context().add_class('box-shadow')
        self._view = ArtistAlbumsView(artist_ids, genre_ids, show_cover)
        self._view.populate([album_id])
        height = min(400, self._view.requested_height)
        self._view.set_property('height-request', height)
        self._view.show()
        self.add(self._view)

    def do_get_preferred_width(self):
        """
            Set maximum width
        """
        width = min(900, self._width * 0.8)
        return (width, width)

#######################
# PRIVATE             #
#######################
