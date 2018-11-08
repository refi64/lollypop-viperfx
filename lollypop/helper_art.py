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

from gi.repository import GObject, Gtk, Gdk

from lollypop.define import App


class ArtHelper(GObject.Object):
    """
        Helper to load artwork smoothly
    """

    __gsignals__ = {
        "artwork-set": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        """
            Init helper
        """
        GObject.Object.__init__(self)

    def get_image(self, art_size, frame,
                  halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER):
        """
            Get an artwork widget
            @param art_size as int
            @param frame as str
            @param halign as Gtk.Align
            @param valign = Gtk.Align
            @return Gtk.Image
        """
        image = Gtk.Image()
        image.get_style_context().add_class(frame)
        image.set_property("halign", halign)
        image.set_property("valign", valign)
        image.set_size_request(art_size, art_size)
        return image

    def set_album_artwork(self, image, album, size, scale_factor):
        """
            Set cover for album id
            @param image as Gtk.Image
            @param album as Album
            @param size as int
            @param scale_factor as int
        """
        App().task_helper.run(
                          App().art.get_album_artwork_pixbuf,
                          album,
                          size,
                          scale_factor,
                          callback=(self._on_get_album_artwork_pixbuf,
                                    image,
                                    album,
                                    size,
                                    scale_factor))

#######################
# PROTECTED           #
#######################
    def _on_get_album_artwork_pixbuf(self, pixbuf, image,
                                     album, size, scale_factor):
        """
            Set pixbuf as surface
            @param pixbuf as Gdk.Pixbuf
            @param image as Gtk.Image
            @param album as Album
            @param size as int
            @param scale_factor as int
        """
        if pixbuf is not None:
            surface = Gdk.cairo_surface_create_from_pixbuf(
                    pixbuf, scale_factor, None)
        else:
            surface = App().art.get_album_artwork(
                          album,
                          size,
                          scale_factor,)
        image.set_from_surface(surface)
        self.emit("artwork-set")
