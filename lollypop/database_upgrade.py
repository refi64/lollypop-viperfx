# Copyright (c) 2014-2018 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

import itertools
from time import time

from lollypop.sqlcursor import SqlCursor
from lollypop.utils import translate_artist_name
from lollypop.database_history import History
from lollypop.radios import Radios
from lollypop.define import App, Type


class DatabaseUpgrade:
    """
        Manage database schema upgrades
    """

    def __init__(self):
        """
            Init object
        """
        # Here are schema upgrade, key is database version,
        # value is sql request
        self.__UPGRADES = {
            1: "UPDATE tracks SET duration=CAST(duration as INTEGER);",
            2: "UPDATE albums SET artist_id=-2001 where artist_id=-999;",
            3: self.__upgrade_3,
            4: self.__upgrade_4,
            5: "CREATE index idx_aa ON album_artists(album_id)",
            6: "CREATE index idx_ta ON track_artists(track_id)",
            7: "ALTER TABLE tracks ADD discname TEXT",
            8: "CREATE index idx_ag ON album_genres(album_id)",
            9: "CREATE index idx_tg ON track_genres(track_id)",
            10: "UPDATE tracks set ltime=0 where ltime is null",
            11: "ALTER TABLE albums ADD synced INT NOT NULL DEFAULT 0",
            12: "ALTER TABLE tracks ADD persistent INT NOT NULL DEFAULT 1",
            13: self.__upgrade_13,
            14: "UPDATE albums SET synced=-1 where mtime=0",
            15: self.__upgrade_15,
            16: self.__upgrade_16,
            17: "ALTER TABLE albums ADD loved INT NOT NULL DEFAULT 0",
            18: self.__upgrade_18,
            19: self.__upgrade_19,
            20: self.__upgrade_20,
            21: self.__upgrade_21,
            22: self.__upgrade_22,
            23: self.__upgrade_23,
            24: "ALTER TABLE albums ADD album_id TEXT",
            25: "ALTER TABLE tracks ADD mb_track_id TEXT",
            26: self.__upgrade_26,
            27: "UPDATE tracks SET duration=CAST(duration AS INT)",
            28: self.__upgrade_28,
        }

    def upgrade(self, db):
        """
            Upgrade db
            @param db as Database
        """
        # Migration from gsettings
        gsettings_version = App().settings.get_value("db-version").get_int32()
        if gsettings_version != -1:
            with SqlCursor(db) as sql:
                sql.execute("PRAGMA user_version=%s" % gsettings_version)
                App().settings.set_value("db-version",
                                         GLib.Variant("i", -1))
        version = 0
        with SqlCursor(db) as sql:
            result = sql.execute("PRAGMA user_version")
            v = result.fetchone()
            if v is not None:
                version = v[0]
            if version < self.version:
                for i in range(version+1, self.version + 1):
                    try:
                        if isinstance(self.__UPGRADES[i], str):
                            sql.execute(self.__UPGRADES[i])
                        else:
                            self.__UPGRADES[i](db)
                    except Exception as e:
                        print("History DB upgrade %s failed: %s" % (i, e))
                sql.execute("PRAGMA user_version=%s" % self.version)

    @property
    def version(self):
        """
            Current wanted version
        """
        return len(self.__UPGRADES)

