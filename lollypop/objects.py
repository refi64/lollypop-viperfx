# Copyright (c) 2014-2017 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# Copyright (c) 2015 Jean-Philippe Braun <eon@patapon.info>
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

from lollypop.radios import Radios
from lollypop.define import Lp, Type
from lollypop.sqlcursor import SqlCursor


class Base:
    """
        Base for album and track objects
    """
    def __init__(self, db):
        self.db = db

    def __dir__(self, *args, **kwargs):
        """
            Concatenate base class"s fields with child class"s fields
        """
        return super(Base, self).__dir__(*args, **kwargs) + self.FIELDS

    def __getattr__(self, attr):
        # Lazy DB calls of attributes referenced
        # in self.FIELDS
        if attr in self.FIELDS:
            if self.id is None or self.id < 0:
                return self.DEFAULTS[self.FIELDS.index(attr)]
            # Actual value of "attr_name" is stored in "_attr_name"
            attr_name = "_" + attr
            attr_value = getattr(self, attr_name)
            if attr_value is None:
                attr_value = getattr(self.db, "get_" + attr)(self.id)
                setattr(self, attr_name, attr_value)
            # Return default value if None
            if attr_value is None:
                return self.DEFAULTS[self.FIELDS.index(attr)]
            else:
                return attr_value

    def get_popularity(self):
        """
            Get popularity
            @return int between 0 and 5
        """
        if self.id is None or self.id == Type.EXTERNALS:
            return 0

        popularity = 0
        if self.id >= 0:
            avg_popularity = self.db.get_avg_popularity()
            if avg_popularity > 0:
                popularity = self.db.get_popularity(self.id)
        elif self.id == Type.RADIOS:
            radios = Radios()
            avg_popularity = radios.get_avg_popularity()
            if avg_popularity > 0:
                popularity = radios.get_popularity(self._album_artists[0])
        return popularity * 5 / avg_popularity + 0.5

    def set_popularity(self, popularity):
        """
            Set popularity
            @param popularity as int between 0 and 5
        """
        if self.id is None or self.id == Type.EXTERNALS:
            return
        try:
            if self.id >= 0:
                avg_popularity = self.db.get_avg_popularity()
                popularity = int((popularity * avg_popularity / 5) + 0.5)
                self.db.set_popularity(self.id, popularity, True)
            elif self.id == Type.RADIOS:
                radios = Radios()
                avg_popularity = radios.get_avg_popularity()
                popularity = int((popularity * avg_popularity / 5) + 0.5)
                radios.set_popularity(self._album_artists[0], popularity)
        except Exception as e:
            print("Base::set_popularity(): %s" % e)

    def get_rate(self):
        """
            Get rate
            @return int
        """
        if self.id is None or self.id == Type.EXTERNALS:
            return 0

        rate = 0
        if self.id >= 0:
            rate = self.db.get_rate(self.id)
        elif self.id == Type.RADIOS:
            radios = Radios()
            rate = radios.get_rate(self._album_artists[0])
        return rate

    def set_rate(self, rate):
        """
            Set rate
            @param rate as int between -1 and 5
        """
        if self.id == Type.RADIOS:
            radios = Radios()
            radios.set_rate(self._album_artists[0], rate)
        else:
            Lp().player.emit("rate-changed")
            self.db.set_rate(self.id, rate)


class Disc:
    """
        Represent an album disc
    """

    def __init__(self, album, disc_number):
        self.db = Lp().albums
        self.album = album
        self.number = disc_number
        self._track_ids = []

    @property
    def name(self):
        """
            Disc name
            @return disc name as str
        """

    @property
    def track_ids(self):
        """
            Get all tracks ids of the disc
            @return list of int
        """
        if not self._track_ids:
            self._track_ids = self.db.get_disc_tracks(self.album.id,
                                                      self.album.genre_ids,
                                                      self.album.artist_ids,
                                                      self.number)
            # If user tagged track with an artist not present in album
            if not self._track_ids:
                print("%s missing an album artist in artists" %
                      self.album.name)
                self._track_ids = self.db.get_disc_tracks(self.album.id,
                                                          self.album.genre_ids,
                                                          [],
                                                          self.number)
        return self._track_ids

    @property
    def tracks(self):
        """
            Get all tracks of the disc

            @return list of Track
        """
        return [Track(id) for id in self.track_ids]


