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

from gettext import gettext as _
import itertools

from lollypop.sqlcursor import SqlCursor
from lollypop.define import Lp, Type
from lollypop.utils import format_artist_name, noaccents


class ArtistsDatabase:
    """
        Artists database helper
    """

    def __init__(self):
        """
            Init artists database object
        """
        pass

    def add(self, name, sortname):
        """
            Add a new artist to database
            @param artist name as string
            @param sortname as string
            @return inserted rowid as int
            @warning: commit needed
        """
        if sortname == "":
            sortname = format_artist_name(name)
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("INSERT INTO artists (name, sortname)\
                                  VALUES (?, ?)",
                                 (name, sortname))
            return result.lastrowid

    def set_sortname(self, artist_id, sortname):
        """
            Set sort name
            @param id as int
            @param sort name a str
            @warning: commit needed
        """
        with SqlCursor(Lp().db) as sql:
            sql.execute("UPDATE artists\
                         SET sortname=?\
                         WHERE rowid=?",
                        (sortname, artist_id))

    def get_sortname(self, artist_id):
        """
            Return sortname
            @param artist id as int
            @return sortname as string
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT sortname from artists\
                                  WHERE rowid=?", (artist_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return self.get_name(artist_id)

    def get_id(self, name):
        """
            Get artist id
            @param Artist name as string
            @return Artist id as int
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT rowid from artists\
                                  WHERE name=? COLLATE NOCASE", (name,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return None

    def get_name(self, artist_id):
        """
            Get artist name
            @param Artist id as int
            @return Artist name as string
        """
        with SqlCursor(Lp().db) as sql:
            if artist_id == Type.COMPILATIONS:
                return _("Many artists")

            result = sql.execute("SELECT name from artists WHERE rowid=?",
                                 (artist_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return _("Unknown")

    def get_albums(self, artist_ids):
        """
            Get all availables albums for artists
            @return Array of id as int
        """
        with SqlCursor(Lp().db) as sql:
            request = "SELECT DISTINCT albums.rowid\
                       FROM album_artists, albums\
                       WHERE albums.rowid=album_artists.album_id AND(1=0 "
            for artist_id in artist_ids:
                request += "OR album_artists.artist_id=%s " % artist_id
            request += ") ORDER BY year"
            result = sql.execute(request)
            return list(itertools.chain(*result))

    def get_compilations(self, artist_ids):
        """
            Get all availables compilations for artist
            @return Array of id as int
        """
        with SqlCursor(Lp().db) as sql:
            request = "SELECT DISTINCT albums.rowid FROM albums,\
                       tracks, track_artists, album_artists\
                       WHERE track_artists.track_id=tracks.rowid\
                       AND album_artists.artists_id=%s\
                       AND album_artists.album_id=albums.rowid\
                       AND albums.rowid=tracks.album_id AND (1=0 " %\
                       Type.COMPILATIONS
            for artist_id in artist_ids:
                request += "OR track_artists.artist_id=%s " % artist_id
            request += ") ORDER BY albums.year"
            result = sql.execute(request)
            return list(itertools.chain(*result))

    def get(self, genre_ids=[]):
        """
            Get all available album artists
            @param genre ids as [int]
            @return Array of (artist id as int, artist name as string)
        """
        with SqlCursor(Lp().db) as sql:
            result = []
            if not genre_ids or genre_ids[0] == Type.ALL:
                # Only artist that really have an album
                result = sql.execute(
                                 "SELECT DISTINCT artists.rowid,\
                                  artists.name, artists.sortname\
                                  FROM artists, albums, album_artists\
                                  WHERE album_artists.artist_id=artists.rowid\
                                  AND album_artists.album_id=albums.rowid\
                                  ORDER BY artists.sortname\
                                  COLLATE NOCASE COLLATE LOCALIZED")
            else:
                genres = tuple(genre_ids)
                request = "SELECT DISTINCT artists.rowid,\
                           artists.name, artists.sortname\
                           FROM artists, albums, album_genres, album_artists\
                           WHERE artists.rowid=album_artists.artist_id\
                           AND albums.rowid=album_artists.album_id\
                           AND album_genres.album_id=albums.rowid AND ("
                for genre_id in genre_ids:
                    request += "album_genres.genre_id=? OR "
                request += "1=0) ORDER BY artists.sortname\
                            COLLATE NOCASE COLLATE LOCALIZED"
                result = sql.execute(request, genres)
            return [(row[0], row[1], row[2]) for row in result]

    def get_local(self):
        """
            Get all available local artists
            @return Array of (artist id as int, artist name as string)
        """
        with SqlCursor(Lp().db) as sql:
            result = []
            result = sql.execute(
                             "SELECT DISTINCT artists.rowid,\
                              artists.name, artists.sortname\
                              FROM artists, albums, album_artists\
                              WHERE album_artists.artist_id=artists.rowid\
                              AND album_artists.album_id=albums.rowid\
                              AND albums.synced!=?\
                              ORDER BY artists.sortname\
                              COLLATE NOCASE COLLATE LOCALIZED",
                             (Type.NONE,))
            return [(row[0], row[1], row[2]) for row in result]

    def get_ids(self, genre_ids=[]):
        """
            Get all available album artists
            @param genre ids as [int]
            @return artist ids as [int]
        """
        with SqlCursor(Lp().db) as sql:
            result = []
            if not genre_ids or genre_ids[0] == Type.ALL:
                # Only artist that really have an album
                result = sql.execute(
                                 "SELECT DISTINCT artists.rowid\
                                  FROM artists, albums, album_artists\
                                  WHERE album_artists.artist_id=artists.rowid\
                                  AND album_artists.album_id=albums.rowid\
                                  ORDER BY artists.sortname\
                                  COLLATE NOCASE COLLATE LOCALIZED")
            else:
                genres = tuple(genre_ids)
                request = "SELECT DISTINCT artists.rowid\
                           FROM artists, albums, album_genres, album_artists\
                           WHERE artists.rowid=album_artists.artist_id\
                           AND albums.rowid=album_artists.album_id\
                           AND album_genres.album_id=albums.rowid AND ("
                for genre_id in genre_ids:
                    request += "album_genres.genre_id=? OR "
                request += "1=0) ORDER BY artists.sortname\
                            COLLATE NOCASE COLLATE LOCALIZED"
                result = sql.execute(request, genres)
            return list(itertools.chain(*result))

    def exists(self, artist_id):
        """
            Return True if artist exist
            @param artist id as int
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT COUNT(1) FROM artists WHERE rowid=?",
                                 (artist_id,))
            v = result.fetchone()
            if v is not None:
                return bool(v[0])
            return False

    def search(self, string):
        """
            Search for artists looking like string
            @param string
            @return Array of id as int
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT artists.rowid FROM artists, albums,\
                                  album_artists\
                                  WHERE noaccents(artists.name) LIKE ?\
                                  AND album_artists.artist_id=artists.rowid\
                                  AND album_artists.album_id=albums.rowid\
                                  LIMIT 25", ("%" + noaccents(string) + "%",))
            return list(itertools.chain(*result))

    def count(self):
        """
            Count artists
            @return int
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT COUNT(DISTINCT artists.rowid)\
                                  FROM artists, album_artists, albums\
                                  WHERE album_artists.album_id=albums.rowid\
                                  AND artists.rowid=album_artists.artist_id")
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def clean(self, artist_id):
        """
            Clean database for artist id
            @param artist id as int
            @warning commit needed
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT album_id from album_artists\
                                  WHERE artist_id=?\
                                  LIMIT 1", (artist_id,))
            v = result.fetchone()
            # Check tracks
            if not v:
                result = sql.execute("SELECT track_id from track_artists\
                                     WHERE artist_id=?\
                                     LIMIT 1", (artist_id,))
                v = result.fetchone()
                # Artist with no relation, remove
                if not v:
                    sql.execute("DELETE FROM artists WHERE rowid=?",
                                (artist_id,))
