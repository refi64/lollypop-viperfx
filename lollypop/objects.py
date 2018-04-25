# Copyright (c) 2014-2018 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from lollypop.helper_task import TaskHelper
from lollypop.radios import Radios
from lollypop.define import App, Type


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
        return super(Base, self).__dir__(*args, **kwargs) +\
            list(self.DEFAULTS.keys())

    # Used by pickle
    def __getstate__(self): return self.__dict__

    def __setstate__(self, d): self.__dict__.update(d)

    def __getattr__(self, attr):
        # Lazy DB calls of attributes
        if attr in list(self.DEFAULTS.keys()):
            if self.id is None or self.id < 0:
                return self.DEFAULTS[attr]
            # Actual value of "attr_name" is stored in "_attr_name"
            attr_name = "_" + attr
            attr_value = getattr(self, attr_name)
            if attr_value is None:
                attr_value = getattr(self.db, "get_" + attr)(self.id)
                setattr(self, attr_name, attr_value)
            # Return default value if None
            if attr_value is None:
                return self.DEFAULTS[attr]
            else:
                return attr_value

    def get_popularity(self):
        """
            Get popularity
            @return int between 0 and 5
        """
        if self.id is None:
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

    def set_popularity(self, new_rate):
        """
            Set popularity
            @param new_rate as int between 0 and 5
        """
        if self.id is None:
            return
        try:
            if self.id >= 0:
                avg_popularity = self.db.get_avg_popularity()
                popularity = int((new_rate * avg_popularity / 5) + 0.5)
                best_popularity = self.db.get_higher_popularity()
                if new_rate == 5:
                    popularity = (popularity + best_popularity) / 2
                self.db.set_popularity(self.id, popularity)
            elif self.id == Type.RADIOS:
                radios = Radios()
                avg_popularity = radios.get_avg_popularity()
                popularity = int((new_rate * avg_popularity / 5) + 0.5)
                best_popularity = self.db.get_higher_popularity()
                if new_rate == 5:
                    popularity = (popularity + best_popularity) / 2
                radios.set_popularity(self._album_artists[0], popularity)
        except Exception as e:
            print("Base::set_popularity(): %s" % e)

    def get_rate(self):
        """
            Get rate
            @return int
        """
        if self.id is None:
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
            self.db.set_rate(self.id, rate)
            App().player.emit("rate-changed", (self.id, rate))


class Disc:
    """
        Represent an album disc
    """

    def __init__(self, album, disc_number):
        self.db = App().albums
        self.__tracks = []
        self.__album = album
        self.__number = disc_number

    def set_tracks(self, tracks):
        """
            Set disc tracks
            @param tracks as [Track]
        """
        self.__tracks = tracks

    @property
    def number(self):
        """
            Get disc number
        """
        return self.__number

    @property
    def album(self):
        """
            Get disc album
            @return Album
        """
        return self.__album

    @property
    def track_ids(self):
        """
            Get disc track ids
            @return [int]
        """
        return [track.id for track in self.tracks]

    @property
    def track_uris(self):
        """
            Get disc track uris
            @return [str]
        """
        return [track.uri for track in self.tracks]

    @property
    def tracks(self):
        """
            Get disc tracks
            @return [Track]
        """
        if not self.__tracks and self.album.id is not None:
            self.__tracks = [Track(track_id, self.album)
                             for track_id in self.db.get_disc_track_ids(
                self.album.id,
                self.album.genre_ids,
                self.album.artist_ids,
                self.number)]
            if not self.__tracks:
                self.__tracks = [Track(track_id, self.album)
                                 for track_id in self.db.get_disc_track_ids(
                    self.album.id,
                    self.album.genre_ids,
                    [],
                    self.number)]
        return self.__tracks


