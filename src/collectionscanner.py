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

from gi.repository import GLib, GObject, Gio

import os
from gettext import gettext as _
from threading import Thread
from time import time

from lollypop.inotify import Inotify
from lollypop.define import Lp
from lollypop.sqlcursor import SqlCursor
from lollypop.tagreader import ScannerTagReader
from lollypop.utils import is_audio, is_pls, debug


class CollectionScanner(GObject.GObject, ScannerTagReader):
    """
        Scan user music collection
    """
    __gsignals__ = {
        'scan-finished': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'artist-added': (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
        'genre-added': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        'album-update': (GObject.SignalFlags.RUN_FIRST, None, (int,))
    }

    def __init__(self):
        """
            Init collection scanner
        """
        GObject.GObject.__init__(self)
        ScannerTagReader.__init__(self)

        self._thread = None
        self._inotify = None
        if Lp().settings.get_value('auto-update'):
            self._inotify = Inotify()
        self._progress = None

    def update(self, progress):
        """
            Update database
            @param progress as Gtk.Scale
        """
        if not self.is_locked():
            progress.show()
            self._progress = progress
            # Keep track of on file with missing codecs
            self._missing_codecs = None
            self.init_discover()
            paths = Lp().settings.get_music_paths()
            if not paths:
                return

            if Lp().notify is not None:
                Lp().notify.send(_("Your music is updating"))
            self._thread = Thread(target=self._scan, args=(paths,))
            self._thread.daemon = True
            self._thread.start()

    def is_locked(self):
        """
            Return True if db locked
        """
        return self._thread is not None and self._thread.isAlive()

    def stop(self):
        """
            Stop scan
        """
        self._thread = None
        if self._progress is not None:
            self._progress.hide()
            self._progress.set_fraction(0.0)
            self._progress = None

#######################
# PRIVATE             #
#######################
    def _get_objects_for_paths(self, paths):
        """
            Return all tracks/dirs for paths
            @param paths as string
            @return ([tracks path], [dirs path], track count)
        """
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
                        if is_pls(f):
                            pass
                        elif is_audio(f):
                            tracks.append(filepath)
                            count += 1
                        else:
                            debug("%s not detected as a music file" % filepath)
                    except Exception as e:
                        print("CollectionScanner::_get_objects_for_paths: %s"
                              % e)
        return (tracks, track_dirs, count)

    def _update_progress(self, current, total):
        """
            Update progress bar status
            @param scanned items as int, total items as int
        """
        if self._progress is not None:
            self._progress.set_fraction(current/total)

    def _finish(self):
        """
            Notify from main thread when scan finished
        """
        Lp().settings.set_value('db-mtime', GLib.Variant('i', int(time())))
        self.stop()
        self.emit("scan-finished")
        if self._missing_codecs is not None:
            Lp().player.load_external(
                                    GLib.filename_to_uri(self._missing_codecs))
            Lp().player.play_first_external()

    def _scan(self, paths):
        """
            Scan music collection for music files
            @param paths as [string], paths to scan
            @thread safe
        """
        mtimes = Lp().tracks.get_mtimes()
        orig_tracks = Lp().tracks.get_paths()

        # Add monitors on dirs
        (new_tracks, new_dirs, count) = self._get_objects_for_paths(paths)
        if self._inotify is not None:
            for d in new_dirs:
                self._inotify.add_monitor(d)

        with SqlCursor(Lp().db) as sql:
            i = 0
            for filepath in new_tracks:
                if self._thread is None:
                    return
                GLib.idle_add(self._update_progress, i, count)
                try:
                    debug("Adding file: %s" % filepath)
                    new = filepath not in orig_tracks
                    # If songs exists and mtime unchanged, continue
                    if not new:
                        orig_tracks.remove(filepath)
                        mtime = int(os.path.getmtime(filepath))
                        if mtime == mtimes[filepath]:
                            continue
                    infos = self.get_infos(filepath)
                    self._add2db(filepath, infos, new)
                except Exception as e:
                    debug("Error scanning: %s, %s" % (filepath, e))
                    string = "%s" % e
                    if string.startswith('gst-core-error-quark'):
                        self._missing_codecs = filepath
                i += 1

            # Clean deleted files
            for filepath in orig_tracks:
                track_id = Lp().tracks.get_id_by_path(filepath)
                self._del_from_db(track_id)

            sql.commit()
        GLib.idle_add(self._finish)

    def _add2db(self, filepath, infos, new=True):
        """
            Add new file to db with informations
            @param filepath as string
            @param infos as GstPbutils.DiscovererInfo
            @param new as bool
            @return track id as int
        """
        tags = infos.get_tags()

        title = self.get_title(tags, filepath)
        artists = self.get_artists(tags)
        sortname = self.get_artist_sortname(tags)
        album_artist = self.get_album_artist(tags)
        album_name = self.get_album_name(tags)
        genres = self.get_genres(tags)
        discnumber = self.get_discnumber(tags)
        tracknumber = self.get_tracknumber(tags)
        year = self.get_year(tags)
        duration = int(infos.get_duration()/1000000000)

        # Restore stats
        (track_pop, track_ltime, album_pop, mtime) = Lp(
                                         ).tracks.get_stats(filepath, duration)
        # If nothing in stats, set mtime
        if mtime == 0:
            mtime = int(os.path.getmtime(filepath))
        # We have stats, remove previous track_id
        if not new:
            track_id = Lp().tracks.get_id_by_path(filepath)
            self._del_from_db(track_id)

        (artist_ids, new_artist_ids) = self.add_artists(artists,
                                                        album_artist,
                                                        sortname)
        (album_artist_id, new) = self.add_album_artist(album_artist)
        if new:
            new_artist_ids.append(album_artist_id)

        # Check for album artist, if none, use first available artist
        no_album_artist = False
        if album_artist_id is None:
            album_artist_id = artist_ids[0]
            no_album_artist = True

        (album_id, new_album) = self.add_album(album_name, album_artist_id,
                                               no_album_artist, year, filepath,
                                               album_pop, mtime)

        (genre_ids, new_genre_ids) = self.add_genres(genres, album_id)

        # Add track to db
        track_id = Lp().tracks.add(title, filepath, duration,
                                   tracknumber, discnumber,
                                   album_id, year, track_pop,
                                   track_ltime, mtime)
        self.update_track(track_id, artist_ids, genre_ids)

        # Notify about new artists/genres
        if new_genre_ids or new_artist_ids:
            with SqlCursor(Lp().db) as sql:
                sql.commit()
            for genre_id in new_genre_ids:
                GLib.idle_add(self.emit, 'genre-added', genre_id)
            for artist_id in new_artist_ids:
                GLib.idle_add(self.emit, 'artist-added', artist_id, album_id)
        return track_id

    def _del_from_db(self, track_id):
        """
            Delete track from db
            @param track_id as int
        """
        album_id = Lp().tracks.get_album_id(track_id)
        genre_ids = Lp().tracks.get_genre_ids(track_id)
        album_artist_id = Lp().albums.get_artist_id(album_id)
        artist_ids = Lp().tracks.get_artist_ids(track_id)
        Lp().tracks.remove(track_id)
        Lp().tracks.clean(track_id)
        modified = Lp().albums.clean(album_id)
        if modified:
            with SqlCursor(Lp().db) as sql:
                sql.commit()
            GLib.idle_add(self.emit, 'album-update', album_id)
        for artist_id in [album_artist_id] + artist_ids:
            Lp().artists.clean(artist_id)
        for genre_id in genre_ids:
            Lp().genres.clean(genre_id)
