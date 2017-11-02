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

import gi
gi.require_version("Secret", "1")
from gi.repository import Gio

from gettext import gettext as _

try:
    from gi.repository import Secret
except Exception as e:
    print(e)
    print(_("Last.fm authentication disabled"))
    Secret = None

try:
    gi.require_version("Goa", "1.0")
    from gi.repository import Goa
except:
    pass

from pylast import LastFMNetwork, LibreFMNetwork, md5, WSError
from pylast import SessionKeyGenerator
from gettext import gettext as _
from locale import getdefaultlocale
import re

from lollypop.helper_task import TaskHelper
from lollypop.define import Lp, Type
from lollypop.objects import Track
from lollypop.utils import debug, get_network_available


class LastFM(LastFMNetwork, LibreFMNetwork):
    """
       Lastfm:
       We recommend you don"t distribute the API key and secret with your app,
       and that you ask users who want to build it to apply for a key of
       their own. We don"t believe that this would violate the terms of most
       open-source licenses.
       That said, we can"t stop you from distributing the key and secret if you
       want, and if your app isn"t written in a compiled language, you don"t
       really have much option :).
    """

    def __init__(self, name):
        """
            Init lastfm support
            @param name as str
        """
        self.__name = name
        self.__login = ""
        self.__is_auth = False
        self.__password = None
        self.__goa = None
        self.__check_for_proxy()
        if name == "librefm":
            LibreFMNetwork.__init__(self)
        else:
            self.__goa = self.__get_goa_oauth()
            if self.__goa is not None:
                self.__API_KEY = self.__goa.props.client_id
                self.__API_SECRET = self.__goa.props.client_secret
            else:
                self.__API_KEY = "7a9619a850ccf7377c46cf233c51e3c6"
                self.__API_SECRET = "9254319364d73bec6c59ace485a95c98"
            LastFMNetwork.__init__(self,
                                   api_key=self.__API_KEY,
                                   api_secret=self.__API_SECRET)
        self.connect()

    def connect(self, full_sync=False, callback=None, *args):
        """
            Connect service
            @param full_sync as bool
            @param callback as function
        """
        if self.__goa is not None:
            helper = TaskHelper()
            helper.run(self.__connect, full_sync)
        elif get_network_available():
            from lollypop.helper_passwords import PasswordsHelper
            helper = PasswordsHelper()
            helper.get(self.__name,
                       self.__on_get_password,
                       full_sync,
                       callback,
                       *args)

    def get_artist_info(self, artist):
        """
            Get artist infos
            @param artist as str
            @return (url as str, content as str)
        """
        if not get_network_available():
            return (None, None, None)
        last_artist = self.get_artist(artist)
        try:
            content = last_artist.get_bio_content(
                language=getdefaultlocale()[0][0:2])
        except:
            content = last_artist.get_bio_content()
        content = re.sub(r"<.*Last.fm.*>.", "", content)
        url = last_artist.get_cover_image(3)
        return (url, content.encode(encoding="UTF-8"))

    def do_scrobble(self, artist, album, title, timestamp):
        """
            Scrobble track
            @param artist as str
            @param title as str
            @param album as str
            @param timestamp as int
            @param duration as int
        """
        if get_network_available() and\
           self.__is_auth and Secret is not None:
            helper = TaskHelper()
            helper.run(self.__scrobble, artist, album, title, timestamp)

    def now_playing(self, artist, album, title, duration):
        """
            Now playing track
            @param artist as str
            @param title as str
            @param album as str
            @param duration as int
        """
        if get_network_available() and\
           self.__is_auth and Secret is not None:
            helper = TaskHelper()
            helper.run(self.__now_playing, artist, album, title, duration)

    def love(self, artist, title):
        """
            Love track
            @param artist as string
            @param title as string
            @thread safe
        """
        # Love the track on lastfm
        if get_network_available() and\
           self.__is_auth:
            track = self.get_track(artist, title)
            try:
                track.love()
            except Exception as e:
                print("Lastfm::love(): %s" % e)

    def unlove(self, artist, title):
        """
            Unlove track
            @param artist as string
            @param title as string
            @thread safe
        """
        # Love the track on lastfm
        if get_network_available() and\
           self.__is_auth:
            track = self.get_track(artist, title)
            try:
                track.unlove()
            except Exception as e:
                print("Lastfm::unlove(): %s" % e)

    def get_similars(self, artist):
        """
            Get similar artists
            @param artist as str
            @return artists as [str]
        """
        artists = []
        try:
            artist_item = self.get_artist(artist)
            for similar_item in artist_item.get_similar():
                artists.append(similar_item.item.name)
        except:
            pass
        return artists

    @property
    def is_auth(self):
        """
            True if valid authentication send
        """
        return self.__is_auth

    @property
    def is_goa(self):
        """
            True if using Gnome Online Account
        """
        return self.__goa is not None

