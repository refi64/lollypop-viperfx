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


import os
import sqlite3

from lollypop.sqlcursor import SqlCursor


class History:
    """
        Playlists manager
    """
    LOCAL_PATH = os.path.expanduser("~") + "/.local/share/lollypop"
    DB_PATH = "%s/history.db" % LOCAL_PATH
    LIMIT = 1000000  # Delete when limit is reached
    DELETE = 100     # How many elements to delete
    create_history = '''CREATE TABLE history (
                            id INTEGER PRIMARY KEY,
                            name TEXT NOT NULL,
                            duration INT NOT NULL,
                            ltime INT NOT NULL,
                            popularity INT NOT NULL,
                            mtime INT NOT NULL,
                            album_popularity INT NOT NULL)'''

    def __init__(self):
        """
            Init playlists manager
        """
        # Create db schema
        try:
            with SqlCursor(self) as sql:
                sql.execute(self.create_history)
                sql.commit()
        except:
            pass
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT COUNT(*)\
                                  FROM history")
            v = result.fetchone()
            if v is not None and v[0] > self.LIMIT:
                sql.execute("DELETE FROM history\
                             WHERE rowid IN (SELECT rowid\
                                             FROM history\
                                             LIMIT %s)" % self.DELETE)
                sql.commit()
                sql.execute('VACUUM')

    def add(self, name, duration, popularity, ltime, mtime, album_popularity):
        """
            Add a radio, update url if radio already exists in db
            @param name as str
            @param duration as int
            @param popularity as int
            @param ltime as int
            @param mtime as int
            @param album_popularity as int
            @thread safe
        """
        with SqlCursor(self) as sql:
            if self.exists(name, duration):
                sql.execute("UPDATE history\
                             SET popularity=?,ltime=?,\
                             mtime=?,album_popularity=?\
                             WHERE name=? AND duration=?",
                            (popularity, ltime, mtime,
                             album_popularity, name, duration))
            else:
                sql.execute("INSERT INTO history\
                             (name, duration, popularity, ltime,\
                              mtime, album_popularity)\
                             VALUES (?, ?, ?, ?, ?, ?)",
                            (name, duration, popularity,
                             ltime, mtime, album_popularity))
            sql.commit()

    def get(self, name, duration):
        """
            Get stats for track with filename and duration
            @param path as str
            @param duration as int
            @return (popularity, ltime, mtime, album_popularity)
             as (int, int, int, int)
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT popularity, ltime,\
                                  mtime, album_popularity\
                                  FROM history\
                                  WHERE name=?\
                                  AND duration=?",
                                 (name, duration))
            v = result.fetchone()
            if v is not None:
                return v
            return (0, 0, 0, 0)

    def exists(self, name, duration):
        """
            Return True if entry exists
            @param name as str
            @parma duration as int
            @return bool
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT rowid\
                                  FROM history\
                                  WHERE name=?\
                                  AND duration=?",
                                 (name, duration))
            v = result.fetchone()
            if v is not None:
                return True
            else:
                return False

    def get_cursor(self):
        """
            Return a new sqlite cursor
        """
        try:
            return sqlite3.connect(self.DB_PATH, 600.0)
        except:
            exit(-1)

#######################
# PRIVATE             #
#######################
