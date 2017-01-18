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

from gi.repository import GObject, GLib

from threading import Thread
from time import time

from lollypop.sqlcursor import SqlCursor
from lollypop.tagreader import TagReader
from lollypop.web_youtube import WebYouTube
from lollypop.web_jgm90 import WebJmg90
from lollypop.define import Lp, DbPersistent, Type
from lollypop.lio import Lio


class Web(GObject.Object):
    """
        Web helper
    """

    __gsignals__ = {
        'saved': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        'progress': (GObject.SignalFlags.RUN_FIRST, None, (float,))
    }

    def play_track(track, play, callback):
        """
            Play track
            @param track as Track
            @param play as bool
            @param callback as func(uri: str, track: Track, play: bool)
        """
        if track.is_jgm:
            uri = WebJmg90.get_uri_content(track.uri)
        elif track.is_youtube:
            uri = WebYouTube.get_uri_content(track.uri)
        else:
            return
        GLib.idle_add(callback, uri, track, play)

    def __init__(self):
        """
            Init helper
        """
        GObject.Object.__init__(self)
        self.__helpers = [WebJmg90(), WebYouTube()]

    def save_track(self, item, persistent, genre_ids=[]):
        """
            Save item into collection as track
            @param item as SearchItem
            @param persistent as DbPersistent
            @param genre ids as [int]
        """
        t = Thread(target=self.__save_track_thread,
                   args=(item, persistent, genre_ids))
        t.daemon = True
        t.start()

    def save_album(self, item, persistent, genre_ids=[]):
        """
            Save item into collection as album
            @param item as SearchItem
            @param persistent as DbPersistent
            @param genre ids as [int]
        """
        t = Thread(target=self.save_album_thread,
                   args=(item, persistent, genre_ids))
        t.daemon = True
        t.start()

    def save_album_thread(self, item, persistent, genre_ids):
        """
            Save item into collection as album
            @param item as SearchItem
            @param persistent as DbPersistent
            @param genre ids as [int]
            @thread safe
        """
        nb_items = len(item.subitems)
        # Should not happen but happen :-/
        if nb_items == 0:
            return
        start = 0
        album_artist = item.subitems[0].artists[0]
        album_id = None
        for track_item in item.subitems:
            (album_id, track_id) = self.__save_track(track_item, persistent,
                                                     album_artist, genre_ids)
            if track_id is not None:
                # Download cover
                if start == 0:
                    t = Thread(target=self.__save_cover, args=(item, album_id))
                    t.daemon = True
                    t.start()
            start += 1
            GLib.idle_add(self.emit, "progress", start / nb_items)
        GLib.idle_add(self.emit, "progress", 1)
        if Lp().settings.get_value('artist-artwork'):
            Lp().art.cache_artists_info()
        if album_id is not None:
            GLib.idle_add(self.emit, "saved", album_id)

#######################
# PRIVATE             #
#######################
    def __save_track_thread(self, item, persistent, genre_ids):
        """
            Save item into collection as track
            @param item as SearchItem
            @param persistent as DbPersistent
            @param genre ids as [int]
        """
        album_artist = item.artists[0]
        (album_id, track_id) = self.__save_track(item, persistent,
                                                 album_artist, genre_ids)
        if track_id is None:
            return
        self.__save_cover(item, album_id)
        if Lp().settings.get_value('artist-artwork'):
            Lp().art.cache_artists_info()
        GLib.idle_add(self.emit, "saved", track_id)

    def __save_track(self, item, persistent, album_artist, genre_ids):
        """
            Save item into collection as track
            @param item as SearchItem
            @param persistent as DbPersistent
            @param album artist as str
            @param genre ids as [int]
            @return (album id as int, track id as int)
        """
        t = TagReader()
        # Get uri from helpers
        for helper in self.__helpers:
            uri = helper.get_uri(item)
            if uri:
                break
        # Don't found anything
        if not uri:
            return (None, None)

        track_id = Lp().tracks.get_id_by_uri(uri)

        # Check if track needs to be updated
        if track_id is not None:
            if Lp().tracks.get_persistent(track_id) == DbPersistent.NONE\
                    and persistent == DbPersistent.EXTERNAL:
                Lp().tracks.set_persistent(track_id, DbPersistent.EXTERNAL)
                return (None, None)
            album_id = Lp().tracks.get_album_id(track_id)
            t.update_track(track_id, [], genre_ids)
            t.update_album(album_id, [], genre_ids, None)
            return (None, None)

        with SqlCursor(Lp().db) as sql:
            # Happen often with Itunes/Spotify
            if album_artist not in item.artists:
                item.artists.append(album_artist)
            artists = "; ".join(item.artists)
            artist_ids = t.add_artists(artists, album_artist, "")
            album_artist_ids = t.add_album_artists(album_artist, "")
            (album_id, new_album) = t.add_album(item.album.name,
                                                album_artist_ids, "",
                                                False, item.album.popularity,
                                                0, int(time()), True)
            # FIXME: Check this, could move this in add_album()
            if new_album:
                Lp().albums.set_synced(album_id, Type.NONE)

            if persistent == DbPersistent.CHARTS:
                genre_ids.append(Type.CHARTS)
                new_artist_ids = []
            else:
                new_artist_ids = list(set(artist_ids) | set(album_artist_ids))

            # Add track to db
            track_id = Lp().tracks.add(item.name, uri, item.duration,
                                       0, item.discnumber, "", album_id,
                                       item.year, item.popularity,
                                       0, 0, persistent)
            t.update_track(track_id, artist_ids, genre_ids)
            t.update_album(album_id, album_artist_ids, genre_ids, None)
            sql.commit()

        if persistent != DbPersistent.CHARTS:
            for genre_id in genre_ids:
                GLib.idle_add(Lp().scanner.emit,
                              'genre-updated', genre_id, True)
            for artist_id in new_artist_ids:
                GLib.idle_add(Lp().scanner.emit,
                              'artist-updated', artist_id, True)
        return (album_id, track_id)

    def __save_cover(self, item, album_id):
        """
            Save cover to store
            @param item as SearchItem
            @param album id as int
        """
        f = Lio.File.new_for_uri(item.cover)
        (status, data, tag) = f.load_contents(None)
        if status:
            Lp().art.save_album_artwork(data, album_id)
