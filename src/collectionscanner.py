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
from lollypop.tagreader import TagReader
from lollypop.database_history import History
from lollypop.utils import is_audio, is_pls, debug


class CollectionScanner(GObject.GObject, TagReader):
    """
        Scan user music collection
    """
    __gsignals__ = {
        'scan-finished': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'artist-updated': (GObject.SignalFlags.RUN_FIRST, None, (int,
                                                                 int,
                                                                 bool)),
        'genre-updated': (GObject.SignalFlags.RUN_FIRST, None, (int, bool)),
        'album-updated': (GObject.SignalFlags.RUN_FIRST, None, (int,))
    }

    def __init__(self):
        """
            Init collection scanner
        """
        GObject.GObject.__init__(self)
        TagReader.__init__(self)

        self.__thread = None
        self.__history = None
        if Lp().settings.get_value('auto-update'):
            self.__inotify = Inotify()
        else:
            self.__inotify = None
        self.__progress = None

    def update(self, progress):
        """
            Update database
            @param progress as Gtk.Scale
        """
        if not self.is_locked():
            progress.show()
            self.__progress = progress
            paths = Lp().settings.get_music_paths()
            if not paths:
                return

            if Lp().notify is not None:
                Lp().notify.send(_("Your music is updating"))
            self.__thread = Thread(target=self.__scan, args=(paths,))
            self.__thread.daemon = True
            self.__thread.start()

    def is_locked(self):
        """
            Return True if db locked
        """
        return self.__thread is not None and self.__thread.isAlive()

    def stop(self):
        """
            Stop scan
        """
        self.__thread = None
        if self.__progress is not None:
            self.__progress.hide()
            self.__progress.set_fraction(0.0)
            self.__progress = None

