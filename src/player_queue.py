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

from lollypop.objects import Track


class QueuePlayer:
    """
        Manage queue
    """

    def __init__(self):
        """
            Init queue
        """
        self._queue = []
        self._prev_id = None
        self._next_id = None

    def append_to_queue(self, track_id, notify=True):
        """
            Append track to queue,
            remove previous track if exist
            @param track id as int
            @param notify as bool
        """
        if track_id in self._queue:
            self._queue.remove(track_id)
        self._queue.append(track_id)
        if not self._init_current_if_needed():
            self.set_next()
            self.set_prev()
        if notify:
            self.emit('queue-changed')

    def insert_in_queue(self, track_id, pos=0, notify=True):
        """
            Prepend track to queue,
            remove previous track if exist
            @param track id as int
            @param notify as bool
        """
        if track_id in self._queue:
            self._queue.remove(track_id)
        self._queue.insert(pos, track_id)
        if not self._init_current_if_needed():
            self.set_next()
            self.set_prev()
        if notify:
            self.emit('queue-changed')

    def del_from_queue(self, track_id, notify=True):
        """
            Remove track from queue
            @param track id as int
            @param notify as bool
        """
        if track_id in self._queue:
            self._queue.remove(track_id)
            self.set_next()
            self.set_prev()
        if notify:
            self.emit('queue-changed')

    def set_queue(self, new_queue, notify=True):
        """
            Set queue
            @param [ids as int]
            @param notify as bool
        """
        self._queue = new_queue
        if not self._init_current_if_needed():
            self.set_next()
            self.set_prev()
        if notify:
            self.emit('queue-changed')

    def get_queue(self):
        """
            Return queue
            @return [ids as int]
        """
        if self._queue:
            return self._queue
        else:
            return []

    def is_in_queue(self, track_id):
        """
            True if track_id exist in queue
            @param track id as int
            @return bool
        """
        if self._queue:
            return track_id in self._queue
        else:
            return False

    def get_track_position(self, track_id):
        """
            Return track position in queue
            @param track id as int
            @return position as int
        """
        return self._queue.index(track_id) + 1

    def next(self, current_next_id):
        """
            Get next track id
            @param current next track id as int
            @return Track
        """
        track_id = None
        if self._queue:
            track_id = self._queue[0]
            if self._next_id is None:
                self._next_id = current_next_id
        elif self._next_id is not None:
            track_id = self._next_id
            self._next_id = None
        return Track(track_id)

    def prev(self, current_prev_id):
        """
            Get prev next track id
            @param current prev track id as int
            @return Track
        """
        track_id = None
        if self._queue and self._prev_id is None:
            self._prev_id = current_prev_id
        elif not self._queue and self._prev_id is not None:
            track_id = self._prev_id
            self._prev_id = None
        return Track(track_id)

#######################
# PRIVATE             #
#######################
    def _init_current_if_needed(self):
        """
            Init current track if needed
        """
        if self.current_track.id is None and self._queue:
            self._load_track(QueuePlayer.next(self))
            if self.current_track.id in self._queue:
                self._queue.remove(self.current_track.id)
            self.set_next()
            self.set_prev()
            self.emit('current-changed')
            return True
        return False
