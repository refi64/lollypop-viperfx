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

from gi.repository import GLib

import json

from lollypop.utils import escape
from lollypop.lio import Lio


class WebJmg90:
    """
        Web Jmg90 helper
    """

    def get_uri_content(uri):
        """
            Get content uri
            @param uri as str
            @return content uri as str/None
        """
        try:
            f = Lio.File.new_for_uri(uri)
            (status, data, tag) = f.load_contents(None)
            if status:
                return data.decode("utf-8")
        except IndexError:
            pass
        except Exception as e:
            print("WebJmg90::get_uri_content():", e)
        return None

    def __init__(self):
        """
            Init helper
        """
        pass

    def get_uri(self, item):
        """
            Item uri
            @param item as SearchItem
            @return uri as str
        """
        jmg_id = self.__get_jgm_id(item)
        if jmg_id is None:
            return ""
        else:
            return "http://app.jgm90.com/cmapi/download/%s/160000" % jmg_id

#######################
# PRIVATE             #
#######################
    def __get_jgm_id(self, item):
        """
            Get jmg id
            @param item as SearchItem
            @return jpg id as str
        """
        # Try to handle compilations (itunes one)
        unwanted = ["variout artists", "multi-interprètes"]
        if item.artists[0].lower() in unwanted:
            if len(item.artists) > 1:
                artist = item.artists[1]
            else:
                artist = ""
        else:
            artist = item.artists[0]
        unescaped = "%s %s" % (artist,
                               item.name)
        for c in ["/", "?", "!"]:
            if c in unescaped:
                unescaped = unescaped.replace(c, " ")

        search = GLib.uri_escape_string(unescaped,
                                        "",
                                        True)
        try:
            f = Lio.File.new_for_uri("http://app.jgm90.com/cmapi/search/"
                                     "%s/1/10" % search)
            (status, data, tag) = f.load_contents(None)
            if status:
                decode = json.loads(data.decode("utf-8"))
                for song in decode["result"]["songs"]:
                    try:
                        song_artist = escape(
                                            song["artists"][0]["name"].lower())
                        if song_artist == escape(artist.lower()):
                            return song["id"]
                    except Exception as e:
                        print("WebJmg90::__get_jmg_id():", e)
        except IndexError:
            pass
        except KeyError:
            pass
        except Exception as e:
            print("WebJmg90::__get_jmg_id():", e)
        return None
