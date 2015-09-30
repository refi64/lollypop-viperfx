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

from gi.repository import GObject, GLib, Gio, TotemPlParser

import os
import sqlite3


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
        'radios-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        """
            Init playlists manager
        """
        GObject.GObject.__init__(self)
        try_import = not os.path.exists(self.DB_PATH)
        self._sql = self.get_cursor()
        # Create db schema
        try:
            self._sql.execute(self.create_radios)
            self._sql.commit()
        except:
            pass

        # We import radios from lollypop < 0.9.60
        if try_import:
            d = Gio.File.new_for_path(self.LOCAL_PATH + "/radios")
            infos = d.enumerate_children(
                'standard::name',
                Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
                None)
            for info in infos:
                f = info.get_name()
                if f.endswith(".m3u"):
                    parser = TotemPlParser.Parser.new()
                    parser.connect('entry-parsed',
                                   self._on_entry_parsed,
                                   f[:-4])
                    parser.parse_async(d.get_uri() + "/%s" % f,
                                       True, None, None)

    def add(self, name, url, sql=None):
        """
            Add a radio, update url if radio already exists in db
            @param radio name as str
            @param url as str
            @thread safe
        """
        if not sql:
            sql = self._sql
        if self.exists(name, sql):
            sql.execute("UPDATE radios SET"
                        " url=?", (url,))
        else:
            sql.execute("INSERT INTO radios (name, url, popularity)"
                        " VALUES (?, ?, ?)",
                        (name, url, 0))
        sql.commit()
        GLib.idle_add(self.emit, 'radios-changed')

    def exists(self, name, sql=None):
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
                             (name,))
        v = result.fetchone()
        if v:
            return True
        else:
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
        GLib.idle_add(self.emit, 'radios-changed')

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
        GLib.idle_add(self.emit, 'radios-changed')

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
    def _on_entry_parsed(self, parser, uri, metadata, name):
        """
            Import entry
            @param parser as TotemPlParser.Parser
            @param radio uri as str
            @param metadata as GLib.HastTable
            @param name as str
        """
        self.add(name, uri)