#######################
# PRIVATE             #
#######################
    def __upgrade_3(self, db):
        """
            Add a sorted field to artists
        """
        with SqlCursor(db) as sql:
            sql.execute("ALTER TABLE artists ADD sortname TEXT")
            result = sql.execute("SELECT DISTINCT artists.rowid,\
                                  artists.name\
                                  FROM artists")
            for row in result:
                translated = translate_artist_name(row[1])
                sql.execute("UPDATE artists SET name=? WHERE rowid=?",
                            (translated, row[0]))
                sql.execute("UPDATE artists SET sortname=? WHERE rowid=?",
                            (row[1], row[0]))

    def __upgrade_4(self, db):
        """
            Add album artists table
        """
        with SqlCursor(db) as sql:
            sql.execute("CREATE TABLE album_artists (\
                                                album_id INT NOT NULL,\
                                                artist_id INT NOT NULL)")
            result = sql.execute("SELECT rowid from albums")
            for album_id in list(itertools.chain(*result)):
                result = sql.execute("SELECT artist_id\
                                     FROM albums\
                                     WHERE rowid=?",
                                     (album_id,))
                v = result.fetchone()
                if v is not None:
                    artist_id = v[0]
                    sql.execute("INSERT INTO album_artists\
                                (album_id, artist_id)\
                                VALUES(?, ?)",
                                (album_id, artist_id))
            sql.execute("CREATE TEMPORARY TABLE backup(id,\
                                                       name,\
                                                       no_album_artist,\
                                                       year,\
                                                       path,\
                                                       popularity,\
                                                       mtime)")
            sql.execute("INSERT INTO backup\
                        SELECT id,\
                               name,\
                               no_album_artist,\
                               year,\
                               path,\
                               popularity,\
                               mtime FROM albums")
            sql.execute("DROP TABLE albums")
            sql.execute("CREATE TABLE albums (id INTEGER PRIMARY KEY,\
                        name TEXT NOT NULL,\
                        no_album_artist BOOLEAN NOT NULL,\
                        year INT,\
                        path TEXT NOT NULL,\
                        popularity INT NOT NULL,\
                        mtime INT NOT NULL)")
            sql.execute("INSERT INTO albums\
                        SELECT id,\
                               name,\
                               no_album_artist,\
                               year,\
                               path,\
                               popularity,\
                               mtime FROM backup")
            sql.execute("DROP TABLE backup")

    def __upgrade_13(self, db):
        """
            Convert tracks filepath column to uri
        """
        with SqlCursor(db) as sql:
            sql.execute("ALTER TABLE tracks RENAME TO tmp_tracks")
            sql.execute("""CREATE TABLE tracks (id INTEGER PRIMARY KEY,
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
                                              DEFAULT 1)""")

            sql.execute("""INSERT INTO tracks(id, name, uri, duration,
                        tracknumber, discnumber, discname, album_id,
                        year, popularity, ltime, mtime, persistent) SELECT
                            id, name, filepath, duration,
                            tracknumber, discnumber, discname, album_id,
                            year, popularity, ltime, mtime, persistent FROM
                          tmp_tracks""")
            sql.execute("DROP TABLE tmp_tracks")
            result = sql.execute("SELECT rowid FROM tracks")
            for track_id in list(itertools.chain(*result)):
                result = sql.execute("SELECT uri FROM tracks WHERE rowid=?",
                                     (track_id,))
                v = result.fetchone()
                if v is not None:
                    uri = v[0]
                    if uri.startswith("/"):
                        uri = GLib.filename_to_uri(uri)
                        sql.execute("UPDATE tracks set uri=? WHERE rowid=?",
                                    (uri, track_id))
        with SqlCursor(App().playlists) as sql:
            sql.execute("ALTER TABLE tracks RENAME TO tmp_tracks")
            sql.execute("""CREATE TABLE tracks (playlist_id INT NOT NULL,
                                                uri TEXT NOT NULL)""")
            sql.execute("""INSERT INTO tracks(playlist_id, uri) SELECT
                            playlist_id, filepath FROM tmp_tracks""")
            sql.execute("DROP TABLE tmp_tracks")
            result = sql.execute("SELECT uri FROM tracks")
            for path in list(itertools.chain(*result)):
                if path.startswith("/"):
                    uri = GLib.filename_to_uri(path)
                    sql.execute("UPDATE tracks set uri=? WHERE uri=?",
                                (uri, path))

    def __upgrade_15(self, db):
        """
            Fix broken 0.9.208 release
        """
        if App().notify:
            App().notify.send("Please wait while upgrading db...")
        with SqlCursor(db) as sql:
            result = sql.execute("SELECT tracks.rowid FROM tracks\
                                  WHERE NOT EXISTS (\
                                                 SELECT track_id\
                                                 FROM track_genres\
                                                 WHERE track_id=tracks.rowid)")
            db.del_tracks(list(itertools.chain(*result)))

    def __upgrade_16(self, db):
        """
            Get ride of paths
        """
        paths = App().settings.get_value("music-path")
        uris = []
        for path in paths:
            uris.append(GLib.filename_to_uri(path))
        App().settings.set_value("music-uris", GLib.Variant("as", uris))
        with SqlCursor(db) as sql:
            sql.execute("ALTER TABLE albums RENAME TO tmp_albums")
            sql.execute("""CREATE TABLE albums (
                                              id INTEGER PRIMARY KEY,
                                              name TEXT NOT NULL,
                                              no_album_artist BOOLEAN NOT NULL,
                                              year INT,
                                              uri TEXT NOT NULL,
                                              popularity INT NOT NULL,
                                              synced INT NOT NULL,
                                              mtime INT NOT NULL)""")

            sql.execute("""INSERT INTO albums(id, name, no_album_artist,
                        year, uri, popularity, synced, mtime) SELECT
                            id, name, no_album_artist,
                            year, path, popularity, synced, mtime FROM
                            tmp_albums""")
            sql.execute("DROP TABLE tmp_albums")
            result = sql.execute("SELECT rowid, uri FROM albums")
            for (rowid, uri) in result:
                if uri.startswith("/"):
                    uri = GLib.filename_to_uri(uri)
                    sql.execute("UPDATE albums set uri=? WHERE rowid=?",
                                (uri, rowid))

    def __upgrade_18(self, db):
        """
            Upgrade history
        """
        with SqlCursor(History()) as sql:
            sql.execute("ALTER TABLE history ADD loved_album\
                        INT NOT NULL DEFAULT 0")

    def __upgrade_19(self, db):
        """
            Upgrade history
        """
        with SqlCursor(History()) as sql:
            try:
                sql.execute("ALTER TABLE history ADD album_rate\
                            INT NOT NULL DEFAULT -1")
                sql.execute("ALTER TABLE history ADD rate\
                            INT NOT NULL DEFAULT -1")
            except:
                pass  # May fails if History was non existent
        with SqlCursor(db) as sql:
            sql.execute("ALTER TABLE tracks ADD rate\
                        INT NOT NULL DEFAULT -1")
            sql.execute("ALTER TABLE albums ADD rate\
                        INT NOT NULL DEFAULT -1")

    def __upgrade_20(self, db):
        """
            Add mtimes tables
        """
        mtime = int(time())
        with SqlCursor(db) as sql:
            sql.execute("ALTER TABLE album_genres\
                         ADD mtime INT NOT NULL DEFAULT %s" % mtime)
            sql.execute("ALTER TABLE track_genres\
                         ADD mtime INT NOT NULL DEFAULT %s" % mtime)
            # Remove mtimes from albums table
            sql.execute("CREATE TEMPORARY TABLE backup(\
                                          id INTEGER PRIMARY KEY,\
                                          name TEXT NOT NULL,\
                                          no_album_artist BOOLEAN NOT NULL,\
                                          year INT,\
                                          uri TEXT NOT NULL,\
                                          popularity INT NOT NULL,\
                                          rate INT NOT NULL,\
                                          loved INT NOT NULL,\
                                          synced INT NOT NULL)")
            sql.execute("INSERT INTO backup\
                            SELECT id,\
                                   name,\
                                   no_album_artist,\
                                   year,\
                                   uri,\
                                   popularity,\
                                   rate,\
                                   loved,\
                                   synced FROM albums")
            sql.execute("DROP TABLE albums")
            sql.execute("CREATE TABLE albums(\
                                          id INTEGER PRIMARY KEY,\
                                          name TEXT NOT NULL,\
                                          no_album_artist BOOLEAN NOT NULL,\
                                          year INT,\
                                          uri TEXT NOT NULL,\
                                          popularity INT NOT NULL,\
                                          rate INT NOT NULL,\
                                          loved INT NOT NULL,\
                                          synced INT NOT NULL)")
            sql.execute("INSERT INTO albums\
                            SELECT id,\
                                   name,\
                                   no_album_artist,\
                                   year,\
                                   uri,\
                                   popularity,\
                                   rate,\
                                   loved,\
                                   synced FROM backup")
            sql.execute("DROP TABLE backup")
            # Remove mtimes from tracks table
            sql.execute("CREATE TEMPORARY TABLE backup(\
                                          id INTEGER PRIMARY KEY,\
                                          name TEXT NOT NULL,\
                                          uri TEXT NOT NULL,\
                                          duration INT,\
                                          tracknumber INT,\
                                          discnumber INT,\
                                          discname TEXT,\
                                          album_id INT NOT NULL,\
                                          year INT,\
                                          popularity INT NOT NULL,\
                                          rate INT NOT NULL,\
                                          ltime INT NOT NULL,\
                                          persistent INT NOT NULL)")
            sql.execute("INSERT INTO backup\
                            SELECT id,\
                                   name,\
                                   uri,\
                                   duration,\
                                   tracknumber,\
                                   discnumber,\
                                   discname,\
                                   album_id,\
                                   year,\
                                   popularity,\
                                   rate,\
                                   ltime,\
                                   persistent FROM tracks")
            sql.execute("DROP TABLE tracks")
            sql.execute("CREATE TABLE tracks(\
                                          id INTEGER PRIMARY KEY,\
                                          name TEXT NOT NULL,\
                                          uri TEXT NOT NULL,\
                                          duration INT,\
                                          tracknumber INT,\
                                          discnumber INT,\
                                          discname TEXT,\
                                          album_id INT NOT NULL,\
                                          year INT,\
                                          popularity INT NOT NULL,\
                                          rate INT NOT NULL,\
                                          ltime INT NOT NULL,\
                                          persistent INT NOT NULL)")
            sql.execute("INSERT INTO tracks\
                            SELECT id,\
                                   name,\
                                   uri,\
                                   duration,\
                                   tracknumber,\
                                   discnumber,\
                                   discname,\
                                   album_id,\
                                   year,\
                                   popularity,\
                                   rate,\
                                   ltime,\
                                   persistent FROM backup")
            sql.execute("DROP TABLE backup")

    def __upgrade_21(self, db):
        """
            Add rate to radios
        """
        with SqlCursor(Radios()) as sql:
            sql.execute("ALTER TABLE radios ADD rate\
                         INT NOT NULL DEFAULT -1")

    def __upgrade_22(self, db):
        """
            Remove Charts/Web entries
        """
        with SqlCursor(db) as sql:
            result = sql.execute("SELECT rowid FROM tracks\
                                  WHERE persistent=0 OR\
                                  persistent=2 OR\
                                  persistent=3")
            track_ids = list(itertools.chain(*result))
            db.del_tracks(track_ids)
            # Remove persistent from tracks table
            sql.execute("CREATE TEMPORARY TABLE backup(\
                                          id INTEGER PRIMARY KEY,\
                                          name TEXT NOT NULL,\
                                          uri TEXT NOT NULL,\
                                          duration INT,\
                                          tracknumber INT,\
                                          discnumber INT,\
                                          discname TEXT,\
                                          album_id INT NOT NULL,\
                                          year INT,\
                                          popularity INT NOT NULL,\
                                          rate INT NOT NULL,\
                                          ltime INT NOT NULL)")
            sql.execute("INSERT INTO backup\
                            SELECT id,\
                                   name,\
                                   uri,\
                                   duration,\
                                   tracknumber,\
                                   discnumber,\
                                   discname,\
                                   album_id,\
                                   year,\
                                   popularity,\
                                   rate,\
                                   ltime FROM tracks")
            sql.execute("DROP TABLE tracks")
            sql.execute("CREATE TABLE tracks(\
                                          id INTEGER PRIMARY KEY,\
                                          name TEXT NOT NULL,\
                                          uri TEXT NOT NULL,\
                                          duration INT,\
                                          tracknumber INT,\
                                          discnumber INT,\
                                          discname TEXT,\
                                          album_id INT NOT NULL,\
                                          year INT,\
                                          popularity INT NOT NULL,\
                                          rate INT NOT NULL,\
                                          ltime INT NOT NULL)")
            sql.execute("INSERT INTO tracks\
                            SELECT id,\
                                   name,\
                                   uri,\
                                   duration,\
                                   tracknumber,\
                                   discnumber,\
                                   discname,\
                                   album_id,\
                                   year,\
                                   popularity,\
                                   rate,\
                                   ltime FROM backup")
            sql.execute("DROP TABLE backup")

    def __upgrade_23(self, db):
        """
            Restore back mtime in tracks
        """
        with SqlCursor(db) as sql:
            sql.execute("ALTER TABLE tracks ADD mtime INT")
            sql.execute("ALTER TABLE albums ADD mtime INT")

            sql.execute("UPDATE tracks SET mtime = (\
                            SELECT mtime FROM track_genres\
                            WHERE track_genres.track_id=tracks.rowid)")

            sql.execute("UPDATE albums SET mtime = (\
                            SELECT mtime FROM album_genres\
                            WHERE album_genres.album_id=albums.rowid)")
            # Remove mtime from album_genres table
            sql.execute("CREATE TABLE album_genres2 (\
                                                album_id INT NOT NULL,\
                                                genre_id INT NOT NULL)")
            sql.execute("INSERT INTO album_genres2\
                            SELECT album_id,\
                                   genre_id FROM album_genres")
            sql.execute("DROP TABLE album_genres")
            sql.execute("ALTER TABLE album_genres2 RENAME TO album_genres")

            # Remove mtime from track_genres table
            sql.execute("CREATE TABLE track_genres2 (\
                                                track_id INT NOT NULL,\
                                                genre_id INT NOT NULL)")
            sql.execute("INSERT INTO track_genres2\
                            SELECT track_id,\
                                   genre_id FROM track_genres")
            sql.execute("DROP TABLE track_genres")
            sql.execute("ALTER TABLE track_genres2 RENAME TO track_genres")

    def __upgrade_26(self, db):
        """
            Rename album_id to mb_album_id in albums
        """
        with SqlCursor(db) as sql:
            sql.execute("ALTER TABLE albums RENAME TO tmp_albums")
            sql.execute("""CREATE TABLE albums (
                               id INTEGER PRIMARY KEY,
                               name TEXT NOT NULL,
                               mb_album_id TEXT,
                               no_album_artist BOOLEAN NOT NULL,
                               year INT,
                               uri TEXT NOT NULL,
                               popularity INT NOT NULL,
                               rate INT NOT NULL,
                               loved INT NOT NULL,
                               mtime INT NOT NULL,
                               synced INT NOT NULL)""")

            sql.execute("""INSERT INTO albums (id, name, mb_album_id,
                            no_album_artist, year, uri, popularity, rate,
                            loved, mtime, synced) SELECT id, name, album_id,
                            no_album_artist, year, uri, popularity, rate,
                            loved, mtime, synced FROM tmp_albums""")
            sql.execute("DROP TABLE tmp_albums")

    def __upgrade_28(self, db):
        """
            Upgrade setting based on db
            https://gitlab.gnome.org/gnumdk/lollypop/issues/1368
        """
        with SqlCursor(db) as sql:
            result = sql.execute("SELECT albums.rowid\
                                  FROM albums, album_artists\
                                  WHERE album_artists.artist_id=?\
                                  AND album_artists.album_id=albums.rowid\
                                  LIMIT 1",
                                 (Type.COMPILATIONS,))
            if list(itertools.chain(*result)):
                App().settings.set_value("show-compilations",
                                         GLib.Variant("b", True))
