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

from gi.repository import GObject, GLib, Gtk, Gdk, GdkPixbuf

from lollypop.define import App
from lollypop.logger import Logger
from lollypop.utils import get_round_surface
from lollypop.information_store import InformationStore


class ArtHelperEffect:
    NONE = 1 << 1
    ROUNDED = 1 << 2
    BLUR = 1 << 3
    BLUR_HARD = 1 << 4
    NO_RATIO = 1 << 5
    FALLBACK = 1 << 6


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
                          callback, effect=ArtHelperEffect.NONE):
        """
            Set artwork for album id
            @param image as Gtk.Image
            @param album as Album
            @param width as int
            @param height as int
            @param callback as function
            @param effect as ArtHelperEffect
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
                                        callback,
                                        effect))

    def set_radio_artwork(self, radio, width, height, scale_factor,
                          callback, effect=ArtHelperEffect.NONE):
        """
            Set artwork for album id
            @param radio as str
            @param width as int
            @param height as int
            @param scale_factor as int
            @param callback as function
            @param effect as ArtHelperEffect
        """
        App().task_helper.run(App().art.get_radio_artwork,
                              radio,
                              width,
                              scale_factor,
                              callback=(self._on_get_artwork_pixbuf,
                                        width,
                                        height,
                                        scale_factor,
                                        callback,
                                        effect))

    def set_artist_artwork(self, artist, width, height, scale_factor,
                           callback, effect=ArtHelperEffect.ROUNDED):
        """
            Set artwork for album id
            @param artist as str
            @param width as int
            @param height as int
            @param scale_factor as int
            @param callback as function
            @param effect as ArtHelperEffect
        """
        App().task_helper.run(self.__get_artist_artwork,
                              artist,
                              width,
                              height,
                              scale_factor,
                              effect,
                              callback=(self._on_get_artist_artwork_pixbuf,
                                        width,
                                        height,
                                        scale_factor,
                                        callback,
                                        effect))

#######################
# PROTECTED           #
#######################
    def _on_get_artist_artwork_pixbuf(self, pixbuf, width, height,
                                      scale_factor, callback, effect):
        """
            Set pixbuf as surface
            @param pixbuf as Gdk.Pixbuf
            @param size as int
            @param scale_factor as int
            @param callback as function
            @param effect as ArtHelperEffect
        """
        surface = None
        if pixbuf is None:
            self._on_get_artwork_pixbuf(pixbuf, width, height,
                                        scale_factor, callback, effect)
        else:
            if effect & ArtHelperEffect.ROUNDED:
                surface = get_round_surface(pixbuf, scale_factor)
            else:
                surface = Gdk.cairo_surface_create_from_pixbuf(
                        pixbuf, scale_factor, None)
        callback(surface)

    def _on_get_artwork_pixbuf(self, pixbuf, width, height, scale_factor,
                               callback, effect):
        """
            Set pixbuf as surface
            @param pixbuf as Gdk.Pixbuf
            @param size as int
            @param scale_factor as int
            @param callback as function
            @param effect as ArtHelperEffect
        """
        surface = None
        if pixbuf is not None:
            if effect & ArtHelperEffect.ROUNDED:
                surface = get_round_surface(pixbuf, scale_factor)
            else:
                surface = Gdk.cairo_surface_create_from_pixbuf(
                        pixbuf, scale_factor, None)
        callback(surface)

#######################
# PRIVATE             #
#######################
    def __get_blur(self, pixbuf, w, h, gaussian):
        """
            Blur surface using PIL
            @param pixbuf as GdkPixbuf.Pixbuf
            @param w as int
            @param h as int
            @param gaussian as int
            @return cairo.Surface
        """
        if pixbuf is None:
            return None
        from PIL import Image, ImageFilter
        width = pixbuf.get_width()
        height = pixbuf.get_height()
        data = pixbuf.get_pixels()
        stride = pixbuf.get_rowstride()
        tmp = Image.frombytes("RGB", (width, height),
                              data, "raw", "RGB", stride)

        tmp = tmp.filter(ImageFilter.GaussianBlur(gaussian))
        imgd = tmp.tobytes()
        data = GLib.Bytes.new(imgd)
        pixbuf = GdkPixbuf.Pixbuf.new_from_data(imgd,
                                                GdkPixbuf.Colorspace.RGB,
                                                False,
                                                8,
                                                width,
                                                height,
                                                width * 3)
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
        pixbuf = App().art.get_album_artwork(
            album, width, height, scale_factor,
            not effect & ArtHelperEffect.NO_RATIO)
        try:
            if effect & ArtHelperEffect.BLUR:
                pixbuf = self.__get_blur(pixbuf, width, height, 10)
            elif effect & ArtHelperEffect.BLUR_HARD:
                pixbuf = self.__get_blur(pixbuf, width, height, 30)
        except Exception as e:
            Logger.warning("ArtHelper::__get_album_artwork(): %s", e)
            if effect & ArtHelperEffect.NO_RATIO:
                return None
        return pixbuf

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
        path = InformationStore.get_artwork_path(artist, width, scale_factor)
        if path is not None:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
            if effect & ArtHelperEffect.BLUR:
                pixbuf = self.__get_blur(pixbuf, width, height)
            return pixbuf
        return None
