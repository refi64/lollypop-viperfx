#!/usr/bin/python
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

from gi.repository import GObject

from lollypop.define import PlayContext, CurrentTrack, Objects


class BasePlayer(GObject.GObject):
    __gsignals__ = {
        'current-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'seeked': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        'status-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'volume-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'queue-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'cover-changed': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        'logo-changed' : (GObject.SignalFlags.RUN_FIRST, None, (str,))
    }
    """
        Init base player variables
    """
    def __init__(self):
        # In case of multiple subclassing, 
        # do not init variables for every subclass
        if not hasattr(self, 'albums'):
            GObject.GObject.__init__(self)    
            self._base_init = True
            # A user playlist used as current playlist
            self._user_playlist = None
            # Used by shuffle tracks to restore user playlist before shuffle
            self._user_playlist_backup = None
            self.current = CurrentTrack()
            self.context = PlayContext()
            # Albums in current playlist
            self._albums = None
            # Current shuffle mode
            self._shuffle = Objects.settings.get_enum('shuffle')
            # Tracks already played
            self._played_tracks_history = []
            # Used by shuffle albums to restore playlist before shuffle
            self._albums_backup = None
            # Albums already played
            self._already_played_albums = []
            # Tracks already played for albums
            self._already_played_tracks = {}
            # Party mode
            self._is_party = False
            # Player errors
            self._errors = 0
            # Bus for messages
            self._bus = None
            # Signal for message::tag
            self._message_tag = None