class Album(Base):
    """
        Represent an album
    """
    FIELDS = ["name", "artists", "artist_ids",
              "year", "uri", "duration", "mtime", "synced", "loved"]
    DEFAULTS = ["", "", [], "", "", 0, 0, False, False]

    def __init__(self, album_id=None, genre_ids=[], artist_ids=[]):
        """
            Init album
            @param album_id as int
            @param genre_ids as [int]
        """
        Base.__init__(self, Lp().albums)
        self.id = album_id
        self.genre_ids = genre_ids
        self._track_ids = None
        # Use artist ids from db else
        if artist_ids:
            self.artist_ids = artist_ids

    def set_genres(self, genre_ids):
        """
            Set album genres
            @param genre_ids as [int]
            @return None
        """
        self.genre_ids = genre_ids
        self._track_ids = None
        self._tracks = None

    def set_artists(self, artist_ids):
        """
            Set album artists
        """
        self.artist_ids = artist_ids
        self._track_ids = None
        self._tracks = None

    @property
    def title(self):
        """
            Get album name
            @return str
        """
        return self.name

    @property
    def track_ids(self):
        """
            Get album track ids
            @return list of int
        """
        if self._track_ids is None:
            self._track_ids = self.db.get_track_ids(self.id,
                                                    self.genre_ids,
                                                    self.artist_ids)
            # If user tagged track with an artist not present in album
            if not self._track_ids:
                print("%s missing an album artist in artists" % self.name)
                self._track_ids = self.db.get_track_ids(self.id,
                                                        self.genre_ids,
                                                        [])
        return self._track_ids

    @property
    def tracks(self):
        """
            Get album tracks
            @return list of Track
        """
        if not self._tracks and self.track_ids:
            self._tracks = [Track(track_id) for track_id in self.track_ids]
        return self._tracks

    @property
    def is_web(self):
        """
            True if a web stream
            @return bool
        """
        return self.synced == Type.NONE

    def disc_names(self, disc):
        """
            Disc names
            @param disc as int
            @return disc names as [str]
        """
        return self.db.get_disc_names(self.id, disc)

    @property
    def discs(self):
        """
            Get albums discs
            @return [Disc]
        """
        if not self._discs:
            self._discs = self.db.get_discs(self.id, self.genre_ids)
        return [Disc(self, number) for number in self._discs]

    def set_loved(self, loved):
        """
            Mark album as loved
            @param loved as bool
        """
        if self.id >= 0:
            Lp().albums.set_loved(self.id, loved)

    def remove(self):
        """
            Remove album
        """
        artist_ids = []
        # We want all tracks
        album = Album(self.id)
        for track_id in self.track_ids:
            artist_ids += Lp().tracks.get_artist_ids(track_id)
            uri = Lp().tracks.get_uri(track_id)
            Lp().playlists.remove(uri)
            Lp().tracks.remove(track_id)
            Lp().tracks.clean(track_id)
            art_file = Lp().art.get_album_cache_name(self)
            Lp().art.clean_store(art_file)
        artist_ids += album.artist_ids
        genre_ids = Lp().albums.get_genre_ids(album.id)
        deleted = Lp().albums.clean(self.id)
        for artist_id in list(set(artist_ids)):
            Lp().artists.clean(artist_id)
            # Do not check clean return
            GLib.idle_add(Lp().scanner.emit, "artist-updated",
                          artist_id, False)
        for genre_id in genre_ids:
            Lp().genres.clean(genre_id)
            GLib.idle_add(Lp().scanner.emit, "genre-updated",
                          genre_id, False)
        with SqlCursor(Lp().db) as sql:
            sql.commit()
        GLib.idle_add(Lp().scanner.emit, "album-updated", self.id, deleted)


