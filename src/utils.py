# Copyright (c) 2014-2015 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import Gio

from lollypop.define import Lp
from gettext import gettext as _
import os


def debug(str):
    """
        Print debug
        @param debug as str
    """
    if Lp.debug is True:
        print(str)


def is_unity():
    """
        Return True if desktop is Unity
    """
    return os.environ.get("XDG_CURRENT_DESKTOP") == "Unity"


def is_gnome():
    """
        Return True if desktop is Gnome
    """
    return os.environ.get("XDG_CURRENT_DESKTOP") == "GNOME"


def is_audio(f):
    """
        Return True if files is audio
        @param f as Gio.File
    """
    try:
        info = f.query_info('standard::content-type',
                            Gio.FileQueryInfoFlags.NONE)
        if info is not None:
            if info.get_content_type()[0:6] == "audio/":
                return True
    except:
        pass
    return False


def is_pls(f):
    """
        Return True if files is a playlist
        @param f as Gio.File
    """
    try:
        info = f.query_info('standard::content-type',
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
    # Handle language ordering
    # Translators: Add here words that shoud be ignored for artist sort order
    for special in _("The the").split():
        if name.startswith(special+" "):
            strlen = len(special)+1
            name = name[strlen:]+"@@@@"+special
    return name


def translate_artist_name(name):
    """
        Return translate formated artist name
        @param str
    """
    split = name.split("@@@@")
    if len(split) == 2:
        name = split[1]+" "+split[0]
    return name


def seconds_to_string(duration):
    """
        Convert seconds to a pretty string
        @param seconds as int
    """
    seconds = duration
    minutes = seconds // 60
    seconds %= 60

    return '%i:%02i' % (minutes, seconds)


def rgba_to_hex(color):
    """
        Convert Gdk.Color to hexadecimal
        @param Gdk.Color
        @return string
    """
    return "#{0:02x}{1:02x}{2:02x}".format(int(color.red * 255),
                                           int(color.green * 255),
                                           int(color.blue * 255))
