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

from gi.repository import GLib, Gdk

import cairo
from random import shuffle

from lollypop.helper_task import TaskHelper
from lollypop.define import App, ArtSize
from lollypop.objects import Album
from lollypop.utils import get_round_surface
from lollypop.widgets_flowbox_rounded import RoundedFlowBoxWidget


class RoundedAlbumsWidget(RoundedFlowBoxWidget):
    """
        Rounded widget showing cover for 9 albums
    """
    _ALBUMS_COUNT = 9

    def __init__(self, data, art_size=ArtSize.ROUNDED):
        """
            Init widget
            @param data as object
        """
        RoundedFlowBoxWidget.__init__(self, data, art_size)
        self.__covers_count = 0
        self.__cover_size = App().settings.get_value("cover-size").get_int32()
        self.__scale = art_size / self.__cover_size / 3

#######################
# PROTECTED           #
#######################
    def _set_artwork(self):
        """
            Set artwork
        """
        self._scale_factor = self.get_scale_factor()
        task_helper = TaskHelper()
        task_helper.run(self._get_surface,
                        callback=(self._set_surface,))

    def _set_surface(self, surface):
        """
            Set artwork from surface
            @param surface as cairo.Surface
        """
        self._artwork.set_from_surface(surface)

    def _get_surface(self):
        """
            Get artwork surface
            @return cairo.Surface
        """
        cover = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                   self._art_size,
                                   self._art_size)
        ctx = cairo.Context(cover)
        ctx.scale(self.__scale, self.__scale)
        album_ids = self._get_album_ids()
        shuffle(album_ids)
        x = self.__cover_size
        y = self.__cover_size
        # Draw centered cover
        self.__draw_surface(album_ids, ctx, x, y)
        # Draw other covers
        for i in [0, 1, 2]:
            for h in [0, 1, 2]:
                # Ignore centered
                if i == 1 and h == 1:
                    continue
                self.__draw_surface(album_ids, ctx, x * i, y * h)
        GLib.idle_add(self.emit, "populated")
        return get_round_surface(cover, self._scale_factor)

#######################
# PRIVATE             #
#######################
    def __draw_surface(self, album_ids, ctx, x, y):
        """
            Draw surface for first available album
            @param album_ids as [int]
            @param ctx as Cairo.context
            @param x as int
            @param y as int
        """
        # Workaround Gdk not being thread safe
        def draw_pixbuf(ctx, pixbuf):
            surface = Gdk.cairo_surface_create_from_pixbuf(
                pixbuf, self._scale_factor, None)
            ctx.translate(x, y)
            ctx.set_source_surface(surface, 0, 0)
            ctx.paint()
            ctx.translate(-x, -y)
        if album_ids:
            album_id = album_ids.pop(0)
            pixbuf = App().art.get_album_artwork(Album(album_id),
                                                 self.__cover_size,
                                                 self._scale_factor)
            if pixbuf is None:
                GLib.idle_add(self.__draw_surface, album_ids, ctx, x, y)
            else:
                self.__covers_count += 1
                GLib.idle_add(draw_pixbuf, ctx, pixbuf)