class Track(Base):
    """
        Represent a track
    """
    FIELDS = ["name", "album_id", "album_artist_ids",
              "artist_ids", "genre_ids", "album_name", "artists", "genres",
              "duration", "number", "year", "persistent", "mtime"]
    DEFAULTS = ["", None, [], [], [], "", "", "", 0.0, 0, None, 1, 0]

    def __init__(self, track_id=None):
        """
            Init track
            @param track_id as int
        """
        Base.__init__(self, Lp().tracks)
        self.id = track_id
        self._uri = None
        self._non_album_artists = []

    @property
    def is_web(self):
        """
            True if a web stream
            @return bool
        """
        return self.is_jgm or self.is_youtube

    @property
    def is_jgm(self):
        """
            True if a jgm stream
            @return bool
        """
        return self.uri.startswith("http://app.jgm90.com")

    @property
    def is_youtube(self):
        """
            True if a youtube stream
            @return bool
        """
        return self.uri.startswith("https://www.youtube.com")

    @property
    def non_album_artists(self):
        """
            Return non album artists
            @return str
        """
        if not self._non_album_artists:
            # Show all artists for compilations
            if self.album.artist_ids and\
                    self.album.artist_ids[0] == Type.COMPILATIONS:
                self._non_album_artists = self.artists
            else:
                lower_album_artists = map(lambda x: x.lower(),
                                          self.album_artists)
                for artist in self.artists:
                    if artist.lower() not in lower_album_artists:
                        self._non_album_artists.append(artist)
        return self._non_album_artists

    @property
    def title(self):
        """
            Get track name
            Alias to Track.name
        """
        return self.name

    @property
    def uri(self):
        """
            Get track file uri
            @return str
        """
        if self._uri is None:
            self._uri = Lp().tracks.get_uri(self.id)
        return self._uri

    @property
    def path(self):
        """
            Get track file path
            Alias to Track.path
            @return str
        """
        return GLib.filename_from_uri(self.uri)[0]

    @property
    def album(self):
        """
            Get track"s album
            @return Album
        """
        return Album(self.album_id)

    @property
    def album_artists(self):
        """
            Get track album artists, can be != than album.artists as track
            may not have any album (radio, externals, ...)
            @return str
        """
        if getattr(self, "_album_artists") is None:
            self._album_artists = self.album.artists
        return self._album_artists

    def set_duration(self, duration):
        """
            Set duration
            @param duration as in
        """
        self._duration = duration

    def set_album_artists(self, artists):
        """
            Set album artist
            @param artists as [int]
        """
        self._album_artists = artists

    def set_uri(self, uri):
        """
            Set uri
            @param uri as string
        """
        self._uri = uri

    def set_radio(self, name, uri):
        """
            Set radio
            @param name as string
            @param uri as string
        """
        self.id = Type.RADIOS
        self._album_artists = [name]
        self._uri = uri

    def remove(self):
        """
            Remove track
        """
        artist_ids = []
        album = self.album
        artist_ids = Lp().tracks.get_artist_ids(self.id)
        Lp().playlists.remove(self.uri)
        Lp().tracks.remove(self.id)
        Lp().tracks.clean(self.id)
        artist_ids += album.artist_ids
        genre_ids = Lp().tracks.get_genre_ids(self.id)
        deleted = Lp().albums.clean(album.id)
        for artist_id in list(set(artist_ids)):
            Lp().artists.clean(artist_id)
            # Do not check clean return
            GLib.idle_add(Lp().scanner.emit, "artist-updated",
                          artist_id, False)
        for genre_id in genre_ids:
            Lp().genres.clean(genre_id)
            GLib.idle_add(Lp().scanner.emit, "genre-updated",
                          genre_id, False)
        with SqlCursor(Lp().db) as sql:
            sql.commit()
        GLib.idle_add(Lp().scanner.emit, "album-updated", album.id, deleted)
