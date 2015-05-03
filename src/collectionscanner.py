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

import os
from time import sleep, time
from gettext import gettext as _
from gi.repository import GLib, GObject, Gio
from _thread import start_new_thread

from lollypop.define import Objects, Navigation
from lollypop.tagreader import TagReader
from lollypop.utils import format_artist_name, is_audio, debug


class CollectionScanner(GObject.GObject, TagReader):
    __gsignals__ = {
        'scan-finished': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'artist-update': (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
        'genre-update': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        'added': (GObject.SignalFlags.RUN_FIRST, None, (int, bool))
    }

    """
        @param progress as Gtk.Progress
    """
    def __init__(self, progress):
        GObject.GObject.__init__(self)
        TagReader.__init__(self)
        self._progress = progress
        self._is_empty = True
        self._in_thread = False
        self._is_locked = False

    """
        Update database
        @param smooth as bool, if smooth, try to scan smoothly
    """
    def update(self, smooth):
        paths = Objects.settings.get_value('music-path')
        if not paths:
            if GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_MUSIC):
                paths = [GLib.get_user_special_dir(
                                          GLib.UserDirectory.DIRECTORY_MUSIC)]
            else:
                print("You need to add a music path"
                      " to org.gnome.Lollypop in dconf")
                return

        if not self._in_thread:
            if Objects.notify is not None:
                Objects.notify.send(_("Your music is updating"))
            self._progress.show()
            self._in_thread = True
            self._is_locked = True
            self._compilations = []
            self._mtimes = Objects.tracks.get_mtimes()
            start_new_thread(self._scan, (paths, smooth))

    """
        Add specified files to collection
        @param files as [Gio.Files]
        @thread safe
    """
    def add(self, files):
        if not files:
            return
        self._in_thread = True
        self._is_locked = True
        start_new_thread(self._add, (files,))

    """
        Return True if db locked
    """
    def is_locked(self):
        return self._is_locked

    """
        Stop scan
    """
    def stop(self):
        self._progress.hide()
        self._in_thread = False

