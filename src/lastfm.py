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

import gi
gi.require_version('Secret', '1')
from gi.repository import GLib, Gio

from gettext import gettext as _

try:
    from gi.repository import Secret
except Exception as e:
    print(e)
    print(_("Last.fm authentication disabled"))
    Secret = None

try:
    gi.require_version('Goa', '1.0')
    from gi.repository import Goa
except:
    pass

from pylast import LastFMNetwork, md5, BadAuthenticationError
from gettext import gettext as _
from locale import getdefaultlocale
from threading import Thread
import re

from lollypop.define import Lp, SecretSchema, SecretAttributes, Type
from lollypop.objects import Track
from lollypop.utils import debug


class LastFM(LastFMNetwork):
    """
       We recommend you don't distribute the API key and secret with your app,
       and that you ask users who want to build it to apply for a key of
       their own. We don't believe that this would violate the terms of most
       open-source licenses.
       That said, we can't stop you from distributing the key and secret if you
       want, and if your app isn't written in a compiled language, you don't
       really have much option :).
    """

    def __init__(self):
        """
            Init lastfm support
        """
        try:
            self._settings = Gio.Settings.new('org.gnome.system.proxy.http')
        except:
            self._settings = None
        self._username = ''
        self._is_auth = False
        self._password = None
        self._check_for_proxy()
        self._goa = self._get_goa_oauth()
        if self._goa is not None:
            self._API_KEY = self._goa.props.client_id
            self._API_SECRET = self._goa.props.client_secret
        else:
            self._API_KEY = '7a9619a850ccf7377c46cf233c51e3c6'
            self._API_SECRET = '9254319364d73bec6c59ace485a95c98'
        LastFMNetwork.__init__(self,
                               api_key=self._API_KEY,
                               api_secret=self._API_SECRET)
        self.connect(None)

    def connect(self, password):
        """
            Connect lastfm
            @param password as str/None
        """
        if self._goa:
            t = Thread(target=self._connect, args=('', '', True))
            t.daemon = True
            t.start()
        # Get username/password from GSettings/Secret
        elif Secret is not None and\
                Gio.NetworkMonitor.get_default().get_network_available():
            self._username = Lp().settings.get_value(
                                                   'lastfm-login').get_string()
            if password is None:
                schema = Secret.Schema.new("org.gnome.Lollypop",
                                           Secret.SchemaFlags.NONE,
                                           SecretSchema)
                Secret.password_lookup(schema, SecretAttributes, None,
                                       self._on_password_lookup)
            else:
                t = Thread(target=self._connect, args=(self._username,
                                                       password, True))
                t.daemon = True
                t.start()

    def connect_sync(self, password):
        """
            Connect lastfm sync
            @param password as str
        """
        if Gio.NetworkMonitor.get_default().get_network_available():
            self._username = Lp().settings.get_value(
                                                   'lastfm-login').get_string()
            self._connect(self._username, password)
            t = Thread(target=self._populate_loved_tracks, args=(True,))
            t.daemon = True
            t.start()

    def get_artist_infos(self, artist):
        """
            Get artist infos
            @param artist as str
            @return (url as str, content as str)
        """
        if not Gio.NetworkMonitor.get_default().get_network_available():
            return (None, None, None)
        last_artist = self.get_artist(artist)
        try:
            content = last_artist.get_bio_content(
                language=getdefaultlocale()[0][0:2])
        except:
            content = last_artist.get_bio_content()
        content = re.sub(r'<.*Last.fm.*>.', '', content)
        url = last_artist.get_cover_image(3)
        return (url, content.encode(encoding='UTF-8'))

    def scrobble(self, artist, album, title, timestamp, duration):
        """
            Scrobble track
            @param artist as str
            @param title as str
            @param album as str
            @param timestamp as int
            @param duration as int
        """
        if Gio.NetworkMonitor.get_default().get_network_available() and\
           self._is_auth and Secret is not None:
            t = Thread(target=self._scrobble,
                       args=(artist,
                             album,
                             title,
                             timestamp,
                             duration))
            t.daemon = True
            t.start()

    def now_playing(self, artist, album, title, duration):
        """
            Now playing track
            @param artist as str
            @param title as str
            @param album as str
            @param duration as int
        """
        if Gio.NetworkMonitor.get_default().get_network_available() and\
           self._is_auth and Secret is not None:
            t = Thread(target=self._now_playing,
                       args=(artist,
                             album,
                             title,
                             duration))
            t.daemon = True
            t.start()

    def love(self, artist, title):
        """
            Love track
            @param artist as string
            @param title as string
            @thread safe
        """
        # Love the track on lastfm
        if Gio.NetworkMonitor.get_default().get_network_available() and\
           self._is_auth:
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
        if Gio.NetworkMonitor.get_default().get_network_available() and\
           self._is_auth:
            track = self.get_track(artist, title)
            try:
                track.unlove()
            except Exception as e:
                print("Lastfm::unlove(): %s" % e)

    @property
    def is_auth(self):
        """
            True if valid authentication send
        """
        return self._is_auth

    @property
    def is_goa(self):
        """
            True if using Gnome Online Account
        """
        return self._goa is not None

