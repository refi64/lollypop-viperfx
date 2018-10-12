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

from gi.repository import Gtk, Gdk

from lollypop.art_base import BaseArt
from lollypop.art_album import AlbumArt
from lollypop.art_radio import RadioArt
from lollypop.logger import Logger
from lollypop.define import App
from lollypop.downloader import Downloader

from shutil import rmtree


class Art(BaseArt, AlbumArt, RadioArt, Downloader):
    """
        Global artwork manager
    """

    def __init__(self):
        """
            Create cache path
        """
        BaseArt.__init__(self)
        AlbumArt.__init__(self)
        RadioArt.__init__(self)
        Downloader.__init__(self)
        self._create_cache()
        self._create_store()

    def clean_all_cache(self):
        """
            Remove all covers from cache
        """
        try:
            rmtree(self._CACHE_PATH)
            self._create_cache()
        except Exception as e:
            Logger.error("Art::clean_all_cache(): %s", e)


class AlbumArtHelper:
    """
        Helper to load covers for albums
    """

    def __init__(self):
        """
            Init helper
        """
        self._artwork = None

    def populate(self, art_size, frame,
                 halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER):
        """
            Populate widget
            @param art_size as int
            @param frame as str
            @param halign as Gtk.Align
            @param valign = Gtk.Align
        """
        if self._artwork is None:
            self._artwork = Gtk.Image()
            self._artwork.get_style_context().add_class(frame)
            self.set_property("halign", halign)
            self.set_property("valign", valign)
            self._artwork.set_size_request(art_size, art_size)

    def get_artwork(self):
        """
            Get album artwork
            @return Gtk.Image
        """
        return self._artwork

    def set_artwork(self):
        """
            Set cover for album id
        """
        if self._artwork is None:
            return
        App().task_helper.run(
                          App().art.get_album_artwork_pixbuf,
                          self._album,
                          self._artwork.get_size_request()[0],
                          self._artwork.get_scale_factor(),
                          callback=(self._on_get_album_artwork_pixbuf,))

#######################
# PROTECTED           #
#######################
    def _on_get_album_artwork_pixbuf(self, pixbuf):
        """
            Set pixbuf as surface
            @param pixbuf as Gdk.Pixbuf
        """
        if pixbuf is not None:
            surface = Gdk.cairo_surface_create_from_pixbuf(
                    pixbuf, self._artwork.get_scale_factor(), None)
        else:
            surface = App().art.get_album_artwork(
                   self._album,
                   self._artwork.get_size_request()[0],
                   self._artwork.get_scale_factor())
        self._artwork.set_from_surface(surface)
        self.emit("populated")
        self.show_all()
