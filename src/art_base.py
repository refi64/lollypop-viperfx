# Copyright (c) 2014-2015 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from math import pi
import cairo
import os

from lollypop.define import Lp, ArtSize


class BaseArt(GObject.GObject):
    """
        Base art manager
    """
    _CACHE_PATH = os.path.expanduser("~") + "/.cache/lollypop"
    __gsignals__ = {
        'cover-changed': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        'logo-changed': (GObject.SignalFlags.RUN_FIRST, None, (str,))
    }

    def __init__(self):
        """
            Init base art
        """
        GObject.GObject.__init__(self)

#######################
# PRIVATE             #
#######################
    def _make_icon_frame(self, pixbuf, scale_factor, selected):
        """
            Draw an icon frame around pixbuf,
            code forked Gnome Music, see copyright header
            @param pixbuf source as Gdk.Pixbuf
            @param scale factor as int
            @param selected as bool
            @return cairo surface
        """
        selected_color = Lp.window.get_selected_color()
        dark = Gtk.Settings.get_default().get_property(
            "gtk-application-prefer-dark-theme")
        degrees = pi / 180
        cover = Gdk.cairo_surface_create_from_pixbuf(pixbuf, 0, None)

        # Covers are always squares
        size = int(pixbuf.get_width() / scale_factor)

        if size < ArtSize.BIG:
            radius = ArtSize.SMALL_RADIUS
            border = ArtSize.SMALL_BORDER
        else:
            radius = ArtSize.RADIUS
            border = ArtSize.BORDER

        surface_size = size + border * 2
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                     surface_size, surface_size)
        ctx = cairo.Context(surface)
        ctx.new_sub_path()
        ctx.arc(surface_size - radius, radius,
                radius - 0.5, -90 * degrees, 0 * degrees)
        ctx.arc(surface_size - radius, surface_size - radius,
                radius - 0.5, 0 * degrees, 90 * degrees)
        ctx.arc(radius, surface_size - radius,
                radius - 0.5, 90 * degrees, 180 * degrees)
        ctx.arc(radius, radius, radius - 0.5, 180 * degrees, 270 * degrees)
        ctx.close_path()
        ctx.set_line_width(1)

        if selected:
            ctx.set_source_rgb(selected_color.red,
                               selected_color.green,
                               selected_color.blue)
        elif dark and size > ArtSize.MEDIUM:
            ctx.set_source_rgb(1, 1, 1)
        else:
            ctx.set_source_rgb(0, 0, 0)
        ctx.stroke_preserve()

        # Fill content for big artwork
        if size > ArtSize.MEDIUM:
            if selected:
                ctx.set_source_rgb(selected_color.red,
                                   selected_color.green,
                                   selected_color.blue)
            elif dark:
                ctx.set_source_rgb(0, 0, 0)
            else:
                ctx.set_source_rgb(1, 1, 1)
            ctx.fill()

        ctx = cairo.Context(surface)
        ctx.set_source_surface(cover, border, border)
        ctx.paint()
        del cover
        return surface

    def _get_default_icon(self, size, icon_name):
        """
            Construct an empty cover album,
            code forked Gnome Music, see copyright header
            @param size as int
            @param icon_name as str
            @return pixbuf as Gdk.Pixbuf
        """
        # First look in cache
        cache_path_jpg = "%s/%s_%s.jpg" % (self._CACHE_PATH, icon_name, size)
        if os.path.exists(cache_path_jpg):
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(cache_path_jpg,
                                                             size,
                                                             size,
                                                             False)
            return pixbuf

        # get a small pixbuf with the given path
        icon_size = size / 4
        icon = Gtk.IconTheme.get_default().load_icon(icon_name,
                                                     icon_size, 0)
        # create an empty pixbuf with the requested size
        result = GdkPixbuf.Pixbuf.new(icon.get_colorspace(),
                                      True,
                                      icon.get_bits_per_sample(),
                                      size,
                                      size)
        result.fill(0xffffffff)
        icon.composite(result,
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
            result.save(cache_path_jpg, "jpeg",
                        ["quality"], ["90"])
        except:
            result.savev(cache_path_jpg, "jpeg",
                         ["quality"], ["90"])
        return result
