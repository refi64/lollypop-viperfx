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

from lollypop.view_artist_albums import ArtistAlbumsView
from lollypop.define import App, ArtSize


class AlbumPopover(Gtk.Popover):
    """
        An ArtistAlbumsView in a popover
        Not an AlbumDetailedWidget because we want a lazy loading view
    """

    def __init__(self, album, genre_ids,
                 artist_ids, width, height, art_size=ArtSize.NONE):
        """
            Init popover
            @param album as Album
            @param genre ids as [int]
            @param artist ids as [int]
            @param width as int
            @param height as int
            @param art size as int
        """
        Gtk.Popover.__init__(self)
        self.__height = height
        self.__width = width
        self.get_style_context().add_class("box-shadow")
        view = ArtistAlbumsView(artist_ids, genre_ids, art_size)
        view.populate([album])
        if App().window.container.is_paned_stack:
            for child in view.children:
                child.hide_header_labels()

        # Get height requested by child
        album_widget = view.children[0]
        album_widget.connect("size-allocate",
                             self.__on_album_size_allocate,
                             view)
        view.show()
        self.add(view)

    def do_get_preferred_width(self):
        """
            Set maximum width
        """
        width = min(900, self.__width)
        return (width, width)

#######################
# PRIVATE             #
#######################
    def __on_album_size_allocate(self, widget, allocation, view):
        """
            Update view height
            @param widget as Gtk.Widget
            @param allocation as Gtk.Allocation
            @param view as ArtistAlbumsView
        """
        requested_height = widget.requested_height
        wanted_height = min(600, min(self.__height, requested_height))
        view.set_property("height-request", wanted_height)
