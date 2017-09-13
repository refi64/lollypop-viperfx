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

from gi.repository import Gst, GstPbutils, GLib, Gio

from re import match

from gettext import gettext as _

from lollypop.define import Lp
from lollypop.utils import format_artist_name, decode_all


class Discoverer:
    """
        Discover tags
    """

    def __init__(self):
        """
            Init tag reader
        """
        self.init_discoverer()

    def init_discoverer(self):
        """
            Init discover
        """
        GstPbutils.pb_utils_init()
        self._discoverer = GstPbutils.Discoverer.new(10*Gst.SECOND)

    def get_info(self, uri):
        """
            Return information for file at uri
            @param path as str
            @Exception GLib.Error
            @return GstPbutils.DiscovererInfo
        """
        info = self._discoverer.discover_uri(uri)
        return info


class TagReader(Discoverer):
    """
        Scanner tag reader
    """

    def __init__(self):
        """
            Init tag reader
        """
        Discoverer.__init__(self)

    def get_title(self, tags, filepath):
        """
            Return title for tags
            @param tags as Gst.TagList
            @param filepath as string
            @return title as string
        """
        if tags is None:
            return GLib.path_get_basename(filepath)
        (exists, title) = tags.get_string_index("title", 0)
        # We need to check tag is not just spaces
        if not exists or not title.strip(" "):
            title = GLib.path_get_basename(filepath)
        return title

    def get_artists(self, tags):
        """
            Return artists for tags
            @param tags as Gst.TagList
            @return string like "artist1;artist2;..."
        """
        if tags is None:
            return _("Unknown")
        artists = []
        for i in range(tags.get_tag_size("artist")):
            (exists, read) = tags.get_string_index("artist", i)
            # We need to check tag is not just spaces
            if exists and read.strip(" "):
                artists.append(read)
        return "; ".join(artists)

    def get_composers(self, tags):
        """
            Return composers for tags
            @param tags as Gst.TagList
            @return string like "composer1;composer2;..."
        """
        if tags is None:
            return _("Unknown")
        composers = []
        for i in range(tags.get_tag_size("composer")):
            (exists, read) = tags.get_string_index("composer", i)
            # We need to check tag is not just spaces
            if exists and read.strip(" "):
                composers.append(read)
        return "; ".join(composers)

    def get_performers(self, tags):
        """
            Return performers for tags
            @param tags as Gst.TagList
            @return string like "performer1;performer2;..."
        """
        if tags is None:
            return _("Unknown")
        performers = []
        for i in range(tags.get_tag_size("performer")):
            (exists, read) = tags.get_string_index("performer", i)
            # We need to check tag is not just spaces
            if exists and read.strip(" "):
                performers.append(read)
        return "; ".join(performers)

    def get_artist_sortnames(self, tags):
        """
            Return artist sort names
            @param tags as Gst.TagList
            @return artist sort names as string;string
        """
        if tags is None:
            return ""
        sortnames = []
        for i in range(tags.get_tag_size("artist-sortname")):
            (exists, read) = tags.get_string_index("artist-sortname", i)
            # We need to check tag is not just spaces
            if exists and read.strip(" "):
                sortnames.append(read)
        return "; ".join(sortnames)

    def get_album_artist_sortnames(self, tags):
        """
            Return album artist sort names
            @param tags as Gst.TagList
            @return artist sort names as string;string
        """
        if tags is None:
            return ""
        sortnames = []
        for i in range(tags.get_tag_size("album-artist-sortname")):
            (exists, read) = tags.get_string_index("album-artist-sortname", i)
            # We need to check tag is not just spaces
            if exists and read.strip(" "):
                sortnames.append(read)
        return "; ".join(sortnames)

    def get_album_artist(self, tags):
        """
            Return album artist for tags
            @param tags as Gst.TagList
            @return album artist as string or None
        """
        if tags is None:
            return _("Unknown")
        artists = []
        for i in range(tags.get_tag_size("album-artist")):
            (exists, read) = tags.get_string_index("album-artist", i)
            # We need to check tag is not just spaces
            if exists and read.strip(" "):
                artists.append(read)
        return "; ".join(artists)

    def get_album_name(self, tags):
        """
            Return album for tags
            @param tags as Gst.TagList
            @return album name as string
        """
        if tags is None:
            return _("Unknown")
        (exists, album_name) = tags.get_string_index("album", 0)
        # We need to check tag is not just spaces
        if not exists or not album_name.strip(" "):
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
        genres = []
        for i in range(tags.get_tag_size("genre")):
            (exists, read) = tags.get_string_index("genre", i)
            # We need to check tag is not just spaces
            if exists and read.strip(" "):
                genres.append(read)
        if not genres:
            return _("Unknown")
        return "; ".join(genres)

    def get_discname(self, tags):
        """
            Return disc name
            @param tags as Gst.TagList
            @return disc name as str
        """
        if tags is None:
            return 0
        discname = ""
        for i in range(tags.get_tag_size("extended-comment")):
            (exists, read) = tags.get_string_index("extended-comment", i)
            if exists and read.startswith("DISCSUBTITLE"):
                discname = read.replace("DISCSUBTITLE=", "")
                break
        return discname

    def get_discnumber(self, tags):
        """
            Return disc number for tags
            @param tags as Gst.TagList
            @return disc number as int
        """
        if tags is None:
            return 0
        (exists, discnumber) = tags.get_uint_index("album-disc-number", 0)
        if not exists:
            discnumber = 0
        return discnumber

    def get_tracknumber(self, tags, filename):
        """
            Return track number for tags
            @param tags as Gst.TagList
            @param filename as str
            @return track number as int
        """
        if tags is None:
            return 0
        (exists, tracknumber) = tags.get_uint_index("track-number", 0)
        if not exists:
            # Guess from filename
            m = match("^([0-9]*)[ ]*-", filename)
            if m:
                try:
                    tracknumber = int(m.group(1))
                except:
                    tracknumber = 0
            else:
                tracknumber = 0
        return min(abs(tracknumber), GLib.MAXINT32)

    def get_year(self, tags):
        """
            Return track year for tags
            @param tags as Gst.TagList
            @return track year as int or None
        """
        if tags is None:
            return None
        (exists, date) = tags.get_date_index("date", 0)
        if not exists:
            (exists, date) = tags.get_date_time_index("datetime", 0)
        if exists:
            year = date.get_year()
        else:
            year = None
        return year

    def get_original_year(self, tags):
        """
            Return original release year
            @param tags as Gst.TagList
            @return year as int or None
        """
        def get_id3():
            try:
                size = tags.get_tag_size("private-id3v2-frame")
                for i in range(0, size):
                    (exists, sample) = tags.get_sample_index(
                                                         "private-id3v2-frame",
                                                         i)
                    if not exists:
                        continue
                    (exists, m) = sample.get_buffer().map(Gst.MapFlags.READ)
                    if not exists:
                        continue
                    string = m.data.decode("utf-8")
                    if string.startswith("TDOR"):
                        split = string.split("\x00")
                        return int(split[-1][:4])
            except:
                pass
            return None

        def get_ogg():
            try:
                size = tags.get_tag_size("extended-comment")
                for i in range(0, size):
                    (exists, sample) = tags.get_string_index(
                                                         "extended-comment",
                                                         i)
                    if not exists or not sample.startswith("ORIGINALDATE="):
                        continue
                    # ORIGINALDATE=1999-03-10 => Only year
                    return int(sample[13:][:4])
            except:
                pass
            return None

        if tags is None:
            return None
        year = get_id3()
        if year is None:
            year = get_ogg()
        return year

    def get_lyrics(self, tags):
        """
            Return lyrics for tags
            @parma tags as Gst.TagList
            @return lyrics as str
        """
        def get_mp4():
            try:
                (exists, sample) = tags.get_string_index("lyrics", 0)
                if exists:
                    return sample
            except Exception as e:
                print("TagReader::get_mp4()", e)
            return ""

        def get_id3():
            try:
                size = tags.get_tag_size("private-id3v2-frame")
                for i in range(0, size):
                    (exists, sample) = tags.get_sample_index(
                                                         "private-id3v2-frame",
                                                         i)
                    if not exists:
                        continue
                    (exists, m) = sample.get_buffer().map(Gst.MapFlags.READ)
                    if not exists:
                        continue
                    string = decode_all(m.data)
                    if string.startswith("USLT"):
                        split = string.split("\x00")
                        return "".join(split[5:-1])
            except Exception as e:
                print("TagReader::get_id3()", e)
            return ""

        def get_ogg():
            try:
                size = tags.get_tag_size("extended-comment")
                for i in range(0, size):
                    (exists, sample) = tags.get_string_index(
                                                         "extended-comment",
                                                         i)
                    if not exists or not sample.startswith("LYRICS="):
                        continue
                    return sample[7:]
            except Exception as e:
                print("TagReader::get_ogg()", e)
            return ""

        if tags is None:
            return ""
        lyrics = get_mp4()
        if not lyrics:
            lyrics = get_id3()
        if not lyrics:
            lyrics = get_ogg()
        return lyrics

    def add_artists(self, artists, album_artists, sortnames):
        """
            Add artists to db
            @param artists as [string]
            @param album artists as [string]
            @param sortnames as [string]
            @return artist ids as [int]
            @commit needed
        """
        artist_ids = []
        sortsplit = sortnames.split(";")
        sortlen = len(sortsplit)
        i = 0
        for artist in artists.split(";"):
            artist = artist.strip()
            if artist != "":
                # Get artist id, add it if missing
                artist_id = Lp().artists.get_id(artist)
                if i >= sortlen or sortsplit[i] == "":
                    sortname = None
                else:
                    sortname = sortsplit[i].strip()
                if artist_id is None:
                    if sortname is None:
                        sortname = format_artist_name(artist)
                    artist_id = Lp().artists.add(artist, sortname)
                elif sortname is not None:
                    Lp().artists.set_sortname(artist_id, sortname)
                i += 1
                artist_ids.append(artist_id)
        return artist_ids

    def add_album_artists(self, artists, sortnames):
        """
            Add album artist to db
            @param artists as [string]
            @param sortnames as [string]
            @param artist ids as int
            @commit needed
        """
        artist_ids = []
        sortsplit = sortnames.split(";")
        sortlen = len(sortsplit)
        i = 0
        for artist in artists.split(";"):
            artist = artist.strip()
            if artist != "":
                # Get album artist id, add it if missing
                artist_id = Lp().artists.get_id(artist)
                if i >= sortlen or sortsplit[i] == "":
                    sortname = None
                else:
                    sortname = sortsplit[i].strip()
                if artist_id is None:
                    if sortname is None:
                        sortname = format_artist_name(artist)
                    artist_id = Lp().artists.add(artist, sortname)
                elif sortname is not None:
                    Lp().artists.set_sortname(artist_id, sortname)
                i += 1
                artist_ids.append(artist_id)
        return artist_ids

    def add_genres(self, genres):
        """
            Add genres to db
            @param genres as string
            @return genre ids as [int]
            @commit needed
        """
        # Get all genre ids
        genre_ids = []
        for genre in genres.split(";"):
            genre = genre.strip()
            if genre != "":
                # Get genre id, add genre if missing
                genre_id = Lp().genres.get_id(genre)
                if genre_id is None:
                    genre_id = Lp().genres.add(genre)
                genre_ids.append(genre_id)
        return genre_ids

    def add_album(self, album_name, artist_ids,
                  uri, loved, popularity, rate, remote):
        """
            Add album to db
            @param album name as string
            @param album artist ids as [int]
            @param uri to an album track as string
            @param year as int
            @param loved as bool
            @param popularity as int
            @param rate as int
            @param remote as bool
            @return (album id as int, new as bool)
            @commit needed
        """
        f = Gio.File.new_for_uri(uri)
        d = f.get_parent()
        if d is not None:
            parent_uri = d.get_uri()
        else:
            parent_uri = ""
        new = False
        album_id = Lp().albums.get_id(album_name, artist_ids, remote)
        if album_id is None:
            new = True
            album_id = Lp().albums.add(album_name, artist_ids, parent_uri,
                                       loved, popularity, rate)
        # Now we have our album id, check if path doesn"t change
        if Lp().albums.get_uri(album_id) != parent_uri:
            Lp().albums.set_uri(album_id, parent_uri)

        return (album_id, new)

    def update_album(self, album_id, artist_ids, genre_ids, mtime, year):
        """
            Set album artists
            @param album id as int
            @param artist ids as [int]
            @param genre ids as [int]
            @param mtime as int
            @param year as int
            @commit needed
        """
        # Set artist ids based on content
        if not artist_ids:
            Lp().albums.set_artist_ids(
                                    album_id,
                                    Lp().albums.calculate_artist_ids(album_id))
        # Update album genres
        for genre_id in genre_ids:
            Lp().albums.add_genre(album_id, genre_id, mtime)

        # Update year based on tracks
        year = Lp().albums.get_year_from_tracks(album_id)
        Lp().albums.set_year(album_id, year)

    def update_track(self, track_id, artist_ids, genre_ids, mtime):
        """
            Set track artists/genres
            @param track id as int
            @param artist ids as [int]
            @param genre ids as [int]
            @param mtime as int
            @param popularity as int
            @commit needed
        """
        # Set artists/genres for track
        for artist_id in artist_ids:
            Lp().tracks.add_artist(track_id, artist_id)
        for genre_id in genre_ids:
            Lp().tracks.add_genre(track_id, genre_id, mtime)
