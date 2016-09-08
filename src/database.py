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

from gi.repository import GLib

import sqlite3
import os

from lollypop.define import Lp
from lollypop.database_upgrade import DatabaseUpgrade
from lollypop.sqlcursor import SqlCursor
from lollypop.localized import LocalizedCollation
from lollypop.utils import noaccents


class Database:
    """
        Base database object
    """
    _LOCAL_PATH = os.path.expanduser("~") + "/.local/share/lollypop"
    DB_PATH = "%s/lollypop.db" % _LOCAL_PATH

    # SQLite documentation:
    # In SQLite, a column with type INTEGER PRIMARY KEY
    # is an alias for the ROWID.
    # Here, we define an id INT PRIMARY KEY but never feed it,
    # this make VACUUM not destroy rowids...
    __create_albums = '''CREATE TABLE albums (id INTEGER PRIMARY KEY,
                                              name TEXT NOT NULL,
                                              no_album_artist BOOLEAN NOT NULL,
                                              year INT,
                                              path TEXT NOT NULL,
                                              popularity INT NOT NULL,
                                              synced INT NOT NULL,
                                              mtime INT NOT NULL)'''
    __create_artists = '''CREATE TABLE artists (id INTEGER PRIMARY KEY,
                                               name TEXT NOT NULL,
                                               sortname TEXT NOT NULL)'''
    __create_genres = '''CREATE TABLE genres (id INTEGER PRIMARY KEY,
                                            name TEXT NOT NULL)'''
    __create_album_artists = '''CREATE TABLE album_artists (
                                                album_id INT NOT NULL,
                                                artist_id INT NOT NULL)'''
    __create_album_genres = '''CREATE TABLE album_genres (
                                                album_id INT NOT NULL,
                                                genre_id INT NOT NULL)'''
    __create_tracks = '''CREATE TABLE tracks (id INTEGER PRIMARY KEY,
                                              name TEXT NOT NULL,
                                              uri TEXT NOT NULL,
                                              duration INT,
                                              tracknumber INT,
                                              discnumber INT,
                                              discname TEXT,
                                              album_id INT NOT NULL,
                                              year INT,
                                              popularity INT NOT NULL,
                                              ltime INT NOT NULL,
                                              mtime INT NOT NULL,
                                              persistent INT NOT NULL
                                              DEFAULT 1)'''
    __create_track_artists = '''CREATE TABLE track_artists (
                                                track_id INT NOT NULL,
                                                artist_id INT NOT NULL)'''
    __create_track_genres = '''CREATE TABLE track_genres (
                                                track_id INT NOT NULL,
                                                genre_id INT NOT NULL)'''
    __create_album_artists_idx = '''CREATE index idx_aa ON album_artists(
                                                album_id)'''
    __create_track_artists_idx = '''CREATE index idx_ta ON track_artists(
                                                track_id)'''
    __create_album_genres_idx = '''CREATE index idx_ag ON album_genres(
                                                album_id)'''
    __create_track_genres_idx = '''CREATE index idx_tg ON track_genres(
                                                track_id)'''

    def __init__(self):
        """
            Create database tables or manage update if needed
        """
        db_version = Lp().settings.get_value('db-version').get_int32()
        upgrade = DatabaseUpgrade(db_version, self)
        if os.path.exists(self.DB_PATH):
            with SqlCursor(self) as sql:
                upgrade.do_db_upgrade()
                Lp().settings.set_value('db-version',
                                        GLib.Variant('i', upgrade.count()))
        else:
            try:
                if not os.path.exists(self._LOCAL_PATH):
                    os.mkdir(self._LOCAL_PATH)
                # Create db schema
                with SqlCursor(self) as sql:
                    sql.execute(self.__create_albums)
                    sql.execute(self.__create_artists)
                    sql.execute(self.__create_genres)
                    sql.execute(self.__create_album_genres)
                    sql.execute(self.__create_album_artists)
                    sql.execute(self.__create_tracks)
                    sql.execute(self.__create_track_artists)
                    sql.execute(self.__create_track_genres)
                    sql.execute(self.__create_album_artists_idx)
                    sql.execute(self.__create_track_artists_idx)
                    sql.execute(self.__create_album_genres_idx)
                    sql.execute(self.__create_track_genres_idx)
                    sql.commit()
                    Lp().settings.set_value('db-version',
                                            GLib.Variant('i', upgrade.count()))
            except Exception as e:
                print("Database::__init__(): %s" % e)

    def get_cursor(self):
        """
            Return a new sqlite cursor
        """
        try:
            c = sqlite3.connect(self.DB_PATH, 600.0)
            c.create_collation('LOCALIZED', LocalizedCollation())
            c.create_function("noaccents", 1, noaccents)
            return c
        except:
            exit(-1)

    def del_non_persistent(self):
        """
            Delete non persistent tracks from db
        """
        for track_id in Lp().tracks.get_non_persistent():
            album_id = Lp().tracks.get_album_id(track_id)
            genre_ids = Lp().tracks.get_genre_ids(track_id)
            album_artist_ids = Lp().albums.get_artist_ids(album_id)
            artist_ids = Lp().tracks.get_artist_ids(track_id)
            Lp().tracks.remove(track_id)
            Lp().tracks.clean(track_id)
            Lp().albums.clean(album_id)
            for artist_id in album_artist_ids + artist_ids:
                Lp().artists.clean(artist_id)
            for genre_id in genre_ids:
                Lp().genres.clean(genre_id)
        with SqlCursor(Lp().db) as sql:
            sql.commit()

#######################
# PRIVATE             #
#######################
