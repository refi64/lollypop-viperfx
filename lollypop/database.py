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

from gi.repository import GLib, Gio

import sqlite3

from lollypop.define import Lp
from lollypop.objects import Album
from lollypop.database_upgrade import DatabaseUpgrade
from lollypop.sqlcursor import SqlCursor
from lollypop.localized import LocalizedCollation
from lollypop.utils import noaccents


class Database:
    """
        Base database object
    """
    if GLib.getenv("XDG_DATA_HOME") is None:
        __LOCAL_PATH = GLib.get_home_dir() + "/.local/share/lollypop"
    else:
        __LOCAL_PATH = GLib.getenv("XDG_DATA_HOME") + "/lollypop"
    DB_PATH = "%s/lollypop.db" % __LOCAL_PATH

    # SQLite documentation:
    # In SQLite, a column with type INTEGER PRIMARY KEY
    # is an alias for the ROWID.
    # Here, we define an id INT PRIMARY KEY but never feed it,
    # this make VACUUM not destroy rowids...
    __create_albums = """CREATE TABLE albums (id INTEGER PRIMARY KEY,
                                              name TEXT NOT NULL,
                                              no_album_artist BOOLEAN NOT NULL,
                                              year INT,
                                              uri TEXT NOT NULL,
                                              popularity INT NOT NULL,
                                              rate INT NOT NULL,
                                              loved INT NOT NULL,
                                              synced INT NOT NULL)"""
    __create_artists = """CREATE TABLE artists (id INTEGER PRIMARY KEY,
                                               name TEXT NOT NULL,
                                               sortname TEXT NOT NULL)"""
    __create_genres = """CREATE TABLE genres (id INTEGER PRIMARY KEY,
                                            name TEXT NOT NULL)"""
    __create_album_artists = """CREATE TABLE album_artists (
                                                album_id INT NOT NULL,
                                                artist_id INT NOT NULL)"""
    __create_album_genres = """CREATE TABLE album_genres (
                                                album_id INT NOT NULL,
                                                mtime INT NOT NULL,
                                                genre_id INT NOT NULL)"""
    __create_tracks = """CREATE TABLE tracks (id INTEGER PRIMARY KEY,
                                              name TEXT NOT NULL,
                                              uri TEXT NOT NULL,
                                              duration INT,
                                              tracknumber INT,
                                              discnumber INT,
                                              discname TEXT,
                                              album_id INT NOT NULL,
                                              year INT,
                                              popularity INT NOT NULL,
                                              rate INT NOT NULL,
                                              ltime INT NOT NULL
                                              )"""
    __create_track_artists = """CREATE TABLE track_artists (
                                                track_id INT NOT NULL,
                                                artist_id INT NOT NULL)"""
    __create_track_genres = """CREATE TABLE track_genres (
                                                track_id INT NOT NULL,
                                                mtime INT NOT NULL,
                                                genre_id INT NOT NULL)"""
    __create_album_artists_idx = """CREATE index idx_aa ON album_artists(
                                                album_id)"""
    __create_track_artists_idx = """CREATE index idx_ta ON track_artists(
                                                track_id)"""
    __create_album_genres_idx = """CREATE index idx_ag ON album_genres(
                                                album_id)"""
    __create_track_genres_idx = """CREATE index idx_tg ON track_genres(
                                                track_id)"""

    def __init__(self):
        """
            Create database tables or manage update if needed
        """
        f = Gio.File.new_for_path(self.DB_PATH)
        if not f.query_exists():
            db_version = Lp().settings.get_value("db-version").get_int32()
            upgrade = DatabaseUpgrade(db_version)
            try:
                d = Gio.File.new_for_path(self.__LOCAL_PATH)
                if not d.query_exists():
                    d.make_directory_with_parents()
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
                    Lp().settings.set_value("db-version",
                                            GLib.Variant("i", upgrade.count()))
            except Exception as e:
                print("Database::__init__(): %s" % e)

    def upgrade(self):
        """
            Upgrade database
        """
        db_version = Lp().settings.get_value("db-version").get_int32()
        upgrade = DatabaseUpgrade(db_version)
        f = Gio.File.new_for_path(self.DB_PATH)
        if f.query_exists():
            upgrade.do_db_upgrade()
            Lp().settings.set_value("db-version",
                                    GLib.Variant("i", upgrade.count()))

    def get_cursor(self):
        """
            Return a new sqlite cursor
        """
        try:
            c = sqlite3.connect(self.DB_PATH, 600.0)
            c.create_collation("LOCALIZED", LocalizedCollation())
            c.create_function("noaccents", 1, noaccents)
            return c
        except:
            exit(-1)

    def drop_db(self):
        """
            Drop database
        """
        try:
            f = Gio.File.new_for_path(self.DB_PATH)
            f.trash()
        except Exception as e:
            print("Database::drop_db():", e)

    def del_tracks(self, track_ids):
        """
            Delete tracks from db
            @param track_ids as [int]
        """
        SqlCursor.add(Lp().playlists)
        with SqlCursor(self) as sql:
            all_album_ids = []
            all_artist_ids = []
            all_genre_ids = []
            for track_id in track_ids:
                album_id = Lp().tracks.get_album_id(track_id)
                art_file = Lp().art.get_album_cache_name(Album(album_id))
                genre_ids = Lp().tracks.get_genre_ids(track_id)
                album_artist_ids = Lp().albums.get_artist_ids(album_id)
                artist_ids = Lp().tracks.get_artist_ids(track_id)
                uri = Lp().tracks.get_uri(track_id)
                Lp().playlists.remove(uri)
                Lp().tracks.remove(track_id)
                Lp().tracks.clean(track_id)
                all_album_ids.append(album_id)
                all_artist_ids += album_artist_ids + artist_ids
                all_genre_ids += genre_ids
            for album_id in list(set(all_album_ids)):
                if Lp().albums.clean(album_id):
                    Lp().art.clean_store(art_file)
            for artist_id in list(set(all_artist_ids)):
                Lp().artists.clean(artist_id)
            for genre_id in list(set(all_genre_ids)):
                Lp().genres.clean(genre_id)
            sql.commit()
        SqlCursor.remove(Lp().playlists)

#######################
# PRIVATE             #
#######################
