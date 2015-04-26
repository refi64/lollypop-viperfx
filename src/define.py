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

# This is global object initialised at lollypop start
# member init order is important!


class Objects_:
    settings = None
    db = None
    sql = None
    albums = None
    artists = None
    genres = None
    tracks = None
    playlists = None
    player = None
    art = None
    window = None
    notify = None
    debug = False


# Represent current playing track
class CurrentTrack:
    id = None
    title = None
    album_id = None
    album = None
    artist = None
    aartist_id = None
    aartist = None
    genre_id = None
    genre = None
    number = None
    duration = None
    path = None


# Represent what to do on next track
class NextContext:
    STOP_NONE = 0    # Continue playback
    STOP_TRACK = 1   # Stop after current track
    STOP_ALBUM = 2   # Stop after current album
    STOP_ARTIST = 3  # Stop after current artist


# Represent playback context
class PlayContext:
    album_id = None
    genre_id = None
    position = None
    next = NextContext.STOP_NONE


class GstPlayFlags:
    GST_PLAY_FLAG_VIDEO = 1 << 0  # We want video output
    GST_PLAY_FLAG_AUDIO = 1 << 1  # We want audio output
    GST_PLAY_FLAG_TEXT = 1 << 3   # We want subtitle output


class ArtSize_:
    SMALL_RADIUS = 2
    RADIUS = 3
    SMALL_BORDER = 1
    BORDER = 3
    SMALL = 32
    MEDIUM = 48
    BIG = 200
    MONSTER = 500


class Shuffle_:
    NONE = 0             # No shuffle
    TRACKS = 1           # Shuffle by tracks on genre
    ALBUMS = 2           # Shuffle by albums on genre
    TRACKS_ARTIST = 3    # Shuffle by tracks on artist
    ALBUMS_ARTIST = 4    # Shuffle by albums on artist


class Navigation_:
    COMPILATIONS = -1
    POPULARS = -2
    PLAYLISTS = -3
    ALL = -4
    RECENTS = -5
    NONE = -6
    DEVICES = -1000

Objects = Objects_()
ArtSize = ArtSize_()
Shuffle = Shuffle_()
Navigation = Navigation_()
