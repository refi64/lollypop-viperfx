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

from gi.repository import Gtk, Gdk, GObject, GdkPixbuf

from math import pi

from lollypop.define import Lp, ArtSize, Type
from lollypop.cache import InfoCache
from lollypop.objects import Album


class CellRendererAlbum(Gtk.CellRenderer):
    album = GObject.Property(type=int)

    def __init__(self):
        Gtk.CellRenderer.__init__(self)

    def do_render(self, ctx, widget, background_area, cell_area, flags):
        if self.album == Type.NONE:
            return
        surface = Lp().art.get_album_artwork(Album(self.album),
                                             ArtSize.MEDIUM,
                                             widget.get_scale_factor())
        width = surface.get_width()
        height = surface.get_height()
        # If cover smaller than wanted size, translate
        translate_x = cell_area.x
        translate_y = cell_area.y
        wanted = ArtSize.MEDIUM * widget.get_scale_factor()
        if width < wanted:
            translate_x += (wanted - width) / 2
        if height < wanted:
            translate_y += (wanted - height) / 2
        ctx.translate(translate_x, translate_y)
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
        if self.album == Type.NONE:
            size = 0
        else:
            size = ArtSize.MEDIUM + 2
        return (size, size)

    def do_get_preferred_height(self, widget):
        return self.do_get_preferred_width(widget)


class CellRendererArtist(Gtk.CellRendererText):
    rowid = GObject.Property(type=int)
    artist = GObject.Property(type=str)
    xshift = 4

    def __init__(self):
        Gtk.CellRendererText.__init__(self)
        self.__is_artists = False
        self.__surfaces = {}
        self.__scale_factor = None

    def set_is_artists(self, is_artists):
        self.__is_artists = is_artists

    def do_render(self, ctx, widget, background_area, cell_area, flags):
        if self.__scale_factor != widget.get_scale_factor():
            self.__scale_factor = widget.get_scale_factor()
            self.__surfaces = {}

        size = ArtSize.ARTIST_SMALL * self.__scale_factor
        draw_artwork = self.__is_artists and\
            self.rowid >= 0 and\
            Lp().settings.get_value("artist-artwork")
        if draw_artwork:
            if Gtk.Widget.get_default_direction() == Gtk.TextDirection.LTR:
                cell_area.x = ArtSize.ARTIST_SMALL + self.xshift * 2
                cell_area.width -= ArtSize.ARTIST_SMALL
            else:
                cell_width = cell_area.width + cell_area.x
                cell_area.width -= ArtSize.ARTIST_SMALL + self.xshift
        Gtk.CellRendererText.do_render(self, ctx, widget,
                                       cell_area, cell_area, flags)
        if draw_artwork:
            if Gtk.Widget.get_default_direction() == Gtk.TextDirection.LTR:
                cell_area.x = self.xshift
            else:
                cell_area.x = cell_width - ArtSize.ARTIST_SMALL
            cell_area.width = ArtSize.ARTIST_SMALL
            self.do_own_render(ctx, widget, cell_area, size)

    def do_own_render(self, ctx, widget, cell_area, size):
        surface = None
        if self.rowid in self.__surfaces.keys():
            surface = self.__surfaces[self.rowid]
        if surface is None:
            for suffix in ["lastfm", "deezer", "spotify", "wikipedia"]:
                uri = InfoCache.get_artwork(self.artist, suffix, size)
                if uri is not None:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(uri,
                                                                    size,
                                                                    size)
                    surface = Gdk.cairo_surface_create_from_pixbuf(
                                                     pixbuf,
                                                     self.__scale_factor,
                                                     None)
                    self.__surfaces[self.rowid] = surface
                    break
        if surface is None:
            surface = Gtk.IconTheme.get_default().load_surface(
                                             "avatar-default-symbolic",
                                             ArtSize.ARTIST_SMALL,
                                             1,
                                             widget.get_window(),
                                             0)
        ctx.translate(cell_area.x, cell_area.y)
        ctx.new_sub_path()
        radius = ArtSize.ARTIST_SMALL / 2
        ctx.arc(ArtSize.ARTIST_SMALL/2, ArtSize.ARTIST_SMALL/2,
                radius, 0, 2 * pi)
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill_preserve()
        ctx.set_line_width(2)
        ctx.set_source_rgba(0, 0, 0, 0.3)
        ctx.stroke_preserve()
        ctx.set_source_surface(surface, 0, 0)
        ctx.clip()
        ctx.paint()

    def do_get_preferred_height_for_width(self, widget, width):
        draw_artwork = self.__is_artists and\
                       self.rowid >= 0 and\
                       Lp().settings.get_value("artist-artwork")
        if draw_artwork:
            return (ArtSize.ARTIST_SMALL, ArtSize.ARTIST_SMALL)
        else:
            return Gtk.CellRendererText.do_get_preferred_height_for_width(
                                                           self, widget, width)

    def on_artist_artwork_changed(self, artist):
        artist_id = Lp().artists.get_id(artist)
        if artist_id in self.__surfaces.keys():
            self.__surfaces.pop(artist_id)
