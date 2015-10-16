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

from gi.repository import GLib, Gio, GObject

from time import sleep

from lollypop.define import Lp
from lollypop.objects import Track


class MtpSync:
    """
        Synchronisation to MTP devices
    """
    __gsignals__ = {
        'sync-finished': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self):
        """
            Init MTP synchronisation
        """
        self._syncing = False
        self._errors = False
        self._errors_count = 0
        self._total = 0  # Total files to sync
        self._done = 0   # Handled files on sync
        self._fraction = 0.0
        self._copied_art_uris = []

############
# Private  #
############
    def _retry(self, func, args, t=5):
        """
            Try to execute func 5 times
            @param func as function
            @param args as tuple
        """
        # Max allowed errors
        if self._errors_count > 10:
            self._syncing = False
            return
        if t == 0:
            self._errors_count += 1
            self._errors = True
            return
        try:
            func(*args)
        except Exception as e:
            print("MtpSync::_retry(%s, %s): %s" % (func, args, e))
            for a in args:
                if isinstance(a, Gio.File):
                    print(a.get_uri())
            sleep(5)
            self._retry(func, args, t-1)

    def _get_children_uris(self, uri):
        """
            Return children uris for uri
            @param uri as str
            @return [str]
        """
        children = []
        dir_uris = [uri]
        while dir_uris:
            uri = dir_uris.pop(0)
            d = Gio.File.new_for_uri(uri)
            infos = d.enumerate_children(
                'standard::name,standard::type',
                Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
                None)
            for info in infos:
                if info.get_file_type() == Gio.FileType.DIRECTORY:
                    dir_uris.append(uri+'/'+info.get_name())
                else:
                    children.append(uri+'/'+info.get_name())
        return children

    def _sync(self, playlists):
        """
            Sync playlists with device as this
            @param playlists as [str]
        """
        try:
            self._in_thread = True
            self._errors = False
            self._errors_count = 0
            self._copied_art_uris = []
            # For progress bar
            self._total = 1
            self._done = 0
            self._fraction = 0.0
            plnames = []

            # New tracks
            for playlist in playlists:
                plnames.append(Lp.playlists.get_name(playlist))
                self._fraction = self._done/self._total
                self._total += len(Lp.playlists.get_tracks(playlist))

            # Old tracks
            try:
                children = self._get_children_uris(self._uri+'/tracks')
                self._total += len(children)
            except:
                pass
            GLib.idle_add(self._update_progress)

            # Copy new tracks to device
            if self._syncing:
                self._copy_to_device(playlists)

            # Remove old tracks from device
            if self._syncing:
                self._remove_from_device(playlists)

            # Delete old playlists
            d = Gio.File.new_for_uri(self._uri)
            infos = d.enumerate_children(
                'standard::name',
                Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
                None)
            for info in infos:
                f = info.get_name()
                if f.endswith(".m3u") and f[:-4] not in plnames:
                    uri = self._uri+'/'+f
                    d = Gio.File.new_for_uri(uri)
                    self._retry(d.delete, (None,))

        except Exception as e:
            print("DeviceManagerWidget::_sync(): %s" % e)
        self._fraction = 1.0
        GLib.idle_add(self._update_progress)
        self._syncing = False
        self._in_thread = False
        if self._errors:
            GLib.idle_add(self._on_errors)
        GLib.idle_add(self._on_finished)

    def _copy_to_device(self, playlists):
        """
            Copy file from playlist to device
            @param playlists as [str]
        """
        for playlist in playlists:
            try:
                playlist_name = Lp.playlists.get_name(playlist)
                # Create playlist
                m3u = Gio.File.new_for_path(
                    "/tmp/lollypop_%s.m3u" % (playlist_name,))
                self._retry(m3u.replace_contents, (b'#EXTM3U\n', None, False,
                            Gio.FileCreateFlags.REPLACE_DESTINATION,
                            None))
                stream = m3u.open_readwrite(None)
            except Exception as e:
                print("DeviceWidget::_copy_to_device(): %s" % e)
                m3u = None
                stream = None

            # Start copying
            tracks_ids = Lp.playlists.get_tracks_ids(playlist)
            for track_id in tracks_ids:
                if track_id is None:
                    continue
                if not self._syncing:
                    self._fraction = 1.0
                    self._in_thread = False
                    return
                track = Track(track_id)
                # Sanitize file names as some MTP devices do not like this
                # Or this is a Gio/GObject Introspection bug
                album_name = "".join([c for c in track.album_name if
                                      c.isalpha() or
                                      c.isdigit() or c == ' ']).rstrip()
                # Sanitize file names as some MTP devices do not like this
                # Or this is a Gio/GObject Introspection bug
                artist_name = "".join([c for c in track.artist if
                                       c.isalpha() or
                                       c.isdigit() or c == ' ']).rstrip()
                on_device_album_uri = "%s/tracks/%s_%s" %\
                                      (self._uri,
                                       artist_name.lower(),
                                       album_name.lower())

                d = Gio.File.new_for_uri(on_device_album_uri)
                if not d.query_exists(None):
                    self._retry(d.make_directory_with_parents, (None,))
                # Copy album art
                art = Lp.art.get_album_artwork_path(track.album)
                if art is not None:
                    src_art = Gio.File.new_for_path(art)
                    art_uri = "%s/cover.jpg" % on_device_album_uri
                    self._copied_art_uris.append(art_uri)
                    dst_art = Gio.File.new_for_uri(art_uri)
                    if not dst_art.query_exists(None):
                        self._retry(src_art.copy,
                                    (dst_art, Gio.FileCopyFlags.OVERWRITE,
                                     None, None))

                track_name = GLib.basename(track.path)
                # Sanitize file names as some MTP devices do not like this
                # Or this is a Gio/GObject Introspection bug
                track_name = "".join([c for c in track_name if c.isalpha() or
                                      c.isdigit() or
                                      c == ' ' or
                                      c == '.']).rstrip()
                src_track = Gio.File.new_for_path(track.path)
                info = src_track.query_info('time::modified',
                                            Gio.FileQueryInfoFlags.NONE,
                                            None)
                # Prefix track with mtime to make sure updating it later
                mtime = info.get_attribute_as_string('time::modified')
                dst_uri = "%s/%s_%s" % (on_device_album_uri,
                                        mtime, track_name)
                if stream is not None:
                    line = "tracks/%s_%s/%s_%s\n" %\
                            (artist_name.lower(),
                             album_name.lower(),
                             mtime,
                             track_name)
                    self._retry(stream.get_output_stream().write,
                                (line.encode(encoding='UTF-8'), None))
                dst_track = Gio.File.new_for_uri(dst_uri)
                if not dst_track.query_exists(None):
                    self._retry(src_track.copy,
                                (dst_track, Gio.FileCopyFlags.OVERWRITE,
                                 None, None))
                else:
                    self._done += 1
                self._done += 1
                self._fraction = self._done/self._total
                GLib.idle_add(self._update_progress)
            if stream is not None:
                stream.close()
            if m3u is not None:
                dst = Gio.File.new_for_uri(self._uri+'/'+playlist_name+'.m3u')
                self._retry(m3u.move,
                            (dst, Gio.FileCopyFlags.OVERWRITE, None, None))

    def _remove_from_device(self, playlists):
        """
            Delete files not available in playlist
        """
        track_uris = []
        tracks_ids = []

        # Get tracks ids
        for playlist in playlists:
            tracks_ids += Lp.playlists.get_tracks_ids(playlist)

        # Get tracks uris
        for track_id in tracks_ids:
            if not self._syncing:
                self._fraction = 1.0
                self._in_thread = False
                return
            track = Track(track_id)
            # Sanitize file names as some MTP devices do not like this
            # Or this is a Gio/GObject Introspection bug
            album_name = "".join([c for c in track.album_name if
                                  c.isalpha() or
                                  c.isdigit() or c == ' ']).rstrip()
            # Sanitize file names as some MTP devices do not like this
            # Or this is a Gio/GObject Introspection bug
            artist_name = "".join([c for c in track.artist if
                                   c.isalpha() or
                                   c.isdigit() or c == ' ']).rstrip()
            track_path = Lp.tracks.get_path(track_id)
            album_uri = "%s/tracks/%s_%s" % (self._uri,
                                             artist_name.lower(),
                                             album_name.lower())

            track_name = GLib.basename(track_path)
            # Sanitize file names as some MTP devices do not like this
            # Or this is a Gio/GObject Introspection bug
            track_name = "".join([c for c in track_name if c.isalpha() or
                                  c.isdigit() or
                                  c == ' ' or
                                  c == '.']).rstrip()
            on_disk = Gio.File.new_for_path(track_path)
            info = on_disk.query_info('time::modified',
                                      Gio.FileQueryInfoFlags.NONE,
                                      None)
            # Prefix track with mtime to make sure updating it later
            mtime = info.get_attribute_as_string('time::modified')
            dst_uri = "%s/%s_%s" % (album_uri, mtime, track_name)
            track_uris.append(dst_uri)

        on_mtp_files = self._get_children_uris(self._uri+'/tracks')

        # Delete file on device and not in playlists
        for uri in on_mtp_files:
            if not self._syncing:
                self._fraction = 1.0
                self._in_thread = False
                return
            if uri not in track_uris and uri not in self._copied_art_uris:
                to_delete = Gio.File.new_for_uri(uri)
                self._retry(to_delete.delete, (None,))
            self._done += 1
            self._fraction = self._done/self._total
            GLib.idle_add(self._update_progress)

    def _update_progress(self):
        """
            Update progress bar. Do nothing
        """
        pass

    def _on_finished(self):
        """
            Clean on finished. Do nothing
        """
        pass

    def _on_errors(self):
        """
            Show something to the user. Do nothing.
        """
        pass
