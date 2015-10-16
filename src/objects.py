# Copyright (c) 2014-2015 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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


class Base:
    """
        Base for album and track objects
    """
    def __init__(self, db):
        self.db = db

    def __dir__(self, *args, **kwargs):
        """
            Concatenate base class's fields with child class's fields
        """
        return super(Base, self).__dir__(*args, **kwargs) + self.FIELDS

    def __getattr__(self, attr):
        # Lazy DB calls of attributes referenced
        # in self.FIELDS
        if attr in self.FIELDS:
            if self.id is None or self.id < 0:
                return self.DEFAULTS[self.FIELDS.index(attr)]
            # Actual value of 'attr_name' is stored in '_attr_name'
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
                popularity = radios.get_popularity(self._album_artist)
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
                radios.set_popularity(self._album_artist, popularity)
        except Exception as e:
            print("Base::set_popularity(): %s" % e)


class Disc:
    """
        Represent an album disc
    """

    def __init__(self, album, disc_number):
        self.db = Lp.albums
        self.album = album
        self.number = disc_number

    @property
    def tracks_ids(self):
        """
            Get all tracks ids of the disc

            @return list of int
        """
        return self.db.get_disc_tracks_ids(self.album.id,
                                           self.album.genre_id,
                                           self.number)

    @property
    def tracks(self):
        """
            Get all tracks of the disc

            @return list of Track
        """
        return [Track(id) for id in self.tracks_ids]


class Album(Base):
    """
        Represent an album
    """
    FIELDS = ['name', 'artist_name', 'artist_id', 'year', 'path']
    DEFAULTS = ['', '', None, '', '']

    def __init__(self, album_id=None, genre_id=None):
        """
            Init album
            @param album_id as int
            @param genre_id as int
        """
        Base.__init__(self, Lp.albums)
        self.id = album_id
        self.genre_id = genre_id

    def set_genre(self, genre_id):
        """
            Change current genre to lookup
            tracks

            @param genre_id as int
            @return None
        """
        self.genre_id = genre_id
        self._tracks_ids = None
        self._tracks = None

    @property
    def title(self):
        """
            Get album name
            @return str
        """
        return self.name

    @property
    def tracks_ids(self):
        """
            Get album tracks id
            @return list of int
        """
        if getattr(self, "_tracks_ids") is None:
            self._tracks_ids = self.db.get_tracks(self.id,
                                                  self.genre_id)
        return self._tracks_ids

    @property
    def tracks(self):
        """
            Get album tracks
            @return list of Track
        """
        if not self._tracks and self.tracks_ids:
            self._tracks = [Track(track_id) for track_id in self.tracks_ids]
        return self._tracks

    @property
    def discs(self):
        """
            Get albums discs
            @return list of int
        """
        if not self._discs:
            self._discs = self.db.get_discs(self.id, self.genre_id)
        return [Disc(self, number) for number in self._discs]


class Track(Base):
    """
        Represent a track
    """
    FIELDS = ['name', 'album_id', 'album_artist_id',
              'artist_ids', 'album_name', 'artist_names',
              'genre_names', 'duration', 'number', 'path']
    DEFAULTS = ['', None, None, [], '', '', '', 0.0, None, '']

    def __init__(self, track_id=None):
        """
            Init track
            @param track_id as int
        """
        Base.__init__(self, Lp.tracks)
        self.id = track_id
        self._uri = None

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
        if self._uri is not None:
            return self._uri
        elif self.path != '':
            return GLib.filename_to_uri(self.path)
        else:
            return self.path

    @property
    def filepath(self):
        """
            Get track file path
            Alias to Track.path
            @return str
        """
        return self.path

    @property
    def album(self):
        """
            Get track's album
            @return Album
        """
        return Album(self.album_id)

    @property
    def year(self):
        """
            Get track year
            @return str
        """
        return self.album.year

    @property
    def album_artist(self):
        """
            Get track artist name
            @return str
        """
        if getattr(self, "_album_artist") is None:
            self._album_artist = Lp.artists.get_name(self.album_artist_id)
        return self._album_artist

    @property
    def artist(self):
        """
            Get track artist(s) name(s)
            Alias to Track.artist_names
            @return str
        """
        return self.artist_names

    @property
    def genre(self):
        """
            Get track genres
            Alias to Track.genre_names
            @return str
        """
        return self.genre_names

    def set_album_artist(self, name):
        """
            Set album artist
            @param name as string
        """
        self._album_artist = name

    def set_uri(self, uri):
        """
            Set uri and path
            @param uri as string
        """
        self._uri = uri
        try:
            self.path = GLib.filename_from_uri(uri)[0]
        except:
            pass

    def set_radio(self, name, uri):
        """
            Set radio
            @param name as string
            @param uri as string
        """
        self.id = Type.RADIOS
        self._album_artist = name
        self._uri = uri
