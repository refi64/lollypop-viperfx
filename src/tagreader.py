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


# Tag reader class
class TagReader:
    """
        Init tag reader
    """
    def __init__(self):
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

    """
        Return title for tags
        @param tags as Gst.TagList
        @param filepath as string
        @return title as string
    """
    def get_title(self, tags, filepath):
        (exist, title) = tags.get_string_index('title', 0)
        if not exist:
            title = os.path.basename(filepath)
        return title

    """
        Return artists for tags
        @param tags as Gst.TagList
        @return array of string
    """
    def get_artists(self, tags):
        artists = []
        size = tags.get_tag_size('artist')
        if size == 0:
            artists.append(_("Unknown"))
        else:
            for i in range(0, size):
                (exist, artist) = tags.get_string_index('artist', i)
                artists.append(artist)
        return artists

    """
        Return album artist for tags
        @param tags as Gst.TagList
        @return album artist as string or None
    """
    def get_album_artist(self, tags):
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
        (exist, album_name) = tags.get_string_index('album', 0)
        if not exist:
            album_name = _("Unknown")
        return album_name

    """
        Return genres for tags
        @param tags as Gst.TagList
        @return array of string
    """
    def get_genres(self, tags):
        genres = []
        size = tags.get_tag_size('genre')
        if size == 0:
            genres.append(_("Unknown"))
        else:
            for i in range(0, size):
                (exist, genre) = tags.get_string_index('genre', i)
                genres.append(genre)
        return genres

    """
        Return disc number for tags
        @param tags as Gst.TagList
        @return disc number as int
    """
    def get_discnumber(self, tags):
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
        (exist, datetime) = tags.get_date_time('datetime')
        if exist:
            year = datetime.get_year()
        else:
            year = None
        return year


