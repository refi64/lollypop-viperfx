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

from lollypop.art_base import BaseArt
from lollypop.art_album import AlbumArt
from lollypop.art_artist import ArtistArt
from lollypop.art_radio import RadioArt
from lollypop.logger import Logger
from lollypop.downloader_art import ArtDownloader
from lollypop.utils import create_dir

from shutil import rmtree


class Art(BaseArt, AlbumArt, ArtistArt, RadioArt, ArtDownloader):
    """
        Global artwork manager
    """

    def __init__(self):
        """
            Init artwork
        """
        BaseArt.__init__(self)
        AlbumArt.__init__(self)
        ArtistArt.__init__(self)
        RadioArt.__init__(self)
        ArtDownloader.__init__(self)
        create_dir(self._CACHE_PATH)
        create_dir(self._STORE_PATH)
        create_dir(self._WEB_PATH)

    def clean_web(self):
        """
            Remove all covers from cache
        """
        try:
            rmtree(self._WEB_PATH)
        except Exception as e:
            Logger.error("Art::clean_web(): %s", e)

    def clean_all_cache(self):
        """
            Remove all covers from cache
        """
        try:
            from pathlib import Path
            for p in Path(self._CACHE_PATH).glob("*.jpg"):
                p.unlink()
        except Exception as e:
            Logger.error("Art::clean_all_cache(): %s", e)
