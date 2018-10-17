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

from gi.repository import Gio, GLib, Gdk

import cairo

from math import pi
from gettext import gettext as _
import unicodedata

from lollypop.logger import Logger
from lollypop.helper_task import TaskHelper
from lollypop.define import App


def blur(surface, image, w, h):
    """
        Blur surface using PIL
        @param surface as cairo.Surface
        @param image as Gtk.Image
        @param w as int
        @param h as int
    """
    def do_blur(surface, w, h):
        try:
            from PIL import Image, ImageFilter
            from array import array
            width = surface.get_width()
            height = surface.get_height()
            data = surface.get_data()
            tmp = Image.frombuffer("RGBA", (width, height),
                                   data, "raw", "RGBA", 0, 1)

            tmp = tmp.filter(ImageFilter.GaussianBlur(10))

            imgd = tmp.tobytes()
            a = array('B', imgd)
            stride = width * 4
            surface = cairo.ImageSurface.create_for_data(
                a, cairo.FORMAT_ARGB32, width, height, stride)
            # Special check for non square images
            if w > width or h > height:
                size = max(w, h)
                resized = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                             size,
                                             size)
                factor1 = size / width
                factor2 = size / height
                factor = max(factor1, factor2)
                context = cairo.Context(resized)
                context.scale(factor, factor)
                context.set_source_surface(surface, 0, 0)
                context.paint()
                surface = resized
        except Exception as e:
            Logger.error("blur():", e)
            return None
        return surface
    TaskHelper().run(do_blur, surface, w, h,
                     callback=(image.set_from_surface,))


def draw_rounded_image(image, ctx):
    """
        Draw rounded image
        @param image as Gtk.Image
        @param ctx as cairo.Context
    """
    if not image.is_drawable():
        return
    surface = None
    if image.props.surface is None:
        pixbuf = image.get_pixbuf()
        if pixbuf is not None:
            surface = Gdk.cairo_surface_create_from_pixbuf(
                pixbuf,
                image.get_scale_factor(),
                None)
    else:
        surface = image.props.surface
    if surface is not None:
        width = surface.get_width() / image.get_scale_factor() - 4
        ctx.translate(2, 2)
        ctx.new_sub_path()
        radius = width / 2
        ctx.arc(width / 2, width / 2, radius, 0, 2 * pi)
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill_preserve()
        ctx.set_line_width(2)
        ctx.set_source_rgba(0, 0, 0, 0.3)
        ctx.stroke_preserve()
        ctx.set_source_surface(surface, 0, 0)
        ctx.clip()
        ctx.paint()


def set_proxy_from_gnome():
    """
        Set proxy settings from GNOME
    """
    try:
        proxy = Gio.Settings.new("org.gnome.system.proxy")
        mode = proxy.get_value("mode").get_string()
        if mode == "manual":
            no_http_proxy = True
            http = Gio.Settings.new("org.gnome.system.proxy.http")
            https = Gio.Settings.new("org.gnome.system.proxy.https")
            h = http.get_value("host").get_string()
            p = http.get_value("port").get_int32()
            hs = https.get_value("host").get_string()
            ps = https.get_value("port").get_int32()
            if h != "" and p != 0:
                no_http_proxy = False
                GLib.setenv("http_proxy", "http://%s:%s" % (h, p), True)
            if hs != "" and ps != 0:
                no_http_proxy = False
                GLib.setenv("https_proxy", "http://%s:%s" % (hs, ps), True)
            if no_http_proxy:
                socks = Gio.Settings.new("org.gnome.system.proxy.socks")
                h = socks.get_value("host").get_string()
                p = socks.get_value("port").get_int32()
                # Set socks proxy
                if h != "" and p != 0:
                    import socket
                    import socks
                    socks.set_default_proxy(socks.SOCKS4, h, p)
                    socket.socket = socks.socksocket
    except Exception as e:
        Logger.error("set_proxy_from_gnome(): %s", e)


def debug(str):
    """
        Print debug
        @param debug as str
    """
    if App().debug is True:
        print(str)


