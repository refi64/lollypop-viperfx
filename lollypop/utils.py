# Copyright (c) 2014-2017 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import Gio, GLib

from gettext import gettext as _
from threading import Thread
import unicodedata

from lollypop.define import Lp, Type, ENCODING
from lollypop.objects import Track
from lollypop.lio import Lio


def decode_all(bytes):
    """
        Decode bytes trying all encodings
        @param bytes as bytes
        @return str
    """
    for encoding in ENCODING:
        try:
            return bytes.decode(encoding)
        except Exception as e:
            print("decode_all():", e)


def get_network_available():
    """
        Return True if network avaialble
        @return bool
    """
    return Gio.NetworkMonitor.get_default().get_network_available() and\
        Lp().settings.get_value("network-access")


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


def debug(str):
    """
        Print debug
        @param debug as str
    """
    if Lp().debug is True:
        print(str)


def is_unity():
    """
        Return True if desktop is Unity
    """
    return GLib.getenv("XDG_CURRENT_DESKTOP") == "Unity"


def is_gnome():
    """
        Return True if desktop is Gnome
    """
    return GLib.getenv("XDG_CURRENT_DESKTOP") == "GNOME"


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
             "audio/x-opus+ogg", "application/x-extension-mp4",
             "audio/x-pn-aiff", "audio/x-pn-au", "audio/x-pn-wav",
             "audio/x-pn-windows-acm", "application/x-matroska",
             "audio/x-matroska", "video/mp4"]
    try:
        info = f.query_info("standard::content-type",
                            Gio.FileQueryInfoFlags.NONE)
        if info is not None:
            content_type = info.get_content_type()
            if content_type in audio:
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
    if not Lp().settings.get_value("smart-artist-sort"):
        return name
    # Handle language ordering
    # Translators: Add here words that shoud be ignored for artist sort order
    # Translators: Add The the too
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

    return "%i:%02i" % (minutes, seconds)


def is_readonly(uri):
    """
        Check if uri is readonly
    """
    f = Lio.File.new_for_uri(uri)
    info = f.query_info("access::can-write",
                        Gio.FileQueryInfoFlags.NONE,
                        None)
    return not info.get_attribute_boolean("access::can-write")


def is_loved(track_id):
    """
        Check if object is in loved playlist
        @return bool
    """
    return Lp().playlists.exists_track(Type.LOVED,
                                       track_id)


def remove_static_genres(genre_ids):
    """
        Remove static genre ids
        @param genre ids as [int]
    """
    return [item for item in genre_ids if item >= 0 or item == Type.CHARTS]


def set_loved(track_id, loved):
    """
        Add or remove track from loved playlist
        @param track_id
        @param loved Add to loved playlist if `True`; remove if `False`
    """
    if not is_loved(track_id):
        if loved:
            Lp().playlists.add_tracks(Type.LOVED,
                                      [Track(track_id)])
            if Lp().lastfm is not None:
                t = Thread(target=_set_loved_on_lastfm, args=(track_id,
                                                              True))
                t.daemon = True
                t.start()
    else:
        if not loved:
            Lp().playlists.remove_tracks(Type.LOVED,
                                         [Track(track_id)])
            if Lp().lastfm is not None:
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
            Lp().lastfm.is_auth:
        title = Lp().tracks.get_name(track_id)
        artists = ", ".join(Lp().tracks.get_artists(track_id))
        if loved:
            Lp().lastfm.love(artists, title)
        else:
            Lp().lastfm.unlove(artists, title)
