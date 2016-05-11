# Copyright (c) 2014-2016 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# Copyright (c) 2013 Vadim Rutkovsky <vrutkovs@redhat.com>
# Copyright (c) 2013 Arnel A. Borja <kyoushuu@yahoo.com>
# Copyright (c) 2013 Seif Lotfy <seif@lotfy.com>
# Copyright (c) 2013 Guillaume Quintard <guillaume.quintard@gmail.com>
# Copyright (c) 2013 Lubosz Sarnecki <lubosz@gmail.com>
# Copyright (c) 2013 Sai Suman Prayaga <suman.sai14@gmail.com>
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

import os

from lollypop.define import ArtSize, Lp


class BaseArt(GObject.GObject):
    """
        Base art manager
    """
    _CACHE_PATH = os.path.expanduser("~") + "/.cache/lollypop"
    # Fallback when album dir is readonly
    _STORE_PATH = os.path.expanduser("~") + "/.local/share/lollypop/store"
    __gsignals__ = {
        'album-artwork-changed': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        'artist-artwork-changed': (GObject.SignalFlags.RUN_FIRST,
                                   None, (str,)),
        'radio-artwork-changed': (GObject.SignalFlags.RUN_FIRST, None, (str,))
    }

    def __init__(self):
        """
            Init base art
        """
        GObject.GObject.__init__(self)

    def update_art_size(self):
        """
            Update value with some check
        """
        value = Lp().settings.get_value('cover-size').get_int32()
        # Check value as user can enter bad value via dconf
        if value < ArtSize.SMALL or value > ArtSize.MAX:
            value = 200
        ArtSize.BIG = value
        # For a 200 album artwork, we want a 60 artist artwork
        ArtSize.ARTIST_SMALL = ArtSize.BIG * 60 / 200

    def get_default_icon(self, icon_name, size, scale):
        """
            Construct an empty cover album,
            code forked Gnome Music, see copyright header
            @param icon_name as str
            @param size as int
            @param scale factor as int
            @return pixbuf as cairo.Surface
        """
        try:
            # First look in cache
            cache_path_jpg = self._get_default_icon_path(size, icon_name)
            if os.path.exists(cache_path_jpg):
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                                                                cache_path_jpg,
                                                                size,
                                                                size,
                                                                False)
            else:
                # get a small pixbuf with the given path
                icon_size = size / 4
                icon = Gtk.IconTheme.get_default().load_icon(icon_name,
                                                             icon_size, 0)
                # create an empty pixbuf with the requested size
                pixbuf = GdkPixbuf.Pixbuf.new(icon.get_colorspace(),
                                              True,
                                              icon.get_bits_per_sample(),
                                              size,
                                              size)
                pixbuf.fill(0xffffffff)
                icon.composite(pixbuf,
                               icon_size * 3 / 2,
                               icon_size * 3 / 2,
                               icon_size,
                               icon_size,
                               icon_size * 3 / 2,
                               icon_size * 3 / 2,
                               1, 1,
                               GdkPixbuf.InterpType.NEAREST, 255)
                # Gdk < 3.15 was missing save method
                # > 3.15 is missing savev method
                try:
                    pixbuf.save(cache_path_jpg, "jpeg",
                                ["quality"], ["90"])
                except:
                    pixbuf.savev(cache_path_jpg, "jpeg",
                                 ["quality"], ["90"])
            surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf, scale, None)
            del pixbuf
            return surface
        except:
            return self.get_default_icon('computer-fail-symbolic',
                                         ArtSize.MEDIUM,
                                         scale)

#######################
# PRIVATE             #
#######################
    def _respect_ratio(self, path):
        """
            Check for aspect ratio based on size
            @param path as str
            @return respect aspect ratio as bool
        """
        cover = GdkPixbuf.Pixbuf.new_from_file(path)
        cover_width = cover.get_width()
        cover_height = cover.get_height()
        del cover
        if cover_width == cover_height:
            return True
        elif cover_width < cover_height:
            cut = cover_height / 5
            return cover_width < cover_height - cut
        else:
            cut = cover_width / 5
            return cover_height < cover_width - cut

    def _create_store(self):
        """
            Create store dir
        """
        if not os.path.exists(self._STORE_PATH):
            try:
                os.mkdir(self._STORE_PATH)
            except:
                print("Can't create %s" % self._STORE_PATH)

    def _create_cache(self):
        """
            Create cache dir
        """
        if not os.path.exists(self._CACHE_PATH):
            try:
                os.mkdir(self._CACHE_PATH)
            except:
                print("Can't create %s" % self._CACHE_PATH)

    def _get_default_icon_path(self, size, icon_name):
        """
            Return default icon path
            @return path as string
        """
        return "%s/%s_%s.jpg" % (self._CACHE_PATH, icon_name, size)
