#!/usr/bin/python
# Copyright (c) 2014-2015 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# Copyright (c) 2013 Vadim Rutkovsky <vrutkovs@redhat.com>
# Copyright (c) 2013 Arnel A. Borja <kyoushuu@yahoo.com>
# Copyright (c) 2013 Seif Lotfy <seif@lotfy.com>
# Copyright (c) 2013 Guillaume Quintard <guillaume.quintard@gmail.com>
# Copyright (c) 2013 Lubosz Sarnecki <lubosz@gmail.com>
# Copyright (c) 2013 Sai Suman Prayaga <suman.sai14@gmail.com>
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

import os

from lollypop.art_album import AlbumArt
from lollypop.art_radio import RadioArt
from lollypop.tagreader import TagReader


# Global artwork manager
class Art(AlbumArt, RadioArt):

    """
        Create cache path
    """
    def __init__(self):
        AlbumArt.__init__(self)
        RadioArt.__init__(self)
        TagReader.__init__(self)

    """
        Remove all covers from cache
    """
    def clean_all_cache(self):
        try:
            files = os.listdir(self._CACHE_PATH)
            for f in files:
                os.remove(os.path.join(self._CACHE_PATH, f))
        except Exception as e:
            print("Art::clean_all_cache(): ", e)


