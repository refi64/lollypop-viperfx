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

from gettext import gettext as _
import os
import itertools

from lollypop.sqlcursor import SqlCursor
from lollypop.define import Lp, Type, OrderBy
from lollypop.utils import remove_static_genres, noaccents


class AlbumsDatabase:
    """
        Albums database helper
    """

    def __init__(self):
        """
            Init albums database object
        """
        self._cached_randoms = []

    def add(self, name, artist_ids, path, popularity, mtime):
        """
            Add a new album to database
            @param Album name as string
            @param artist ids as int
            @param path as string
            @param mtime as int
            @return inserted rowid as int
            @warning: commit needed
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("INSERT INTO albums\
                                  (name, no_album_artist,\
                                  path, popularity, mtime, synced)\
                                  VALUES (?, ?, ?, ?, ?, ?)",
                                 (name, artist_ids == [],
                                  path, popularity, mtime, 0))
            for artist_id in artist_ids:
                sql.execute("INSERT INTO album_artists\
                             (album_id, artist_id)\
                             VALUES (?, ?)", (result.lastrowid, artist_id))
            return result.lastrowid

    def add_artist(self, album_id, artist_id):
        """
            Add artist to track
            @param album id as int
            @param artist id as int
            @warning: commit needed
        """
        with SqlCursor(Lp().db) as sql:
            artist_ids = self.get_artist_ids(album_id)
            if artist_id not in artist_ids:
                sql.execute("INSERT INTO "
                            "album_artists (album_id, artist_id)"
                            "VALUES (?, ?)", (album_id, artist_id))

    def add_genre(self, album_id, genre_id):
        """
            Add genre to album
            @param album id as int
            @param genre id as int
            @warning: commit needed
        """
        with SqlCursor(Lp().db) as sql:
            genres = self.get_genre_ids(album_id)
            if genre_id not in genres:
                sql.execute("INSERT INTO "
                            "album_genres (album_id, genre_id)"
                            "VALUES (?, ?)", (album_id, genre_id))

    def set_artist_ids(self, album_id, artist_ids):
        """
            Set artist id
            @param album id as int
            @param artist_ids as [int]
            @warning: commit needed
        """
        with SqlCursor(Lp().db) as sql:
            currents = self.get_artist_ids(album_id)
            if not currents or set(currents) - set(artist_ids):
                sql.execute("DELETE FROM album_artists\
                            WHERE album_id=?", (album_id,))
                for artist_id in artist_ids:
                    sql.execute("INSERT INTO album_artists\
                                (album_id, artist_id)\
                                VALUES (?, ?)", (album_id, artist_id))

    def set_synced(self, album_id, synced):
        """
            Set album synced
            @param album id as int
            @param synced as bool
            @warning: commit needed
        """
        with SqlCursor(Lp().db) as sql:
            sql.execute("UPDATE albums SET synced=? WHERE rowid=?",
                        (synced, album_id))

    def set_year(self, album_id, year):
        """
            Set year
            @param album id as int
            @param year as int
            @warning: commit needed
        """
        with SqlCursor(Lp().db) as sql:
            sql.execute("UPDATE albums SET year=? WHERE rowid=?",
                        (year, album_id))

    def set_path(self, album_id, path):
        """
            Set album path for album id
            @param Album id as int, path as string
            @warning: commit needed
        """
        with SqlCursor(Lp().db) as sql:
            sql.execute("UPDATE albums SET path=? WHERE rowid=?",
                        (path, album_id))

    def set_popularity(self, album_id, popularity, commit=False):
        """
            Set popularity
            @param album_id as int
            @param popularity as int
            @param commit as bool
        """
        with SqlCursor(Lp().db) as sql:
            try:
                sql.execute("UPDATE albums set popularity=? WHERE rowid=?",
                            (popularity, album_id))
                if commit:
                    sql.commit()
            except:  # Database is locked
                pass

    def get_synced_ids(self):
        """
            Get synced album ids
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT rowid FROM albums\
                                  WHERE synced=1")
            return list(itertools.chain(*result))

    def get_synced(self, album_id):
        """
            Get album synced status
            @param album_id as int
            @return synced as bool
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT synced FROM albums WHERE\
                                 rowid=?", (album_id,))

            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def get_mtime(self, album_id):
        """
            Get modification time
            @param album_id as int
            @return modification time as int
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT synced FROM albums WHERE\
                                 rowid=?", (album_id,))

            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def get_popularity(self, album_id):
        """
            Get popularity
            @param album_id as int
            @return popularity as int
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT popularity FROM albums WHERE\
                                 rowid=?", (album_id,))

            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def set_more_popular(self, album_id):
        """
            Increment popularity field for album id
            @param int
            @raise sqlite3.OperationalError on db update
        """
        with SqlCursor(Lp().db) as sql:
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

    def get_avg_popularity(self):
        """
            Return avarage popularity
            @return avarage popularity as int
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT AVG(popularity)\
                                  FROM (SELECT popularity\
                                        FROM albums\
                                        ORDER BY POPULARITY DESC LIMIT 100)")
            v = result.fetchone()
            if v and v[0] > 5:
                return v[0]
            return 5

    def get_non_compilation_id(self, album_name, artist_ids):
        """
            Get non compilation album id
            @param Album name as string,
            @param artist ids as [int]
            @return Album id as int
        """
        with SqlCursor(Lp().db) as sql:
            filters = (album_name,)
            filters += tuple(artist_ids)
            request = "SELECT albums.rowid FROM albums, album_artists\
                       WHERE name=? AND\
                       no_album_artist=0 AND\
                       album_artists.album_id=albums.rowid AND (1=0 "
            for artist_id in artist_ids:
                request += "OR artist_id=? "
            request += ")"
            result = sql.execute(request, filters)
            v = result.fetchone()
            if v is not None:
                return v[0]
            return None

    def get_compilation_id(self, album_name):
        """
            Get compilation id
            @param Album name as string,
            @param year as int
            @return Album id as int
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT rowid FROM albums where name=?\
                                  AND no_album_artist=1", (album_name,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return None

    def get_year_from_tracks(self, album_id):
        """
            Get album year based on tracks
            Use most used year by tracks
            @param album id as int
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT year, COUNT(year) AS occurrence\
                                  FROM tracks\
                                  WHERE tracks.album_id=?\
                                  GROUP BY year\
                                  ORDER BY occurrence DESC\
                                  LIMIT 1", (album_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return None

    def get_genre_ids(self, album_id):
        """
            Get genre ids
            @param Album id as int
            @return Genres id as [int]
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT genre_id FROM album_genres\
                                  WHERE album_id=?", (album_id,))
            return list(itertools.chain(*result))

    def get_name(self, album_id):
        """
            Get album name for album id
            @param Album id as int
            @return Album name as string
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT name FROM albums where rowid=?",
                                 (album_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]

            return _("Unknown")

    def get_artists(self, album_id):
        """
            Get artist names
            @param Album id as int
            @return artists as [str]
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT artists.name\
                                 FROM artists, album_artists\
                                 WHERE album_artists.album_id=?\
                                 AND album_artists.artist_id=artists.rowid",
                                 (album_id,))
            return list(itertools.chain(*result))

    def get_artist_ids(self, album_id):
        """
            Get album artist id
            @param album_id
            @return artist ids as [int]
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT artist_id\
                                  FROM album_artists\
                                  WHERE album_id=?",
                                 (album_id,))
            return list(itertools.chain(*result))

    def get_year(self, album_id):
        """
            Get album year
            @param album id as int
            @return album year as string
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT year FROM albums where rowid=?",
                                 (album_id,))
            v = result.fetchone()
            if v and v[0]:
                return str(v[0])
            return ""

    def get_path(self, album_id):
        """
            Get album path for album id
            @param Album id as int
            @return Album path as string
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT path FROM albums WHERE rowid=?",
                                 (album_id,))
            path = ""
            v = result.fetchone()
            if v is not None:
                path = v[0]
            if path != "" and not os.path.exists(path):
                tracks = self.get_track_ids(album_id, [], [])
                if tracks:
                    filepath = Lp().tracks.get_path(tracks[0])
                    path = os.path.dirname(filepath)
                    if os.path.exists(path):
                        sql.execute("UPDATE albums SET path=? "
                                    "WHERE rowid=?", (path, album_id))
                        sql.commit()
            return path

    def get_path_count(self, path):
        """
            Count album having path as album path
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT count(path) FROM albums WHERE path=?",
                                 (path,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 1

    def get_populars(self):
        """
            Get albums ids with popularity
            @return array of album ids as int
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT rowid FROM albums WHERE popularity!=0\
                                 ORDER BY popularity DESC LIMIT 100")
            return list(itertools.chain(*result))

    def get_recents(self):
        """
            Return recent albums
            @return array of albums ids as int
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT rowid FROM albums\
                                  ORDER BY mtime DESC LIMIT 100")
            return list(itertools.chain(*result))

    def get_randoms(self):
        """
            Return random albums
            @return array of albums ids as int
        """
        with SqlCursor(Lp().db) as sql:
            albums = []

            result = sql.execute("SELECT rowid FROM albums\
                                  ORDER BY random() LIMIT 100")
            albums = list(itertools.chain(*result))
            self._cached_randoms = list(albums)
            return albums

    def get_cached_randoms(self):
        """
            Same as above (cached result)
        """
        return self._cached_randoms

    def get_party_ids(self, genre_ids):
        """
            Get album ids for party mode based on genre ids
            @param Array of genre ids
            @return Array of album ids as int
        """
        albums = []
        # get popular first
        if Type.POPULARS in genre_ids:
            albums += self.get_populars()
        # get recents next
        if Type.RECENTS in genre_ids:
            recents = self.get_recents()
            for recent in recents:
                if recent not in albums:
                    albums.append(recent)
        for genre_id in genre_ids:
            for album in Lp().genres.get_albums(genre_id):
                if album not in albums:
                    albums.append(album)
        return albums

    def get_disc_names(self, album_id, disc):
        """
            Get disc names
            @param album id as int
            @param disc as int
            @return name as str
        """
        with SqlCursor(Lp().db) as sql:
            request = "SELECT DISTINCT discname\
                       FROM tracks\
                       WHERE tracks.album_id=?\
                       AND tracks.discnumber=?\
                       AND discname!=''"
            filters = (album_id, disc)
            result = sql.execute(request, filters)
            return list(itertools.chain(*result))

    def get_discs(self, album_id, genre_ids):
        """
            Get disc numbers
            @param album id as int
            @param genre id as int
            @return [disc as int]
        """
        genre_ids = remove_static_genres(genre_ids)
        with SqlCursor(Lp().db) as sql:
            filters = (album_id,)
            filters += tuple(genre_ids)
            request = "SELECT DISTINCT discnumber\
                       FROM tracks, track_genres\
                       WHERE tracks.album_id=?\
                       AND track_genres.track_id = tracks.rowid"
            if genre_ids:
                request += " AND ("
                for genre_id in genre_ids:
                    request += "track_genres.genre_id=? OR "
                request += "1=0)"
            request += " ORDER BY discnumber"
            result = sql.execute(request, filters)
            return list(itertools.chain(*result))

    def get_track_ids(self, album_id, genre_ids=[], artist_ids=[]):
        """
            Get tracks for album id
            @param album id as int
            @param genre ids as [int]
            @param artist_ids as [int]
            @return track ids as [int]
        """
        genre_ids = remove_static_genres(genre_ids)
        # Reset filters if not needed
        if not self.__has_genres(album_id):
            genre_ids = []
        if not self.__has_artists(album_id):
            artist_ids = []
        with SqlCursor(Lp().db) as sql:
            filters = (album_id,)
            request = "SELECT DISTINCT tracks.rowid\
                       FROM tracks"
            if genre_ids:
                request += ", track_genres"
                filters += tuple(genre_ids)
            if artist_ids:
                request += ", track_artists"
                filters += tuple(artist_ids)
            request += " WHERE album_id=? "
            if genre_ids:
                request += "AND track_genres.track_id=tracks.rowid AND ("
                for genre_id in genre_ids:
                    request += "track_genres.genre_id=? OR "
                request += "1=0)"
            if artist_ids:
                request += "AND track_artists.track_id=tracks.rowid AND ("
                for artist_id in artist_ids:
                    request += "track_artists.artist_id=? OR "
                request += "1=0)"
            request += " ORDER BY discnumber, tracknumber"
            result = sql.execute(request, filters)
            return list(itertools.chain(*result))

    def get_track_paths(self, album_id, genre_ids, artist_ids):
        """
            Get track paths for album id/disc
            Will search track from albums from same artist
            with same name and different genre
            @param album id as int
            @param genre ids as [int]
            @param artist_ids as [int]
            @return Arrays of tracks id as int
        """
        genre_ids = remove_static_genres(genre_ids)
        # Reset filters if not needed
        if not self.__has_genres(album_id):
            genre_ids = []
        if not self.__has_artists(album_id):
            artist_ids = []
        with SqlCursor(Lp().db) as sql:
            filters = (album_id,)
            request = "SELECT DISTINCT tracks.filepath\
                       FROM tracks"
            if genre_ids:
                request += ", track_genres"
                filters += tuple(genre_ids)
            if artist_ids:
                request += ", track_artists"
                filters += tuple(artist_ids)
            request += " WHERE album_id=? "
            if genre_ids:
                request += "AND track_genres.track_id = tracks.rowid AND ("
                for genre_id in genre_ids:
                    request += "track_genres.genre_id=? OR "
                request += "1=0)"
            if artist_ids:
                request += "AND track_artists.track_id=tracks.rowid AND ("
                for artist_id in artist_ids:
                    request += "track_artists.artist_id=? OR "
                request += "1=0)"
            request += " ORDER BY discnumber, tracknumber"
            result = sql.execute(request, filters)
            return list(itertools.chain(*result))

    def get_disc_tracks(self, album_id, genre_ids, artist_ids, disc):
        """
            Get tracks ids for album id disc

            @param album id as int
            @param genre ids as [int]
            @param artist ids as [int]
            @param disc as int
            @return [int]
        """
        genre_ids = remove_static_genres(genre_ids)
        # Reset filters if not needed
        if not self.__has_genres(album_id):
            genre_ids = []
        if not self.__has_artists(album_id):
            artist_ids = []
        with SqlCursor(Lp().db) as sql:
            filters = (album_id, disc)
            request = "SELECT DISTINCT tracks.rowid\
                       FROM tracks"
            if genre_ids:
                request += ", track_genres"
                filters += tuple(genre_ids)
            if artist_ids:
                request += ", track_artists"
                filters += tuple(artist_ids)
            request += " WHERE album_id=?\
                       AND discnumber=?"
            if genre_ids:
                request += " AND track_genres.track_id = tracks.rowid AND ("
                for genre_id in genre_ids:
                    request += "track_genres.genre_id=? OR "
                request += "1=0)"
            if artist_ids:
                request += " AND track_artists.track_id=tracks.rowid AND ("
                for artist_id in artist_ids:
                    request += "track_artists.artist_id=? OR "
                request += "1=0)"
            request += " ORDER BY discnumber, tracknumber"
            result = sql.execute(request, filters)
            return list(itertools.chain(*result))

    def get_ids(self, artist_ids=[], genre_ids=[]):
        """
            Get albums ids
            @param artist ids as [int]
            @param genre ids as [int]
            @return Array of album ids as int
        """
        genre_ids = remove_static_genres(genre_ids)
        orderby = Lp().settings.get_enum('orderby')
        if orderby == OrderBy.ARTIST:
            order = "ORDER BY artists.sortname\
                     COLLATE NOCASE COLLATE LOCALIZED,\
                     albums.year,\
                     albums.name\
                     COLLATE NOCASE COLLATE LOCALIZED"
        elif orderby == OrderBy.NAME:
            order = "ORDER BY albums.name\
                     COLLATE NOCASE COLLATE LOCALIZED"
        elif orderby == OrderBy.YEAR:
            order = "ORDER BY albums.year,\
                     albums.name\
                     COLLATE NOCASE COLLATE LOCALIZED"
        else:
            order = "ORDER BY albums.popularity DESC,\
                     albums.name\
                     COLLATE NOCASE COLLATE LOCALIZED"

        with SqlCursor(Lp().db) as sql:
            result = []
            # Get albums for all artists
            if not artist_ids and not genre_ids:
                result = sql.execute(
                                 "SELECT DISTINCT albums.rowid\
                                  FROM albums, artists, album_artists\
                                  WHERE artists.rowid=album_artists.artist_id\
                                  AND albums.rowid=album_artists.album_id\
                                  %s" % order)
            # Get albums for genre
            elif not artist_ids:
                genres = tuple(genre_ids)
                request = "SELECT DISTINCT albums.rowid FROM albums,\
                           album_genres, artists, album_artists\
                           WHERE artists.rowid=album_artists.artist_id\
                           AND albums.rowid=album_artists.album_id\
                           AND album_genres.album_id=albums.rowid AND ("
                for genre_id in genre_ids:
                    request += "album_genres.genre_id=? OR "
                request += "1=0) %s" % order
                result = sql.execute(request, genres)
            # Get albums for artist
            elif not genre_ids:
                artists = tuple(artist_ids)
                request = "SELECT DISTINCT albums.rowid\
                           FROM albums, artists, album_artists WHERE\
                           artists.rowid=album_artists.artist_id AND\
                           album_artists.album_id=albums.rowid AND ("
                for artist_id in artist_ids:
                    request += "album_artists.artist_id=? OR "
                request += "1=0) %s" % order
                result = sql.execute(request, artists)
            # Get albums for artist id and genre id
            else:
                filters = tuple(artist_ids)
                filters += tuple(genre_ids)
                request = "SELECT DISTINCT albums.rowid\
                           FROM albums, album_genres, artists, album_artists\
                           WHERE album_genres.album_id=albums.rowid AND\
                           artists.rowid=album_artists.artist_id AND\
                           album_artists.album_id=albums.rowid AND ("
                for artist_id in artist_ids:
                    request += "album_artists.artist_id=? OR "
                request += "1=0) AND ("
                for genre_id in genre_ids:
                    request += "album_genres.genre_id=? OR "
                request += "1=0) %s" % order
                result = sql.execute(request, filters)
            return list(itertools.chain(*result))

    def get_compilation_ids(self, genre_ids=[]):
        """
            Get all compilations
            @param Filter genre ids as [int]
            @return Array of album ids as int
        """
        with SqlCursor(Lp().db) as sql:
            result = []
            # Get all compilations
            if not genre_ids or genre_ids[0] == Type.ALL:
                result = sql.execute("SELECT DISTINCT albums.rowid\
                                      FROM albums, album_artists\
                                      WHERE album_artists.artist_id=?\
                                      AND album_artists.album_id=albums.rowid\
                                      ORDER BY albums.name, albums.year",
                                     (Type.COMPILATIONS,))
            # Get compilation for genre id
            else:
                filters = (Type.COMPILATIONS,)
                filters += tuple(genre_ids)
                request = "SELECT DISTINCT albums.rowid\
                           FROM albums, album_genres, album_artists\
                           WHERE album_genres.album_id=albums.rowid\
                           AND album_artists.album_id=albums.rowid\
                           AND album_artists.artist_id=? AND ( "
                for genre_id in genre_ids:
                    request += "album_genres.genre_id=? OR "
                request += "1==0) ORDER BY albums.name,albums.year"
                result = sql.execute(request, filters)
            return list(itertools.chain(*result))

    def get_duration(self, album_id, genre_ids):
        """
            Album duration in seconds
            @param album id as int
            @param genre ids as [int]
            @return album duration as int
        """
        with SqlCursor(Lp().db) as sql:
            if genre_ids and genre_ids[0] > 0:
                filters = (album_id,)
                filters += tuple(genre_ids)
                request = "SELECT SUM(duration)\
                           FROM tracks, track_genres\
                           WHERE tracks.album_id=?\
                           AND track_genres.track_id = tracks.rowid AND ("
                for genre_id in genre_ids:
                    request += "track_genres.genre_id=? OR "
                request += "1=0)"
                result = sql.execute(request, filters)
            else:
                result = sql.execute("SELECT SUM(duration) FROM tracks\
                                      WHERE album_id=?", (album_id,))
            v = result.fetchone()
            if v and v[0] is not None:
                return v[0]
            return 0

    def search(self, string):
        """
            Search for albums looking like string
            @param search as str
            @return album ids as [int]
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT albums.rowid\
                                  FROM albums\
                                  WHERE noaccents(name) LIKE ?\
                                  LIMIT 25", ('%' + noaccents(string) + '%',))
            return list(itertools.chain(*result))

    def calculate_artist_ids(self, album_id):
        """
            Calculate artist ids based on tracks
            @WARNING Be sure album already have a track
            @param album id as int
            @return artist_ids as [int]
        """
        try:
            ret = []
            for track_id in self.get_track_ids(album_id, [], []):
                artist_ids = Lp().tracks.get_artist_ids(track_id)
                # Check if previous track and
                # track do not have same artists
                if ret:
                    if not set(ret) & set(artist_ids):
                        return [Type.COMPILATIONS]
                ret = artist_ids
        except Exception as e:
            print("AlbumsDatabase::calculate_artist_ids()", e)
        return ret

    def count(self):
        """
            Count albums
            @return int
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT COUNT(1) from albums")
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def clean(self, album_id):
        """
            Clean database for album id
            @param album id as int
            @param return True if album deleted or genre modified
            @warning commit needed
        """
        with SqlCursor(Lp().db) as sql:
            ret = False
            # Check album really have tracks from its genres
            for genre_id in self.get_genre_ids(album_id):
                result = sql.execute("SELECT track_id\
                                      FROM tracks, track_genres\
                                      WHERE track_genres.track_id ==\
                                      tracks.rowid\
                                      AND tracks.album_id=?\
                                      AND track_genres.genre_id=?",
                                     (album_id, genre_id))
                v = result.fetchone()
                if not v:
                    ret = True
                    sql.execute("DELETE from album_genres\
                                 WHERE album_id=?\
                                 AND genre_id=?", (album_id, genre_id))

            # Remove album if orphaned
            result = sql.execute("SELECT rowid from tracks\
                                  WHERE album_id=?\
                                  LIMIT 1", (album_id,))
            v = result.fetchone()
            # Album empty, remove it
            if not v:
                ret = True
                sql.execute("DELETE FROM album_artists\
                            WHERE album_id=?",
                            (album_id,))
                sql.execute("DELETE FROM albums WHERE rowid=?", (album_id,))
            return ret

#######################
# PRIVATE             #
#######################
    def __has_genres(self, album_id):
        """
            Return True if album has more than one genre
            @param album id as int
            @return bool
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT COUNT(*)\
                                 FROM album_genres\
                                 WHERE album_id=?\
                                 LIMIT 2", (album_id,))
            v = result.fetchone()
            if v is not None:
                return v[0] > 1
        return False

    def __has_artists(self, album_id):
        """
            Return True if album has more than one artist
            @param album id as int
            @return bool
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT COUNT(*)\
                                 FROM album_artists\
                                 WHERE album_id=?\
                                 LIMIT 2", (album_id,))
            v = result.fetchone()
            if v is not None:
                return v[0] > 1
        return False
