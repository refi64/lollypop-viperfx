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

from gi.repository import GLib

from os import path

from lollypop.define import Lp, Type
from lollypop.utils import translate_artist_name


# Represent a atrack
class Track:
    """
        Init track
        @param track_id as int
        @param sql as sqlite cursor
    """
    def __init__(self, track_id=None, sql=None):
        self.uri = None
        if track_id is None:
            self.id = None
            self.title = ''
            self.album_id = None
            self.album = ''
            self.artist = ''
            self.aartist_id = None
            self.aartist = ''
            self.genre_id = None
            self.genre = ''
            self.number = 0
            self.duration = 0.0
        else:
            self.id = track_id
            self.title = Lp.tracks.get_name(self.id,
                                                 sql)
            self.album_id = Lp.tracks.get_album_id(track_id,
                                                        sql)
            self.album = Lp.albums.get_name(self.album_id,
                                                 sql)
            self.aartist_id = Lp.tracks.get_aartist_id(track_id,
                                                            sql)
            self.aartist = translate_artist_name(
                                            Lp.artists.get_name(
                                                           self.aartist_id,
                                                           sql))
            artist_name = ""
            for artist_id in Lp.tracks.get_artist_ids(self.id, sql):
                artist_name += translate_artist_name(
                                Lp.artists.get_name(artist_id, sql)) +\
                                ", "
            self.artist = artist_name[:-2]
            self.genre = Lp.albums.get_genre_name(self.album_id,
                                                       sql)
            self.duration = Lp.tracks.get_length(self.id, sql)
            self.number = Lp.tracks.get_number(self.id, sql)
            filepath = Lp.tracks.get_path(self.id, sql)
            if path.exists(filepath):
                self.uri = GLib.filename_to_uri(filepath)

    """
        Set radio
        @param name as string
        @param uri as string
    """
    def set_radio(self, name, uri):
        self.id = Type.RADIOS
        self.artist = name
        self.uri = uri
