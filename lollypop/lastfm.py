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

import gi
gi.require_version("Secret", "1")
from gi.repository import Gio, GLib

from gettext import gettext as _

try:
    from gi.repository import Secret
except Exception as e:
    print(e)
    print(_("Last.fm authentication disabled"))
    Secret = None

from pylast import LastFMNetwork, LibreFMNetwork, md5, WSError
from pylast import SessionKeyGenerator
from gettext import gettext as _
from locale import getdefaultlocale
import re

from lollypop.define import App
from lollypop.objects import Track
from lollypop.logger import Logger
from lollypop.goa import GoaSyncedAccount


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
        self.session_key = ""
        self.__password = None
        self.__goa = None
        self.__queue = []
        if name == "librefm":
            LibreFMNetwork.__init__(self)
        else:
            self.__goa = GoaSyncedAccount("Last.fm")
            self.__goa.connect("account-switched",
                               self.on_goa_account_switched)
            if self.is_goa:
                auth = self.__goa.oauth2_based
                self.__API_KEY = auth.props.client_id
                self.__API_SECRET = auth.props.client_secret
            else:
                self.__API_KEY = "7a9619a850ccf7377c46cf233c51e3c6"
                self.__API_SECRET = "9254319364d73bec6c59ace485a95c98"
            LastFMNetwork.__init__(self,
                                   api_key=self.__API_KEY,
                                   api_secret=self.__API_SECRET)
        self.connect(True)

    def connect(self, full_sync=False, callback=None, *args):
        """
            Connect service
            @param full_sync as bool
            @param callback as function
        """
        if self.is_goa:
            App().task_helper.run(self.__connect, full_sync)
        elif Gio.NetworkMonitor.get_default().get_network_available():
            from lollypop.helper_passwords import PasswordsHelper
            helper = PasswordsHelper()
            helper.get(self.__name,
                       self.__on_get_password,
                       full_sync,
                       callback,
                       *args)

    def get_artist_artwork_uri(self, artist):
        """
            Get artist infos
            @param artist as str
            @return uri as str/None
        """
        if not Gio.NetworkMonitor.get_default().get_network_available():
            return (None, None, None)
        last_artist = self.get_artist(artist)
        uri = last_artist.get_cover_image(3)
        return uri

    def get_artist_bio(self, artist):
        """
            Get artist infos
            @param artist as str
            @return content as str/None
        """
        if not Gio.NetworkMonitor.get_default().get_network_available():
            return None
        last_artist = self.get_artist(artist)
        try:
            content = last_artist.get_bio_content(
                language=getdefaultlocale()[0][0:2])
        except:
            content = last_artist.get_bio_content()
        content = re.sub(r"<.*Last.fm.*>.", "", content)
        return content.encode(encoding="UTF-8")

    def listen(self, track, timestamp):
        """
            Submit a listen for a track (scrobble)
            @param track as Track
            @param timestamp as int
        """
        if Gio.NetworkMonitor.get_default().get_network_available() and\
                self.available:
            self.__clean_queue()
            App().task_helper.run(
                       self.__scrobble,
                       ", ".join(track.artists),
                       track.album_name,
                       track.title,
                       timestamp,
                       track.mb_track_id)
        else:
            self.__queue.append((track, timestamp))

    def playing_now(self, track):
        """
            Submit a playing now notification for a track
            @param track as Track
        """
        if Gio.NetworkMonitor.get_default().get_network_available() and\
                track.id > 0 and self.available:
            App().task_helper.run(
                       self.__now_playing,
                       ", ".join(track.artists),
                       track.album_name,
                       track.title,
                       int(track.duration),
                       track.mb_track_id)

    def love(self, artist, title):
        """
            Love track
            @param artist as string
            @param title as string
            @thread safe
        """
        # Love the track on lastfm
        if Gio.NetworkMonitor.get_default().get_network_available() and\
                self.available:
            track = self.get_track(artist, title)
            try:
                track.love()
            except Exception as e:
                Logger.error("Lastfm::love(): %s" % e)

    def unlove(self, artist, title):
        """
            Unlove track
            @param artist as string
            @param title as string
            @thread safe
        """
        # Love the track on lastfm
        if Gio.NetworkMonitor.get_default().get_network_available() and\
                self.available:
            track = self.get_track(artist, title)
            try:
                track.unlove()
            except Exception as e:
                Logger.error("Lastfm::unlove(): %s" % e)

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

    def on_goa_account_switched(self, obj):
        """
            Callback for GoaSyncedAccount signal "account-switched"
            @param obj as GoaSyncedAccount
        """
        self.connect()

    def set_loved(self, track, loved):
        """
            Add or remove track from loved playlist on Last.fm
            @param track as Track
            @param loved as bool
        """
        if Gio.NetworkMonitor.get_default().get_network_available() and\
                self.available:
            if loved == 1:
                self.love(",".join(track.artists), track.name)
            else:
                self.unlove(",".join(track.artists), track.name)

    @property
    def can_love(self):
        """
            True if engine can love
            @return bool
        """
        return True

    @property
    def is_goa(self):
        """
            True if using Gnome Online Account
        """
        return self.__goa is not None and self.__goa.has_account

    @property
    def available(self):
        """
            Return True if Last.fm/Libre.fm submission is available
            @return bool
        """
        if not self.session_key:
            return False
        if self.is_goa:
            music_disabled = self.__goa.account.props.music_disabled
            Logger.debug("Last.fm GOA scrobbling disabled: %s" %
                         music_disabled)
            return not music_disabled
        return True