def get_network_available():
    """
        Return True if network avaialble
        @return bool
    """
    return Gio.NetworkMonitor.get_default().get_network_available() and\
        App().settings.get_value("network-access")


def noaccents(string):
    """
        Return string without accents
        @param string as str
        @return str
    """
    nfkd_form = unicodedata.normalize("NFKD", string)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])


def escape(str, ignore=["_", "-", " ", "."]):
    """
        Escape string
        @param string as str
        @param ignore as [str]
    """
    return "".join([c for c in str if
                    c.isalpha() or
                    c.isdigit() or c in ignore]).rstrip()


def is_unity():
    """
        Return True if desktop is Unity
    """
    return GLib.getenv("XDG_CURRENT_DESKTOP") == "Unity"


def is_gnome():
    """
        Return True if desktop is Gnome
    """
    return GLib.getenv("XDG_CURRENT_DESKTOP") in ["ubuntu:GNOME", "GNOME"]


def is_audio(f):
    """
        Return True if files is audio
        @param f as Gio.File
    """
    audio = ["application/ogg", "application/x-ogg", "application/x-ogm-audio",
             "audio/aac", "audio/mp4", "audio/mpeg", "audio/mpegurl",
             "audio/ogg", "audio/vnd.rn-realaudio", "audio/vorbis",
             "audio/x-flac", "audio/x-mp3", "audio/x-mpeg", "audio/x-mpegurl",
             "audio/x-ms-wma", "audio/x-musepack", "audio/x-oggflac",
             "audio/x-pn-realaudio", "application/x-flac", "audio/x-speex",
             "audio/x-vorbis", "audio/x-vorbis+ogg", "audio/x-wav",
             "x-content/audio-player", "audio/x-aac", "audio/m4a",
             "audio/x-m4a", "audio/mp3", "audio/ac3", "audio/flac",
             "audio/x-opus+ogg", "application/x-extension-mp4", "audio/x-ape",
             "audio/x-pn-aiff", "audio/x-pn-au", "audio/x-pn-wav",
             "audio/x-pn-windows-acm", "application/x-matroska",
             "audio/x-matroska", "audio/x-wavpack", "video/mp4"]
    try:
        info = f.query_info("standard::content-type",
                            Gio.FileQueryInfoFlags.NONE)
        if info is not None:
            content_type = info.get_content_type()
            if content_type in audio:
                return True
    except Exception as e:
        Logger.error("is_audio: %s", e)
    return False


def is_pls(f):
    """
        Return True if files is a playlist
        @param f as Gio.File
    """
    try:
        info = f.query_info("standard::content-type",
                            Gio.FileQueryInfoFlags.NONE)
        if info is not None:
            if info.get_content_type() in ["audio/x-mpegurl",
                                           "application/xspf+xml"]:
                return True
    except:
        pass
    return False


def format_artist_name(name):
    """
        Return formated artist name
        @param str
    """
    if not App().settings.get_value("smart-artist-sort"):
        return name
    # Handle language ordering
    # Translators: Add here words that shoud be ignored for artist sort order
    # Translators: Add The the too
    for special in _("The the").split():
        if name.startswith(special + " "):
            strlen = len(special) + 1
            name = name[strlen:] + "@@@@" + special
    return name


def translate_artist_name(name):
    """
        Return translate formated artist name
        @param str
    """
    split = name.split("@@@@")
    if len(split) == 2:
        name = split[1] + " " + split[0]
    return name


def seconds_to_string(duration):
    """
        Convert seconds to a pretty string
        @param seconds as int
    """
    seconds = duration
    minutes = seconds // 60
    seconds %= 60

    return "%i:%02i" % (minutes, seconds)


def is_readonly(uri):
    """
        Check if uri is readonly
    """
    f = Gio.File.new_for_uri(uri)
    info = f.query_info("access::can-write",
                        Gio.FileQueryInfoFlags.NONE,
                        None)
    return not info.get_attribute_boolean("access::can-write")


def remove_static_genres(genre_ids):
    """
        Remove static genre ids
        @param genre ids as [int]
    """
    return [item for item in genre_ids if item >= 0]
