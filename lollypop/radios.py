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

from gi.repository import GObject, GLib

import sqlite3

from lollypop.sqlcursor import SqlCursor


class Radios(GObject.GObject):
    """
        Playlists manager
    """
    __LOCAL_PATH = GLib.get_user_data_dir() + "/lollypop"
    DB_PATH = "%s/radios.db" % __LOCAL_PATH

    create_radios = """CREATE TABLE radios (
                            id INTEGER PRIMARY KEY,
                            name TEXT NOT NULL,
                            url TEXT NOT NULL,
                            rate INT NOT NULL DEFAULT -1,
                            popularity INT NOT NULL)"""
    __gsignals__ = {
        # Add, rename, delete
        "radios-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        """
            Init playlists manager
        """
        GObject.GObject.__init__(self)
        # Create db schema
        try:
            with SqlCursor(self) as sql:
                sql.execute(self.create_radios)
                sql.commit()
        except:
            pass

    def add(self, name, url):
        """
            Add a radio, update url if radio already exists in db
            @param radio name as str
            @param url as str
            @thread safe
        """
        with SqlCursor(self) as sql:
            if self.exists(name):
                sql.execute("UPDATE radios\
                             SET url=?\
                             WHERE name=?", (url, name))
            else:
                sql.execute("INSERT INTO radios (name, url, popularity)\
                             VALUES (?, ?, ?)",
                            (name, url, 0))
            sql.commit()
            GLib.idle_add(self.emit, "radios-changed")

    def exists(self, name):
        """
            Return True if radio exists
            @param radio as string
            @return bool
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT rowid\
                                  FROM radios\
                                  WHERE name=?",
                                 (name,))
            v = result.fetchone()
            if v is not None:
                return True
            else:
                return False

    def rename(self, old_name, new_name):
        """
            Rename playlist
            @param old playlist name as str
            @param new playlist name as str
        """
        with SqlCursor(self) as sql:
            sql.execute("UPDATE radios\
                        SET name=?\
                        WHERE name=?",
                        (new_name, old_name))
            sql.commit()
            GLib.idle_add(self.emit, "radios-changed")

    def delete(self, name):
        """
            delete radio
            @param radio name as str
        """
        with SqlCursor(self) as sql:
            sql.execute("DELETE FROM radios\
                        WHERE name=?",
                        (name,))
            sql.commit()
            GLib.idle_add(self.emit, "radios-changed")

    def get(self):
        """
            Return availables radios
            @return array of (name, url) as[(str, str)]
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT name, url\
                                  FROM radios\
                                  ORDER BY rate DESC,\
                                  popularity DESC, name")
            return list(result)

    def get_url(self, name):
        """
            Return url for name
            @param name as str
            @return url as str
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT url\
                                  FROM radios\
                                  WHERE name=?", (name,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return ""

    def set_more_popular(self, name):
        """
            Set radio more popular
            @param name as str
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT popularity from radios WHERE name=?",
                                 (name,))
            pop = result.fetchone()
            if pop:
                current = pop[0]
            else:
                current = 0
            current += 1
            sql.execute("UPDATE radios set popularity=? WHERE name=?",
                        (current, name))
            sql.commit()

    def get_higher_popularity(self):
        """
            Get higher available popularity
            @return int
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT popularity\
                                  FROM radios\
                                  ORDER BY POPULARITY DESC LIMIT 1")
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def get_avg_popularity(self):
        """
            Return avarage popularity
            @return avarage popularity as int
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT AVG(popularity)\
                                  FROM (SELECT popularity\
                                        FROM radios\
                                        ORDER BY POPULARITY DESC LIMIT 100)")
            v = result.fetchone()
            if v and v[0] is not None and v[0] > 5:
                return v[0]
            return 5

    def set_popularity(self, name, popularity):
        """
            Set popularity
            @param name as str
            @param popularity as int
        """
        with SqlCursor(self) as sql:
            try:
                sql.execute("UPDATE radios SET\
                            popularity=? WHERE name=?",
                            (popularity, name))
                sql.commit()
            except:  # Database is locked
                pass

    def set_rate(self, name, rate):
        """
            Set rate
            @param name as str
            @param rate as int
        """
        with SqlCursor(self) as sql:
            try:
                sql.execute("UPDATE radios SET\
                            rate=? WHERE name=?",
                            (rate, name))
                sql.commit()
            except:  # Database is locked
                pass

    def get_id(self, name):
        """
            Get radio id by name
            @param name as str
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT id\
                                 FROM radios WHERE\
                                 name=?", (name,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def get_name(self, radio_id):
        """
            Get name by id
            @param radio id as int
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT name\
                                 FROM radios WHERE\
                                 id=?", (radio_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def get_popularity(self, name):
        """
            Get popularity
            @param name as str
            @return popularity as int
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT popularity\
                                 FROM radios\
                                 WHERE name=?", (name,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def get_rate(self, name):
        """
            Get radio rate
            @param name as str
            @return rate as int
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT rate\
                                  FROM radios\
                                  WHERE name=?", (name,))
            v = result.fetchone()
            if v:
                return v[0]
            return 0

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
    def __on_entry_parsed(self, parser, uri, metadata, name):
        """
            Import entry
            @param parser as TotemPlParser.Parser
            @param radio uri as str
            @param metadata as GLib.HastTable
            @param name as str
        """
        self.add(name, uri)