class Album(Base):
    """
        Represent an album
    """
    DEFAULTS = {"name": "",
                "artists": "",
                "artist_ids": [],
                "year": None,
                "uri": "",
                "tracks_count": 0,
                "duration": 0,
                "mtime": 0,
                "synced": False,
                "loved": False}

    def __init__(self, album_id=None, genre_ids=[], artist_ids=[]):
        """
            Init album
            @param album_id as int
            @param genre_ids as [int]
        """
        Base.__init__(self, App().albums)
        self.id = album_id
        self.genre_ids = genre_ids
        self._tracks = []
        self._discs = []
        # Use artist ids from db else
        if artist_ids:
            self.artist_ids = artist_ids

    def merge_discs(self):
        """
            Merge discs into one
        """
        tracks = self.tracks
        self._discs = [Disc(self, 0)]
        self._discs[0].set_tracks(tracks)

    def move_track(self, track, index):
        """
            Move track to index
            @param track as Track
            @param index
        """
        if track in self._tracks:
            self._tracks.remove(track)
            self._tracks.insert(index, track)

    def set_tracks(self, tracks):
        """
            Set album tracks
            @param tracks as [Track]
        """
        self._tracks = tracks
        for track in tracks:
            track.set_album(self)

    def add_track(self, track):
        """
            Add track to album
            @param track as Track
        """
        self._tracks.append(track)
        track.set_album(self)

    def remove_track(self, track):
        """
            Remove track from album
            @param track as Track
        """
        if track in self.tracks:
            self._tracks.remove(track)

    def clear_tracks(self):
        """
            Clear album tracks
        """
        self._tracks = []

    def disc_names(self, disc):
        """
            Disc names
            @param disc as int
            @return disc names as [str]
        """
        return self.db.get_disc_names(self.id, disc)

    def set_loved(self, loved):
        """
            Mark album as loved
            @param loved as bool
        """
        if self.id >= 0:
            App().albums.set_loved(self.id, loved)
            self.loved = loved

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
            @return [int]
        """
        return [track.id for track in self.tracks]

    @property
    def track_uris(self):
        """
            Get album track uris
            @return [str]
        """
        return [track.uri for track in self.tracks]

    @property
    def tracks(self):
        """
            Get album tracks
            @return [Track]
        """
        if not self._tracks and self.id is not None:
            for disc in self.discs:
                self._tracks += disc.tracks
        return self._tracks

    @property
    def discs(self):
        """
            Get albums discs
            @return [Disc]
        """
        if not self._discs:
            disc_numbers = self.db.get_discs(self.id, self.genre_ids)
            self._discs = [Disc(self, number) for number in disc_numbers]
        return self._discs


class Track(Base):
    """
        Represent a track
    """
    DEFAULTS = {"name": "",
                "album_id": None,
                "album_artist_ids": [],
                "artist_ids": [],
                "genre_ids": [],
                "popularity": 0,
                "album_name": "",
                "artists": "",
                "genres": "",
                "duration": 0,
                "number": 0,
                "year": None,
                "mtime": 0,
                "mb_track_id": None}

    def __init__(self, track_id=None, album=None):
        """
            Init track
            @param track_id as int
            @param album as Album
        """
        Base.__init__(self, App().tracks)
        self.id = track_id
        self._uri = None
        self._number = 0

        if album is None:
            self.__album = Album(self.album_id)
        else:
            self.__album = album
        self.__featuring_ids = []

    def set_featuring_ids(self, album_artist_ids):
        """
            Set featuring artist ids
            @param artist ids as [int]
            @return featuring artist ids as [int]
        """
        artist_ids = self.db.get_artist_ids(self.id)
        album_id = self.db.get_album_id(self.id)
        if not album_artist_ids:
            db_album_artist_ids = App().albums.get_artist_ids(album_id)
            if len(db_album_artist_ids) == 1:
                artist_ids = list(set(artist_ids) - set(db_album_artist_ids))
        self.__featuring_ids = list(set(artist_ids) - set(album_artist_ids))

    def set_album_artists(self, artists):
        """
            Set album artist
            @param artists as [int]
        """
        self._album_artists = artists

    def set_album(self, album):
        """
            Set track album
            @param album as Album
        """
        self.__album = album

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

    def set_number(self, number):
        """
            Set number
            @param number as int
        """
        self._number = number

    def set_loved(self, loved):
        """
            Add or remove track from loved playlist
            @param loved Add to loved playlist if `True`; remove if `False`
        """
        scrobbler_love = True
        if not self.loved:
            if loved:
                App().playlists.add_tracks(Type.LOVED, [self])
        elif not loved:
            scrobbler_love = False
            App().playlists.remove_tracks(Type.LOVED, [self])
        for scrobbler in App().scrobblers:
            if scrobbler.can_love:
                helper = TaskHelper()
                helper.run(scrobbler.set_loved, self, scrobbler_love)

    @property
    def loved(self):
        """
            True if track loved
            @return bool
        """
        return App().playlists.exists_track(Type.LOVED,
                                            self)

    @property
    def featuring_artist_ids(self):
        """
            Get featuring artist ids
            @return [int]
        """
        return self.__featuring_ids

    @property
    def position(self):
        """
            Get track position for album
            @return int
        """
        i = 0
        for track_id in self.__album.track_ids:
            if track_id == self.id:
                break
            i += 1
        return i

    @property
    def first(self):
        """
            Is track first for album
            @return bool
        """
        tracks = self.__album.tracks
        return tracks and self.id == tracks[0].id

    @property
    def last(self):
        """
            Is track last for album
            @return bool
        """
        tracks = self.__album.tracks
        return tracks and self.id == tracks[-1].id

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
            self._uri = App().tracks.get_uri(self.id)
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
        if self.__album is None:
            self.__album = Album(self._album_id)
        return self.__album

    @property
    def album_artists(self):
        """
            Get track album artists, can be != than album.artists as track
            may not have any album
            @return str
        """
        if getattr(self, "_album_artists") is None:
            self._album_artists = self.album.artists
        return self._album_artists
