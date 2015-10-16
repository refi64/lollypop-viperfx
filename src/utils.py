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

from gettext import gettext as _
from threading import Thread
import os

from lollypop.define import Lp, Type
from lollypop.objects import Track


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
            if info.get_content_type()[0:6] == "audio/" or\
               info.get_content_type() == "video/mp4":
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


def is_loved(track_id):
    """
        Check if object is in loved playlist
        @return bool
    """
    return Lp.playlists.exists_track(Type.LOVED,
                                     track_id)


def set_loved(track_id, loved):
    """
        Add or remove track from loved playlist
        @param track_id
        @param loved Add to loved playlist if `True`; remove if `False`
    """
    if not is_loved(track_id):
        if loved:
            Lp.playlists.add_tracks(Type.LOVED,
                                    [Track(track_id)])
            if Lp.lastfm is not None:
                t = Thread(target=_set_loved_on_lastfm, args=(track_id,
                                                              True))
                t.daemon = True
                t.start()
    else:
        if not loved:
            Lp.playlists.remove_tracks(Type.LOVED,
                                       [Track(track_id)])
            if Lp.lastfm is not None:
                t = Thread(target=_set_loved_on_lastfm, args=(track_id,
                                                              False))
                t.daemon = True
                t.start()


def _set_loved_on_lastfm(track_id, loved):
    """
        Add or remove track from loved playlist on Last.fm
        @param track_id
        @param loved Add to loved playlist if `True`; remove if `False`
    """
    # Love the track on lastfm
    if Gio.NetworkMonitor.get_default().get_network_available() and\
            Lp.lastfm.is_auth():
        title = Lp.tracks.get_name(track_id)
        album_id = Lp.tracks.get_album_id(track_id)
        artist_id = Lp.albums.get_artist_id(album_id)

        if artist_id == Type.COMPILATIONS:
            artist = Lp.tracks.get_artist_names(track_id)
        else:
            artist = Lp.artists.get_name(artist_id)

        if loved:
            Lp.lastfm.love(artist, title)
        else:
            Lp.lastfm.unlove(artist, title)
