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

from gi.repository import GLib, Gst, GstPbutils

import os
from time import time
from gettext import gettext as _

from lollypop.define import Lp, Type
from lollypop.utils import format_artist_name


# Tag reader class
class TagReader:
    """
        Init tag reader
    """
    def __init__(self):
        Gst.init(None)
        self._tagreader = GstPbutils.Discoverer.new(10*Gst.SECOND)

    """
        Return informations on file at path
        @param path as str
        @return GstPbutils.DiscovererInfo
    """
    def get_infos(self, path):
        try:
            uri = GLib.filename_to_uri(path)
            infos = self._tagreader.discover_uri(uri)
            return infos
        except:
            return None


# Scanner tag reader class
class ScannerTagReader(TagReader):
    """
        Init tag reader
    """
    def __init__(self):
        TagReader.__init__(self)

    """
        Return title for tags
        @param tags as Gst.TagList
        @param filepath as string
        @return title as string
    """
    def get_title(self, tags, filepath):
        exist = False
        if tags is not None:
            (exist, title) = tags.get_string_index('title', 0)
        if not exist:
            title = os.path.basename(filepath)
        return title

    """
        Return artists for tags
        @param tags as Gst.TagList
        @return string like "artist1;artist2;..."
    """
    def get_artists(self, tags):
        artists = ""
        if tags is None:
            return artists

        size = tags.get_tag_size('artist')
        if size == 0:
            artists = _("Unknown")
        else:
            for i in range(0, size):
                (exist, artist) = tags.get_string_index('artist', i)
                artists += artist
                if i < size-1:
                    artists += ";"
        return artists

    """
        Return album artist for tags
        @param tags as Gst.TagList
        @return album artist as string or None
    """
    def get_album_artist(self, tags):
        exist = False
        if tags is not None:
            (exist, album_artist) = tags.get_string_index('album-artist', 0)
        if not exist:
            album_artist = None
        return album_artist

    """
        Return album for tags
        @param tags as Gst.TagList
        @return album name as string
    """
    def get_album_name(self, tags):
        exist = False
        if tags is not None:
            (exist, album_name) = tags.get_string_index('album', 0)
        if not exist:
            album_artist = self.get_album_artist(tags)
            if album_artist is None:
                album_artist = self.get_artists(tags)
            album_name = album_artist+" - "+_("Unknown")
        return album_name

    """
        Return genres for tags
        @param tags as Gst.TagList
        @return string like "genre1;genre2;..."
    """
    def get_genres(self, tags):
        genres = ""
        if tags is None:
            return genres

        size = tags.get_tag_size('genre')
        if size == 0:
            genres = _("Unknown")
        else:
            for i in range(0, size):
                (exist, genre) = tags.get_string_index('genre', i)
                genres += genre
                if i < size-1:
                    genres += ";"
        return genres

    """
        Return disc number for tags
        @param tags as Gst.TagList
        @return disc number as int
    """
    def get_discnumber(self, tags):
        exist = False
        if tags is not None:
            (exist, discnumber) = tags.get_uint_index('album-disc-number', 0)
        if not exist:
            discnumber = 0
        return discnumber

    """
        Return track number for tags
        @param tags as Gst.TagList
        @return track number as int
    """
    def get_tracknumber(self, tags):
        exist = False
        if tags is not None:
            (exist, tracknumber) = tags.get_uint_index('track-number', 0)
        if not exist:
            tracknumber = 0
        return tracknumber

    """
        Return track year for tags
        @param tags as Gst.TagList
        @return track year as int or None
    """
    def get_year(self, tags):
        exist = False
        if tags is not None:
            (exist, datetime) = tags.get_date_time('datetime')
        if exist:
            year = datetime.get_year()
        else:
            year = None
        return year

    """
        Add artists to db
        @param artists as [string]
        @param album artist as string
        @param outside as bool
        @param sql as sqlite cursor
        @commit needed
        @param return ([artist ids as int], [new artist ids as int])
    """
    def add_artists(self, artists, album_artist, outside, sql):
        new_artist_ids = []
        # Get all artist ids
        artist_ids = []
        for word in artists.split(';'):
            artist = format_artist_name(word)
            # Get artist id, add it if missing
            artist_id = Lp.artists.get_id(artist, sql)
            if artist_id is None:
                Lp.artists.add(artist, outside, sql)
                artist_id = Lp.artists.get_id(artist, sql)
                if artist == album_artist:
                    new_artist_ids.append(artist_id)
            artist_ids.append(artist_id)
        return (artist_ids, new_artist_ids)

    """
        Add album artist to db
        @param album_artist as string
        @param outside as bool
        @param sql as sqlite cursor
        @param return ([album artist ids as int], [new as bool])
        @commit needed
    """
    def add_album_artist(self, album_artist, outside, sql):
        album_artist_id = None
        new = False
        if album_artist is not None:
            album_artist = format_artist_name(album_artist)
            # Get album artist id, add it if missing
            album_artist_id = Lp.artists.get_id(album_artist, sql)
            if album_artist_id is None:
                Lp.artists.add(album_artist, outside, sql)
                album_artist_id = Lp.artists.get_id(album_artist, sql)
                new = True
        return (album_artist_id, new)

    """
        Add genres to db
        @param genres as [string]
        @param outside as bool
        @param sql as sqlite cursor
        @param return ([genre_ids], [new_genre_ids])
        @commit needed
    """
    def add_genres(self, genres, album_id, outside, sql):
        # Get all genre ids
        genre_ids = []
        new_genre_ids = []
        for genre in genres.split(';'):
            # Get genre id, add genre if missing
            genre_id = Lp.genres.get_id(genre, sql)
            if genre_id is None:
                Lp.genres.add(genre, outside, sql)
                genre_id = Lp.genres.get_id(genre, sql)
                new_genre_ids.append(genre_id)
            genre_ids.append(genre_id)

        for genre_id in genre_ids:
            Lp.albums.add_genre(album_id, genre_id, outside, sql)
        return (genre_ids, new_genre_ids)

    """
        Add album to db
        @param album name as string
        @param album artist id as int
        @param no album artist as bool
        @param path to an album track as string
        @param outside as bool
        @param sql as sqlite cursor
        @return (album id as int, new as bool)
        @commit needed
    """
    def add_album(self, album_name, artist_id, noaartist,
                  filepath, outside, sql):
        path = os.path.dirname(filepath)

        if noaartist:
            album_id = Lp.albums.get_compilation_id(album_name, sql)
        else:
            album_id = Lp.albums.get_id(album_name, artist_id, sql)
        if album_id is None:
            # If db was empty on scan,
            # use file modification time to get recents
            if self._is_empty:
                mtime = int(os.path.getmtime(filepath))
            # Use current time
            else:
                mtime = int(time())
            Lp.albums.add(album_name, artist_id, noaartist,
                               path, 0, outside, mtime, sql)
            if noaartist:
                album_id = Lp.albums.get_compilation_id(album_name, sql)
            else:
                album_id = Lp.albums.get_id(album_name, artist_id, sql)
        # Now we have our album id, check if path doesn't change
        if Lp.albums.get_path(album_id, sql) != path and not outside:
            Lp.albums.set_path(album_id, path, sql)

        # If no album artist, handle album artist id for compilations
        if noaartist:
            if Lp.albums.is_compilation(album_id, sql):
                Lp.albums.set_artist_id(album_id,
                                             Type.COMPILATIONS,
                                             sql)
            else:
                Lp.albums.set_artist_id(album_id,
                                             artist_id,
                                             sql)
        return album_id

    """
        Update album year
        @param album id as int
        @param sql as sqlite cursor
        @commit needed
    """
    def update_year(self, album_id, sql):
        year = Lp.albums.get_year_from_tracks(album_id, sql)
        Lp.albums.set_year(album_id, year, sql)

    """
        Set track artists/genres
        @param track id as int
        @param artist ids as [int]
        @param genre ids as [int]
        @param outside as bool
        @param sql as sqlite cursor
        @commit needed
    """
    def update_track(self, track_id, artist_ids, genre_ids, outside, sql):
         # Set artists/genres for track
        for artist_id in artist_ids:
            Lp.tracks.add_artist(track_id, artist_id, outside, sql)
        for genre_id in genre_ids:
            Lp.tracks.add_genre(track_id, genre_id, outside, sql)
