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

import itertools

from lollypop.sqlcursor import SqlCursor
from lollypop.utils import translate_artist_name


class DatabaseUpgrade:
    """
        Manage database schema upgrades
    """

    def __init__(self, version, db):
        """
            Init object
            @param version as int
            @param db as Database
        """
        self._version = version
        self._db = db
        # Here are schema upgrade, key is database version,
        # value is sql request
        self._UPGRADES = {
            1: "UPDATE tracks SET duration=CAST(duration as INTEGER);",
            2: "UPDATE albums SET artist_id=-2001 where artist_id=-999;",
            3: self._upgrade_3,
            4: self._upgrade_4,
            5: "CREATE index idx_aa ON album_artists(album_id)",
            6: "CREATE index idx_ta ON track_artists(track_id)",
            7: "ALTER TABLE tracks ADD discname TEXT",
            8: "CREATE index idx_ag ON album_genres(album_id)",
            9: "CREATE index idx_tg ON track_genres(track_id)",
            10: "UPDATE tracks set ltime=0 where ltime is null",
                         }

    """
        Return upgrade count
        @return int
    """
    def count(self):
        return len(self._UPGRADES)

    """
        Upgrade database based on version
        @return new db version as int
    """
    def do_db_upgrade(self):
        with SqlCursor(self._db) as sql:
            for i in range(self._version+1, len(self._UPGRADES)+1):
                try:
                    if isinstance(self._UPGRADES[i], str):
                        sql.execute(self._UPGRADES[i])
                    else:
                        self._UPGRADES[i]()
                except Exception as e:
                    print("Database upgrade failed: ", e)
            sql.commit()
            return len(self._UPGRADES)

#######################
# PRIVATE             #
#######################
    def _upgrade_3(self):
        """
            Add a sorted field to artists
        """
        with SqlCursor(self._db) as sql:
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
            sql.commit()

    def _upgrade_4(self):
        """
            Add album artists table
        """
        with SqlCursor(self._db) as sql:
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
            sql.commit()
