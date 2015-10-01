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

from gettext import gettext as _
import itertools

from lollypop.define import Lp, Type
from lollypop.utils import translate_artist_name


class ArtistsDatabase:
    """
        All functions take a sqlite cursor as last parameter,
        set another one if you're in a thread
    """

    def __init__(self):
        """
            Init artists database object
        """
        pass

    def add(self, name, sql=None):
        """
            Add a new artist to database
            @param Artist name as string
            @return inserted rowid as int
            @warning: commit needed
        """
        if not sql:
            sql = Lp.sql
        result = sql.execute("INSERT INTO artists (name) VALUES (?)",
                             (name,))
        return result.lastrowid

    def get_id(self, name, sql=None):
        """
            Get artist id
            @param Artist name as string
            @return Artist id as int
        """
        if not sql:
            sql = Lp.sql

        result = sql.execute("SELECT rowid from artists\
                              WHERE name=?", (name,))
        v = result.fetchone()
        if v is not None:
            return v[0]

        return None

    def get_name(self, artist_id, sql=None):
        """
            Get artist name
            @param Artist id as int
            @return Artist name as string
        """
        if not sql:
            sql = Lp.sql
        if artist_id == Type.COMPILATIONS:
            return _("Many artists")

        result = sql.execute("SELECT name from artists WHERE rowid=?",
                             (artist_id,))
        v = result.fetchone()
        if v is not None:
            return translate_artist_name(v[0])

        return _("Unknown")

    def get_albums(self, artist_id, sql=None):
        """
            Get all availables albums for artist
            @return Array of id as int
        """
        if not sql:
            sql = Lp.sql
        result = sql.execute("SELECT rowid FROM albums\
                              WHERE artist_id=?\
                              ORDER BY year", (artist_id,))
        return list(itertools.chain(*result))

    def get_compilations(self, artist_id, sql=None):
        """
            Get all availables compilations for artist
            @return Array of id as int
        """
        if not sql:
            sql = Lp.sql
        result = sql.execute("SELECT DISTINCT albums.rowid FROM albums,\
                              tracks, track_artists\
                              WHERE track_artists.artist_id=?\
                              AND track_artists.track_id=tracks.rowid\
                              AND albums.rowid=tracks.album_id\
                              AND albums.artist_id=?\
                              ORDER BY albums.year", (artist_id,
                                                      Type.COMPILATIONS))
        return list(itertools.chain(*result))

    def get(self, genre_id, sql=None):
        """
            Get all available artists
            @param None
            or
            @param Filter genre id as int
            @return Array of (artist id as int, artist name as string)
        """
        if not sql:
            sql = Lp.sql
        result = []
        if genre_id == Type.ALL or genre_id is None:
            # Only artist that really have an album
            result = sql.execute("SELECT DISTINCT artists.rowid, artists.name\
                                  FROM artists, albums\
                                  WHERE albums.artist_id = artists.rowid\
                                  ORDER BY artists.name COLLATE NOCASE")
        else:
            result = sql.execute("SELECT DISTINCT artists.rowid, artists.name\
                                  FROM artists, albums, album_genres\
                                  WHERE artists.rowid == albums.artist_id\
                                  AND album_genres.genre_id=?\
                                  AND album_genres.album_id=albums.rowid\
                                  ORDER BY artists.name\
                                  COLLATE NOCASE", (genre_id,))
        return [(row[0], translate_artist_name(row[1])) for row in result]

    def exists(self, artist_id, sql=None):
        """
            Return True if artist exist
            @param artist id as int
        """
        if not sql:
            sql = Lp.sql

        result = sql.execute("SELECT COUNT(*) from artists WHERE rowid=?",
                             (artist_id,))
        v = result.fetchone()
        if v is not None:
            return bool(v[0])

        return False

    def search(self, string, sql=None):
        """
            Search for artists looking like string
            @param string
            @return Array of id as int
        """
        if not sql:
            sql = Lp.sql
        result = sql.execute("SELECT rowid FROM artists\
                              WHERE name LIKE ?\
                              LIMIT 25", ('%' + string + '%',))
        return list(itertools.chain(*result))

    def clean(self, artist_id, sql=None):
        """
            Clean database for artist id
            @param artist id as int
            @warning commit needed
        """
        if not sql:
            sql = Lp.sql
        result = sql.execute("SELECT rowid from albums\
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
                sql.execute("DELETE FROM artists WHERE rowid=?", (artist_id,))
