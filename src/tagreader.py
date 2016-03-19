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

import gi
gi.require_version('GstPbutils', '1.0')
from gi.repository import GLib, Gst, GstPbutils

import os

from gettext import gettext as _

from lollypop.define import Lp, Type
from lollypop.utils import format_artist_name


class TagReader:
    """
        Read tags from file
    """

    def __init__(self):
        """
            Init tag reader
        """
        self._index = 0
        self.init_discover()

    def init_discover(self):
        """
            Init discover
        """
        GstPbutils.pb_utils_init()
        self._tagreader = GstPbutils.Discoverer.new(10*Gst.SECOND)

    def get_infos(self, path):
        """
            Return informations on file at path
            @param path as str
            @Exception GLib.Error
            @return GstPbutils.DiscovererInfo
        """
        uri = GLib.filename_to_uri(path)
        infos = self._tagreader.discover_uri(uri)
        return infos


class ScannerTagReader(TagReader):
    """
        Scanner tag reader
    """

    def __init__(self):
        """
            Init tag reader
        """
        TagReader.__init__(self)

    def get_title(self, tags, filepath):
        """
            Return title for tags
            @param tags as Gst.TagList
            @param filepath as string
            @return title as string
        """
        if tags is None:
            return os.path.basename(filepath)
        (exists, title) = tags.get_string_index('title', self._index)
        if not exists:
            title = os.path.basename(filepath)
        return title

    def get_artists(self, tags):
        """
            Return artists for tags
            @param tags as Gst.TagList
            @return string like "artist1;artist2;..."
        """
        if tags is None:
            return _("Unknown")
        (exists, artists) = tags.get_string_index('artist', self._index)
        if not exists:
            artists = ""
        return artists

    def get_artist_sortnames(self, tags):
        """
            Return artist sort name
            @param tags as Gst.TagList
            @return artist sort names as string;string
        """
        if tags is not None:
            (exists, sortnames) = tags.get_string_index('artist-sortname',
                                                        self._index)
        if not exists:
            sortnames = ""
        return sortnames

    def get_album_artist(self, tags):
        """
            Return album artist for tags
            @param tags as Gst.TagList
            @return album artist as string or None
        """
        if tags is None:
            return _("Unknown")
        (exists, artist) = tags.get_string_index('album-artist', self._index)
        if not exists:
            artist = ""
        return artist

    def get_album_name(self, tags):
        """
            Return album for tags
            @param tags as Gst.TagList
            @return album name as string
        """
        if tags is None:
            return _("Unknown")
        (exists, album_name) = tags.get_string_index('album', self._index)
        if not exists:
            album_name = _("Unknown")
        return album_name

    def get_genres(self, tags):
        """
            Return genres for tags
            @param tags as Gst.TagList
            @return string like "genre1;genre2;..."
        """
        if tags is None:
            return _("Unknown")
        (exists, genres) = tags.get_string_index('genre', self._index)
        if not exists:
            genres = _("Unknown")
        return genres

    def get_discnumber(self, tags):
        """
            Return disc number for tags
            @param tags as Gst.TagList
            @return disc number as int
        """
        if tags is None:
            return 0
        (exists, discnumber) = tags.get_uint_index('album-disc-number',
                                                   self._index)
        if not exists:
            discnumber = 0
        return discnumber

    def get_tracknumber(self, tags):
        """
            Return track number for tags
            @param tags as Gst.TagList
            @return track number as int
        """
        if tags is None:
            return 0
        (exists, tracknumber) = tags.get_uint_index('track-number',
                                                    self._index)
        if not exists:
            tracknumber = 0
        return tracknumber

    def get_year(self, tags):
        """
            Return track year for tags
            @param tags as Gst.TagList
            @return track year as int or None
        """
        if tags is None:
            return None
        (exists, date) = tags.get_date_index('date', self._index)
        if not exists:
            (exists, date) = tags.get_date_time_index('datetime',
                                                      self._index)
        if exists:
            year = date.get_year()
        else:
            year = None
        return year

    def add_artists(self, artists, album_artists, sortnames):
        """
            Add artists to db
            @param artists as [string]
            @param album artists as [string]
            @param sortnames as [string]
            @commit needed
            @param return ([artist ids as int], [new artist ids as int])
        """
        new_artist_ids = []
        artist_ids = []
        sortsplit = sortnames.split(';')
        sortlen = len(sortsplit)
        i = 0
        for artist in artists.split(';'):
            # Get artist id, add it if missing
            artist_id = Lp().artists.get_id(artist)
            if i >= sortlen or sortsplit[i] == "":
                sortname = format_artist_name(artist)
            else:
                sortname = sortsplit[i]
            if artist_id is None:
                artist_id = Lp().artists.add(artist, sortname)
                if artist in album_artists:
                    new_artist_ids.append(artist_id)
            else:
                Lp().artists.set_sortname(artist_id, sortname)
            i += 1
            artist_ids.append(artist_id)
        return (artist_ids, new_artist_ids)

    def add_album_artists(self, artists):
        """
            Add album artist to db
            @param artists as [string]
            @param return ([album artist ids as int], [new as bool])
            @commit needed
        """
        artist_ids = []
        new_artist_ids = []
        for artist in artists.split(';'):
            if artist != '':
                # Get album artist id, add it if missing
                artist_id = Lp().artists.get_id(artist)
                if artist_id is None:
                    album_artist_id = Lp().artists.add(artist,
                                                       format_artist_name(
                                                                       artist))
                    artist_ids.append(album_artist_id)
                    new_artist_ids.append(album_artist_id)
                else:
                    artist_ids.append(artist_id)
        return (artist_ids, new_artist_ids)

    def add_genres(self, genres, album_id):
        """
            Add genres to db
            @param genres as [string]
            @param return ([genre_ids], [new_genre_ids])
            @commit needed
        """
        # Get all genre ids
        genre_ids = []
        new_genre_ids = []
        for genre in genres.split(';'):
            # Get genre id, add genre if missing
            genre_id = Lp().genres.get_id(genre)
            if genre_id is None:
                genre_id = Lp().genres.add(genre)
                new_genre_ids.append(genre_id)
            genre_ids.append(genre_id)
        return (genre_ids, new_genre_ids)

    def add_album(self, album_name, artist_ids, no_album_artist,
                  year, filepath, popularity, mtime):
        """
            Add album to db
            @param album name as string
            @param album artist ids as [int]
            @param no album artist as bool
            @param path to an album track as string
            @param year as int
            @param popularity as int
            @param mtime as int
            @return (album id as int, new as bool)
            @commit needed
        """
        path = os.path.dirname(filepath)
        new = False
        if no_album_artist:
            album_id = Lp().albums.get_compilation_id(album_name, year)
        else:
            album_id = Lp().albums.get_non_compilation_id(album_name,
                                                          artist_ids,
                                                          year)
        if album_id is None:
            new = True
            album_id = Lp().albums.add(album_name, artist_ids, no_album_artist,
                                       year, path, popularity, mtime)
        # Now we have our album id, check if path doesn't change
        if Lp().albums.get_path(album_id) != path:
            Lp().albums.set_path(album_id, path)

        # If no album artist, handle album artist id for compilations
        if no_album_artist:
            if Lp().albums.is_compilation(album_id):
                Lp().albums.set_artist_ids(album_id,
                                           [Type.COMPILATIONS])
            else:
                Lp().albums.set_artist_ids(album_id,
                                           artist_ids)
        return (album_id, new)

    def update_album(self, album_id, artist_ids, genre_ids):
        """
            Set album artists
            @param album id as int
            @param artist ids as [int]
            @param genre ids as [int]
            @commit needed
        """
        # Set artists/genres for album
        for artist_id in artist_ids:
            Lp().albums.add_artist(album_id, artist_id)
        for genre_id in genre_ids:
            Lp().albums.add_genre(album_id, genre_id)

    def update_track(self, track_id, artist_ids, genre_ids):
        """
            Set track artists/genres
            @param track id as int
            @param artist ids as [int]
            @param genre ids as [int]
            @commit needed
        """
        # Set artists/genres for track
        for artist_id in artist_ids:
            Lp().tracks.add_artist(track_id, artist_id)
        for genre_id in genre_ids:
            Lp().tracks.add_genre(track_id, genre_id)
