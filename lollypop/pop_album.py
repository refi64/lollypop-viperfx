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

from lollypop.view_artist_albums import ArtistAlbumsView
from lollypop.define import App
from lollypop.widgets_utils import Popover


class AlbumPopover(Popover):
    """
        An ArtistAlbumsView in a popover
        Not an AlbumDetailedWidget because we want a lazy loading view
    """

    def __init__(self, album, width):
        """
            Init popover
            @param album as Album
            @param width as int
            @param art size as int
        """
        Popover.__init__(self)
        self.__width = width
        self.get_style_context().add_class("box-shadow")
        view = ArtistAlbumsView(album.artist_ids, album.genre_ids, False)
        view.populate([album])
        window_width = App().window.get_allocated_width()
        window_height = App().window.get_allocated_height()
        wanted_width = min(900, window_width * 0.5)
        wanted_height = max(200,
                            min(window_height * 0.5,
                                view.children[0].requested_height[0]))
        view.set_property("width-request", wanted_width)
        view.set_property("height-request", wanted_height)
        view.show()
        self.add(view)
#######################
# PRIVATE             #
#######################
