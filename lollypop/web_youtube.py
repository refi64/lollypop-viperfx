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
from re import sub

from lollypop.define import Lp, GOOGLE_API_ID
from lollypop.utils import escape
from lollypop.lio import Lio


class WebYouTube:
    """
        Web YoutTube helper
    """

    __BAD_SCORE = 1000000

    def get_uri_content(uri):
        """
            Get content uri
            @param uri as str
            @return content uri as str/None
        """
        # Remove playlist args
        uri = sub("list=.*", "", uri)
        argv = ["youtube-dl", "-g", "-f", "bestaudio", uri, None]
        (s, o, e, s) = GLib.spawn_sync(None,
                                       argv,
                                       None,
                                       GLib.SpawnFlags.SEARCH_PATH,
                                       None)
        if o:
            return o.decode("utf-8")
        else:
            if Lp().notify:
                Lp().notify.send(e.decode("utf-8"))
            print("WebYouTube::get_uri_content:", e.decode("utf-8"))
            return None

    def __init__(self):
        """
            Init helper
        """
        self.__fallback = False

    def get_uri(self, item):
        """
            Item uri
            @param item as SearchItem
            @return uri as str
        """
        yid = self.__get_youtube_id(item)
        if yid is None:
            return ""
        else:
            return "https://www.youtube.com/watch?v=%s" % yid

#######################
# PRIVATE             #
#######################
    def __get_youtube_id(self, item):
        """
            Get youtube id
            @param item as SearchItem
            @return youtube id as str
        """
        if self.__fallback:
            return self.__get_youtube_id_fallback(item)
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
        search = GLib.uri_escape_string(
                            unescaped.replace(" ", "+"),
                            None,
                            True)
        key = Lp().settings.get_value("cs-api-key").get_string() or\
            Lp().settings.get_default_value("cs-api-key").get_string()
        try:
            f = Lio.File.new_for_uri("https://www.googleapis.com/youtube/v3/"
                                     "search?part=snippet&q=%s&"
                                     "type=video&key=%s&cx=%s" % (
                                                              search,
                                                              key,
                                                              GOOGLE_API_ID))
            (status, data, tag) = f.load_contents(None)
            if status:
                decode = json.loads(data.decode("utf-8"))
                dic = {}
                best = self.__BAD_SCORE
                for i in decode["items"]:
                    score = self.__get_youtube_score(i["snippet"]["title"],
                                                     item.name,
                                                     artist,
                                                     item.album.name)
                    if score < best:
                        best = score
                    elif score == best:
                        continue  # Keep first result
                    dic[score] = i["id"]["videoId"]
                # Return url from first dic item
                if best == self.__BAD_SCORE:
                    return None
                else:
                    return dic[best]
        except Exception as e:
            self.__fallback = True
            return self.__get_youtube_id_fallback(item)
        return None

    def __get_youtube_score(self, page_title, title, artist, album):
        """
            Calculate youtube score
            if page_title looks like (title, artist, album), score is lower
            @return int
        """
        page_title = escape(page_title.lower(), [])
        artist = escape(artist.lower(), [])
        album = escape(album.lower(), [])
        title = escape(title.lower(), [])
        # YouTube page title should be at least as long as wanted title
        if len(page_title) < len(title):
            return self.__BAD_SCORE
        # Remove common word for a valid track
        page_title = page_title.replace("official", "")
        page_title = page_title.replace("video", "")
        page_title = page_title.replace("audio", "")
        # Remove artist name
        page_title = page_title.replace(artist, "")
        # Remove album name
        page_title = page_title.replace(album, "")
        # Remove title
        page_title = page_title.replace(title, "")
        return len(page_title)

    def __get_youtube_id_fallback(self, item):
        """
            Get youtube id (fallback)
            @param item as SearchItem
            @return youtube id as str
        """
        try:
            from bs4 import BeautifulSoup
        except:
            print("$ sudo pip3 install beautifulsoup4")
            return None
        try:
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
            search = GLib.uri_escape_string(
                            unescaped.replace(" ", "+"),
                            None,
                            True)
            f = Lio.File.new_for_uri("https://www.youtube.com/"
                                     "results?search_query=%s" % search)
            (status, data, tag) = f.load_contents(None)
            if not status:
                return None

            html = data.decode("utf-8")
            soup = BeautifulSoup(html, "html.parser")
            ytems = []
            for link in soup.findAll("a"):
                href = link.get("href")
                title = link.get("title")
                if href is None or title is None:
                    continue
                if href.startswith("/watch?v="):
                    href = href.replace("/watch?v=", "")
                    ytems.append((href, title))
            dic = {}
            best = self.__BAD_SCORE
            for (yid, title) in ytems:
                score = self.__get_youtube_score(title,
                                                 item.name,
                                                 artist,
                                                 item.album.name)
                if score < best:
                    best = score
                elif score == best:
                    continue  # Keep first result
                dic[score] = yid
            # Return url from first dic item
            if best == self.__BAD_SCORE:
                return None
            else:
                return dic[best]
        except Exception as e:
            print("WebYouTube::__get_youtube_id_fallback():", e)
            self.__fallback = True
        return None
