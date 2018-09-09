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
from lollypop.widgets_albums_rounded import RoundedAlbumsWidget


class AlbumsDecadeWidget(RoundedAlbumsWidget):
    """
        Decade widget showing cover for 9 albums
    """

    def __init__(self, item_ids):
        """
            Init widget
            @param decade as [int]
        """
        RoundedAlbumsWidget.__init__(self, item_ids)

    def populate(self):
        """
            Populate widget content
        """
        decade_str = "%s - %s" % (self._item_ids[0], self._item_ids[-1])
        RoundedAlbumsWidget.populate(self, decade_str)

#######################
# PROTECTED           #
#######################
    def _get_album_ids(self):
        """
            Get ids for widget
            @return [int]
        """
        album_ids = []
        for year in self._item_ids:
            album_ids += App().albums.get_albums_for_year(year,
                                                          self._ALBUMS_COUNT)
            l = len(album_ids)
            if l < self._ALBUMS_COUNT:
                album_ids += App().albums.get_compilations_for_year(
                                                       year,
                                                       self._ALBUMS_COUNT)
        return album_ids

#######################
# PRIVATE             #
#######################
