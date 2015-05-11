#!/usr/bin/python
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
import os

from lollypop.define import Objects, Navigation


# All functions take a sqlite cursor as last parameter,
# set another one if you're in a thread
class DatabaseAlbums:
    def __init__(self):
        self._cached_randoms = []
        pass

    """
        Add a new album to database
        @param Album name as string
        @param artist id as int,
        @param compilation as bool,
        @param path as string
        @param outside as bool
        @param mtime as int
        @warning: commit needed
    """
    def add(self, name, artist_id, compilation, path, popularity,
            outside, mtime, sql=None):
        if not sql:
            sql = Objects.sql
        sql.execute("INSERT INTO albums "
                    "(name, artist_id, compilation, path, popularity, outside, mtime)"
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (name, artist_id, compilation,
                     path, popularity, outside, mtime))

    """
        Add genre to album
        @param album id as int
        @param genre id as int
        @param outside as bool
        @warning: commit needed
    """
    def add_genre(self, album_id, genre_id, outside, sql=None):
        if not sql:
            sql = Objects.sql
        genres = self.get_genre_ids(album_id, sql)
        if genre_id not in genres:
            sql.execute("INSERT INTO "
                        "album_genres (album_id, genre_id, outside)"
                        "VALUES (?, ?, ?)", (album_id, genre_id, outside))

    """
        Set artist id
        @param album id as int, artist_id as int
        @warning: commit needed
    """
    def set_artist_id(self, album_id, artist_id, sql=None):
        if not sql:
            sql = Objects.sql
        sql.execute("UPDATE albums SET artist_id=? WHERE rowid=?",
                    (artist_id, album_id))

    """
        Set year
        @param album id as int
        @param year as int
        @warning: commit needed
    """
    def set_year(self, album_id, year, sql=None):
        if not sql:
            sql = Objects.sql
        sql.execute("UPDATE albums SET year=? WHERE rowid=?",
                    (year, album_id))

    """
        Set album path for album id
        @param Album id as int, path as string
        @warning: commit needed
    """
    def set_path(self, album_id, path, sql=None):
        if not sql:
            sql = Objects.sql
        sql.execute("UPDATE albums SET path=? WHERE rowid=?", (path, album_id))

    """
        Set mtime
        @param album_id as int
        @param mtime as int
        @warning: commit needed
    """
    def set_mtime(self, album_id, mtime, sql=None):
        if not sql:
            sql = Objects.sql
        sql.execute("UPDATE albums set mtime=? WHERE rowid=?",
                    (mtime, album_id))

    """
        Set popularity
        @param album_id as int
        @param popularity as int
        @warning: commit needed
    """
    def set_popularity(self, album_id, popularity, sql=None):
        if not sql:
            sql = Objects.sql
        try:
            sql.execute("UPDATE albums set popularity=? WHERE rowid=?",
                        (popularity, album_id))
        except:  # Database is locked
            pass

    """
        Get popularity
        @param album_id as int
        @return popularity as int
    """
    def get_popularity(self, album_id, sql=None):
        if not sql:
            sql = Objects.sql
        result = sql.execute("SELECT popularity FROM albums WHERE "
                             "rowid=?",(album_id,))

        v = result.fetchone()
        if v:
            return v[0]
        return 0

    """
        Increment popularity field for album id
        @param int
        @raise sqlite3.OperationalError on db update
    """
    def set_more_popular(self, album_id, sql=None):
        if not sql:
            sql = Objects.sql
        result = sql.execute("SELECT popularity from albums WHERE rowid=?",
                             (album_id,))
        pop = result.fetchone()
        if pop:
            current = pop[0]
        else:
            current = 0
        current += 1
        sql.execute("UPDATE albums set popularity=? WHERE rowid=?",
                    (current, album_id))
        sql.commit()

    """
        Return avarage popularity
        @return avarage popularity as int
    """
    def get_avg_popularity(self, sql=None):
        if not sql:
            sql = Objects.sql
        result = sql.execute("SELECT AVG(popularity) FROM (SELECT popularity "
                             "FROM albums ORDER BY POPULARITY DESC LIMIT 100)")
        v = result.fetchone()
        if v and v[0] > 5:
            return v[0]
        return 5

    """
        Get album id
        @param Album name as string,
        @param artist id as int
        @return Album id as int
    """
    def get_id(self, album_name, artist_id, sql=None):
        if not sql:
            sql = Objects.sql
        result = sql.execute("SELECT rowid FROM albums where name=?\
                              AND artist_id=?\
                              AND compilation=0", (album_name,
                                                   artist_id))
        v = result.fetchone()
        if v:
            return v[0]
        return None

    """
        Get compilation id
        @param Album name as string,
        @return Album id as int
    """
    def get_compilation_id(self, album_name, sql=None):
        if not sql:
            sql = Objects.sql
        result = sql.execute("SELECT rowid FROM albums where name=?\
                              AND compilation=1", (album_name,))
        v = result.fetchone()
        if v:
            return v[0]
        return None

    """
        Get genre ids
        @param Album id as int
        @return Genres id as [int]
    """
    def get_genre_ids(self, album_id, sql=None):
        if not sql:
            sql = Objects.sql
        result = sql.execute("SELECT genre_id FROM album_genres\
                              WHERE album_id=?", (album_id,))
        genres = []
        for row in result:
            genres += row
        return genres

    """
        Get genre name
        @param Album id as int
        @return Genre name as str "genre1 genre2_..."
    """
    def get_genre_name(self, album_id, sql=None):
        if not sql:
            sql = Objects.sql
        result = sql.execute("SELECT name FROM genres, album_genres\
                              WHERE album_genres.album_id=?\
                              AND album_genres.genre_id=genres.rowid",
                             (album_id,))
        genres = ""
        for row in result:
            genres += row[0]
            genres += " "
        return genres

    """
        Get album name for album id
        @param Album id as int
        @return Album name as string
    """
    def get_name(self, album_id, sql=None):
        if not sql:
            sql = Objects.sql
        result = sql.execute("SELECT name FROM albums where rowid=?",
                             (album_id,))
        v = result.fetchone()
        if v:
            return v[0]

        return _("Unknown")

    """
        Get artist name
        @param Album id as int
        @return Artist name as string
    """
    def get_artist_name(self, album_id, sql=None):
        if not sql:
            sql = Objects.sql
        result = sql.execute("SELECT artists.name from artists, albums\
                              WHERE albums.rowid=? AND albums.artist_id ==\
                              artists.rowid", (album_id,))
        v = result.fetchone()
        if v:
            return v[0]

        return _("Compilation")

    """
        Get album artist id
        @param album_id
        @return artist id
    """
    def get_artist_id(self, album_id, sql=None):
        if not sql:
            sql = Objects.sql
        result = sql.execute("SELECT artist_id FROM albums where rowid=?",
                             (album_id,))
        v = result.fetchone()
        if v:
            return v[0]

        return None

    """
        Get album year
        @param album id as int
        @return album year as string
    """
    def get_year(self, album_id, sql=None):
        if not sql:
            sql = Objects.sql
        result = sql.execute("SELECT year FROM albums where rowid=?",
                             (album_id,))
        v = result.fetchone()
        if v:
            if v[0]:
                return str(v[0])

        return ""

    """
        Get album path for album id
        @param Album id as int
        @return Album path as string
    """
    def get_path(self, album_id, sql=None):
        if not sql:
            sql = Objects.sql
        result = sql.execute("SELECT path FROM albums WHERE rowid=?",
                             (album_id,))
        path = ""
        v = result.fetchone()
        if v:
            path = v[0]
        if path != "":
            if not os.path.exists(path):
                tracks = self.get_tracks(album_id, None, sql)
                if tracks:
                    filepath = Objects.tracks.get_path(tracks[0], sql)
                    path = os.path.dirname(filepath)
                    if os.path.exists(path):
                        sql.execute("UPDATE albums SET path=? "
                                    "WHERE rowid=?", (path, album_id))
                        sql.commit()
        return path

    """
        Count album having path as album path
    """
    def get_path_count(self, path, sql=None):
        if not sql:
            sql = Objects.sql

        result = sql.execute("SELECT count(path) FROM albums WHERE path=?",
                             (path,))
        v = result.fetchone()
        if v:
            return v[0]

        return 1

    """
        Get albums ids with popularity
        @return array of album ids as int
    """
    def get_populars(self, sql=None):
        if not sql:
            sql = Objects.sql
        albums = []
        result = sql.execute("SELECT rowid FROM albums WHERE popularity!=0\
                             ORDER BY popularity DESC LIMIT 100")
        for row in result:
            albums += row
        return albums

    """
        Return recent albums
        @return array of albums ids as int
    """
    def get_recents(self, sql=None):
        if not sql:
            sql = Objects.sql
        albums = []
        result = sql.execute("SELECT rowid FROM albums\
                              ORDER BY mtime DESC LIMIT 100")
        for row in result:
            albums += row
        return albums

    """
        Return randoms albums
        @return array of albums ids as int
    """
    def get_randoms(self, sql=None):
        if not sql:
            sql = Objects.sql
        albums = []

        result = sql.execute("SELECT rowid FROM albums\
                              ORDER BY random() LIMIT 100")
        for row in result:
            albums += row
        self._cached_randoms = list(albums)
        return albums

    """
        Same as above (cached result)
    """
    def get_cached_randoms(self):
        return self._cached_randoms

    """
        Get album ids for party mode based on genre ids
        @param Array of genre ids
        @return Array of album ids as int
    """
    def get_party_ids(self, genre_ids, sql=None):
        if not sql:
            sql = Objects.sql
        albums = []
        # get popular first
        if Navigation.POPULARS in genre_ids:
            albums += self.get_populars()
        # get recents next
        if Navigation.RECENTS in genre_ids:
            albums += self.get_recents()
        for genre_id in genre_ids:
            for album in Objects.genres.get_albums(genre_id, sql):
                if album not in albums:
                    albums.append(album)
        return albums

    """
        Get number of tracks for album_id
        @param album id as int
        @param genre id as int
        @return count as int
    """
    def get_count(self, album_id, genre_id, sql=None):
        if not sql:
            sql = Objects.sql
        if genre_id is not None and genre_id > 0:
            result = sql.execute("SELECT COUNT(tracks.rowid)\
                                  FROM tracks, track_genres\
                                  WHERE tracks.album_id=?\
                                  AND track_genres.track_id = tracks.rowid\
                                  AND track_genres.genre_id=?", (album_id,
                                                                 genre_id))
        else:
            result = sql.execute("SELECT COUNT(tracks.rowid)\
                                  FROM tracks\
                                  WHERE tracks.album_id=?", (album_id,))
        v = result.fetchone()
        if v:
            return v[0]
        return 0

    """
        Get number of tracks for album_id/disc
        @param album id as int
        @param genre id as int
        @param disc number as int
        @return count as int
    """
    def get_count_for_disc(self, album_id, genre_id, disc, sql=None):
        if not sql:
            sql = Objects.sql
        if genre_id is not None and genre_id > 0:
            result = sql.execute("SELECT COUNT(tracks.rowid)\
                                  FROM tracks, track_genres\
                                  WHERE tracks.album_id=?\
                                  AND track_genres.track_id = tracks.rowid\
                                  AND track_genres.genre_id=?\
                                  AND discnumber=?", (album_id,
                                                      genre_id,
                                                      disc))
        else:
            result = sql.execute("SELECT COUNT(tracks.rowid)\
                                  FROM tracks\
                                  WHERE tracks.album_id=?\
                                  AND discnumber=?", (album_id, disc))
        v = result.fetchone()
        if v:
            return v[0]
        return 0

    """
        Get disc numbers
        @param album id as int
        @param genre id as int
        @param disc number as int
        @return count as int
    """
    def get_discs(self, album_id, genre_id, sql=None):
        if not sql:
            sql = Objects.sql
        if genre_id is not None and genre_id > 0:
            result = sql.execute("SELECT DISTINCT discnumber\
                                  FROM tracks, track_genres\
                                  WHERE tracks.album_id=?\
                                  AND track_genres.track_id = tracks.rowid\
                                  AND track_genres.genre_id=?\
                                  ORDER BY discnumber", (album_id,
                                                         genre_id))
        else:
            result = sql.execute("SELECT DISTINCT discnumber\
                                  FROM tracks\
                                  WHERE tracks.album_id=?\
                                  ORDER BY discnumber", (album_id,))
        discs = []
        for row in result:
            discs += row
        return discs


    """
        Get tracks for album id
        @param album id as int
        @param genre id as int
        @return Arrays of tracks id as int
    """
    def get_tracks(self, album_id, genre_id, sql=None):
        if not sql:
            sql = Objects.sql
        tracks = []
        if genre_id is not None and genre_id > 0:
            result = sql.execute("SELECT tracks.rowid FROM tracks, track_genres\
                                  WHERE album_id=?\
                                  AND track_genres.track_id = tracks.rowid\
                                  AND track_genres.genre_id=?\
                                  ORDER BY discnumber, tracknumber",
                                 (album_id, genre_id))
        else:
            result = sql.execute("SELECT rowid FROM tracks\
                                  WHERE album_id=?\
                                  ORDER BY discnumber, tracknumber",
                                 (album_id,))
        for row in result:
            tracks += row
        return tracks

    """
        Get tracks path for album id/disc
        Will search track from albums from same artist
        with same name and different genre
        @param album id as int
        @param genre id as int
        @return Arrays of tracks id as int
    """
    def get_tracks_path(self, album_id, genre_id, sql=None):
        if not sql:
            sql = Objects.sql
        tracks = []
        if genre_id is not None and genre_id > 0:
            result = sql.execute("SELECT tracks.filepath\
                                  FROM tracks, track_genres\
                                  WHERE album_id=?\
                                  AND track_genres.genre_id=?\
                                  AND track_genres.track_id=tracks.rowid\
                                  ORDER BY discnumber, tracknumber",
                                 (album_id, genre_id))
        else:
            result = sql.execute("SELECT tracks.filepath\
                                  FROM tracks\
                                  WHERE album_id=?\
                                  ORDER BY discnumber, tracknumber",
                                 (album_id,))
        for row in result:
            tracks += row
        return tracks

    """
        Get tracks informations for album id
        Will search track from albums from same artist
        with same name and different genre
        @param album id as int
        @param genre id as int
        @param disc number as int
        @return Arrays of (tracks id as int, name as string,
                           length as int, is_compilation as bool, [artist ids])
    """
    def get_tracks_infos(self, album_id, genre_id, disc, sql=None):
        if not sql:
            sql = Objects.sql

        if genre_id is not None and genre_id > 0:
            result = sql.execute("SELECT tracks.rowid,\
                                  tracks.name,\
                                  tracks.length,\
                                  albums.compilation\
                                  FROM tracks, albums,\
                                  track_artists, track_genres\
                                  WHERE albums.rowid=?\
                                  AND albums.rowid = tracks.album_id\
                                  AND tracks.rowid = track_artists.track_id\
                                  AND tracks.rowid = track_genres.track_id\
                                  AND track_genres.genre_id=?\
                                  AND discnumber=?\
                                  ORDER BY discnumber, tracknumber",
                                 (album_id, genre_id, disc))
        else:
            result = sql.execute("SELECT tracks.rowid,\
                                  tracks.name,\
                                  tracks.length,\
                                  albums.compilation\
                                  FROM tracks, track_artists, albums\
                                  WHERE albums.rowid = ?\
                                  AND albums.rowid = tracks.album_id\
                                  AND track_artists.track_id = tracks.rowid\
                                  AND discnumber=?\
                                  ORDER BY discnumber, tracknumber",
                                 (album_id, disc))

        infos = []
        rm_doublon = []
        for row in result:
            # Check for doublon
            if row[0] not in rm_doublon:
                rm_doublon.append(row[0])
                # Add artists
                row += (Objects.tracks.get_artist_ids(row[0], sql),)
                infos.append(row,)
        del rm_doublon
        return infos

    """
        Get albums ids
        @param Artist id as int/None, genre id as int/None
        @return Array of album ids as int
    """
    def get_ids(self, artist_id=None, genre_id=None, sql=None):
        if not sql:
            sql = Objects.sql
        albums = []
        result = []
        # Get albums for all artists
        if artist_id is None and genre_id is None:
            result = sql.execute("SELECT albums.rowid FROM albums, artists\
                                  WHERE artists.rowid=albums.artist_id\
                                  AND albums.compilation=0\
                                  ORDER BY artists.name COLLATE NOCASE,\
                                  albums.year,\
                                  albums.name COLLATE NOCASE")
        # Get albums for genre
        elif artist_id is None:
            result = sql.execute("SELECT albums.rowid FROM albums,\
                                  album_genres, artists\
                                  WHERE album_genres.genre_id=?\
                                  AND albums.compilation=0\
                                  AND artists.rowid=artist_id\
                                  AND album_genres.album_id=albums.rowid\
                                  ORDER BY artists.name COLLATE NOCASE,\
                                  albums.year,\
                                  albums.name COLLATE NOCASE", (genre_id,))
        # Get albums for artist
        elif genre_id is None:
            result = sql.execute("SELECT rowid FROM albums\
                                  WHERE artist_id=?\
                                  AND albums.compilation=0\
                                  ORDER BY year, name COLLATE NOCASE",
                                 (artist_id,))
        # Get albums for artist id and genre id
        else:
            result = sql.execute("SELECT albums.rowid\
                                  FROM albums, album_genres\
                                  WHERE artist_id=?\
                                  AND albums.compilation=0\
                                  AND album_genres.genre_id=?\
                                  AND album_genres.album_id=albums.rowid\
                                  ORDER BY year, name COLLATE NOCASE",
                                 (artist_id, genre_id))
        for row in result:
            albums += row
        return albums

    """
        Get all compilations
        @param genre id as int
        @return Array of album ids as int
    """
    def get_compilations(self, genre_id=None, sql=None):
        if not sql:
            sql = Objects.sql
        albums = []
        result = []
        # Get all compilations
        if genre_id == Navigation.ALL or genre_id is None:
            result = sql.execute(
                           "SELECT DISTINCT albums.rowid\
                            FROM albums, tracks, track_artists\
                            WHERE compilation=1\
                            AND albums.rowid = tracks.album_id\
                            AND track_artists.track_id = tracks.rowid\
                            AND track_artists.artist_id != albums.artist_id\
                            ORDER BY albums.name, albums.year")
        # Get compilation for genre id
        else:
            result = sql.execute(
                        "SELECT DISTINCT albums.rowid\
                         FROM albums, album_genres, tracks, track_artists\
                         WHERE album_genres.genre_id=?\
                         AND compilation=1\
                         AND album_genres.album_id=albums.rowid\
                         AND albums.rowid = tracks.album_id\
                         AND track_artists.track_id = tracks.rowid\
                         AND track_artists.artist_id != albums.artist_id\
                         ORDER BY albums.name,\
                         albums.year", (genre_id,))
        for row in result:
            albums += row
        return albums

    """
        Get album year based on tracks
        Use most used year by tracks
        @param album id as int
    """
    def get_year_from_tracks(self, album_id, sql=None):
        if not sql:
            sql = Objects.sql
        result = sql.execute("SELECT year, COUNT(year) AS occurrence\
                              FROM tracks\
                              WHERE tracks.album_id=?\
                              GROUP BY year\
                              ORDER BY occurrence DESC\
                              LIMIT 1", (album_id,))
        v = result.fetchone()
        if v:
            return v[0]
        return None

    """
        Search for albums looking like string
        @param string
        return: Array of (id as int, artist_id as int)
    """
    def search(self, string, sql=None):
        if not sql:
            sql = Objects.sql
        albums = []
        result = sql.execute("SELECT rowid, artist_id FROM albums\
                              WHERE name LIKE ?\
                              LIMIT 25", ('%'+string+'%',))
        for row in result:
            albums += (row,)
        return albums

    """
        Clean database for album id
        @param album id as int
        @warning commit needed
    """
    def clean(self, album_id, sql=None):
        if not sql:
            sql = Objects.sql
        result = sql.execute("SELECT rowid from tracks\
                              WHERE album_id=?\
                              LIMIT 1", (album_id,))
        v = result.fetchone()
        # Album empty, remove it
        if not v:
            sql.execute("DELETE FROM albums WHERE rowid=?", (album_id,))
            sql.execute("DELETE from album_genres\
                         WHERE album_id=?", (album_id,))
