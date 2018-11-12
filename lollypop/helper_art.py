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

from lollypop.define import App, ArtSize
from lollypop.logger import Logger
from lollypop.utils import get_round_surface
from lollypop.information_store import InformationStore


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
            @param halign as Gtk.Align
            @param valign = Gtk.Align
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

    def set_album_artwork(self, image, album, width, height,
                          enable_blur=False):
        """
            Set artwork for album id
            @param image as Gtk.Image
            @param album as Album
            @param width as int
            @param height as int
            @param enable_blur as bool
        """
        scale_factor = image.get_scale_factor()
        App().task_helper.run(self.__get_album_artwork,
                              album,
                              width,
                              height,
                              scale_factor,
                              enable_blur,
                              callback=(self._on_get_artwork_pixbuf,
                                        image,
                                        width,
                                        height,
                                        scale_factor,
                                        "folder-music-symbolic"))

    def set_radio_artwork(self, image, radio, width, height):
        """
            Set artwork for album id
            @param image as Gtk.Image
            @param radio as str
            @param width as int
            @param height as int
        """
        scale_factor = image.get_scale_factor()
        App().task_helper.run(App().art.get_radio_artwork,
                              radio,
                              width,
                              scale_factor,
                              callback=(self._on_get_artwork_pixbuf,
                                        image,
                                        width,
                                        height,
                                        scale_factor,
                                        "audio-input-microphone-symbolic"))

    def set_artist_artwork(self, image, artist, width, height):
        """
            Set artwork for album id
            @param image as Gtk.Image
            @param artist as str
            @param width as int
            @param height as int
        """
        scale_factor = image.get_scale_factor()
        App().task_helper.run(self.__get_artist_artwork,
                              artist,
                              width,
                              height,
                              scale_factor,
                              callback=(self._on_get_artist_artwork_pixbuf,
                                        image,
                                        width,
                                        height,
                                        scale_factor,
                                        "avatar-default-symbolic"))

#######################
# PROTECTED           #
#######################
    def _on_get_artist_artwork_pixbuf(self, pixbuf, image,
                                      width, height, scale_factor, icon):
        """
            Set pixbuf as surface
            @param pixbuf as Gdk.Pixbuf
            @param image as Gtk.Image
            @param size as int
            @param scale_factor as int
            @param icon as str
        """
        if pixbuf is None:
            self._on_get_artwork_pixbuf(pixbuf, image,
                                        width, height, scale_factor, icon)
        else:
            surface = get_round_surface(pixbuf, scale_factor)
            image.set_from_surface(surface)

    def _on_get_artwork_pixbuf(self, pixbuf, image,
                               width, height, scale_factor, icon):
        """
            Set pixbuf as surface
            @param pixbuf as Gdk.Pixbuf
            @param image as Gtk.Image
            @param size as int
            @param scale_factor as int
            @param icon as str
        """
        if pixbuf is not None:
            surface = Gdk.cairo_surface_create_from_pixbuf(
                    pixbuf, scale_factor, None)
            image.set_from_surface(surface)
        elif width / scale_factor < ArtSize.BIG:
            image.set_from_icon_name(icon, Gtk.IconSize.DND)
        elif width / scale_factor < ArtSize.ARTIST_SMALL:
            image.set_from_icon_name(icon, Gtk.IconSize.BUTTON)
        else:
            image.set_from_icon_name(icon, Gtk.IconSize.DIALOG)

#######################
# PRIVATE             #
#######################
    def __get_blur(self, pixbuf, w, h):
        """
            Blur surface using PIL
            @param pixbuf as GdkPixbuf.Pixbuf
            @param w as int
            @param h as int
            @return cairo.Surface
        """
        if pixbuf is None:
            return None
        try:
            from PIL import Image, ImageFilter
            width = pixbuf.get_width()
            height = pixbuf.get_height()
            data = pixbuf.get_pixels()
            stride = pixbuf.get_rowstride()
            tmp = Image.frombytes("RGB", (width, height),
                                  data, "raw", "RGB", stride)

            tmp = tmp.filter(ImageFilter.GaussianBlur(10))
            imgd = tmp.tobytes()
            data = GLib.Bytes.new(imgd)
            pixbuf = GdkPixbuf.Pixbuf.new_from_data(imgd,
                                                    GdkPixbuf.Colorspace.RGB,
                                                    False,
                                                    8,
                                                    width,
                                                    height,
                                                    width * 3)
        except Exception as e:
            Logger.error("ArtHelper::__get_blur():", e)
            return None
        return pixbuf

    def __get_album_artwork(self, album, width, height,
                            scale_factor, enable_blur=False):
        """
            Set artwork for album id
            @param album as Album
            @param width as int
            @param height as int
            @param scale_factor as int
            @param enable_blur as bool
            @return GdkPixbuf.Pixbuf
        """
        pixbuf = App().art.get_album_artwork(album, width, scale_factor)
        if enable_blur:
            pixbuf = self.__get_blur(pixbuf, width, height)
        return pixbuf

    def __get_artist_artwork(self, artist, width, height, scale_factor):
        """
            Set artwork for album id
            @param artist as str
            @param width as int
            @param height as int
            @param scale_factor as int
            @param enable_blur as bool
            @return GdkPixbuf.Pixbuf
        """
        path = InformationStore.get_artwork_path(artist, width, scale_factor)
        if path is not None:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
            return pixbuf
        return None
