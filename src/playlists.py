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

import os
from gettext import gettext as _
import itertools
import sqlite3
from datetime import datetime

from lollypop.database import Database
from lollypop.define import Lp, Type
from lollypop.objects import Track
from lollypop.sqlcursor import SqlCursor
from lollypop.localized import LocalizedCollation


class Playlists(GObject.GObject):
    """
        Playlists manager
    """
    LOCAL_PATH = os.path.expanduser("~") + "/.local/share/lollypop"
    DB_PATH = "%s/playlists.db" % LOCAL_PATH
    __gsignals__ = {
        # Add or remove a playlist
        'playlists-changed': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        # Objects added/removed to/from playlist
        'playlist-add': (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
        'playlist-del': (GObject.SignalFlags.RUN_FIRST, None, (int, int))
    }
    create_playlists = '''CREATE TABLE playlists (
                            id INTEGER PRIMARY KEY,
                            name TEXT NOT NULL,
                            mtime BIGINT NOT NULL)'''

    create_tracks = '''CREATE TABLE tracks (
                        playlist_id INT NOT NULL,
                        filepath TEXT NOT NULL)'''

    def __init__(self):
        """
            Init playlists manager
        """
        GObject.GObject.__init__(self)
        self._LOVED = _("Loved tracks")
        # Create db schema
        try:
            with SqlCursor(self) as sql:
                sql.execute(self.create_playlists)
                sql.execute(self.create_tracks)
                sql.commit()
        except:
            pass

    def add(self, name):
        """
            Add a playlist
            @param playlist name as str
            @thread safe
        """
        with SqlCursor(self) as sql:
            result = sql.execute("INSERT INTO playlists (name, mtime)"
                                 " VALUES (?, ?)",
                                 (name, datetime.now().strftime('%s')))
            sql.commit()
            GLib.idle_add(self.emit, 'playlists-changed', result.lastrowid)

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

    def rename(self, new_name, old_name):
        """
            Rename playlist
            @param new playlist name as str
            @param old playlist name as str
        """
        with SqlCursor(self) as sql:
            playlist_id = self.get_id(old_name)
            sql.execute("UPDATE playlists\
                        SET name=?\
                        WHERE name=?",
                        (new_name, old_name))
            sql.commit()
            GLib.idle_add(self.emit, 'playlists-changed', playlist_id)

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
            sql.commit()
            GLib.idle_add(self.emit, 'playlists-changed', playlist_id)

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
            @return array of paths as [str]
        """
        with SqlCursor(self) as sql:
            if playlist_id == Type.ALL:
                return Lp().tracks.get_paths()
            else:
                result = sql.execute("SELECT filepath\
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
        with SqlCursor(self) as sql:
            if playlist_id == Type.ALL:
                tracks = Lp().tracks.get_ids()
            else:
                result = sql.execute("SELECT music.tracks.rowid\
                                      FROM tracks, music.tracks\
                                      WHERE tracks.playlist_id=?\
                                      AND music.tracks.filepath=\
                                      main.tracks.filepath",
                                     (playlist_id,))
                return list(itertools.chain(*result))
            return tracks

    def get_id(self, playlist_name):
        """
            Get playlist id
            @param playlist name as str
            @return playlst id as int
        """
        if playlist_name == self._LOVED:
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
            return self._LOVED

        with SqlCursor(self) as sql:
            result = sql.execute("SELECT name\
                                 FROM playlists\
                                 WHERE rowid=?", (playlist_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return ''

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

    def clear(self, playlist_id, notify=True):
        """
            Clear playlsit
            @param playlist id as int
            @param notify as bool
        """
        with SqlCursor(self) as sql:
            sql.execute("DELETE FROM tracks\
                         WHERE playlist_id=?", (playlist_id,))
            sql.commit()
            if notify:
                GLib.idle_add(self.emit, 'playlist-del', playlist_id, None)

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
                if not self.exists_track(playlist_id, track.id):
                    changed = True
                    sql.execute("INSERT INTO tracks"
                                " VALUES (?, ?)",
                                (playlist_id, track.path))
                if notify:
                    GLib.idle_add(self.emit, 'playlist-add',
                                  playlist_id, track.id)
            if changed:
                sql.execute("UPDATE playlists SET mtime=?\
                             WHERE rowid=?", (datetime.now().strftime('%s'),
                                              playlist_id))
                sql.commit()

    def remove_tracks(self, playlist_id, tracks, notify=True):
        """
            Remove tracks from playlist
            @param playlist id as int
            @param tracks as [Track]
        """
        with SqlCursor(self) as sql:
            for track in tracks:
                sql.execute("DELETE FROM tracks\
                             WHERE filepath=?\
                             AND playlist_id=?", (track.path, playlist_id))
                if notify:
                    GLib.idle_add(self.emit, 'playlist-del',
                                  playlist_id, track.id)
            sql.commit()

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

    def exists_track(self, playlist_id, track_id):
        """
            Check if track id exist in playlist
            @param playlist id as int
            @param track as Track
            @return bool
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT main.tracks.filepath\
                                  FROM tracks, music.tracks\
                                  WHERE music.tracks.rowid=?\
                                  AND playlist_id=?\
                                  AND music.tracks.filepath=\
                                  main.tracks.filepath",
                                 (track_id, playlist_id))
            v = result.fetchone()
            if v is not None:
                return True
            return False

    def exists_album(self, playlist_id, album_id, genre_ids, artist_ids):
        """
            Return True if object_id is already present in playlist
            @param playlist id as int
            @param album id as int
            @param genre ids as [int]
            @param artist ids as [int]
            @param sql as sqlite cursor
            @return bool
        """
        # We do not use Album object for performance reasons
        playlist_paths = self.get_tracks(playlist_id)
        track_paths = Lp().albums.get_track_paths(album_id,
                                                  genre_ids,
                                                  artist_ids)
        return len(set(playlist_paths) & set(track_paths)) == len(track_paths)

    def get_cursor(self):
        """
            Return a new sqlite cursor
        """
        try:
            sql = sqlite3.connect(self.DB_PATH, 600.0)
            sql.execute("ATTACH DATABASE '%s' AS music" % Database.DB_PATH)
            sql.create_collation('LOCALIZED', LocalizedCollation())
            return sql
        except:
            exit(-1)

#######################
# PRIVATE             #
#######################
    def _on_entry_parsed(self, parser, uri, metadata, playlist_id):
        """
            Import entry
            @param parser as TotemPlParser.Parser
            @param playlist uri as str
            @param metadata as GLib.HastTable
            @param playlist id as int
        """
        try:
            track_id = Lp().tracks.get_id_by_path(
                                            GLib.filename_from_uri(uri)[0])
            if track_id is not None:
                self.add_tracks(playlist_id, [Track(track_id)])
        except Exception as e:
            print("Playlists::_on_entry_parsed: %s" % e)
