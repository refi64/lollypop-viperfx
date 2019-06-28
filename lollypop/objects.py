# Copyright (c) 2014-2019 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import GLib, Gio

import json

from urllib.parse import urlparse
from lollypop.radios import Radios
from lollypop.logger import Logger
from lollypop.define import App, Type
from lollypop.utils import escape


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

    def reset(self, attr):
        """
            Reset attr
            @param attr as str
        """
        attr_name = "_" + attr
        attr_value = getattr(self.db, "get_" + attr)(self.id)
        setattr(self, attr_name, attr_value)

    @property
    def is_in_user_collection(self):
        """
            True if track is in user collection
            @return bool
        """
        return self.mtime > 0

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
                popularity = radios.get_popularity(self._radio_id)
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
                radios.set_popularity(self._radio_id, popularity)
        except Exception as e:
            Logger.error("Base::set_popularity(): %s" % e)

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
            rate = radios.get_rate(self._radio_id)
        return rate

    def set_rate(self, rate):
        """
            Set rate
            @param rate as int between -1 and 5
        """
        if self.id == Type.RADIOS:
            radios = Radios()
            radios.set_rate(self._radio_id, rate)
            App().player.emit("rate-changed", self._radio_id, rate)
        else:
            self.db.set_rate(self.id, rate)
            App().player.emit("rate-changed", self.id, rate)


class Disc:
    """
        Represent an album disc
    """

    def __init__(self, album, disc_number, disallow_ignored_tracks):
        self.db = App().albums
        self.__tracks = []
        self.__album = album
        self.__number = disc_number
        self.__disallow_ignored_tracks = disallow_ignored_tracks

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
                self.number,
                self.__disallow_ignored_tracks)]
        return self.__tracks


class Album(Base):
    """
        Represent an album
    """
    DEFAULTS = {"name": "",
                "artists": [],
                "artist_ids": [],
                "year": None,
                "timestamp": None,
                "uri": "",
                "tracks_count": 1,
                "duration": 0,
                "popularity": 0,
                "mtime": 1,
                "synced": False,
                "loved": False,
                "mb_album_id": None}

    def __init__(self, album_id=None, genre_ids=[], artist_ids=[],
                 disallow_ignored_tracks=False):
        """
            Init album
            @param album_id as int
            @param genre_ids as [int]
            @param disallow_ignored_tracks as bool
        """
        Base.__init__(self, App().albums)
        self.id = album_id
        self.genre_ids = genre_ids
        self._tracks = []
        self._discs = []
        self.__disallow_ignored_tracks = disallow_ignored_tracks
        self.__one_disc = None
        # Use artist ids from db else
        if artist_ids:
            self.artist_ids = artist_ids

    def clone(self, disallow_ignored_tracks):
        """
            Clone album
            @param disallow_ignored_tracks as bool
        """
        album = Album(self.id, self.genre_ids,
                      self.artist_ids, disallow_ignored_tracks)
        if not disallow_ignored_tracks:
            album.set_tracks(self.tracks)
        return album

    def set_discs(self, discs):
        """
            Set album discs
            @param discs as [Disc]
        """
        self._discs = discs

    def set_tracks(self, tracks):
        """
            Set album tracks (cloned tracks)
            @param tracks as [Track]
        """
        self._tracks = []
        for track in tracks:
            new_track = Track(track.id, self)
            self._tracks.append(new_track)

    def insert_track(self, track, position=-1):
        """
            Add track to album (cloned track)
            @param track as Track
            @param position as int
        """
        new_track = Track(track.id, self)
        if position == -1:
            self._tracks.append(new_track)
        else:
            self._tracks.insert(position, new_track)

    def remove_track(self, track):
        """
            Remove track from album
            @param track as Track
            @return True if album empty
        """
        if track in self.tracks:
            self._tracks.remove(track)
        return len(self._tracks) == 0

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

    def set_uri(self, uri):
        """
            Set album uri
            @param uri as str
        """
        if self.id >= 0:
            App().albums.set_uri(self.id, uri)
        self.uri = uri

    def get_track(self, track_id):
        """
            Get track
            @param track_id as int
            @return Track
        """
        for track in self.tracks:
            if track.id == track_id:
                return track
        return Track()

    def save(self, save):
        """
            Save album to collection
            @param save as bool
        """
        if save:
            App().albums.set_mtime(self.id, -1)
        else:
            App().albums.set_mtime(self.id, 0)
        for track in self.tracks:
            track.save(save)
        self.reset("mtime")
        for artist_id in self.artist_ids:
            App().scanner.emit("artist-updated", artist_id, save)
        App().scanner.emit("album-updated", self.id, save)

    @property
    def synced(self):
        """
            Get synced state
            Remove from cache
            @return int
        """
        return App().albums.get_synced(self.id)

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
    def one_disc(self):
        """
            Get album as one disc
            @return Disc
        """
        if self.__one_disc is None:
            tracks = self.tracks
            self.__one_disc = Disc(self, 0, self.__disallow_ignored_tracks)
            self.__one_disc.set_tracks(tracks)
        return self.__one_disc

    @property
    def discs(self):
        """
            Get albums discs
            @return [Disc]
        """
        if not self._discs:
            disc_numbers = self.db.get_discs(self.id, self.genre_ids)
            self._discs = [Disc(self, number, self.__disallow_ignored_tracks)
                           for number in disc_numbers]
        return self._discs


