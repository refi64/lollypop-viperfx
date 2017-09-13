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
from lollypop.define import Lp
from lollypop.utils import noaccents


class TracksDatabase:
    """
        All functions take a sqlite cursor as last parameter,
        set another one if you"re in a thread
    """

    def __init__(self):
        """
            Init tracks database object
        """
        pass

    def add(self, name, uri, duration, tracknumber, discnumber,
            discname, album_id, year, popularity, rate, ltime, mtime):
        """
            Add a new track to database
            @param name as string
            @param uri as string,
            @param duration as int
            @param tracknumber as int
            @param discnumber as int
            @param discname as str
            @param album_id as int
            @param genre_id as int
            @param year as int
            @param popularity as int
            @param rate as int
            @param ltime as int
            @param mtime as int
            @return inserted rowid as int
            @warning: commit needed
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute(
                "INSERT INTO tracks (name, uri, duration, tracknumber,\
                discnumber, discname, album_id,\
                year, popularity, rate, ltime, mtime) VALUES\
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (
                                                        name,
                                                        uri,
                                                        duration,
                                                        tracknumber,
                                                        discnumber,
                                                        discname,
                                                        album_id,
                                                        year,
                                                        popularity,
                                                        rate,
                                                        ltime,
                                                        mtime))
            return result.lastrowid

    def add_artist(self, track_id, artist_id):
        """
            Add artist to track
            @param track id as int
            @param artist id as int
            @warning: commit needed
        """
        with SqlCursor(Lp().db) as sql:
            artists = self.get_artist_ids(track_id)
            if artist_id not in artists:
                sql.execute("INSERT INTO "
                            "track_artists (track_id, artist_id)"
                            "VALUES (?, ?)", (track_id, artist_id))

    def add_genre(self, track_id, genre_id):
        """
            Add genre to track
            @param track id as int
            @param genre id as int
            @warning: commit needed
        """
        with SqlCursor(Lp().db) as sql:
            genres = self.get_genre_ids(track_id)
            if genre_id not in genres:
                sql.execute("INSERT INTO\
                             track_genres (track_id, genre_id)\
                             VALUES (?, ?)",
                            (track_id, genre_id))

    def get_ids(self):
        """
            Return all internal track ids
            @return track ids as [int]
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT rowid FROM tracks")
            return list(itertools.chain(*result))

    def get_ids_for_name(self, name):
        """
            Return tracks ids with name
            @param name as str
            @return track id as [int]
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT rowid\
                                  FROM tracks WHERE name=?\
                                  COLLATE NOCASE COLLATE LOCALIZED",
                                 (name,))
            return list(itertools.chain(*result))

    def get_id_by_uri(self, uri):
        """
            Return track id for uri
            @param uri as str
            @return track id as int
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT rowid FROM tracks WHERE uri=?",
                                 (uri,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return None

    def get_id_by(self, name, album_id, artist_ids):
        """
            Return track id for uri
            @param name as str
            @param album id as int
            @return track id as int
        """
        with SqlCursor(Lp().db) as sql:
            filters = (name, album_id) + tuple(artist_ids)
            request = "SELECT tracks.rowid FROM tracks\
                       WHERE name = ? COLLATE NOCASE\
                       AND album_id = ?\
                       AND EXISTS (\
                            SELECT rowid\
                            FROM track_artists\
                            WHERE track_artists.track_id=tracks.rowid\
                            AND ("
            for artist_id in artist_ids:
                request += " track_artists.artist_id=? OR"
            request += " 1=0))"
            result = sql.execute(request, filters)
            v = result.fetchone()
            if v is not None:
                return v[0]
            return None

    def get_name(self, track_id):
        """
            Get track name for track id
            @param Track id as int
            @return Name as string
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT name FROM tracks WHERE rowid=?",
                                 (track_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return ""

    def get_year(self, track_id):
        """
            Get track year
            @param track id as int
            @return track year as string
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT year FROM tracks WHERE rowid=?",
                                 (track_id,))
            v = result.fetchone()
            if v and v[0]:
                return str(v[0])
            return ""

    def get_rate(self, track_id):
        """
            Get track rate
            @param track id as int
            @return rate as int
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT rate FROM tracks WHERE rowid=?",
                                 (track_id,))
            v = result.fetchone()
            if v:
                return v[0]
            return 0

    def get_uri(self, track_id):
        """
            Get track uri for track id
            @param Track id as int
            @return uri as string
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT uri FROM tracks WHERE rowid=?",
                                 (track_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return ""

    def set_uri(self, track_id, uri):
        """
            Set track uri, reset duration if web uri
            @param Track id as int
            @param uri as string
        """
        with SqlCursor(Lp().db) as sql:
            sql.execute("UPDATE tracks SET uri=?\
                         WHERE rowid=?",
                        (uri, track_id))
            sql.commit()
            if uri.startswith("http") or uri.startswith("https"):
                self.set_duration(track_id, 0)

    def set_rate(self, track_id, rate):
        """
            Set track rate
            @param Track id as int
            @param rate as int
        """
        with SqlCursor(Lp().db) as sql:
            sql.execute("UPDATE tracks SET rate=?\
                         WHERE rowid=?",
                        (rate, track_id))
            sql.commit()

    def get_album_id(self, track_id):
        """
            Get album id for track id
            @param track id as int
            @return album id as int
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT album_id FROM tracks WHERE rowid=?",
                                 (track_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return -1

    def get_album_name(self, track_id):
        """
            Get album name for track id
            @param track id as int
            @return album name as str
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT albums.name from albums,tracks\
                                  WHERE tracks.rowid=? AND\
                                  tracks.album_id=albums.rowid", (track_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return _("Unknown")

    def get_artist_ids(self, track_id):
        """
            Get artist ids
            @param track id as int
            @return artist ids as [int]
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT artist_id FROM track_artists\
                                  WHERE track_id=?", (track_id,))
            return list(itertools.chain(*result))

    def get_artists(self, track_id):
        """
            Get artist names
            @param track id as int
            @return artists as [str]
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT name FROM artists, track_artists\
                                  WHERE track_artists.track_id=?\
                                  AND track_artists.artist_id=artists.rowid",
                                 (track_id,))
            return list(itertools.chain(*result))

    def get_genre_ids(self, track_id):
        """
            Get genre ids
            @param track id as int
            @return genre ids as [int]
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT genre_id FROM track_genres\
                                  WHERE track_id=?", (track_id,))
            return list(itertools.chain(*result))

    def get_genres(self, track_id):
        """
            Get genres
            @param track id as int
            @return [str]
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT name FROM genres, track_genres\
                                  WHERE track_genres.track_id=?\
                                  AND track_genres.genre_id=genres.rowid",
                                 (track_id,))
            return list(itertools.chain(*result))

    def get_mtimes(self):
        """
            Get mtime for tracks
            WARNING: Should be called before anything is shown on screen
            @param None
            @return dict of {uri as string: mtime as int}
        """
        with SqlCursor(Lp().db) as sql:
            mtimes = {}
            result = sql.execute("SELECT DISTINCT uri, mtime\
                                  FROM tracks")
            for row in result:
                mtimes.update((row,))
            return mtimes

    def get_uris(self, exclude=[]):
        """
            Get all tracks uri
            @param exclude as [str]
            @return Array of uri as string
        """
        with SqlCursor(Lp().db) as sql:
            filters = ()
            for e in exclude:
                filters += ("%" + e + "%",)
            request = "SELECT uri FROM tracks\
                       WHERE 1=1"
            for e in exclude:
                request += " AND uri not like ?"
            result = sql.execute(request, filters)
            return list(itertools.chain(*result))

    def get_number(self, track_id):
        """
            Get track position in album
            @param track id as int
            @return position as int
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT tracknumber FROM tracks\
                                  WHERE rowid=?", (track_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def get_duration(self, track_id):
        """
            Get track duration for track id
            @param Track id as int
            @return duration as int
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT duration FROM tracks\
                                  WHERE rowid=?", (track_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def set_duration(self, track_id, duration):
        """
            Get track duration for track id
            @param Track id as int
            @param duration as int
        """
        with SqlCursor(Lp().db) as sql:
            sql.execute("UPDATE tracks\
                         SET duration=?\
                         WHERE rowid=?", (duration, track_id,))
            sql.commit()

    def is_empty(self):
        """
            Return True if no tracks in db
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT COUNT(1) FROM tracks  LIMIT 1")
            v = result.fetchone()
            if v is not None:
                return v[0] == 0
            return True

    def get_as_non_album_artist(self, artist_id):
        """
            Get tracks for artist_id where artist_id isn"t main artist
            @param artist id as int
            @return list of [tracks id as int, track name as string]
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT tracks.rowid, tracks.name\
                                 FROM tracks, track_artists, album_artists\
                                 WHERE album_artists.album_id=tracks.album_id\
                                 AND track_artists.artist_id=?\
                                 AND track_artists.track_id=tracks.rowid\
                                 AND NOT EXISTS (\
                                  SELECT artist_id\
                                  FROM album_artists\
                                  WHERE artist_id=track_artists.artist_id\
                                  AND album_id=tracks.album_id)",
                                 (artist_id,))
            return list(result)

    def get_rated(self, limit=100):
        """
            Return tracks with rate >= 4
            @param limit as int
            @return tracks as [int]
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT rowid FROM tracks\
                                  WHERE rate >= 4\
                                  ORDER BY popularity DESC LIMIT ?",
                                 (limit,))
            return list(itertools.chain(*result))

    def get_populars(self, limit=100):
        """
            Return populars tracks
            @param limit as int
            @return tracks as [int]
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT rowid FROM tracks\
                                  WHERE popularity!=0\
                                  ORDER BY popularity DESC LIMIT ?",
                                 (limit,))
            return list(itertools.chain(*result))

    def get_avg_popularity(self):
        """
            Return avarage popularity
            @return avarage popularity as int
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT AVG(popularity)\
                                  FROM (SELECT popularity\
                                        FROM tracks\
                                        ORDER BY POPULARITY DESC LIMIT 100)")
            v = result.fetchone()
            if v and v[0] > 5:
                return v[0]
            return 5

    def set_more_popular(self, track_id):
        """
            Increment popularity field
            @param track id as int
            @raise sqlite3.OperationalError on db update
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT popularity from tracks WHERE rowid=?",
                                 (track_id,))
            pop = result.fetchone()
            if pop:
                current = pop[0]
            else:
                current = 0
            current += 1
            sql.execute("UPDATE tracks set popularity=? WHERE rowid=?",
                        (current, track_id))
            sql.commit()

    def set_listened_at(self, track_id, time):
        """
            Set ltime for track
            @param track id as int
            @param time as int
        """
        with SqlCursor(Lp().db) as sql:
            sql.execute("UPDATE tracks set ltime=? WHERE rowid=?",
                        (time, track_id))
            sql.commit()

    def get_never_listened_to(self):
        """
            Return random tracks never listened to
            @return tracks as [int]
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT tracks.rowid\
                                  FROM tracks\
                                  WHERE ltime=0\
                                  ORDER BY random() LIMIT 100")
            return list(itertools.chain(*result))

    def get_recently_listened_to(self):
        """
            Return tracks listened recently
            @return tracks as [int]
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT tracks.rowid\
                                  FROM tracks\
                                  WHERE ltime!=0\
                                  ORDER BY ltime DESC LIMIT 100")
            return list(itertools.chain(*result))

    def get_persistent(self, track_id):
        """
            Return track persistent
            @param track id as int
            @return int
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT rowid FROM tracks\
                                  WHERE persistent=?", (track_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def set_persistent(self, track_id, persistent):
        """
            Set track persistent
            @param track id as int
            @param persistent as int
        """
        with SqlCursor(Lp().db) as sql:
            sql.execute("UPDATE tracks\
                         SET persistent=?\
                         WHERE rowid=?", (persistent, track_id,))
            sql.commit()

    def get_randoms(self):
        """
            Return random tracks
            @return array of track ids as int
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT tracks.rowid\
                                  FROM tracks\
                                  ORDER BY random() LIMIT 100")
            return list(itertools.chain(*result))

    def set_popularity(self, track_id, popularity, commit=False):
        """
            Set popularity
            @param track id as int
            @param popularity as int
            @warning: commit needed
        """
        with SqlCursor(Lp().db) as sql:
            try:
                sql.execute("UPDATE tracks set popularity=? WHERE rowid=?",
                            (popularity, track_id))
                if commit:
                    sql.commit()
            except:  # Database is locked
                pass

    def get_popularity(self, track_id):
        """ème a déjà été remonté en début de semaine et semble ancien.
Nous traitons le problème dès que possible (salle très occupée).

            Get popularity
            @param track id  as int
            @return popularity as int
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT popularity FROM tracks WHERE\
                                 rowid=?", (track_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def get_ltime(self, track_id):
        """
            Get listen time
            @param track id  as int
            @return listen time as int
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT ltime FROM tracks WHERE\
                                 rowid=?", (track_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def get_mtime(self, track_id, genre_ids=[]):
        """
            Get modification time, if genre_ids empty, only local tracks
            @param track_id as int
            @param genre_ids as [int]
            @return modification time as int
        """
        with SqlCursor(Lp().db) as sql:
            filters = tuple([track_id] + genre_ids)
            request = "SELECT mtime FROM track_genres\
                       WHERE track_id=?"
            for genre_id in genre_ids:
                request += " AND genre_id=?"
            result = sql.execute(request, filters)
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def count(self):
        """
            Count albums
            @return int
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT COUNT(1) FROM tracks")
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def clean(self, track_id):
        """
            Clean database for track id
            @param track_id as int
            @warning commit needed
        """
        with SqlCursor(Lp().db) as sql:
            sql.execute("DELETE FROM track_artists\
                         WHERE track_id = ?", (track_id,))
            sql.execute("DELETE FROM track_genres\
                         WHERE track_id = ?", (track_id,))

    def search(self, searched):
        """
            Search for tracks looking like searched
            @param searched as string
            return: list of [id as int, name as string]
        """
        with SqlCursor(Lp().db) as sql:
            result = sql.execute("SELECT tracks.rowid, tracks.name\
                                  FROM tracks\
                                  WHERE noaccents(name) LIKE ? LIMIT 25",
                                 ("%" + noaccents(searched) + "%",))
            return list(result)

    def search_track(self, artist, title):
        """
            Get track id for artist and title
            @param artist as string
            @param title as string
            @param sql as sqlite cursor
            @return track id as int
            @thread safe
        """
        track_ids = self.get_ids_for_name(title)
        for track_id in track_ids:
            album_id = Lp().tracks.get_album_id(track_id)
            artist_ids = set(Lp().albums.get_artist_ids(album_id)) &\
                set(Lp().tracks.get_artist_ids(track_id))
            for artist_id in artist_ids:
                if artist == Lp().artists.get_name(artist_id):
                    return track_id
            if ", ".join(Lp().tracks.get_artists(track_id)) == artist:
                return track_id
        return None

    def remove(self, track_id):
        """
            Remove track
            @param track id as int
        """
        with SqlCursor(Lp().db) as sql:
            sql.execute("DELETE FROM track_genres\
                         WHERE track_id=?", (track_id,))
            sql.execute("DELETE FROM track_artists\
                         WHERE track_id=?", (track_id,))
            sql.execute("DELETE FROM tracks\
                         WHERE rowid=?", (track_id,))