#######################
# PRIVATE             #
#######################
    def _get_goa_oauth(self):
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

    def _check_for_proxy(self):
        """
            Enable proxy if needed
        """
        if self._settings is not None:
            h = self._settings.get_value('host').get_string()
            p = self._settings.get_value('port').get_int32()
            if h != '' and p != 0:
                self.enable_proxy(host=h, port=p)
                return
        self.disable_proxy()

    def _connect(self, username, password, populate_loved=False):
        """
            Connect lastfm
            @param username as str
            @param password as str
            @thread safe
        """
        self._username = username
        if self._goa is not None or (password != '' and username != ''):
            self._is_auth = True
        else:
            self._is_auth = False
        try:
            self._check_for_proxy()
            if self._goa is None:
                LastFMNetwork.__init__(
                    self,
                    api_key=self._API_KEY,
                    api_secret=self._API_SECRET,
                    username=self._username,
                    password_hash=md5(password))
            else:
                LastFMNetwork.__init__(
                    self,
                    api_key=self._API_KEY,
                    api_secret=self._API_SECRET,
                    session_key=self._goa.call_get_access_token_sync(None)[0])
            if populate_loved:
                self._populate_loved_tracks()
        except Exception as e:
            debug("Lastfm::_connect(): %s" % e)
            self._is_auth = False

    def _scrobble(self, artist, album, title, timestamp, duration, first=True):
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
        debug("LastFM::_scrobble(): %s, %s, %s, %s, %s" % (artist,
                                                           album,
                                                           title,
                                                           timestamp,
                                                           duration))
        try:
            LastFMNetwork.scrobble(self,
                                   artist=artist,
                                   album=album,
                                   title=title,
                                   timestamp=timestamp)
        except BadAuthenticationError as e:
            pass
        except Exception as e:
            print("Lastfm::scrobble():", e)
            # Scrobble sometimes fails
            if first:
                self._connect(self._username, self._password)

    def _now_playing(self, artist, album, title, duration, first=True):
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
            LastFMNetwork.update_now_playing(self,
                                             artist=artist,
                                             album=album,
                                             title=title,
                                             duration=duration)
            debug("LastFM::_now_playing(): %s, %s, %s, %s" % (artist,
                                                              album,
                                                              title,
                                                              duration))
        except BadAuthenticationError:
            if Lp().notify is not None:
                GLib.idle_add(Lp().notify.send, _("Wrong Last.fm credentials"))
        except Exception as e:
            print("Lastfm::scrobble():", e)
            # now playing sometimes fails
            if first:
                self._connect(self._username, self._password)
                self._now_playing(artist, album, title, duration, False)

    def _populate_loved_tracks(self, force=False):
        """
            Populate loved tracks playlist
            @param bool as force
        """
        if not self._is_auth:
            return
        try:
            if force or len(Lp().playlists.get_tracks(Type.LOVED)) == 0:
                tracks = []
                user = self.get_user(self._username)
                for loved in user.get_loved_tracks():
                    track_id = Lp().tracks.search_track(
                                                      str(loved.track.artist),
                                                      str(loved.track.title))
                    if track_id is not None:
                        tracks.append(Track(track_id))
                Lp().playlists.add_tracks(Type.LOVED, tracks)
        except Exception as e:
                print("LastFM::_populate_loved_tracks: %s" % e)

    def _on_password_lookup(self, source, result):
        """
            Init self object
            @param source as GObject.Object
            @param result Gio.AsyncResult
        """
        try:
            password = Secret.password_lookup_finish(result)
            self._password = password
            if Gio.NetworkMonitor.get_default().get_network_available():
                t = Thread(target=self._connect,
                           args=(self._username, password))
                t.daemon = True
                t.start()
        except Exception as e:
            print("Lastfm::_on_password_lookup(): %s" % e)
