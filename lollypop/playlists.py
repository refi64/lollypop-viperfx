# Copyright (c) 2014-2018 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import GObject, GLib, Gio, TotemPlParser

from gettext import gettext as _
import itertools
import sqlite3
from datetime import datetime
from threading import Lock

from lollypop.database import Database
from lollypop.define import App, Type
from lollypop.objects import Track
from lollypop.logger import Logger
from lollypop.sqlcursor import SqlCursor
from lollypop.localized import LocalizedCollation
from lollypop.shown import ShownPlaylists
from lollypop.database_upgrade import DatabasePlaylistsUpgrade


class Playlists(GObject.GObject):
    """
        Playlists manager
    """
    __LOCAL_PATH = GLib.get_user_data_dir() + "/lollypop"
    _DB_PATH = "%s/playlists.db" % __LOCAL_PATH
    __gsignals__ = {
        # Add or remove a playlist
        "playlists-changed": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        # Objects added/removed to/from playlist
        "playlist-add": (GObject.SignalFlags.RUN_FIRST, None, (int, int, int)),
        "playlist-del": (GObject.SignalFlags.RUN_FIRST, None, (int, int))
    }
    __create_playlists = """CREATE TABLE playlists (
                            id INTEGER PRIMARY KEY,
                            name TEXT NOT NULL,
                            mtime BIGINT NOT NULL)"""

    __create_tracks = """CREATE TABLE tracks (
                        playlist_id INT NOT NULL,
                        uri TEXT NOT NULL)"""

    def __init__(self):
        """
            Init playlists manager
        """
        self.thread_lock = Lock()
        GObject.GObject.__init__(self)
        self.LOVED = _("Loved tracks")
        upgrade = DatabasePlaylistsUpgrade()
        # Create db schema
        f = Gio.File.new_for_path(self._DB_PATH)
        if not f.query_exists():
            try:
                with SqlCursor(self) as sql:
                    sql.execute(self.__create_playlists)
                    sql.execute(self.__create_tracks)
                    sql.execute("PRAGMA user_version=%s" % upgrade.version)
            except:
                pass
        else:
            upgrade.upgrade(self)

    def add(self, name):
        """
            Add a playlist
            @param playlist name as str
            @return playlist_id as int
            @thread safe
        """
        with SqlCursor(self) as sql:
            result = sql.execute("INSERT INTO playlists (name, mtime)"
                                 " VALUES (?, ?)",
                                 (name, datetime.now().strftime("%s")))
            GLib.idle_add(self.emit, "playlists-changed", result.lastrowid)
            return result.lastrowid

    def exists(self, playlist_id):
        """
            Return True if playlist exists
            @param playlist id as int
            @param bool
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT rowid\
                                  FROM playlists\
                                  WHERE rowid=?",
                                 (playlist_id,))
            v = result.fetchone()
            if v is not None:
                return True
            else:
                return False

    def rename(self, old_name, new_name):
        """
            Rename playlist
            @param old_name as str
            @param new_name as str
        """
        with SqlCursor(self) as sql:
            playlist_id = self.get_id(old_name)
            sql.execute("UPDATE playlists\
                        SET name=?\
                        WHERE name=?",
                        (new_name, old_name))
            GLib.idle_add(self.emit, "playlists-changed", playlist_id)

    def delete(self, name):
        """
            delete playlist
            @param playlist name as str
        """
        with SqlCursor(self) as sql:
            playlist_id = self.get_id(name)
            sql.execute("DELETE FROM playlists\
                        WHERE name=?",
                        (name,))
            sql.execute("DELETE FROM tracks\
                        WHERE playlist_id=?",
                        (playlist_id,))
            GLib.idle_add(self.emit, "playlists-changed", playlist_id)

    def remove(self, uri):
        """
            Remove track from playlists
            @param uri as str
        """
        with SqlCursor(self) as sql:
            sql.execute("DELETE FROM tracks\
                        WHERE uri=?",
                        (uri,))

    def get(self):
        """
            Return availables playlists
            @return array of (id, string)
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT rowid, name\
                                  FROM playlists\
                                  ORDER BY name\
                                  COLLATE NOCASE COLLATE LOCALIZED")
            return list(result)

    def get_ids(self):
        """
            Return availables playlists
            @return [int]
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT rowid\
                                  FROM playlists\
                                  ORDER BY name\
                                  COLLATE NOCASE COLLATE LOCALIZED")
            return list(itertools.chain(*result))

    def get_last(self):
        """
            Return 6 last modified playlist
            @return [string]
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT rowid, name\
                                  FROM playlists\
                                  ORDER BY mtime DESC\
                                  LIMIT 6")
            return list(result)

    def get_tracks(self, playlist_id):
        """
            Return availables tracks for playlist
            If playlist name == Type.ALL, then return all tracks from db
            @param playlist name as str
            @return [str]
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT uri\
                                  FROM tracks\
                                  WHERE playlist_id=?", (playlist_id,))
            return list(itertools.chain(*result))

    def get_track_ids(self, playlist_id):
        """
            Return availables track ids for playlist
            If playlist name == Type.ALL, then return all tracks from db
            @param playlist id as int
            @return array of track id as int
        """
        track_ids = []
        if playlist_id == Type.POPULARS:
            track_ids = App().tracks.get_rated()
            for track in App().tracks.get_populars():
                track_ids.append(track)
        elif playlist_id == Type.RECENTS:
            track_ids = App().tracks.get_recently_listened_to()
        elif playlist_id == Type.NEVER:
            track_ids = App().tracks.get_never_listened_to()
        elif playlist_id == Type.RANDOMS:
            track_ids = App().tracks.get_randoms()
        else:
            with SqlCursor(self) as sql:
                result = sql.execute("SELECT music.tracks.rowid\
                                      FROM tracks, music.tracks\
                                      WHERE tracks.playlist_id=?\
                                      AND music.tracks.uri=\
                                      main.tracks.uri",
                                     (playlist_id,))
                track_ids = list(itertools.chain(*result))
        return track_ids

    def get_duration(self, playlist_id):
        """
            Return playlist duration
            @param playlist_id as int
            @return duration as int
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT SUM(music.tracks.duration)\
                                  FROM tracks, music.tracks\
                                  WHERE tracks.playlist_id=?\
                                  AND music.tracks.uri=\
                                  main.tracks.uri",
                                 (playlist_id,))
            v = result.fetchone()
            if v is not None and v[0] is not None:
                return v[0]
            return 0

    def get_track_ids_sorted(self, playlist_id):
        """
            Return availables track ids for playlist sorted by artist/album
            If playlist name == Type.ALL, then return all tracks from db
            @param playlist id as int
            @return array of track id as int
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT music.tracks.rowid\
                                  FROM tracks, music.tracks,\
                                  music.track_artists, music.artists\
                                  WHERE tracks.playlist_id=?\
                                  AND music.track_artists.track_id=\
                                  music.tracks.rowid\
                                  AND music.artists.id=\
                                  music.track_artists.artist_id\
                                  AND music.tracks.uri=\
                                  main.tracks.uri\
                                  ORDER BY\
                                  music.artists.sortname, album_id",
                                 (playlist_id,))
            return list(itertools.chain(*result))

    def get_id(self, playlist_name):
        """
            Get playlist id
            @param playlist name as str
            @return playlst id as int
        """
        if playlist_name == self.LOVED:
            return Type.LOVED

        with SqlCursor(self) as sql:
            result = sql.execute("SELECT rowid\
                                 FROM playlists\
                                 WHERE name=?", (playlist_name,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return Type.NONE

    def get_name(self, playlist_id):
        """
            Get playlist name
            @param playlist id as int
            @return playlist name as str
        """
        if playlist_id == Type.LOVED:
            return self.LOVED
        elif playlist_id < 0:
            for (id, name) in ShownPlaylists.get(True):
                if id == playlist_id:
                    return name

        with SqlCursor(self) as sql:
            result = sql.execute("SELECT name\
                                 FROM playlists\
                                 WHERE rowid=?", (playlist_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return ""

    def get_names(self, playlist_ids):
        """
            Return playlist names
            @param playlist_ids as [int]
            @return names as [str]
        """
        names = []
        for playlist_id in playlist_ids:
            if playlist_id == Type.POPULARS:
                names.append(_("Popular tracks"))
            elif playlist_id == Type.RECENTS:
                names.append(_("Recently played"))
            elif playlist_id == Type.NEVER:
                names.append(_("Never played"))
            elif playlist_id == Type.RANDOMS:
                names.append(_("Random tracks"))
            elif playlist_id == Type.SEARCH:
                names.append(_("Search"))
            else:
                names.append(self.get_name(playlist_id))
        return names

    def get_synced(self, playlist_id):
        """
            True if playlist synced
            @param playlist_id as int
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT synced\
                                 FROM playlists\
                                 WHERE rowid=?", (playlist_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return False

    def get_synced_ids(self):
        """
            Return availables synced playlists
            @return [int]
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT rowid\
                                  FROM playlists\
                                  WHERE synced=1\
                                  ORDER BY name\
                                  COLLATE NOCASE COLLATE LOCALIZED")
            return list(itertools.chain(*result))

    def set_synced(self, playlist_id, synced):
        """
            Mark playlist as synced
            @param playlist_id as int
            @param synced as bool
        """
        with SqlCursor(self) as sql:
            sql.execute("UPDATE playlists\
                        SET synced=?\
                        WHERE rowid=?",
                        (synced, playlist_id))

    def clear(self, playlist_id, notify=True):
        """
            Clear playlsit
            @param playlist id as int
            @param notify as bool
        """
        with SqlCursor(self) as sql:
            sql.execute("DELETE FROM tracks\
                         WHERE playlist_id=?", (playlist_id,))
            if notify:
                GLib.idle_add(self.emit, "playlist-del", playlist_id, None)

    def add_tracks(self, playlist_id, tracks, notify=True):
        """
            Add tracks to playlist if not already present
            @param playlist id as int
            @param tracks as [Track]
            @param notify as bool
        """
        with SqlCursor(self) as sql:
            changed = False
            for track in tracks:
                if not self.exists_track(playlist_id, track):
                    changed = True
                    sql.execute("INSERT INTO tracks"
                                " VALUES (?, ?)",
                                (playlist_id, track.uri))
                if notify:
                    GLib.idle_add(self.emit, "playlist-add",
                                  playlist_id, track.id, -1)
            if changed:
                sql.execute("UPDATE playlists SET mtime=?\
                             WHERE rowid=?", (datetime.now().strftime("%s"),
                                              playlist_id))

    def add_uris(self, playlist_id, uris):
        """
            Add uris to playlists (even if exists)
            @param playlist id as int
            @param uris as [str]
        """
        with SqlCursor(self) as sql:
            for uri in uris:
                sql.execute("INSERT INTO tracks"
                            " VALUES (?, ?)",
                            (playlist_id, uri))
            sql.execute("UPDATE playlists SET mtime=?\
                         WHERE rowid=?", (datetime.now().strftime("%s"),
                                          playlist_id))

    def remove_tracks(self, playlist_id, tracks, notify=True):
        """
            Remove tracks from playlist
            @param playlist id as int
            @param tracks as [Track]
        """
        with SqlCursor(self) as sql:
            for track in tracks:
                sql.execute("DELETE FROM tracks\
                             WHERE uri=?\
                             AND playlist_id=?", (track.uri, playlist_id))
                if notify:
                    GLib.idle_add(self.emit, "playlist-del",
                                  playlist_id, track.id)

    def import_uri(self, playlist_id, uri, start=None, down=True):
        """
            Import uri in playlist
            @param playlist id as int
            @param uri as str
            @param start track id as int
            @param down as bool
        """
        try:
            uri = uri.strip("\n\r")
            f = Gio.File.new_for_uri(uri)
            if f.query_exists():
                if f.query_file_type(Gio.FileQueryInfoFlags.NONE,
                                     None) == Gio.FileType.DIRECTORY:
                    walk_uris = [uri]
                    track_ids = []
                    while walk_uris:
                        uri = walk_uris.pop(0)
                        try:
                            d = Gio.File.new_for_uri(uri)
                            infos = d.enumerate_children(
                                "standard::name,standard::type",
                                Gio.FileQueryInfoFlags.NONE,
                                None)
                        except Exception as e:
                            Logger.info("Playlists::import_uri(): %s" % e)
                            continue
                        for info in infos:
                            f = infos.get_child(info)
                            if info.get_file_type() == Gio.FileType.DIRECTORY:
                                walk_uris.append(f.get_uri())
                            else:
                                track_id = App().tracks.get_id_by_uri(
                                    f.get_uri())
                                if track_id is not None:
                                    track_ids.append(track_id)
                else:
                    track_id = App().tracks.get_id_by_uri(uri)
                    track_ids = [track_id]
                tracks = []
                if start is None:
                    for track_id in track_ids:
                        tracks.append(Track(track_id))
                    self.add_tracks(playlist_id, tracks)
                else:
                    # Insert at wanted position
                    playlist_track_ids = self.get_track_ids(playlist_id)
                    start_idx = playlist_track_ids.index(start)
                    if down:
                        start_idx += 1
                    for track_id in track_ids:
                        playlist_track_ids.insert(start_idx, track_id)
                        GLib.idle_add(self.emit, "playlist-add",
                                      playlist_id, track_id, start_idx)
                        start_idx += 1
                    self.clear(playlist_id, False)
                    tracks = []
                    for track_id in playlist_track_ids:
                        tracks.append(Track(track_id))
                    self.add_tracks(playlist_id, tracks, False)
        except:
            pass

    def get_position(self, playlist_id, track_id):
        """
            Get track position in playlist
            @param playlist id as int
            @param track id as int
            @return position as int
        """
        i = 0
        for tid in self.get_track_ids(playlist_id):
            if track_id == tid:
                break
            i += 1
        return i

    def exists_track(self, playlist_id, track):
        """
            Check if track id exist in playlist
            @param playlist id as int
            @param track as Track
            @return bool
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT main.tracks.uri\
                                  FROM tracks, music.tracks\
                                  WHERE music.tracks.rowid=?\
                                  AND playlist_id=?\
                                  AND music.tracks.uri=\
                                  main.tracks.uri",
                                 (track.id, playlist_id))
            v = result.fetchone()
            if v is not None:
                return True
            return False

    def exists_album(self, playlist_id, album):
        """
            Return True if object_id is already present in playlist
            @param playlist id as int
            @param album as Album/Disc
            @return bool
        """
        # We do not use Album object for performance reasons
        playlist_uris = self.get_tracks(playlist_id)
        track_uris = album.track_uris
        return len(set(playlist_uris) & set(track_uris)) == len(track_uris)

    def import_tracks(self, f):
        """
            Import file as playlist
            @param f as Gio.File
        """
        basename = ".".join(f.get_basename().split(".")[:-1])
        parser = TotemPlParser.Parser.new()
        playlist_id = self.get_id(basename)
        # FIXME Why Type.NONE? Need to check old code
        if playlist_id == Type.NONE:
            playlist_id = self.add(basename)
            tracks = []
            parser.connect("entry-parsed", self.__on_entry_parsed,
                           playlist_id, tracks)
            parser.parse_async(f.get_uri(), True,
                               None, self.__on_parse_finished,
                               playlist_id, tracks)

    def get_cursor(self):
        """
            Return a new sqlite cursor
        """
        try:
            sql = sqlite3.connect(self._DB_PATH, 600.0)
            sql.execute('ATTACH DATABASE "%s" AS music' % Database.DB_PATH)
            sql.create_collation("LOCALIZED", LocalizedCollation())
            return sql
        except:
            exit(-1)

#######################
# PRIVATE             #
#######################
    def __on_parse_finished(self, parser, result, playlist_id, uris):
        """
            Add tracks to playlists
            @param parser as TotemPlParser.Parser
            @param result as Gio.AsyncResult
            @param playlist_id as int
            @param uris as [str]
        """
        self.add_uris(playlist_id, uris)

    def __on_entry_parsed(self, parser, uri, metadata, playlist_id, uris):
        """
            Play stream
            @param parser as TotemPlParser.Parser
            @param track uri as str
            @param metadata as GLib.HastTable
            @param playlist_id as int
            @param uris as [str]
        """
        uris.append(uri)
