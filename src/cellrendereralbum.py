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

from lollypop.define import Lp, ArtSize


class CellRendererAlbum(Gtk.CellRenderer):
    album = GObject.property(type=int)

    def do_render(self, ctx, widget, background_area, cell_area, flags):
        surface = Lp.art.get_album(self.album,
                                   ArtSize.MEDIUM,
                                   widget.get_scale_factor())
        ctx.translate(cell_area.x, cell_area.y)
        ctx.set_source_surface(surface, 0, 0)
        ctx.paint()

    def do_get_preferred_width(self, widget):
        size = ArtSize.MEDIUM + ArtSize.SMALL_BORDER * 2
        return (size, size)

    def do_get_preferred_height(self, widget):
        size = ArtSize.MEDIUM + ArtSize.SMALL_BORDER * 2
        return (size, size)