#######################
# PRIVATE             #
#######################
    def __clean_queue(self):
        """
            Send tracks in queue
        """
        if self.__queue:
            (track, timestamp) = self.__queue.pop(0)
            App().task_helper.run(
                       self.__scrobble,
                       ", ".join(track.artists),
                       track.album_name,
                       track.title,
                       timestamp,
                       track.mb_track_id)
            GLib.timeout_add(1000, self.__clean_queue)

    def __connect(self, full_sync=False):
        """
            Connect service
            @param full_sync as bool
            @thread safe
        """
        try:
            self.session_key = ""
            if self.is_goa:
                auth = self.__goa.oauth2_based
                self.api_key = auth.props.client_id
                self.api_secret = auth.props.client_secret
                self.session_key = auth.call_get_access_token_sync(None)[0]
            else:
                skg = SessionKeyGenerator(self)
                self.session_key = skg.get_session_key(
                    username=self.__login,
                    password_hash=md5(self.__password))
            if full_sync:
                App().task_helper.run(self.__populate_loved_tracks)
        except Exception as e:
            Logger.debug("LastFM::__connect(): %s" % e)

    def __scrobble(self, artist, album, title, timestamp, mb_track_id,
                   first=True):
        """
            Scrobble track
            @param artist as str
            @param title as str
            @param album_title as str
            @param timestamp as int
            @param duration as int
            @param mb_track_id as str
            @param first is internal
            @thread safe
        """
        if App().settings.get_value("disable-scrobbling"):
            return
        Logger.debug("LastFM::__scrobble(): %s, %s, %s, %s, %s" % (
                                                            artist,
                                                            album,
                                                            title,
                                                            timestamp,
                                                            mb_track_id))
        try:
            self.scrobble(artist=artist,
                          album=album,
                          title=title,
                          timestamp=timestamp,
                          mbid=mb_track_id)
        except WSError:
            pass
        except Exception as e:
            Logger.error("LastFM::__scrobble(): %s" % e)
            # Scrobble sometimes fails
            if first:
                self.__connect()
                self.__scrobble(artist, album, title, timestamp,
                                mb_track_id, False)

    def __now_playing(self, artist, album, title, duration, mb_track_id,
                      first=True):
        """
            Now playing track
            @param artist as str
            @param title as str
            @param album as str
            @param duration as int
            @param first is internal
            @thread safe
        """
        if App().settings.get_value("disable-scrobbling"):
            return
        try:
            self.update_now_playing(artist=artist,
                                    album=album,
                                    title=title,
                                    duration=duration,
                                    mbid=mb_track_id)
            Logger.debug("LastFM::__now_playing(): %s, %s, %s, %s, %s" % (
                artist, album, title, duration, mb_track_id))
        except WSError:
            pass
        except Exception as e:
            Logger.error("LastFM::__now_playing(): %s" % e)
            # now playing sometimes fails
            if first:
                self.__connect()
                self.__now_playing(artist, album, title, duration,
                                   mb_track_id, False)

    def __populate_loved_tracks(self):
        """
            Populate loved tracks playlist
        """
        if not self.available or\
                App().settings.get_value("lastfm-loved-status"):
            return
        try:
            user = self.get_user(self.__login)
            for loved in user.get_loved_tracks():
                track_id = App().tracks.search_track(
                    str(loved.track.artist),
                    str(loved.track.title))
                if track_id is not None:
                    Track(track_id).set_loved(1)
            App().settings.set_value("lastfm-loved-status",
                                     GLib.Variant("b", True))
        except Exception as e:
            Logger.error("LastFM::__populate_loved_tracks: %s" % e)

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
        if Gio.NetworkMonitor.get_default().get_network_available():
            App().task_helper.run(self.__connect, full_sync,
                                  callback=(callback, *args))