class Track(Base):
    """
        Represent a track
    """
    DEFAULTS = {"name": "",
                "album_id": None,
                "artist_ids": [],
                "genre_ids": [],
                "popularity": 0,
                "album_name": "",
                "artists": [],
                "genres": [],
                "duration": 0,
                "number": 0,
                "discnumber": 0,
                "discname": "",
                "year": None,
                "timestamp": None,
                "mtime": 1,
                "loved": False,
                "mb_track_id": None,
                "mb_artist_ids": []}

    def __init__(self, track_id=None, album=None):
        """
            Init track
            @param track_id as int
            @param album as Album
        """
        Base.__init__(self, App().tracks)
        self.id = track_id
        self._radio_id = None
        self._radio_name = ""
        self._uri = None
        self._number = 0

        if album is None:
            self.__album = Album(self.album_id)
        else:
            self.__album = album

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
            Set radio for non DB radios (Tunein)
            @param name as string
            @param uri as string
        """
        from lollypop.radios import Radios
        radios = Radios()
        self.id = Type.RADIOS
        self._radio_id = radios.get_id(name)
        self._radio_name = name
        self._uri = uri
        # Generate a tmp album id, needed by InfoController
        album_id = 0
        for i in list(map(ord, name)):
            album_id += i
        self.album.id = album_id

    def set_radio_id(self, radio_id):
        """
            Set radio id
            @param radio_id as int
        """
        from lollypop.radios import Radios
        radios = Radios()
        name = radios.get_name(radio_id)
        uri = radios.get_uri(radio_id)
        self.set_radio(name, uri)

    def set_number(self, number):
        """
            Set number
            @param number as int
        """
        self._number = number

    def set_loved(self, loved):
        """
            Mark album as loved
            @param loved as bool
        """
        if self.id >= 0:
            App().tracks.set_loved(self.id, loved)
            self.loved = loved

    def save(self, save):
        """
            Save track to collection
            Cache it to Web Collection (for restore on reset)
            @param save as bool
        """
        try:
            filename = "%s_%s_%s" % (self.album.name, self.artists, self.name)
            filepath = "%s/%s.txt" % (App().scanner._WEB_COLLECTION,
                                      escape(filename))
            f = Gio.File.new_for_path(filepath)
            if save:
                App().tracks.set_mtime(self.id, -1)
                data = {
                    "title": self.name,
                    "album_name": self.album.name,
                    "artists": self.artists,
                    "album_artists": self.album.artists,
                    "album_loved": self.album.loved,
                    "album_popularity": self.album.popularity,
                    "album_rate": self.album.get_rate(),
                    "discnumber": self.discnumber,
                    "discname": self.discname,
                    "duration": self.duration,
                    "tracknumber": App().tracks.get_number(self.id),
                    "track_popularity": self.popularity,
                    "track_loved": self.loved,
                    "track_rate": self.get_rate(),
                    "year": self.year,
                    "timestamp": self.timestamp,
                    "uri": self.uri
                }
                content = json.dumps(data).encode("utf-8")
                fstream = f.replace(None, False,
                                    Gio.FileCreateFlags.REPLACE_DESTINATION,
                                    None)
                if fstream is not None:
                    fstream.write(content, None)
                    fstream.close()
            else:
                App().tracks.set_mtime(self.id, 0)
                f.delete()
            self.reset("mtime")
        except Exception as e:
            Logger.error("Track::save(): %s", e)

    def get_featuring_artist_ids(self, album_artist_ids):
        """
            Get featuring artist ids
            @return [int]
        """
        artist_ids = self.db.get_artist_ids(self.id)
        return list(set(artist_ids) - set(album_artist_ids))

    @property
    def is_web(self):
        """
            True if track is a web track
            @return bool
        """
        return self.is_http or self.uri.startswith("web:")

    @property
    def is_http(self):
        """
            True if track is a http track
            @return bool
        """
        parsed = urlparse(self.uri)
        return parsed.scheme in ["http", "https"]

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
    def radio_id(self):
        """
            Get radio id
            @return int
        """
        return self._radio_id

    @property
    def radio_name(self):
        """
            Get radio name
            @return str
        """
        return self._radio_name

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
