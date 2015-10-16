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

import sqlite3
import os
from gi.repository import GLib

from lollypop.define import Lp
from lollypop.database_upgrade import DatabaseUpgrade
from lollypop.sqlcursor import SqlCursor


class Database:
    """
        Base database object
    """
    LOCAL_PATH = os.path.expanduser("~") + "/.local/share/lollypop"
    DB_PATH = "%s/lollypop.db" % LOCAL_PATH

    # SQLite documentation:
    # In SQLite, a column with type INTEGER PRIMARY KEY
    # is an alias for the ROWID.
    # Here, we define an id INT PRIMARY KEY but never feed it,
    # this make VACUUM not destroy rowids...
    create_albums = '''CREATE TABLE albums (id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        artist_id INT NOT NULL,
                        no_album_artist BOOLEAN NOT NULL,
                        year INT,
                        path TEXT NOT NULL,
                        popularity INT NOT NULL,
                        mtime INT NOT NULL)'''
    create_artists = '''CREATE TABLE artists (id INTEGER PRIMARY KEY,
                                              name TEXT NOT NULL)'''
    create_genres = '''CREATE TABLE genres (id INTEGER PRIMARY KEY,
                                            name TEXT NOT NULL)'''
    create_album_genres = '''CREATE TABLE album_genres (
                                                album_id INT NOT NULL,
                                                genre_id INT NOT NULL)'''
    create_tracks = '''CREATE TABLE tracks (id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        filepath TEXT NOT NULL,
                        duration INT,
                        tracknumber INT,
                        discnumber INT,
                        album_id INT NOT NULL,
                        year INT,
                        popularity INT NOT NULL,
                        ltime INT,
                        mtime INT)'''
    create_track_artists = '''CREATE TABLE track_artists (
                                                track_id INT NOT NULL,
                                                artist_id INT NOT NULL)'''
    create_track_genres = '''CREATE TABLE track_genres (
                                                track_id INT NOT NULL,
                                                genre_id INT NOT NULL)'''

    def __init__(self):
        """
            Init object
        """
        # Create db directory if missing
        if not os.path.exists(self.LOCAL_PATH):
            try:
                os.mkdir(self.LOCAL_PATH)
            except:
                print("Can't create %s" % self.LOCAL_PATH)

    def create(self):
        """
            Create database tables or manage update if needed
        """
        with SqlCursor(self) as sql:
            db_version = Lp.settings.get_value('db-version').get_int32()
            upgrade = DatabaseUpgrade(db_version, self)
            upgrade.do_db_upgrade()
            Lp.settings.set_value('db-version',
                                  GLib.Variant('i', upgrade.count()))
            # Create db schema
            try:
                sql.execute(self.create_albums)
                sql.execute(self.create_artists)
                sql.execute(self.create_genres)
                sql.execute(self.create_album_genres)
                sql.execute(self.create_tracks)
                sql.execute(self.create_track_artists)
                sql.execute(self.create_track_genres)
                sql.commit()
            except:
                pass

    def get_cursor(self):
        """
            Return a new sqlite cursor
        """
        try:
            return sqlite3.connect(self.DB_PATH, 600.0)
        except:
            exit(-1)
