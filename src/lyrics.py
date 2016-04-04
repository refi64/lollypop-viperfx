# Copyright (c) 2014-2016 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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
import re


class Lyriki:
    """
        Download lyrics from lyriki
    """
    def __init__(self):
        """
            Init lyriki
        """
        pass

    def get(self, artist, title):
        """
            Get lyrics for artist/title
            @param artist as str
            @param title as str
        """
        data = None
        if not Gio.NetworkMonitor.get_default().get_network_available():
            return None
        try:
            artist = GLib.uri_escape_string(artist.replace(" ", "_"),
                                            "", False).title()
            title = GLib.uri_escape_string(title.replace(" ", "_"),
                                           "", False).title()
            f = Gio.File.new_for_uri("http://lyriki.com/"
                                     "index.php?title=%s:%s&action=edit" %
                                     (artist, title))
            (status, data, tag) = f.load_contents()
            if not status:
                return None
            result = data.decode('utf-8')
            m = re.compile(
                   ".*&lt;lyrics>(.*)&lt;/lyrics>.*", re.DOTALL).search(result)
            return m.group(1)
        except Exception as e:
            print("Lyriki::get()", e)
            return None


class Lyrics:
    """
        Download lyrics from providers
    """
    def __init__(self):
        """
            Init Lyrics
        """
        self._providers = [Lyriki()]

    def get(self, artist, title):
        """
            Get lyrics for artist/title
            @param artist as str
            @param title as str
        """
        for provider in self._providers:
            lyrics = provider.get(artist, title)
            if lyrics is not None:
                return lyrics
        return _("No lyrics for this track")
