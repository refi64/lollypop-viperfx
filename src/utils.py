#!/usr/bin/python
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

from lollypop.define import Objects
from gettext import gettext as _
import os

"""
    Return True if desktop is elementary os
"""

def is_eos():
    return os.environ.get("XDG_CURRENT_DESKTOP") == "Pantheon"


"""
    Return True if desktop is Gnome
"""

def is_gnome():
    return os.environ.get("XDG_CURRENT_DESKTOP") == "GNOME"

"""
    Return True if CSDs are to be used based on several criterions
"""
def use_csd():
    return is_gnome() or is_eos() or Objects.settings.get_value('force-csd')

"""
    Return True if files is audio
    @param f as Gio.File
"""


def is_audio(f):
    try:
        info = f.query_info('standard::content-type',
                            Gio.FileQueryInfoFlags.NONE)
        if info is not None:
            if info.get_content_type().find('audio/') != -1:
                return True
    except:
        pass
    return False

"""
    Return formated artist name
    @param str
"""


def format_artist_name(name):
    # Handle language ordering
    # Translators: Add here words that shoud be ignored for artist sort order
    for special in _("The the").split():
        if name.startswith(special+" "):
            strlen = len(special)+1
            name = name[strlen:]+"@@@@"+special
    return name


"""
    Return translate formated artist name
    @param str
"""


def translate_artist_name(name):
    split = name.split("@@@@")
    if len(split) == 2:
        name = split[1]+" "+split[0]
    return name


"""
    Convert seconds to a pretty string
    @param seconds as int
"""


def seconds_to_string(duration):
    seconds = duration
    minutes = seconds // 60
    seconds %= 60

    return '%i:%02i' % (minutes, seconds)
