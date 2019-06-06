# Copyright (c) 2014-2019 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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
from locale import getdefaultlocale

from lollypop.define import App, AUDIODB_CLIENT_ID
from lollypop.utils import get_network_available
from lollypop.logger import Logger
from lollypop.downloader import Downloader


class Wikipedia:
    """
        Helper for wikipedia search
    """

    def __init__(self):
        """
            Init wikipedia
            @raise exception  is wikipedia module not installed
        """
        import wikipedia
        wikipedia

    def get_content(self, string):
        """
            Get content for string
            @param string as str
            @return str/None
        """
        content = None
        try:
            name = self.__get_duckduck_name(string)
            if name is None:
                return None
            import wikipedia
            language = getdefaultlocale()[0][0:2]
            wikipedia.set_lang(language)
            page = wikipedia.page(name)
            if page is None:
                wikipedia.set_lang("en")
                page = wikipedia.page(name)
            if page is not None:
                content = page.content.encode(encoding="UTF-8")
        except Exception as e:
            Logger.error("Wikipedia::get_content(): %s", e)
        return content

#######################
# PRIVATE             #
#######################
    def __get_duckduck_name(self, string):
        """
            Get wikipedia duck duck name for string
            @param string as str
            @return str
        """
        name = None
        try:
            uri = "https://api.duckduckgo.com/?q=%s&format=json&pretty=1"\
                % string
            (status, data) = App().task_helper.load_uri_content_sync(uri)
            if status:
                import json
                decode = json.loads(data.decode("utf-8"))
                uri = decode["AbstractURL"]
                if uri:
                    name = uri.split("/")[-1]
        except Exception as e:
            Logger.error("Wikipedia::__get_duckduck_name(): %s", e)
        return name


class InfoDownloader(Downloader):
    """
        Download info from the web
    """

    def __init__(self):
        """
            Init info downloader
        """
        Downloader.__init__(self)

    def cache_artist_info(self, artist):
        """
            Cache info for artist
            @param artist as str
        """
        if not get_network_available("DATA"):
            self.emit("artist-info-changed", artist)
            return
        App().task_helper.run(self.__cache_artist_info, artist)

#######################
# PROTECTED           #
#######################
    def _get_audiodb_artist_info(self, artist):
        """
            Get artist info from audiodb
            @param artist as str
            @return info as bytes
        """
        if not get_network_available("AUDIODB"):
            return None
        try:
            artist = GLib.uri_escape_string(artist, None, True)
            uri = "https://theaudiodb.com/api/v1/json/"
            uri += "%s/search.php?s=%s" % (AUDIODB_CLIENT_ID, artist)
            (status, data) = App().task_helper.load_uri_content_sync(uri, None)
            if status:
                decode = json.loads(data.decode("utf-8"))
                language = getdefaultlocale()[0][-2:]
                for item in decode["artists"]:
                    for key in ["strBiography%s" % language,
                                "strBiographyEN"]:
                        info = item[key]
                        if info is not None:
                            return info.encode("utf-8")
        except Exception as e:
            Logger.error("InfoDownloader::_get_audiodb_artist_info: %s, %s" %
                         (e, artist))
        return None

    def _get_lastfm_artist_info(self, artist):
        """
            Get artist info from audiodb
            @param artist as str
            @return info as bytes
        """
        info = None
        try:
            if App().lastfm is not None and get_network_available("LASTFM"):
                info = App().lastfm.get_artist_bio(artist)
        except Exception as e:
            Logger.error("InfoDownloader::_get_lastfm_artist_info(): %s" % e)
        return info

#######################
# PRIVATE             #
#######################
    def __cache_artist_info(self, artist):
        """
            Cache artist information
            @param artist as str
        """
        content = None
        try:
            if get_network_available("WIKIPEDIA"):
                wikipedia = Wikipedia()
                content = wikipedia.get_content(artist)
            else:
                for (api, a_helper, ar_helper, helper) in self._WEBSERVICES:
                    if helper is None:
                        continue
                    try:
                        method = getattr(self, helper)
                        content = method(artist)
                        if content is not None:
                            break
                    except Exception as e:
                        Logger.error(
                            "InfoDownloader::__cache_artists_artwork(): %s"
                            % e)
            self.save_artist_information(artist, content)
        except Exception as e:
            Logger.info("InfoDownloader::__cache_artist_info(): %s" % e)
        GLib.idle_add(self.emit, "artist-info-changed", artist)
