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

from gi.repository import GLib, GObject, Gio

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
        "scan-finished": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "artist-updated": (GObject.SignalFlags.RUN_FIRST, None, (int, bool)),
        "genre-updated": (GObject.SignalFlags.RUN_FIRST, None, (int, bool)),
        "album-updated": (GObject.SignalFlags.RUN_FIRST, None, (int, bool))
    }

    def __init__(self):
        """
            Init collection scanner
        """
        GObject.GObject.__init__(self)
        TagReader.__init__(self)

        self.__thread = None
        self.__history = None
        if Lp().settings.get_value("auto-update"):
            self.__inotify = Inotify()
        else:
            self.__inotify = None
        Lp().albums.update_max_count()

    def update(self):
        """
            Update database
        """
        if not self.is_locked():
            uris = Lp().settings.get_music_uris()
            if not uris:
                return

            Lp().window.progress.add(self)
            Lp().window.progress.set_fraction(0.0, self)

            self.__thread = Thread(target=self.__scan, args=(uris,))
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

#######################
# PRIVATE             #
#######################
    def __get_objects_for_uris(self, uris):
        """
            Return all tracks/dirs for uris
            @param uris as string
            @return (track uri as [str], track dirs as [str],
                     ignore dirs as [str])
        """
        tracks = []
        ignore_dirs = []
        track_dirs = list(uris)
        walk_uris = list(uris)
        while walk_uris:
            uri = walk_uris.pop(0)
            empty = True
            try:
                d = Gio.File.new_for_uri(uri)
                infos = d.enumerate_children(
                    "standard::name,standard::type,standard::is-hidden",
                    Gio.FileQueryInfoFlags.NONE,
                    None)
            except Exception as e:
                print("CollectionScanner::__get_objects_for_uris():", e)
                continue
            for info in infos:
                f = infos.get_child(info)
                child_uri = f.get_uri()
                empty = False
                if info.get_is_hidden():
                    continue
                elif info.get_file_type() == Gio.FileType.DIRECTORY:
                    track_dirs.append(child_uri)
                    walk_uris.append(child_uri)
                else:
                    try:
                        f = Gio.File.new_for_uri(child_uri)
                        if is_pls(f):
                            pass
                        elif is_audio(f):
                            tracks.append(child_uri)
                        else:
                            debug("%s not detected as a music file" %
                                  child_uri)
                    except Exception as e:
                        print("CollectionScanner::"
                              "__get_objects_for_uris():", e)
            # If a root uri is empty
            # Ensure user is not doing something bad
            if empty and uri in uris:
                ignore_dirs.append(uri)
        return (tracks, track_dirs, ignore_dirs)

    def __update_progress(self, current, total):
        """
            Update progress bar status
            @param scanned items as int, total items as int
        """
        Lp().window.progress.set_fraction(current / total, self)

    def __finish(self):
        """
            Notify from main thread when scan finished
        """
        Lp().window.progress.set_fraction(1.0, self)
        self.stop()
        self.emit("scan-finished")
        # Update max count value
        Lp().albums.update_max_count()
        if Lp().settings.get_value("artist-artwork"):
            Lp().art.cache_artists_info()

    def __scan(self, uris):
        """
            Scan music collection for music files
            @param uris as [string], uris to scan
            @thread safe
        """
        if self.__history is None:
            self.__history = History()
        mtimes = Lp().tracks.get_mtimes()
        (new_tracks, new_dirs, ignore_dirs) = self.__get_objects_for_uris(
                                                                         uris)
        orig_tracks = Lp().tracks.get_uris(ignore_dirs)
        was_empty = len(orig_tracks) == 0

        if ignore_dirs:
            if Lp().notify is not None:
                Lp().notify.send(_("Lollypop is detecting an empty folder."),
                                 _("Check your music settings."))
        count = len(new_tracks) + len(orig_tracks)
        # Add monitors on dirs
        if self.__inotify is not None:
            for d in new_dirs:
                if d.startswith("file://"):
                    self.__inotify.add_monitor(d)

        with SqlCursor(Lp().db) as sql:
            i = 0
            # Look for new files/modified files
            try:
                to_add = []
                for uri in new_tracks:
                    if self.__thread is None:
                        return
                    try:
                        GLib.idle_add(self.__update_progress, i, count)
                        f = Gio.File.new_for_uri(uri)
                        info = f.query_info("time::modified",
                                            Gio.FileQueryInfoFlags.NONE,
                                            None)
                        mtime = int(info.get_attribute_as_string(
                                                             "time::modified"))
                        # If songs exists and mtime unchanged, continue,
                        # else rescan
                        if uri in orig_tracks:
                            orig_tracks.remove(uri)
                            i += 1
                            if mtime <= mtimes.get(uri, mtime + 1):
                                i += 1
                                continue
                            else:
                                self.__del_from_db(uri)
                        # On first scan, use modification time
                        # Else, use current time
                        if not was_empty:
                            mtime = int(time())
                        to_add.append((uri, mtime))
                    except Exception as e:
                        print("CollectionScanner::__scan(mtime):", e)
                # Clean deleted files
                # Now because we need to populate history
                for uri in orig_tracks:
                    i += 1
                    GLib.idle_add(self.__update_progress, i, count)
                    self.__del_from_db(uri)
                # Add files to db
                for (uri, mtime) in to_add:
                    try:
                        debug("Adding file: %s" % uri)
                        i += 1
                        GLib.idle_add(self.__update_progress, i, count)
                        self.__add2db(uri, mtime)
                    except Exception as e:
                        print("CollectionScanner::__scan(add):", e, uri)
                sql.commit()
            except Exception as e:
                print("CollectionScanner::__scan():", e)
        GLib.idle_add(self.__finish)
        del self.__history
        self.__history = None

    def __add2db(self, uri, mtime):
        """
            Add new file to db with information
            @param uri as string
            @param mtime as int
            @return track id as int
        """
        f = Gio.File.new_for_uri(uri)
        debug("CollectionScanner::add2db(): Read tags")
        info = self.get_info(uri)
        tags = info.get_tags()
        name = f.get_basename()
        title = self.get_title(tags, name)
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
        tracknumber = self.get_tracknumber(tags, name)
        year = self.get_original_year(tags)
        if year is None:
            year = self.get_year(tags)
        duration = int(info.get_duration()/1000000000)

        # If no artists tag, use album artist
        if artists == "":
            artists = album_artists
        # if artists is always null, no album artists too,
        # use composer/performer
        if artists == "":
            artists = performers
            album_artists = composers
            if artists == "":
                artists = album_artists
            if artists == "":
                artists = _("Unknown")

        debug("CollectionScanner::add2db(): Restore stats")
        # Restore stats
        (track_pop, track_rate, track_ltime, album_mtime,
         loved, album_pop, album_rate) = self.__history.get(name, duration)
        # If nothing in stats, use track mtime
        if album_mtime == 0:
            album_mtime = mtime

        debug("CollectionScanner::add2db(): Add artists %s" % artists)
        artist_ids = self.add_artists(artists, album_artists, a_sortnames)

        debug("CollectionScanner::add2db(): "
              "Add album artists %s" % album_artists)
        album_artist_ids = self.add_album_artists(album_artists, aa_sortnames)

        new_artist_ids = list(set(album_artist_ids) | set(artist_ids))

        debug("CollectionScanner::add2db(): Add album: "
              "%s, %s" % (album_name, album_artist_ids))
        (album_id, new_album) = self.add_album(album_name, album_artist_ids,
                                               uri, loved, album_pop,
                                               album_rate, False)

        genre_ids = self.add_genres(genres)

        # Add track to db
        debug("CollectionScanner::add2db(): Add track")
        track_id = Lp().tracks.add(title, uri, duration,
                                   tracknumber, discnumber, discname,
                                   album_id, year, track_pop, track_rate,
                                   track_ltime)

        debug("CollectionScanner::add2db(): Update tracks")
        self.update_track(track_id, artist_ids, genre_ids, mtime)
        self.update_album(album_id, album_artist_ids,
                          genre_ids, album_mtime, year)
        if new_album:
            with SqlCursor(Lp().db) as sql:
                sql.commit()
        for genre_id in genre_ids:
            GLib.idle_add(self.emit, "genre-updated", genre_id, True)
        for artist_id in new_artist_ids:
            GLib.idle_add(self.emit, "artist-updated", artist_id, True)
        return track_id

    def __del_from_db(self, uri):
        """
            Delete track from db
            @param uri as str
        """
        try:
            f = Gio.File.new_for_uri(uri)
            name = f.get_basename()
            track_id = Lp().tracks.get_id_by_uri(uri)
            album_id = Lp().tracks.get_album_id(track_id)
            genre_ids = Lp().tracks.get_genre_ids(track_id)
            album_artist_ids = Lp().albums.get_artist_ids(album_id)
            artist_ids = Lp().tracks.get_artist_ids(track_id)
            popularity = Lp().tracks.get_popularity(track_id)
            rate = Lp().tracks.get_rate(track_id)
            ltime = Lp().tracks.get_ltime(track_id)
            mtime = Lp().albums.get_mtime(album_id)
            duration = Lp().tracks.get_duration(track_id)
            album_popularity = Lp().albums.get_popularity(album_id)
            album_rate = Lp().albums.get_rate(album_id)
            loved = Lp().albums.get_loved(album_id)
            uri = Lp().tracks.get_uri(track_id)
            self.__history.add(name, duration, popularity, rate,
                               ltime, mtime, loved, album_popularity,
                               album_rate)
            Lp().tracks.remove(track_id)
            Lp().tracks.clean(track_id)
            deleted = Lp().albums.clean(album_id)
            if deleted:
                with SqlCursor(Lp().db) as sql:
                    sql.commit()
                GLib.idle_add(self.emit, "album-updated", album_id, True)
            for artist_id in album_artist_ids + artist_ids:
                Lp().artists.clean(artist_id)
                GLib.idle_add(self.emit, "artist-updated", artist_id, False)
            for genre_id in genre_ids:
                Lp().genres.clean(genre_id)
                GLib.idle_add(self.emit, "genre-updated", genre_id, False)
        except Exception as e:
            print("CollectionScanner::__del_from_db:", e)
