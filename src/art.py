# Copyright (c) 2014-2017 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from lollypop.art_album import AlbumArt
from lollypop.art_radio import RadioArt
from lollypop.downloader import Downloader

from shutil import rmtree


class Art(AlbumArt, RadioArt, Downloader):
    """
        Global artwork manager
    """

    def __init__(self):
        """
            Create cache path
        """
        AlbumArt.__init__(self)
        RadioArt.__init__(self)
        Downloader.__init__(self)
        self._create_cache()
        self._create_store()

    def clean_all_cache(self):
        """
            Remove all covers from cache
        """
        try:
            rmtree(self._CACHE_PATH)
            self._create_cache()
        except Exception as e:
            print("Art::clean_all_cache(): ", e)