#######################
# PRIVATE             #
#######################
    def __get_objects_for_paths(self, paths):
        """
            Return all tracks/dirs for paths
            @param paths as string
            @return ([tracks path], [dirs path], track count)
        """
        tracks = []
        track_dirs = list(paths)
        for path in paths:
            for root, dirs, files in os.walk(path, followlinks=True):
                # Add dirs
                for d in dirs:
                    track_dirs.append(os.path.join(root, d))
                # Add files
                for name in files:
                    path = os.path.join(root, name)
                    uri = GLib.filename_to_uri(path)
                    try:
                        f = Gio.File.new_for_uri(uri)
                        if is_pls(f):
                            pass
                        elif is_audio(f):
                            tracks.append(uri)
                        else:
                            debug("%s not detected as a music file" % uri)
                    except Exception as e:
                        print("CollectionScanner::__get_objects_for_paths: %s"
                              % e)
        return (tracks, track_dirs)

    def __update_progress(self, current, total):
        """
            Update progress bar status
            @param scanned items as int, total items as int
        """
        if self.__progress is not None:
            self.__progress.set_fraction(current/total)

    def __finish(self):
        """
            Notify from main thread when scan finished
        """
        self.stop()
        self.emit("scan-finished")
        if Lp().settings.get_value('artist-artwork'):
            Lp().art.cache_artists_info()

    def __scan(self, paths):
        """
            Scan music collection for music files
            @param paths as [string], paths to scan
            @thread safe
        """
        gst_message = None
        if self.__history is None:
            self.__history = History()
        mtimes = Lp().tracks.get_mtimes()
        orig_tracks = Lp().tracks.get_uris()
        was_empty = len(orig_tracks) == 0

        (new_tracks, new_dirs) = self.__get_objects_for_paths(paths)
        count = len(new_tracks) + len(orig_tracks)
        # Add monitors on dirs
        if self.__inotify is not None:
            for d in new_dirs:
                self.__inotify.add_monitor(d)

        with SqlCursor(Lp().db) as sql:
            i = 0
            for uri in new_tracks:
                if self.__thread is None:
                    return
                GLib.idle_add(self.__update_progress, i, count)
                try:
                    f = Gio.File.new_for_uri(uri)
                    info = f.query_info('time::modified',
                                        Gio.FileQueryInfoFlags.NONE,
                                        None)
                    mtime = info.get_attribute_as_string('time::modified')
                    # If songs exists and mtime unchanged, continue,
                    # else rescan
                    if uri in orig_tracks:
                        orig_tracks.remove(uri)
                        i += 1
                        if mtime <= mtimes[uri]:
                            i += 1
                            continue
                        else:
                            self.__del_from_db(uri)
                    info = self.get_info(uri)
                    # On first scan, use modification time
                    # Else, use current time
                    if not was_empty:
                        mtime = int(time())
                    debug("Adding file: %s" % uri)
                    self.__add2db(uri, info, mtime)
                except GLib.GError as e:
                    print(e, uri)
                    if e.message != gst_message:
                        gst_message = e.message
                        if Lp().notify is not None:
                            Lp().notify.send(gst_message)
                except:
                    pass
                i += 1

            # Clean deleted files
            for uri in orig_tracks:
                i += 1
                GLib.idle_add(self.__update_progress, i, count)
                self.__del_from_db(uri)

            sql.commit()
        GLib.idle_add(self.__finish)
        del self.__history
        self.__history = None

    def __add2db(self, uri, info, mtime):
        """
            Add new file to db with informations
            @param uri as string
            @param info as GstPbutils.DiscovererInfo
            @param mtime as int
            @return track id as int
        """
        debug("CollectionScanner::add2db(): Read tags")
        path = GLib.filename_from_uri(uri)[0]
        tags = info.get_tags()
        title = self.get_title(tags, path)
        artists = self.get_artists(tags)
        composers = self.get_composers(tags)
        performers = self.get_performers(tags)
        a_sortnames = self.get_artist_sortnames(tags)
        aa_sortnames = self.get_album_artist_sortnames(tags)
        album_artists = self.get_album_artist(tags)
        album_name = self.get_album_name(tags)
        genres = self.get_genres(tags)
        discnumber = self.get_discnumber(tags)
        discname = self.get_discname(tags)
        tracknumber = self.get_tracknumber(tags, GLib.basename(path))
        year = self.get_year(tags)
        duration = int(info.get_duration()/1000000000)
        name = GLib.path_get_basename(path)

        # If no artists tag, use album artist
        if artists == '':
            artists = album_artists
        # if artists is always null, no album artists too,
        # use composer/performer
        if artists == '':
            artists = performers
            album_artists = composers
            if artists == '':
                artists = album_artists
            if artists == '':
                artists = _("Unknown")

        debug("CollectionScanner::add2db(): Restore stats")
        # Restore stats
        (track_pop, track_ltime, amtime, album_pop) = self.__history.get(
                                                            name, duration)
        # If nothing in stats, set mtime
        if amtime == 0:
            amtime = mtime
        debug("CollectionScanner::add2db(): Add artists %s" % artists)
        (artist_ids, new_artist_ids) = self.add_artists(artists,
                                                        album_artists,
                                                        a_sortnames)
        debug("CollectionScanner::add2db(): "
              "Add album artists %s" % album_artists)
        (album_artist_ids, new_album_artist_ids) = self.add_album_artists(
                                                                 album_artists,
                                                                 aa_sortnames)
        new_artist_ids += new_album_artist_ids

        debug("CollectionScanner::add2db(): Add album: "
              "%s, %s" % (album_name, album_artist_ids))
        (album_id, new_album) = self.add_album(album_name, album_artist_ids,
                                               path, album_pop, amtime)

        (genre_ids, new_genre_ids) = self.add_genres(genres, album_id)

        # Add track to db
        debug("CollectionScanner::add2db(): Add track")
        track_id = Lp().tracks.add(title, uri, duration,
                                   tracknumber, discnumber, discname,
                                   album_id, year, track_pop,
                                   track_ltime, mtime)

        debug("CollectionScanner::add2db(): Update tracks")
        self.update_track(track_id, artist_ids, genre_ids)
        self.update_album(album_id, album_artist_ids, genre_ids, year)
        # Notify about new artists/genres
        if new_genre_ids or new_artist_ids:
            with SqlCursor(Lp().db) as sql:
                sql.commit()
            for genre_id in new_genre_ids:
                GLib.idle_add(self.emit, 'genre-updated', genre_id, True)
            for artist_id in new_artist_ids:
                GLib.idle_add(self.emit, 'artist-updated',
                              artist_id, album_id, True)
        return track_id

    def __del_from_db(self, uri):
        """
            Delete track from db
            @param uri as str
        """
        path = GLib.filename_from_uri(uri)[0]
        name = GLib.path_get_basename(path)
        track_id = Lp().tracks.get_id_by_uri(uri)
        album_id = Lp().tracks.get_album_id(track_id)
        genre_ids = Lp().tracks.get_genre_ids(track_id)
        album_artist_ids = Lp().albums.get_artist_ids(album_id)
        artist_ids = Lp().tracks.get_artist_ids(track_id)
        popularity = Lp().tracks.get_popularity(track_id)
        ltime = Lp().tracks.get_ltime(track_id)
        mtime = Lp().albums.get_mtime(album_id)
        duration = Lp().tracks.get_duration(track_id)
        album_popularity = Lp().albums.get_popularity(album_id)
        self.__history.add(name, duration, popularity,
                           ltime, mtime, album_popularity)
        Lp().tracks.remove(track_id)
        Lp().tracks.clean(track_id)
        modified = Lp().albums.clean(album_id)
        if modified:
            with SqlCursor(Lp().db) as sql:
                sql.commit()
            GLib.idle_add(self.emit, 'album-updated', album_id)
        for artist_id in album_artist_ids + artist_ids:
            ret = Lp().artists.clean(artist_id)
            if ret:
                GLib.idle_add(self.emit, 'artist-updated',
                              artist_id, album_id, False)
        for genre_id in genre_ids:
            ret = Lp().genres.clean(genre_id)
            if ret:
                GLib.idle_add(self.emit, 'genre-updated', genre_id, False)