#######################
# PRIVATE             #
#######################
    """
        Update progress bar status
        @param scanned items as int, total items as int
    """
    def _update_progress(self, current, total):
        self._progress.set_fraction(current/total)

    """
        Notify from main thread when scan finished
    """
    def _finish(self):
        self._progress.hide()
        self._progress.set_fraction(0.0)
        self._in_thread = False
        self._is_locked = False
        self.emit("scan-finished")

    """
        Clean track's compilation if needed
        @param album id as int
    """
    def _clean_compilation(self, album_id, sql=None):
        artists = Objects.albums.get_compilation_artists(album_id, sql)
        # It's not a compilation anymore
        if len(artists) == 1:
            artist_id = artists[0]
            Objects.albums.set_artist_id(album_id, artist_id, sql)
            # Update album path
            tracks = Objects.albums.get_tracks(album_id, None, sql)
            filepath = Objects.tracks.get_path(tracks[0], sql)
            path = os.path.dirname(filepath)
            Objects.albums.set_path(album_id, path, sql)

    """
        Add specified files to collection
        @param files as [Gio.Files]
        @thread safe
    """
    def _add(self, files):
        GLib.idle_add(self._progress.show)
        sql = Objects.db.get_cursor()
        tracks = Objects.tracks.get_paths(sql)
        count = len(files)
        i = 0
        GLib.idle_add(self._update_progress, i, count)
        for f in files:
            track_id = None
            if not self._in_thread:
                sql.close()
                self._is_locked = False
                return
            if f not in tracks:
                infos = self.get_infos(f)
                if infos is not None:
                    debug("Adding file: %s" % f)
                    track_id = self._add2db(f, 0, infos, True, sql)
                else:
                    print("Can't get infos for ", f)
            else:
                track_id = Objects.tracks.get_id_by_path(f, sql)
            if track_id is not None:
                if i == 0:
                    sql.commit()
                GLib.idle_add(self.emit, "added", track_id, i==0)
            i += 1
            GLib.idle_add(self._update_progress, i, count)
        Objects.albums.search_compilations(True, sql)
        sql.commit()
        sql.close()
        GLib.idle_add(self._progress.hide)
        self._in_thread = False
        self._is_locked = False

    """
        Scan music collection for music files
        @param paths as [string], paths to scan
        @param smooth as bool
        @thread safe
    """
    def _scan(self, paths, smooth):
        sql = Objects.db.get_cursor()
        tracks = Objects.tracks.get_paths(sql)
        self._is_empty = len(tracks) == 0
        # Clear cover cache
        if not smooth:
            Objects.art.clean_all_cache(sql)

        new_tracks = []
        count = 0
        for path in paths:
            for root, dirs, files in os.walk(path):
                for name in files:
                    filepath = os.path.join(root, name)
                    f = Gio.File.new_for_path(filepath)
                    if is_audio(f):
                        new_tracks.append(filepath)
                        count += 1
                    else:
                        debug("%s not detected as a music file" % filepath)
        i = 0
        for filepath in new_tracks:
            if not self._in_thread:
                sql.close()
                self._is_locked = False
                return
            GLib.idle_add(self._update_progress, i, count)
            mtime = int(os.path.getmtime(filepath))
            try:
                if filepath not in tracks:
                    infos = self.get_infos(filepath)
                    if infos is not None:
                        debug("Adding file: %s" % filepath)
                        self._add2db(filepath, mtime, infos, False, sql)
                    else:
                        print("Can't get infos for ", filepath)
                else:
                    # Update tags by removing song and readd it
                    if mtime != self._mtimes[filepath]:
                        track_id = Objects.tracks.get_id_by_path(filepath, sql)
                        album_id = Objects.tracks.get_album_id(track_id, sql)
                        Objects.tracks.remove(filepath, sql)
                        self._clean_compilation(album_id, sql)
                        infos = self.get_infos(filepath)
                        if infos is not None:
                            debug("Adding file: %s" % filepath)
                            self._add2db(filepath, mtime, infos, False, sql)
                        else:
                            print("Can't get infos for ", filepath)
                    tracks.remove(filepath)

            except Exception as e:
                print(ascii(filepath))
                print("CollectionScanner::_scan(): %s" % e)
            i += 1
            if smooth:
                sleep(0.001)

        # Clean deleted files
        if i > 0:
            for filepath in tracks:
                track_id = Objects.tracks.get_id_by_path(filepath, sql)
                album_id = Objects.tracks.get_album_id(track_id, sql)
                Objects.tracks.remove(filepath, sql)
                self._clean_compilation(album_id, sql)

        Objects.tracks.clean(sql)
        Objects.albums.search_compilations(False, sql)
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
        @param outside as bool
        @param sql as sqlite cursor
        @return track id as int
    """
    def _add2db(self, filepath, mtime, infos, outside, sql):
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

        (artist_ids, new_artist_ids) = self._add_artists(artists,
                                                         album_artist,
                                                         outside,
                                                         sql)

        (album_artist_id, new) = self._add_album_artist(album_artist, outside, sql)
        if new:
            new_artist_ids.append(album_artist_id)

        album_id = self._add_album(album_name, album_artist_id,
                                   filepath, outside, sql)

        (genre_ids, new_genre_ids) = self._add_genres(genres, album_id,
                                                      outside, sql)

        # Now we have our album id, check if path doesn't change
        path = os.path.dirname(filepath)
        if Objects.albums.get_path(album_id, sql) != path and not outside:
            Objects.albums.set_path(album_id, path, sql)

        # Add track to db
        Objects.tracks.add(title, filepath, length,
                           tracknumber, discnumber,
                           album_id, year, mtime, outside, sql)

        # Update year for album
        year = Objects.albums.get_year_from_tracks(album_id, sql)
        Objects.albums.set_year(album_id, year, sql)

        # Set artists/genres for track
        track_id = Objects.tracks.get_id_by_path(filepath, sql)
        for artist_id in artist_ids:
            Objects.tracks.add_artist(track_id, artist_id, outside, sql)
        for genre_id in genre_ids:
            Objects.tracks.add_genre(track_id, genre_id, outside, sql)
        # Notify about new artists/genres
        if new_genre_ids or new_artist_ids:
            sql.commit()
            for genre_id in new_genre_ids:
                GLib.idle_add(self.emit, "genre-update", genre_id)
            for artist_id in new_artist_ids:
                GLib.idle_add(self.emit, "artist-update", artist_id, album_id)
        return track_id

    """
        Add artists to db
        @param artists as [string]
        @param album artist as string
        @param outside as bool
        @param sql as sqlite cursor
        @commit needed
        @param return ([artist ids as int], [new artist ids as int])
    """
    def _add_artists(self, artists, album_artist, outside, sql):
        new_artist_ids = []
        # Get all artist ids
        artist_ids = []
        for artist in artists:
            artist = format_artist_name(artist)
            # Get artist id, add it if missing
            artist_id = Objects.artists.get_id(artist, sql)
            if artist_id is None:
                Objects.artists.add(artist, outside, sql)
                artist_id = Objects.artists.get_id(artist, sql)
                if artist == album_artist:
                    new_artist_ids.append(artist_id)
            artist_ids.append(artist_id)
        return (artist_ids, new_artist_ids)

    """
        Add album artist to db
        @param album_artist as string
        @param outside as bool
        @param sql as sqlite cursor
        @param return ([album artist ids as int], [new as bool])
        @commit needed
    """
    def _add_album_artist(self, album_artist, outside, sql):
        album_artist_id = Navigation.COMPILATIONS
        new = False
        if album_artist is not None:
            album_artist = format_artist_name(album_artist)
            # Get album artist id, add it if missing
            album_artist_id = Objects.artists.get_id(album_artist, sql)
            if album_artist_id is None:
                Objects.artists.add(album_artist, outside, sql)
                album_artist_id = Objects.artists.get_id(album_artist, sql)
                new = True
        return (album_artist_id, new)

    """
        Add genres to db
        @param genres as [string]
        @param outside as bool
        @param sql as sqlite cursor
        @param return ([genre_ids], [new_genre_ids])
        @commit needed
    """
    def _add_genres(self, genres, album_id, outside, sql):
        # Get all genre ids
        genre_ids = []
        new_genre_ids = []
        for genre in genres:
            # Get genre id, add genre if missing
            genre_id = Objects.genres.get_id(genre, sql)
            if genre_id is None:
                Objects.genres.add(genre, outside, sql)
                genre_id = Objects.genres.get_id(genre, sql)
                new_genre_ids.append(genre_id)
            genre_ids.append(genre_id)

        for genre_id in genre_ids:
            Objects.albums.add_genre(album_id, genre_id, outside, sql)
        return (genre_ids, new_genre_ids)

    """
        Add album to db
        @param album name as string
        @param album artist id as int
        @param path to an album track as string
        @param outside as bool
        @param sql as sqlite cursor
        @return album id as int
        @commit needed
    """
    def _add_album(self, album_name, artist_id, filepath, outside, sql):
        path = os.path.dirname(filepath)
        album_id = Objects.albums.get_id(album_name, artist_id, sql)
        if album_id is None:
            # If db was empty on scan,
            # use file modification time to get recents
            if self._is_empty:
                mtime = int(os.path.getmtime(filepath))
            # Use current time
            else:
                mtime = int(time())
            Objects.albums.add(album_name, artist_id,
                               path, 0, outside, mtime, sql)
            album_id = Objects.albums.get_id(album_name, artist_id, sql)
        return album_id

    """
        Restore albums popularties
    """
    def _restore_popularities(self, sql):
        self._popularities = Objects.db.get_popularities()
        result = sql.execute("SELECT albums.name, artists.name, albums.rowid\
                              FROM albums, artists\
                              WHERE artists.rowid == albums.artist_id")
        for row in result:
            string = "%s_%s" % (row[0], row[1])
            if string in self._popularities:
                Objects.albums.set_popularity(row[2],
                                              self._popularities[string], sql)
    """
        Restore albums mtimes
    """
    def _restore_mtimes(self, sql):
        self._mtimes = Objects.db.get_mtimes()
        result = sql.execute("SELECT albums.name, artists.name, albums.rowid\
                              FROM albums, artists\
                              WHERE artists.rowid == albums.artist_id")
        for row in result:
            string = "%s_%s" % (row[0], row[1])
            if string in self._mtimes:
                Objects.albums.set_mtime(row[2],
                                         self._mtimes[string], sql)
