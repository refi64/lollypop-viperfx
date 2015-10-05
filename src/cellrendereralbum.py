# Copyright (c) 2014-2015 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import Gtk, GObject

from math import pi

from lollypop.define import Lp, ArtSize
from lollypop.objects import Album


class CellRendererAlbum(Gtk.CellRenderer):
    album = GObject.property(type=int)

    def __init__(self):
        Gtk.CellRenderer.__init__(self)

    def do_render(self, ctx, widget, background_area, cell_area, flags):
        size = ArtSize.MEDIUM * widget.get_scale_factor()
        surface = Lp.art.get_album(Album(self.album), size)
        ctx.translate(cell_area.x, cell_area.y)
        ctx.new_sub_path()
        radius = 2
        degrees = pi / 180
        ctx.arc(size + 2 - radius, radius,
                radius - 0.5, -90 * degrees, 0 * degrees)
        ctx.arc(size + 2 - radius, size + 2 - radius,
                radius - 0.5, 0 * degrees, 90 * degrees)
        ctx.arc(radius, size + 2 - radius,
                radius - 0.5, 90 * degrees, 180 * degrees)
        ctx.arc(radius, radius, radius - 0.5, 180 * degrees, 270 * degrees)
        ctx.close_path()
        ctx.set_line_width(1)
        ctx.fill()
        ctx.set_source_surface(surface, 1, 1)
        ctx.paint()

    def do_get_preferred_width(self, widget):
        size = ArtSize.MEDIUM
        return (size+2, size+2)

    def do_get_preferred_height(self, widget):
        size = ArtSize.MEDIUM
        return (size+2, size+2)
