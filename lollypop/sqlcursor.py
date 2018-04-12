# Copyright (c) 2017-2018 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# Copyright (c) 2015 Jean-Philippe Braun <eon@patapon.info>
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

from threading import current_thread
from time import sleep

from lollypop.define import App


class SqlCursor:
    """
        Context manager to get the SQL cursor
    """
    def add(obj):
        """
            Add cursor to thread list
            Raise an exception if cursor already exists
        """
        obj.thread_lock.acquire()
        name = current_thread().getName() + obj.__class__.__name__
        App().cursors[name] = obj.get_cursor()

    def remove(obj):
        """
            Remove cursor from thread list and commit
            Raise an exception if cursor already exists
        """
        name = current_thread().getName() + obj.__class__.__name__
        App().cursors[name].commit()
        App().cursors[name].close()
        del App().cursors[name]
        obj.thread_lock.release()

    def commit(obj):
        """
            Commit current obj
        """
        name = current_thread().getName() + obj.__class__.__name__
        App().cursors[name].commit()

    def allow_thread_execution(obj):
        """
            Release thread lock allowing others threads execution
        """
        name = current_thread().getName() + obj.__class__.__name__
        if name in App().cursors.keys() and len(App().cursors.keys()) > 1:
            obj.thread_lock.release()
            sleep(0.01)
            obj.thread_lock.acquire()

    def __init__(self, obj):
        """
            Init object
        """
        self.__obj = obj
        self.__creator = False

    def __enter__(self):
        """
            Return cursor for thread, create a new one if needed
        """
        name = current_thread().getName() + self.__obj.__class__.__name__
        if name not in App().cursors:
            self.__creator = True
            App().cursors[name] = self.__obj.get_cursor()
            self.__obj.thread_lock.acquire()
        return App().cursors[name]

    def __exit__(self, type, value, traceback):
        """
            If creator, close cursor and remove it
        """
        if self.__creator:
            name = current_thread().getName() + self.__obj.__class__.__name__
            App().cursors[name].commit()
            App().cursors[name].close()
            del App().cursors[name]
            self.__obj.thread_lock.release()
