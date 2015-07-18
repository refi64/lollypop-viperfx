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

from lollypop.objects import Track


# Manage a queue
class QueuePlayer:
    """
        Init queue
    """
    def __init__(self):
        self._queue = []

    """
        Append track to queue,
        remove previous track if exist
        @param track id as int
    """
    def append_to_queue(self, track_id):
        if track_id in self._queue:
            self._queue.remove(track_id)
        self._queue.append(track_id)
        self.set_next()
        self.emit("queue-changed")

    """
        Prepend track to queue,
        remove previous track if exist
        @param track id as int
    """
    def prepend_to_queue(self, track_id):
        if track_id in self._queue:
            self._queue.remove(track_id)
        self._queue.insert(0, track_id)
        self.set_next()
        self.emit("queue-changed")

    """
        Remove track from queue
        @param track id as int
    """
    def del_from_queue(self, track_id):
        if track_id in self._queue:
            self._queue.remove(track_id)
            self.set_next()
            self.emit("queue-changed")

    """
        Set queue
        @param [ids as int]
    """
    def set_queue(self, new_queue):
        self._queue = new_queue
        self.set_next()
        self.emit("queue-changed")

    """
        Return queue
        @return [ids as int]
    """
    def get_queue(self):
        if self._queue:
            return self._queue
        else:
            return []

    """
        True if track_id exist in queue
        @param track id as int
        @return bool
    """
    def is_in_queue(self, track_id):
        if self._queue:
            return track_id in self._queue
        else:
            return False

    """
        Return track position in queue
        @param track id as int
        @return position as int
    """
    def get_track_position(self, track_id):
        return self._queue.index(track_id)+1

    """
        Get next track id
        @return Track
    """
    def next(self):
        track_id = None
        if self._queue:
            track_id = self._queue[0]
        return Track(track_id)

#######################
# PRIVATE             #
#######################
