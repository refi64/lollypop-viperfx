#!/usr/bin/python
# Copyright (c) 2014-2015 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# Copyright (c) 2013 Arnel A. Borja <kyoushuu@yahoo.com>
# Copyright (c) 2013 Vadim Rutkovsky <vrutkovs@redhat.com>
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

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import Gst

from lollypop.define import Lp, ArtSize, Type


class MPRIS(dbus.service.Object):
    MPRIS_IFACE = 'org.mpris.MediaPlayer2'
    MPRIS_PLAYER_IFACE = 'org.mpris.MediaPlayer2.Player'
    MPRIS_LOLLYPOP = 'org.mpris.MediaPlayer2.Lollypop'
    MPRIS_PATH = '/org/mpris/MediaPlayer2'

    def __init__(self, app):
        DBusGMainLoop(set_as_default=True)
        name = dbus.service.BusName(self.MPRIS_LOLLYPOP, dbus.SessionBus())
        dbus.service.Object.__init__(self, name, self.MPRIS_PATH)
        self._app = app
        self._metadata = {}
        Lp.player.connect('current-changed', self._on_current_changed)
        Lp.player.connect('seeked', self._on_seeked)
        Lp.player.connect('status-changed', self._on_status_changed)
        Lp.player.connect('volume-changed', self._on_volume_changed)

    @dbus.service.method(dbus_interface=MPRIS_IFACE)
    def Raise(self):
        self._app.do_activate()

    @dbus.service.method(dbus_interface=MPRIS_IFACE)
    def Quit(self):
        self._app.quit()

    @dbus.service.method(dbus_interface=MPRIS_PLAYER_IFACE)
    def Next(self):
        Lp.player.next()

    @dbus.service.method(dbus_interface=MPRIS_PLAYER_IFACE)
    def Previous(self):
        Lp.player.prev()

    @dbus.service.method(dbus_interface=MPRIS_PLAYER_IFACE)
    def Pause(self):
        Lp.player.pause()

    @dbus.service.method(dbus_interface=MPRIS_PLAYER_IFACE)
    def PlayPause(self):
        Lp.player.play_pause()

    @dbus.service.method(dbus_interface=MPRIS_PLAYER_IFACE)
    def Stop(self):
        Lp.player.stop()

    @dbus.service.method(dbus_interface=MPRIS_PLAYER_IFACE)
    def Play(self):
        Lp.player.play()

    @dbus.service.method(dbus_interface=MPRIS_PLAYER_IFACE,
                         in_signature='ox')
    def SetPosition(self, track_id, position):
        Lp.player.seek(position/1000000)

    @dbus.service.method(dbus_interface=MPRIS_PLAYER_IFACE,
                         in_signature='s')
    def OpenUri(self, uri):
        pass

    @dbus.service.signal(dbus_interface=MPRIS_PLAYER_IFACE,
                         signature='x')
    def Seeked(self, position):
        pass

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                         in_signature='ss', out_signature='v')
    def Get(self, interface, property_name):
        return self.GetAll(interface)[property_name]

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                         in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface == self.MPRIS_IFACE:
            return {
                'CanQuit': True,
                'CanRaise': True,
                'HasTrackList': False,
                'Identity': 'Lollypop',
                'DesktopEntry': 'lollypop'
            }
        elif interface == self.MPRIS_PLAYER_IFACE:
            return {
                'PlaybackStatus': self._get_status(),
                'LoopStatus': 'Playlist',
                'Rate': dbus.Double(1.0),
                'Shuffle': True,
                'Metadata': dbus.Dictionary(self._metadata, signature='sv'),
                'Volume': dbus.Double(Lp.player.get_volume()),
                'Position': dbus.Int64(Lp.player.get_position_in_track()),
                'MinimumRate': dbus.Double(1.0),
                'MaximumRate': dbus.Double(1.0),
                'CanGoNext': Lp.player.current_track.id is not None or
                Lp.player.current_track.id != Type.RADIOS,
                'CanGoPrevious': Lp.player.current_track.id is not None or
                Lp.player.current_track.id != Type.RADIOS,
                'CanPlay': Lp.player.current_track.id is not None,
                'CanPause': Lp.player.is_playing(),
                'CanSeek': True,
                'CanControl': True,
            }
        else:
            raise dbus.exceptions.DBusException(
                self.MPRIS_LOLLYPOP,
                "Lollypop doesn't handle %s interface"
                % interface)

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                         in_signature='ssv')
    def Set(self, interface, property_name, new_value):
        if property_name == 'Volume':
            Lp.player.set_volume(new_value)

    @dbus.service.signal(dbus_interface=dbus.PROPERTIES_IFACE,
                         signature='sa{sv}as')
    def PropertiesChanged(self, interface, changed_properties,
                          invalidated_properties):
        pass

#######################
# PRIVATE             #
#######################

    def _get_status(self):
        state = Lp.player.get_status()
        if state == Gst.State.PLAYING:
            return 'Playing'
        elif state == Gst.State.PAUSED:
            return 'Paused'
        else:
            return 'Stopped'

    def _update_metadata(self):
        if self._get_status() == 'Stopped':
            self._metadata = {}
        else:
            if Lp.player.current_track.id >= 0:
                self._metadata['mpris:trackid'] = dbus.ObjectPath(
                    '/org/lollypop/%s' % Lp.player.current_track.id)
            self._metadata['xesam:trackNumber'] =\
                Lp.player.current_track.number
            self._metadata['xesam:title'] = Lp.player.current_track.title
            self._metadata['xesam:album'] = Lp.player.current_track.album
            self._metadata['xesam:artist'] = [Lp.player.current_track.artist]
            self._metadata['xesam:albumArtist'] = [
                Lp.player.current_track.aartist]
            self._metadata['mpris:length'] = dbus.Int64(
                Lp.player.current_track.duration * 1000000)
            self._metadata['xesam:genre'] = [Lp.player.current_track.genre]
            self._metadata['xesam:url'] = Lp.player.current_track.uri
            if Lp.player.current_track.id == Type.RADIOS:
                cover_path = Lp.art.get_radio_cache_path(
                    Lp.player.current_track.artist, ArtSize.BIG)
            else:
                cover_path = Lp.art.get_album_cache_path(
                    Lp.player.current_track.album_id, ArtSize.BIG)
            if cover_path is not None:
                self._metadata['mpris:artUrl'] = "file://" + cover_path

    def _on_seeked(self, player, position):
        self.Seeked(position * 1000000)

    def _on_volume_changed(self, player, data=None):
        self.PropertiesChanged(self.MPRIS_PLAYER_IFACE,
                               {'Volume': dbus.Double(
                                Lp.player.get_volume()), },
                               [])

    def _on_current_changed(self, player):
        self._update_metadata()
        properties = {'Metadata': dbus.Dictionary(self._metadata,
                                                  signature='sv')}
        try:
            self.PropertiesChanged(self.MPRIS_PLAYER_IFACE, properties, [])
        except:
            pass

    def _on_status_changed(self, data=None):
        properties = {'PlaybackStatus': self._get_status()}
        self.PropertiesChanged(self.MPRIS_PLAYER_IFACE, properties, [])