#######################
# PRIVATE             #
#######################
    def __get_goa_oauth(self):
        """
            Init Gnome Online Account
            @return get_oauth2_based()/None
        """
        try:
            c = Goa.Client.new_sync()
            for proxy in c.get_accounts():
                if proxy.get_account().props.provider_name == "Last.fm":
                    return proxy.get_oauth2_based()
        except:
            pass
        return None

    def __check_for_proxy(self):
        """
            Enable proxy if needed
        """
        try:
            proxy = Gio.Settings.new("org.gnome.system.proxy")
            https = Gio.Settings.new("org.gnome.system.proxy.https")
            mode = proxy.get_value("mode").get_string()
            if mode != "none":
                h = https.get_value("host").get_string()
                p = https.get_value("port").get_int32()
                if h != "" and p != 0:
                    self.enable_proxy(host=h, port=p)
            else:
                self.disable_proxy()
        except:
            pass

    def __connect(self, full_sync=False):
        """
            Connect service
            @param full_sync as bool
            @thread safe
        """
        if self.__goa is not None or (self.__password != "" and
                                      self.__login != ""):
            self.__is_auth = True
        else:
            self.__is_auth = False
        try:
            self.session_key = ""
            self.__check_for_proxy()
            if self.__goa is not None:
                self.session_key = self.__goa.call_get_access_token_sync(
                                                                      None)[0]
            else:
                skg = SessionKeyGenerator(self)
                self.session_key = skg.get_session_key(
                                          username=self.__login,
                                          password_hash=md5(self.__password))
            if full_sync:
                helper = TaskHelper()
                helper.run(self.__populate_loved_tracks)
        except Exception as e:
            debug("LastFM::__connect(): %s" % e)
            self.__is_auth = False

    def __scrobble(self, artist, album, title, timestamp, first=True):
        """
            Scrobble track
            @param artist as str
            @param title as str
            @param album_title as str
            @param timestamp as int
            @param duration as int
            @param first is internal
            @thread safe
        """
        debug("LastFM::__scrobble(): %s, %s, %s, %s" % (artist,
                                                        album,
                                                        title,
                                                        timestamp))
        try:
            self.scrobble(artist=artist,
                          album=album,
                          title=title,
                          timestamp=timestamp)
        except WSError:
            pass
        except Exception as e:
            print("LastFM::__scrobble():", e)
            # Scrobble sometimes fails
            if first:
                self.__connect()
                self.__scrobble(artist, album, title, timestamp, False)

    def __now_playing(self, artist, album, title, duration, first=True):
        """
            Now playing track
            @param artist as str
            @param title as str
            @param album as str
            @param duration as int
            @param first is internal
            @thread safe
        """
        try:
            self.update_now_playing(artist=artist,
                                    album=album,
                                    title=title,
                                    duration=duration)
            debug("LastFM::__now_playing(): %s, %s, %s, %s" % (artist,
                                                               album,
                                                               title,
                                                               duration))
        except WSError:
            pass
        except Exception as e:
            print("LastFM::__now_playing():", e)
            # now playing sometimes fails
            if first:
                self.__connect()
                self.__now_playing(artist, album, title, duration, False)

    def __populate_loved_tracks(self):
        """
            Populate loved tracks playlist
        """
        if not self.__is_auth:
            return
        try:
            tracks = []
            user = self.get_user(self.__login)
            for loved in user.get_loved_tracks():
                track_id = Lp().tracks.search_track(
                                                  str(loved.track.artist),
                                                  str(loved.track.title))
                if track_id is not None:
                    tracks.append(Track(track_id))
            Lp().playlists.add_tracks(Type.LOVED, tracks)
        except Exception as e:
                print("LastFM::__populate_loved_tracks: %s" % e)

    def __on_get_password(self, attributes, password,
                          name, full_sync, callback, *args):
        """
             Set password label
             @param attributes as {}
             @param password as str
             @param name as str
             @param full_sync as bool
             @param callback as function
        """
        if attributes is None:
            return
        self.__login = attributes["login"]
        self.__password = password
        if get_network_available():
            helper = TaskHelper()
            helper.run(self.__connect, full_sync, callback=(callback, *args))
