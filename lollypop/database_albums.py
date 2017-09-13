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
        self.__max_count = 1
        self._cached_randoms = []

    def add(self, name, artist_ids, uri, loved, popularity, rate, mtime):
        """
            Add a new album to database
            @param Album name as string
            @param artist ids as int
            @param uri as string
            @param loved as bool
            @param popularity as int
            @param rate as int
            @param mtime as int
            @return inserted rowid as int
            @warning: commit needed
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("INSERT INTO albums\
                                  (name, no_album_artist,\
                                  uri, loved, popularity, rate, mtime, synced)\
                                  VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                 (name, artist_ids == [],
                                  uri, loved, popularity, rate, mtime, 0))
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
                sql.execute("INSERT INTO\
                             album_genres (album_id, genre_id)\
                             VALUES (?, ?)",
                            (album_id, genre_id))

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
            @param synced as int
            @warning: commit needed
        """
        with SqlCursor(Lp().db) as sql:
            sql.execute("UPDATE albums SET synced=? WHERE rowid=?",
                        (synced, album_id))

    def set_loved(self, album_id, loved):
        """
            Set album loved
            @param album id as int
            @param loved as int
            @warning: commit needed
        """
        with SqlCursor(Lp().db) as sql:
            sql.execute("UPDATE albums SET loved=? WHERE rowid=?",
                        (loved, album_id))
            sql.commit()

    def set_rate(self, album_id, rate):
        """
            Set album rate
            @param rate as int
        """
        with SqlCursor(Lp().db) as sql:
            sql.execute("UPDATE albums SET rate=? WHERE rowid=?",
                        (rate, album_id))
            sql.commit()

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

    def set_uri(self, album_id, uri):
        """
            Set album uri for album id
            @param Album id as int, uri as string
            @warning: commit needed
        """
        with SqlCursor(Lp().db) as sql:
            sql.execute("UPDATE albums SET uri=? WHERE rowid=?",
                        (uri, album_id))

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
            request = "SELECT DISTINCT albums.rowid\
                       FROM albums, artists, album_artists\
                       WHERE album_artists.album_id = albums.rowid\
                       AND (album_artists.artist_id = artists.rowid\
                            OR album_artists.artist_id=?)\
                       AND synced=1"
            order = " ORDER BY artists.sortname\
                     COLLATE NOCASE COLLATE LOCALIZED,\
                     albums.year,\
                     albums.name\
                     COLLATE NOCASE COLLATE LOCALIZED"
            filters = (Type.COMPILATIONS,)
            result = sql.execute(request + order, filters)
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

    def get_loved(self, album_id):
        """
            Get album loved
            @param album id as int
            @return loved as bool
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT loved FROM albums WHERE\
                                 rowid=?", (album_id,))

            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def get_by_year(self, year):
        """
            Get albums with year
            @param year as str
        """
        with SqlCursor(Lp().db) as sql:
            filters = (year, )
            request = "SELECT DISTINCT albums.rowid\
                       FROM albums\
                       WHERE year=?"
            result = sql.execute(request, filters)
            return list(itertools.chain(*result))

    def get_rate(self, album_id):
        """
            Get album rate
            @param album id as int
            @return rate as int
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT rate FROM albums WHERE\
                                 rowid=?", (album_id,))

            v = result.fetchone()
            if v:
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

    def set_more_popular(self, album_id, pop_to_add):
        """
            Increment popularity field for album id
            @param album id as int
            @param pop as int
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
            current += pop_to_add
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

    def get_id(self, album_name, artist_ids):
        """
            Get non compilation album id
            @param Album name as string,
            @param artist ids as [int]
            @return Album id as int
        """
        with SqlCursor(Lp().db) as sql:
            filters = (album_name,)
            if artist_ids:
                filters += tuple(artist_ids)
                request = "SELECT albums.rowid FROM albums, album_artists\
                           WHERE name=? COLLATE NOCASE AND\
                           no_album_artist=0 AND\
                           album_artists.album_id=albums.rowid AND (1=0 "
                for artist_id in artist_ids:
                    request += "OR artist_id=? "
                request += ")"
            else:
                request = "SELECT rowid FROM albums\
                           WHERE name=?\
                           AND no_album_artist=1"
            result = sql.execute(request, filters)
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

    def get_uri(self, album_id):
        """
            Get album uri for album id
            @param Album id as int
            @return Album uri as string
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT uri FROM albums WHERE rowid=?",
                                 (album_id,))
            uri = ""
            v = result.fetchone()
            if v is not None:
                uri = v[0]
            return uri

    def get_uri_count(self, uri):
        """
            Count album having uri as album uri
            @param uri as str
            @return count as int
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT COUNT(uri) FROM albums WHERE uri=?",
                                 (uri,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 1

    def get_tracks_count(self, album_id):
        """
            Return tracks count
            @param album id as int
            @return count as int
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT COUNT(tracks.rowid)\
                                  FROM tracks WHERE album_id=?",
                                 (album_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 1

    def get_rated(self, limit=100):
        """
            Get albums with user rating >= 4
            @param limit as int
            @return array of album ids as int
        """
        with SqlCursor(Lp().db) as sql:
            request = "SELECT DISTINCT albums.rowid\
                       FROM albums\
                       WHERE rate>=4\
                       ORDER BY popularity DESC LIMIT ?"
            result = sql.execute(request, (limit,))
            return list(itertools.chain(*result))

    def get_populars(self, limit=100):
        """
            Get albums ids with popularity
            @param limit as int
            @return array of album ids as int
        """
        with SqlCursor(Lp().db) as sql:
            request = "SELECT DISTINCT albums.rowid\
                       FROM albums\
                       WHERE popularity!=0\
                       ORDER BY popularity DESC LIMIT ?"
            result = sql.execute(request, (limit,))
            return list(itertools.chain(*result))

    def get_loves(self):
        """
            Get albums ids with popularity
            @return array of album ids as int
        """
        with SqlCursor(Lp().db) as sql:
            request = "SELECT DISTINCT albums.rowid\
                       FROM albums\
                       WHERE loved=1\
                       ORDER BY popularity DESC"
            result = sql.execute(request)
            return list(itertools.chain(*result))

    def get_recents(self):
        """
            Return recent albums
            @return array of albums ids as int
        """
        with SqlCursor(Lp().db) as sql:
            request = "SELECT DISTINCT albums.rowid\
                       FROM albums\
                       ORDER BY mtime DESC LIMIT 100"
            result = sql.execute(request)
            return list(itertools.chain(*result))

    def get_randoms(self):
        """
            Return random albums
            @return array of albums ids as int
        """
        with SqlCursor(Lp().db) as sql:
            albums = []
            request = "SELECT DISTINCT albums.rowid\
                       FROM albums ORDER BY random() LIMIT 100"
            result = sql.execute(request)
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

    def get_track_uris(self, album_id, genre_ids, artist_ids):
        """
            Get track uris for album id/disc
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
            request = "SELECT DISTINCT tracks.uri\
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
            request += " ORDER BY discnumber, tracknumber, tracks.name"
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
            request += " ORDER BY discnumber, tracknumber, tracks.name"
            result = sql.execute(request, filters)
            return list(itertools.chain(*result))

    def get_id_by_uri(self, uri):
        """
            Get album id for uri
            @param uri as str
            @return id as int
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT rowid\
                                  FROM albums\
                                  WHERE uri=?",
                                 (uri,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def get_ids(self, artist_ids=[], genre_ids=[]):
        """
            Get albums ids
            @param artist ids as [int]
            @param genre ids as [int]
            @return albums ids as [int]
        """
        genre_ids = remove_static_genres(genre_ids)
        orderby = Lp().settings.get_enum("orderby")
        if orderby == OrderBy.ARTIST:
            order = " ORDER BY artists.sortname\
                     COLLATE NOCASE COLLATE LOCALIZED,\
                     albums.year,\
                     albums.name\
                     COLLATE NOCASE COLLATE LOCALIZED"
        elif orderby == OrderBy.NAME:
            order = " ORDER BY albums.name\
                     COLLATE NOCASE COLLATE LOCALIZED"
        elif orderby == OrderBy.YEAR:
            order = " ORDER BY albums.year,\
                     albums.name\
                     COLLATE NOCASE COLLATE LOCALIZED"
        else:
            order = " ORDER BY albums.popularity DESC,\
                     albums.name\
                     COLLATE NOCASE COLLATE LOCALIZED"

        with SqlCursor(Lp().db) as sql:
            result = []
            # Get albums for all artists
            if not artist_ids and not genre_ids:
                request = "SELECT DISTINCT albums.rowid\
                           FROM albums, album_artists, artists\
                           WHERE albums.rowid = album_artists.album_id AND\
                           artists.rowid = album_artists.artist_id"
                request += order
                result = sql.execute(request)
            # Get albums for genres
            elif not artist_ids:
                filters = tuple(genre_ids)
                request = "SELECT DISTINCT albums.rowid FROM albums,\
                           album_genres, album_artists, artists\
                           WHERE albums.rowid = album_artists.album_id AND\
                           artists.rowid = album_artists.artist_id AND\
                           album_genres.album_id=albums.rowid AND ( "
                for genre_id in genre_ids:
                    request += "album_genres.genre_id=? OR "
                request += "1=0)"
                request += order
                result = sql.execute(request, filters)
            # Get albums for artist
            elif not genre_ids:
                filters = tuple(artist_ids)
                request = "SELECT DISTINCT albums.rowid\
                           FROM albums, album_artists, artists\
                           WHERE album_artists.album_id=albums.rowid AND\
                           artists.rowid = album_artists.artist_id AND ("
                for artist_id in artist_ids:
                    request += "artists.rowid=? OR "
                request += "1=0)"
                request += order
                result = sql.execute(request, filters)
            # Get albums for artist id and genre id
            else:
                filters = tuple(artist_ids)
                filters += tuple(genre_ids)
                request = "SELECT DISTINCT albums.rowid\
                           FROM albums, album_genres, album_artists, artists\
                           WHERE album_genres.album_id=albums.rowid AND\
                           artists.rowid = album_artists.artist_id AND\
                           album_artists.album_id=albums.rowid AND ("
                for artist_id in artist_ids:
                    request += "artists.rowid=? OR "
                request += "1=0) AND ("
                for genre_id in genre_ids:
                    request += "album_genres.genre_id=? OR "
                request += "1=0)"
                request += order
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

    def get_genres(self, album_id):
        """
            Return genres for album
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT genres.name\
                                  FROM albums, album_genres, genres\
                                  WHERE albums.rowid = ?\
                                  AND album_genres.album_id = albums.rowid\
                                  AND album_genres.genre_id = genres.rowid",
                                 (album_id,))
            return list(itertools.chain(*result))

    def has_loves(self):
        """
            True if db has loved albums
            @return bool
        """
        with SqlCursor(Lp().db) as sql:
            filters = ()
            request = "SELECT albums.rowid\
                       FROM albums\
                       WHERE loved=1"
            request += " LIMIT 1"
            result = sql.execute(request, filters)
            return list(itertools.chain(*result)) != []

    def search(self, string, limit=25):
        """
            Search for albums looking like string
            @param search as str
            @param limit as int/None
            @return album ids as [int]
        """
        with SqlCursor(Lp().db) as sql:
            if limit is None:
                filters = ("%" + noaccents(string) + "%")
            else:
                filters = ("%" + noaccents(string) + "%", limit)
            request = ("SELECT albums.rowid\
                       FROM albums\
                       WHERE noaccents(name) LIKE ?")
            if limit is not None:
                request += " LIMIT ?"
            result = sql.execute(request, filters)
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
            result = sql.execute("SELECT COUNT(1) FROM albums")
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

    @property
    def max_count(self):
        """
            Get MAX(COUNT(tracks)) for albums
        """
        return self.__max_count

    def update_max_count(self):
        """
            Update MAX(COUNT(tracks)) for albums
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT MAX(num_tracks)\
                                  FROM (SELECT COUNT(t.rowid)\
                                  AS num_tracks FROM albums\
                                  INNER JOIN tracks t\
                                  ON albums.rowid=t.album_id\
                                  GROUP BY albums.rowid)")
            v = result.fetchone()
            if v:
                self.__max_count = v[0]

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
