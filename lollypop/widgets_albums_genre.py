# Copyright (c) 2014-2019 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from lollypop.define import App, Type
from lollypop.widgets_albums_rounded import RoundedAlbumsWidget
from lollypop.helper_overlay_genre import OverlayGenreHelper


class AlbumsGenreWidget(RoundedAlbumsWidget, OverlayGenreHelper):
    """
        Genre widget showing cover for 4 albums
    """

    def __init__(self, genre_id, view_type):
        """
            Init widget
            @param Genre as [int]
            @param view_type as ViewType
        """
        OverlayGenreHelper.__init__(self)
        name = sortname = App().genres.get_name(genre_id)
        RoundedAlbumsWidget.__init__(self, genre_id, name, sortname, view_type)
        self._genre = Type.GENRES

    def populate(self):
        """
            Populate widget content
        """
        self._lock_overlay = False
        self._album_ids = App().albums.get_ids([], [self._data])
        RoundedAlbumsWidget.populate(self)
        self._widget.connect("enter-notify-event", self._on_enter_notify)
        self._widget.connect("leave-notify-event", self._on_leave_notify)

#######################
# PROTECTED           #
#######################

#######################
# PRIVATE             #
#######################
