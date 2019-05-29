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

from gi.repository import GObject, GLib, Gtk, Gdk, GdkPixbuf

from PIL import Image, ImageFilter
import cairo

from lollypop.define import App, ArtHelperEffect
from lollypop.utils import get_round_surface


class ArtHelper(GObject.Object):
    """
        Helper to load artwork smoothly
    """

    def __init__(self):
        """
            Init helper
        """
        GObject.Object.__init__(self)

    def get_image(self, width, height, frame):
        """
            Get an artwork widget
            @param width as int
            @param height as int
            @param frame as str
            @return Gtk.Image
        """
        image = Gtk.Image()
        context = image.get_style_context()
        context.add_class(frame)
        padding = context.get_padding(Gtk.StateFlags.NORMAL)
        border = context.get_border(Gtk.StateFlags.NORMAL)
        image.set_size_request(width + padding.left +
                               padding.right + border.left + border.right,
                               height + padding.top +
                               padding.bottom + border.top + border.bottom)
        return image

    def set_album_artwork(self, album, width, height, scale_factor,
                          effect, callback, *args):
        """
            Set artwork for album id
            @param image as Gtk.Image
            @param album as Album
            @param width as int
            @param height as int
            @param effect as ArtHelperEffect
            @param callback as function
        """
        App().task_helper.run(self.__get_album_artwork,
                              album,
                              width,
                              height,
                              scale_factor,
                              effect,
                              callback=(self._on_get_artwork_pixbuf,
                                        width,
                                        height,
                                        scale_factor,
                                        effect,
                                        callback,
                                        *args))

    def set_radio_artwork(self, radio, width, height, scale_factor,
                          effect, callback, *args):
        """
            Set artwork for album id
            @param radio as str
            @param width as int
            @param height as int
            @param scale_factor as int
            @param effect as ArtHelperEffect
            @param callback as function
        """
        App().task_helper.run(self.__get_radio_artwork,
                              radio,
                              width,
                              height,
                              scale_factor,
                              effect,
                              callback=(self._on_get_artwork_pixbuf,
                                        width,
                                        height,
                                        scale_factor,
                                        effect,
                                        callback,
                                        *args))

    def set_artist_artwork(self, artist, width, height, scale_factor,
                           effect, callback, *args):
        """
            Set artwork for album id
            @param artist as str
            @param width as int
            @param height as int
            @param scale_factor as int
            @param effect as ArtHelperEffect
            @param callback as function
        """
        App().task_helper.run(self.__get_artist_artwork,
                              artist,
                              width,
                              height,
                              scale_factor,
                              effect,
                              callback=(self._on_get_artwork_pixbuf,
                                        width,
                                        height,
                                        scale_factor,
                                        effect,
                                        callback,
                                        *args))

#######################
# PROTECTED           #
#######################
    def _on_get_artwork_pixbuf(self, pixbuf, width, height, scale_factor,
                               effect, callback, *args):
        """
            Set pixbuf as surface
            @param pixbuf as Gdk.Pixbuf
            @param size as int
            @param scale_factor as int
            @param effect as ArtHelperEffect
            @param callback as function
        """
        surface = None
        if pixbuf is not None:
            if effect & ArtHelperEffect.RESIZE:
                pixbuf = pixbuf.scale_simple(width * scale_factor,
                                             height * scale_factor,
                                             GdkPixbuf.InterpType.NEAREST)
            if effect & ArtHelperEffect.BLUR:
                pixbuf = self.__get_blur(pixbuf, 25)
            elif effect & ArtHelperEffect.BLUR_HARD:
                pixbuf = self.__get_blur(pixbuf, 50)
            if effect & ArtHelperEffect.ROUNDED:
                radius = pixbuf.get_width() / 2
                surface = get_round_surface(pixbuf, scale_factor, radius)
            else:
                surface = Gdk.cairo_surface_create_from_pixbuf(
                        pixbuf, scale_factor, None)
            if effect & ArtHelperEffect.DARKER:
                self.__set_color(surface, 0, 0, 0)
        callback(surface, *args)

#######################
# PRIVATE             #
#######################
    def __set_color(self, surface, r, g, b):
        """
            Get a darker pixbuf
            @param surface as cairo.Surface
            @param r as int
            @param g as int
            @param b as int
            @return cairo.Surface
        """
        ctx = cairo.Context(surface)
        ctx.rectangle(0, 0, surface.get_width(), surface.get_height())
        ctx.set_source_rgba(r, g, b, 0.5)
        ctx.fill()

    def __get_blur(self, pixbuf, gaussian):
        """
            Blur surface using PIL
            @param pixbuf as GdkPixbuf.Pixbuf
            @param gaussian as int
            @return GdkPixbuf.Pixbuf
        """
        if pixbuf is None:
            return None
        width = pixbuf.get_width()
        height = pixbuf.get_height()
        data = pixbuf.get_pixels()
        stride = pixbuf.get_rowstride()
        has_alpha = pixbuf.get_has_alpha()
        if has_alpha:
            mode = "RGBA"
            dst_row_stride = width * 4
        else:
            mode = "RGB"
            dst_row_stride = width * 3
        tmp = Image.frombytes(mode, (width, height),
                              data, "raw", mode, stride)
        tmp = tmp.filter(ImageFilter.GaussianBlur(gaussian))
        bytes = GLib.Bytes.new(tmp.tobytes())
        pixbuf = GdkPixbuf.Pixbuf.new_from_bytes(bytes,
                                                 GdkPixbuf.Colorspace.RGB,
                                                 has_alpha,
                                                 8,
                                                 width,
                                                 height,
                                                 dst_row_stride)
        return pixbuf

    def __get_album_artwork(self, album, width, height, scale_factor, effect):
        """
            Set artwork for album id
            @param album as Album
            @param width as int
            @param height as int
            @param scale_factor as int
            @param effect as ArtHelperEffect
            @return GdkPixbuf.Pixbuf
        """
        return App().art.get_album_artwork(album, width, height,
                                           scale_factor, effect)

    def __get_radio_artwork(self, radio, width, height, scale_factor, effect):
        """
            Set artwork for album id
            @param radio as str
            @param width as int
            @param height as int
            @param scale_factor as int
            @param effect as ArtHelperEffect
            @return GdkPixbuf.Pixbuf
        """
        return App().art.get_radio_artwork(radio, width, height,
                                           scale_factor, True)

    def __get_artist_artwork(self, artist, width, height,
                             scale_factor, effect):
        """
            Set artwork for album id
            @param artist as str
            @param width as int
            @param height as int
            @param scale_factor as int
            @return GdkPixbuf.Pixbuf
        """
        return App().art.get_artist_artwork(artist, width, height,
                                            scale_factor, effect)
