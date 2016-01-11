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


class BaseArt(GObject.GObject):
    """
        Base art manager
    """
    _CACHE_PATH = os.path.expanduser("~") + "/.cache/lollypop"
    __gsignals__ = {
        'album-artwork-changed': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        'radio-artwork-changed': (GObject.SignalFlags.RUN_FIRST, None, (str,))
    }

    def __init__(self):
        """
            Init base art
        """
        GObject.GObject.__init__(self)

#######################
# PRIVATE             #
#######################
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

    def _get_default_icon(self, size, icon_name):
        """
            Construct an empty cover album,
            code forked Gnome Music, see copyright header
            @param size as int
            @param icon_name as str
            @return pixbuf as Gdk.Pixbuf
        """
        # First look in cache
        cache_path_jpg = self._get_default_icon_path(size, icon_name)
        if os.path.exists(cache_path_jpg):
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(cache_path_jpg,
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
        surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf, 0, None)
        del pixbuf
        return surface
