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

import os
import sqlite3
from datetime import datetime


class Radios(GObject.GObject):
    """
        Playlists manager
    """
    LOCAL_PATH = os.path.expanduser("~") + "/.local/share/lollypop"
    DB_PATH = "%s/radios.db" % LOCAL_PATH

    create_radios = '''CREATE TABLE radios (
                            id INTEGER PRIMARY KEY,
                            name TEXT NOT NULL,
                            url TEXY NOT NULL,
                            popularity INT NOT NULL)'''
    __gsignals__ = {
        # Add, rename, delete
        'radios-changed': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
    }

    def __init__(self):
        """
            Init playlists manager
        """
        GObject.GObject.__init__(self)
        self._sql = self.get_cursor()
        # Create db schema
        try:
            self._sql.execute(self.create_radios)
            self._sql.commit()
        except:
            pass

    def add(self, name, url, sql=None):
        """
            Add a radio
            @param radio name as str
            @param url as str
            @thread safe
        """
        if not sql:
            sql = self._sql
        sql.execute("INSERT INTO radios (name, url, mtime, popularity)"
                    " VALUES (?, ?, ?, ?)",
                    (name, url, datetime.now().strftime('%s'), 0))
        sql.commit()

    def exists(self, radio, sql=None):
        """
            Return True if radio exists
            @param radio as string
            @return bool
        """
        if not sql:
            sql = self._sql
        result = sql.execute("SELECT rowid\
                              FROM radios\
                              WHERE name=?",
                             (radio,))
        v = result.fetchone()
        if v:
            return v[0] > 1
        return False

    def rename(self, new_name, old_name, sql=None):
        """
            Rename playlist
            @param new playlist name as str
            @param old playlist name as str
        """
        if not sql:
            sql = self._sql
        sql.execute("UPDATE radios\
                    SET name=?\
                    WHERE name=?",
                    (new_name, old_name))
        sql.commit()

    def delete(self, name, sql=None):
        """
            delete radio
            @param radio name as str
        """
        if not sql:
            sql = self._sql
        sql.execute("DELETE FROM radios\
                    WHERE name=?",
                    (name,))
        sql.commit()

    def get(self, sql=None):
        """
            Return availables radios
            @return array of (name, url) as[(str, str)]
        """
        if not sql:
            sql = self._sql
        result = sql.execute("SELECT name, url\
                              FROM radios\
                              ORDER BY popularity, name")
        return list(result)

    def get_url(self, name, sql=None):
        """
            Return url for name
            @param name as str
            @return url as str
        """
        if not sql:
            sql = self._sql
        result = sql.execute("SELECT url\
                              FROM radios\
                              WHERE name=?", (name,))
        v = result.fetchone()
        if v:
            return v[0]
        return ''

#######################
# PRIVATE             #
#######################
    def get_cursor(self):
        """
            Return a new sqlite cursor
        """
        try:
            return sqlite3.connect(self.DB_PATH, 600.0)
        except:
            exit(-1)
