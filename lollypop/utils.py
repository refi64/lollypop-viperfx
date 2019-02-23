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

from gi.repository import Gio, GLib, Gdk, GdkPixbuf

from math import pi
from gettext import gettext as _
import unicodedata
import cairo
import time
from functools import wraps

from lollypop.logger import Logger
from lollypop.define import App, Type, SelectionListMask


def seconds_to_string(duration):
    """
        Convert seconds to a pretty string
        @param seconds as int
    """
    hours = duration // 3600
    if hours == 0:
        minutes = duration // 60
        seconds = duration % 60
        return "%i:%02i" % (minutes, seconds)
    else:
        seconds = duration % 3600
        minutes = seconds // 60
        seconds %= 60
        return "%i:%02i:%02i" % (hours, minutes, seconds)


def get_human_duration(duration):
    """
        Get human readable duration
        @param duration in seconds
        @return str
    """
    hours = duration // 3600
    minutes = duration // 60
    if hours > 0:
        seconds = duration % 3600
        minutes = seconds // 60
        if minutes > 0:
            return _("%s h  %s m") % (hours, minutes)
        else:
            return _("%s h") % hours
    else:
        return _("%s m") % minutes


def get_round_surface(image, scale_factor, radius):
    """
        Get rounded surface from pixbuf
        @param image as GdkPixbuf.Pixbuf/cairo.Surface
        @return surface as cairo.Surface
        @param scale_factor as int
        @param radius as int
        @warning not thread safe!
    """
    width = image.get_width()
    height = image.get_height()
    is_pixbuf = isinstance(image, GdkPixbuf.Pixbuf)
    if is_pixbuf:
        width = width // scale_factor
        height = height // scale_factor
        radius = radius // scale_factor
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(surface)
    degrees = pi / 180
    ctx.arc(width - radius, radius, radius, -90 * degrees, 0 * degrees)
    ctx.arc(width - radius, height - radius,
            radius, 0 * degrees, 90 * degrees)
    ctx.arc(radius, height - radius, radius, 90 * degrees, 180 * degrees)
    ctx.arc(radius, radius, radius, 180 * degrees, 270 * degrees)
    ctx.close_path()
    ctx.set_line_width(10)
    if is_pixbuf:
        image = Gdk.cairo_surface_create_from_pixbuf(image, scale_factor, None)
    ctx.set_source_surface(image, 0, 0)
    ctx.clip()
    ctx.paint()
    return surface


def on_realize(widget):
    """
        Set cursor on widget
        @param widget as Gtk.Widget
    """
    try:
        window = widget.get_window()
        if window is not None:
            window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))
    except:
        Logger.warning(_("You are using a broken cursor theme!"))


def on_query_tooltip(label, x, y, keyboard, tooltip):
    """
        Show label tooltip if needed
        @param label as Gtk.Label
        @param x as int
        @param y as int
        @param keyboard as bool
        @param tooltip as Gtk.Tooltip
    """
    layout = label.get_layout()
    if layout.is_ellipsized():
        tooltip.set_markup(label.get_label())
        return True


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
    v = u"".join([c for c in nfkd_form if not unicodedata.combining(c)])
    return v.lower()


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
             "audio/x-matroska", "audio/x-wavpack", "video/mp4",
             "audio/x-mod", "audio/x-mo3", "audio/x-xm", "audio/x-s3m",
             "audio/x-it", "audio/aiff", "audio/x-aiff"]
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


def get_mtime(info):
    """
        Return Last modified time of a given file
        @param info as Gio.FileInfo
    """
    try:
        # We do not use time::modified because many tag editors
        # just preserve this setting
        return int(info.get_attribute_as_string("time::changed"))
    except:
        pass
    # Fallback for remote fs
    return int(info.get_attribute_as_string("time::modified"))


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
            name = name[strlen:] + ", " + special
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


def get_position_list(items, position):
    """
        Return a list with item and position
        @param items as []
        @param position as int
        @return []
    """
    _items = []
    for item in items:
        _items.append((item, position))
        position += 1
    return _items


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


def get_icon_name(object_id, type=SelectionListMask.ARTISTS):
    """
        Return icon name for id
        @param ojbect_id as int
        @param type as SelectionListMask
    """
    icon = ""
    if object_id == Type.POPULARS:
        icon = "starred-symbolic"
    elif object_id == Type.PLAYLISTS:
        icon = "emblem-documents-symbolic"
    elif object_id == Type.ALL:
        icon = "media-optical-cd-audio-symbolic"
    elif object_id == Type.ARTISTS:
        icon = "avatar-default-symbolic"
    elif object_id == Type.COMPILATIONS:
        icon = "system-users-symbolic"
    elif object_id == Type.RECENTS:
        icon = "document-open-recent-symbolic"
    elif object_id == Type.RADIOS:
        icon = "audio-input-microphone-symbolic"
    elif object_id < Type.DEVICES:
        icon = "multimedia-player-symbolic"
    elif object_id == Type.RANDOMS:
        icon = "media-playlist-shuffle-symbolic"
    elif object_id == Type.LOVED:
        icon = "emblem-favorite-symbolic"
    elif object_id == Type.NEVER:
        icon = "audio-speakers-symbolic"
    elif object_id == Type.YEARS:
        icon = "view-sort-ascending-symbolic"
    elif object_id == Type.CURRENT:
        icon = "view-list-symbolic"
    elif object_id == Type.SEARCH:
        icon = "edit-find-symbolic"
    elif object_id == Type.GENRES:
        icon = "folder-symbolic"
    return icon


def profile(f):
    """
        Decorator to get execution time of a function
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()

        ret = f(*args, **kwargs)

        elapsed_time = time.perf_counter() - start_time
        Logger.debug("%s::%s: execution time %d:%f" % (
            f.__module__, f.__name__, elapsed_time / 60, elapsed_time % 60))

        return ret

    return wrapper
