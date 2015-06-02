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

from gi.repository import GLib, GObject, Gio

import os
from gettext import gettext as _
from _thread import start_new_thread

from lollypop.inotify import Inotify
from lollypop.define import Lp
from lollypop.tagreader import ScannerTagReader
from lollypop.utils import is_audio, debug


class CollectionScanner(GObject.GObject, ScannerTagReader):
    __gsignals__ = {
        'scan-finished': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'artist-update': (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
        'genre-update': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        'album-modified': (GObject.SignalFlags.RUN_FIRST, None, (int,))
    }
    """
        Init collection scanner
    """
    def __init__(self):
        GObject.GObject.__init__(self)
        ScannerTagReader.__init__(self)

        self._inotify = None
        if Lp.settings.get_value('auto-update'):
            self._inotify = Inotify()
        self._is_empty = True
        self._in_thread = False
        self._is_locked = False
        self._progress = None

    """
        Update database
        @param progress as progress bar
    """
    def update(self, progress):
        self._progress = progress
        paths = Lp.settings.get_music_paths()
        if not paths:
            return

        if not self._in_thread:
            if Lp.notify is not None:
                Lp.notify.send(_("Your music is updating"))
            if self._progress is not None:
                self._progress.show()
            self._in_thread = True
            self._is_locked = True
            self._mtimes = Lp.tracks.get_mtimes()
            start_new_thread(self._scan, (paths,))

    """
        Return True if db locked
    """
    def is_locked(self):
        return self._is_locked

    """
        Stop scan
    """
    def stop(self):
        if self._progress is not None:
            self._progress.hide()
            self._progress.set_fraction(0.0)
            self._progress = None
        self._in_thread = False

#######################
# PRIVATE             #
#######################
    """
        Return all tracks/dirs for paths
        @param paths as string
        @return ([tracks path], [dirs path], track count)
    """
    def _get_objects_for_paths(self, paths):
        tracks = []
        track_dirs = list(paths)
        count = 0
        for path in paths:
            for root, dirs, files in os.walk(path):
                # Add dirs
                for d in dirs:
                    track_dirs.append(os.path.join(root, d))
                # Add files
                for name in files:
                    filepath = os.path.join(root, name)
                    try:
                        f = Gio.File.new_for_path(filepath)
                        if is_audio(f):
                            tracks.append(filepath)
                            count += 1
                        else:
                            debug("%s not detected as a music file" % filepath)
                    except Exception as e:
                        print("CollectionScanner::_get_objects_for_paths: %s"
                              % e)
        return (tracks, track_dirs, count)

    """
        Update progress bar status
        @param scanned items as int, total items as int
    """
    def _update_progress(self, current, total):
        if self._progress is not None:
            self._progress.set_fraction(current/total)

    """
        Notify from main thread when scan finished
    """
    def _finish(self):
        if self._progress is not None:
            self._progress.hide()
            self._progress.set_fraction(0.0)
            self._progress = None
        self._in_thread = False
        self._is_locked = False
        self.emit("scan-finished")

    """
        Scan music collection for music files
        @param paths as [string], paths to scan
        @thread safe
    """
    def _scan(self, paths):
        sql = Lp.db.get_cursor()
        orig_tracks = Lp.tracks.get_paths(sql)
        self._is_empty = len(orig_tracks) == 0

        # Add monitors on dirs
        (new_tracks, new_dirs, count) = self._get_objects_for_paths(paths)
        if self._inotify is not None:
            for d in new_dirs:
                self._inotify.add_monitor(d)

        i = 0
        for filepath in new_tracks:
            if not self._in_thread:
                sql.close()
                self._is_locked = False
                return
            GLib.idle_add(self._update_progress, i, count)
            try:
                mtime = int(os.path.getmtime(filepath))
                if filepath not in orig_tracks:
                    infos = self.get_infos(filepath)
                    if infos is not None:
                        debug("Adding file: %s" % filepath)
                        self._add2db(filepath, mtime, infos, sql)
                    else:
                        print("Can't get infos for ", filepath)
                else:
                    # Update tags by removing song and readd it
                    if mtime != self._mtimes[filepath]:
                        self._del_from_db(filepath, sql)
                        infos = self.get_infos(filepath)
                        if infos is not None:
                            debug("Adding file: %s" % filepath)
                            self._add2db(filepath, mtime, infos, sql)
                        else:
                            print("Can't get infos for ", filepath)
                    orig_tracks.remove(filepath)

            except Exception as e:
                print(ascii(filepath))
                print("CollectionScanner::_scan(): %s" % e)
            i += 1

        # Clean deleted files
        if i > 0:
            for filepath in orig_tracks:
                self._del_from_db(filepath, sql)

        self._restore_popularities(sql)
        self._restore_mtimes(sql)
        sql.commit()
        sql.close()
        GLib.idle_add(self._finish)

    """
        Add new file to db with informations
        @param filepath as string
        @param file modification time as int
        @param infos as GstPbutils.DiscovererInfo
        @param sql as sqlite cursor
        @return track id as int
    """
    def _add2db(self, filepath, mtime, infos, sql):
        tags = infos.get_tags()

        title = self.get_title(tags, filepath)
        artists = self.get_artists(tags)
        album_artist = self.get_album_artist(tags)
        album_name = self.get_album_name(tags)
        genres = self.get_genres(tags)
        discnumber = self.get_discnumber(tags)
        tracknumber = self.get_tracknumber(tags)
        year = self.get_year(tags)
        length = infos.get_duration()/1000000000

        (artist_ids, new_artist_ids) = self.add_artists(artists,
                                                        album_artist,
                                                        sql)

        (album_artist_id, new) = self.add_album_artist(album_artist,
                                                       sql)
        if new:
            new_artist_ids.append(album_artist_id)

        noaartist = False
        if album_artist_id is None:
            album_artist_id = artist_ids[0]
            noaartist = True

        album_id = self.add_album(album_name, album_artist_id, noaartist,
                                  filepath, sql)

        (genre_ids, new_genre_ids) = self.add_genres(genres, album_id, sql)

        # Add track to db
        Lp.tracks.add(title, filepath, length,
                      tracknumber, discnumber,
                      album_id, year, mtime, sql)

        self.update_year(album_id, sql)

        track_id = Lp.tracks.get_id_by_path(filepath, sql)
        self.update_track(track_id, artist_ids, genre_ids, sql)

        # Notify about new artists/genres
        if new_genre_ids or new_artist_ids:
            sql.commit()
            for genre_id in new_genre_ids:
                GLib.idle_add(self.emit, 'genre-update', genre_id)
            for artist_id in new_artist_ids:
                GLib.idle_add(self.emit, 'artist-update', artist_id, album_id)
        return track_id

    """
        Delete track from db
        @param filepath as string
        @param sql as sqlite cursor
    """
    def _del_from_db(self, filepath, sql):
        track_id = Lp.tracks.get_id_by_path(filepath, sql)
        album_id = Lp.tracks.get_album_id(track_id, sql)
        genre_ids = Lp.tracks.get_genre_ids(track_id, sql)
        album_artist_id = Lp.albums.get_artist_id(album_id, sql)
        artist_ids = Lp.tracks.get_artist_ids(track_id, sql)
        Lp.tracks.remove(filepath, sql)
        Lp.tracks.clean(track_id, sql)
        modified = Lp.albums.clean(album_id, sql)
        if modified:
            self.emit('album-modified', album_id)
        for artist_id in [album_artist_id] + artist_ids:
            Lp.artists.clean(artist_id, sql)
        for genre_id in genre_ids:
            Lp.genres.clean(genre_id, sql)

    """
        Restore albums popularties
    """
    def _restore_popularities(self, sql):
        self._popularities = Lp.db.get_popularities()
        result = sql.execute("SELECT albums.name, artists.name, albums.rowid\
                              FROM albums, artists\
                              WHERE artists.rowid == albums.artist_id")
        for row in result:
            string = "%s_%s" % (row[0], row[1])
            if string in self._popularities:
                Lp.albums.set_popularity(row[2],
                                         self._popularities[string], sql)
    """
        Restore albums mtimes
    """
    def _restore_mtimes(self, sql):
        self._mtimes = Lp.db.get_mtimes()
        result = sql.execute("SELECT albums.name, artists.name, albums.rowid\
                              FROM albums, artists\
                              WHERE artists.rowid == albums.artist_id")
        for row in result:
            string = "%s_%s" % (row[0], row[1])
            if string in self._mtimes:
                Lp.albums.set_mtime(row[2],
                                    self._mtimes[string], sql)
