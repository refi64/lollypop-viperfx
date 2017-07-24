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

from gi.repository import GObject

from lollypop.define import PlayContext, Lp, NextContext
from lollypop.objects import Track


class BasePlayer(GObject.GObject):
    """
        Base player object
    """
    __gsignals__ = {
        "current-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "album-added": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        "album-removed": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        "next-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "prev-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "seeked": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        "lock-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "status-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "volume-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "loading-changed": (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
        "queue-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "duration-changed": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        "rate-changed": (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_PYOBJECT,)),
        "party-changed": (GObject.SignalFlags.RUN_FIRST, None, (bool,))
    }

    def __init__(self):
        """
            Init base player variables
        """
        # In case of multiple subclassing,
        # do not init variables for every subclass
        if not hasattr(self, "_albums"):
            GObject.GObject.__init__(self)
            self._base_init = True
            # Lock adding tracks to playback, do nothing here, just get it
            # with locked property
            self._locked = False
            # Should player do crossfading
            self._crossfading = False
            # Keep track of artist/album finished
            self._next_context = NextContext.NONE
            # A user playlist used as current playlist
            self._user_playlist_ids = []
            self._user_playlist = []
            # Used by shuffle tracks to restore user playlist before shuffle
            self._user_playlist_backup = None
            self._current_track = Track()
            self._next_track = Track()
            self._prev_track = Track()
            self._context = PlayContext()
            # Albums in current playlist
            self._albums = []
            # Current shuffle mode
            self._shuffle = Lp().settings.get_enum("shuffle")
            # For tracks from the cmd line
            self._external_tracks = []

    def lock(self):
        """
            Mark player as locked
        """
        self._locked = not self._locked
        self.emit("lock-changed")

    @property
    def locked(self):
        """
            Is player locked as bool
        """
        return self._locked

    def reset_pcn(self):
        """
            Reset prev, current, next
        """
        self._current_track = Track()
        self._prev_track = Track()
        self._next_track = Track()

    def set_next(self):
        """
            Set next track
        """
        pass

    def set_prev(self):
        """
            Set prev track
        """
        pass

#######################
# PRIVATE             #
#######################
