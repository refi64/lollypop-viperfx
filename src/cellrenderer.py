# Copyright (c) 2014-2016 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import Gtk, Gdk, GObject, GdkPixbuf

from math import pi

from lollypop.define import Lp, ArtSize
from lollypop.cache import InfoCache
from lollypop.objects import Album


class CellRendererAlbum(Gtk.CellRenderer):
    album = GObject.Property(type=int)

    def __init__(self):
        Gtk.CellRenderer.__init__(self)

    def do_render(self, ctx, widget, background_area, cell_area, flags):
        size = ArtSize.MEDIUM * widget.get_scale_factor()
        surface = Lp().art.get_album_artwork(Album(self.album), size)
        width = surface.get_width()
        height = surface.get_height()
        ctx.translate(cell_area.x, cell_area.y)
        ctx.new_sub_path()
        radius = 2
        degrees = pi / 180
        ctx.arc(width + 2 - radius, radius,
                radius - 0.5, -90 * degrees, 0 * degrees)
        ctx.arc(width + 2 - radius, height + 2 - radius,
                radius - 0.5, 0 * degrees, 90 * degrees)
        ctx.arc(radius, height + 2 - radius,
                radius - 0.5, 90 * degrees, 180 * degrees)
        ctx.arc(radius, radius, radius - 0.5, 180 * degrees, 270 * degrees)
        ctx.close_path()
        ctx.set_line_width(1)
        ctx.fill()
        ctx.set_source_surface(surface, 1, 1)
        ctx.paint()

    def do_get_preferred_width(self, widget):
        size = ArtSize.MEDIUM + 2
        return (size, size)

    def do_get_preferred_height(self, widget):
        return self.do_get_preferred_width(widget)


class CellRendererArtist(Gtk.CellRendererText):
    rowid = GObject.Property(type=int)
    artist = GObject.Property(type=str)

    def __init__(self):
        Gtk.CellRendererText.__init__(self)
        self._is_artists = False

    def set_is_artists(self, is_artists):
        self._is_artists = is_artists

    def do_render(self, ctx, widget, background_area, cell_area, flags):
        size = ArtSize.ARTIST * widget.get_scale_factor()
        if self._is_artists and self.rowid >= 0:
            cell_area.width -= size
            cell_area.x = size
        Gtk.CellRendererText.do_render(self, ctx, widget,
                                       cell_area, cell_area, flags)
        if self._is_artists and self.rowid >= 0:
            cell_area.width = size
            cell_area.x = 0
            self.do_own_render(ctx, widget, cell_area, size)

    def do_own_render(self, ctx, widget, cell_area, size):
        surface = None
        alpha = False
        for suffix in ["lastfm", "spotify", "wikipedia"]:
            uri = InfoCache.get_artwork(self.artist, suffix, True)
            if uri:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(uri,
                                                                size,
                                                                size)
                surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf,
                                                               0,
                                                               None)
                del pixbuf
                break
        if surface is None:
            alpha = True
            surface = Gtk.IconTheme.get_default().load_surface(
                                             'media-optical-cd-audio-symbolic',
                                             size,
                                             1,
                                             widget.get_window(),
                                             0)
        ctx.translate(cell_area.x, cell_area.y)
        ctx.new_sub_path()
        radius = size / 2 - 2
        ctx.arc(ArtSize.ARTIST/2, ArtSize.ARTIST/2, radius, 0, 2 * pi)
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill_preserve()
        ctx.set_line_width(2)
        ctx.set_source_rgba(0, 0, 0, 0.3)
        ctx.stroke_preserve()
        ctx.set_source_surface(surface, 0, 0)
        ctx.clip()
        if alpha:
            ctx.paint_with_alpha(0.5)
        else:
            ctx.paint()

    def do_get_preferred_height_for_width(self, widget, width):
        if self._is_artists and self.rowid >= 0:
            return (ArtSize.ARTIST, ArtSize.ARTIST)
        else:
            return Gtk.CellRendererText.do_get_preferred_height_for_width(
                                                           self, widget, width)
