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

from os import path

from threading import current_thread

from lollypop.define import Lp, Type


class Base:
    """
        Base for album and track objects
    """
    def __init__(self, db):
        self.db = db

    def __dir__(self, *args, **kwargs):
        return super(Base, self).__dir__(*args, **kwargs) + self.FIELDS

    def __getattr__(self, attr):
        # Lazy DB calls of attributes referenced
        # in self.FIELDS
        if attr in self.FIELDS:
            if self.id is None:
                return self.DEFAULTS[self.FIELDS.index(attr)]
            # Actual value of 'attr_name' is stored in '_attr_name'
            attr_name = "_" + attr
            attr_value = getattr(self, attr_name)
            if attr_value is None and not self.id == Type.RADIOS:
                sql = None
                if current_thread() != '_Mainthread':
                    sql = Lp.db.get_cursor()
                attr_value = getattr(self.db, "get_" + attr)(self.id, sql)
                if sql is not None:
                    sql.close()
                setattr(self, attr_name, attr_value)
            return attr_value

    def get_popularity(self):
        """
            Get popularity
            @return int between 0 and 5
        """
        if self.id is None:
            return

        popularity = 0
        avg_popularity = self.db.get_avg_popularity()
        if avg_popularity > 0:
            popularity = self.db.get_popularity(self.id)

        return popularity * 5 / avg_popularity + 0.5

    def set_popularity(self, popularity):
        """
            Set popularity
            @param popularity as int between 0 and 5
        """
        avg_popularity = self.db.get_avg_popularity()
        popularity = int((popularity * avg_popularity / 5) + 0.5)
        try:
            self.db.set_popularity(self.id, popularity, True)
        except:
            self.db.set_popularity(self.id, 0, True)



class Album(Base):
    """
        Represent an album
    """
    FIELDS = ['name', 'artist_name', 'artist_id', 'year', 'tracks_id']
    DEFAULTS = ['', '', None, '', []]

    def __init__(self, album_id=None, genre_id=None, sql=None, fields=[]):
        """
            Init album
            @param album_id as int
            @param genre_id as int
        """
        Base.__init__(self, Lp.albums)
        self.id = album_id
        self.genre_id = genre_id

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
            sql = None
            if current_thread() != '_Mainthread':
                sql = Lp.db.get_cursor()
            self._tracks_ids = self.db.get_tracks(self.id, self.genre_id, sql)
            if sql is not None:
                sql.close()
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


class Track(Base):
    """
        Represent a track
    """
    FIELDS = ['name', 'album_id', 'album_artist_id',
              'artist_ids', 'artist_names',
              'genre_names', 'length', 'number', 'path']
    DEFAULTS = ['', None, None, [], '', '', 0.0, None, '']

    def __init__(self, track_id=None):
        """
            Init track
            @param track_id as int
        """
        Base.__init__(self, Lp.tracks)
        self.id = track_id

    @property
    def title(self):
        """
            Get track name
            Alias to Track.name
        """
        return self.name

    @property
    def uri(self):
        """Get track file uri

        @return str
        """
        if path.exists(self.path):
            return GLib.filename_to_uri(self.path)

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
            Get track's album name
            @return str
        """
        return Album(self.album_id).name

    @property
    def year(self):
        """
            Get track year
            @return str
        """
        return Album(self.album_id).year

    @property
    def aartist_id(self):
        """
            Get track artist id
            Alias to Track.album_artist_id
            @return int
        """
        return self.album_artist_id

    @property
    def aartist(self):
        """
            Get track artist name
            @return str
        """
        if getattr(self, "_aartist") is None:
            sql = None
            if current_thread() != '_Mainthread':
                sql = Lp.db.get_cursor()
            self._aartist = Lp.artists.get_name(self.aartist_id, sql)
            if sql is not None:
                sql.close()
        return self._aartist

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

    @property
    def duration(self):
        """
            Get track length
            Alias to Track.length
            @return float
        """
        return self.length

    def set_radio(self, name, uri):
        """
            Set radio
            @param name as string
            @param uri as string
        """
        self._id = Type.RADIOS
        self._aartist = name
        self._uri = uri
