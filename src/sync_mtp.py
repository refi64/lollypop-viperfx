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

from gi.repository import GLib, Gio, Gst

import os.path
from time import sleep

from lollypop.utils import escape
from lollypop.define import Lp, Type
from lollypop.objects import Track


# TODO Rework this code: was designed
# for playlists and then for albums, it sucks!
class MtpSync:
    """
        Synchronisation to MTP devices
    """
    def __init__(self):
        """
            Init MTP synchronisation
        """
        self._syncing = False
        self.__errors = False
        self.__convert = False
        self.__normalize = False
        self.__errors_count = 0
        self._uri = ""
        self.__total = 0  # Total files to sync
        self.__done = 0   # Handled files on sync
        self._fraction = 0.0
        self.__copied_art_uris = []

#######################
# PROTECTED           #
#######################
    def _check_encoder_status(self):
        """
            Check MP3 encode status
            @return bool
        """
        if Gst.ElementFactory.find('lamemp3enc'):
            return True
        return False

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

    def _sync(self, playlists, convert, normalize):
        """
            Sync playlists with device. If playlists contains Type.NONE,
            sync albums marked as to be synced
            @param playlists as [str]
            @param convert as bool
            @param normalize as bool
        """
        try:
            self.__in_thread = True
            self.__convert = convert
            self.__normalize = normalize
            self.__errors = False
            self.__errors_count = 0
            self.__copied_art_uris = []
            # For progress bar
            self.__total = 1
            self.__done = 0
            self._fraction = 0.0
            plnames = []

            if playlists[0] == Type.NONE:
                # New tracks for synced albums
                album_ids = Lp().albums.get_synced_ids()
                for album_id in album_ids:
                    self.__total += len(Lp().albums.get_track_ids(album_id))
            else:
                # New tracks for playlists
                for playlist in playlists:
                    plnames.append(Lp().playlists.get_name(playlist))
                    self.__total += len(Lp().playlists.get_tracks(playlist))

            # Old tracks
            try:
                children = self.__get_track_files()
                self.__total += len(children)
            except:
                pass
            GLib.idle_add(self._update_progress)

            # Copy new tracks to device
            if self._syncing:
                self.__copy_to_device(playlists)

            # Remove old tracks from device
            if self._syncing:
                self.__remove_from_device(playlists)

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
                    self.__retry(d.delete, (None,))

            d = Gio.File.new_for_uri(self._uri+"/unsync")
            if not d.query_exists(None):
                self.__retry(d.make_directory_with_parents, (None,))
        except Exception as e:
            print("DeviceManagerWidget::_sync(): %s" % e)
        self._fraction = 1.0
        self._syncing = False
        self.__in_thread = False
        if self.__errors:
            GLib.idle_add(self.__on_errors)

############
# Private  #
############
    def __retry(self, func, args, t=5):
        """
            Try to execute func 5 times
            @param func as function
            @param args as tuple
        """
        # Max allowed errors
        if self.__errors_count > 10:
            self._syncing = False
            return
        if t == 0:
            self.__errors_count += 1
            self.__errors = True
            return
        try:
            func(*args)
        except Exception as e:
            print("MtpSync::_retry(%s, %s): %s" % (func, args, e))
            for a in args:
                if isinstance(a, Gio.File):
                    print(a.get_uri())
            sleep(5)
            self.__retry(func, args, t-1)

    def __get_track_files(self):
        """
            Return files in self._uri/tracks
            @return [str]
        """
        children = []
        dir_uris = [self._uri]
        d = Gio.File.new_for_uri(self._uri)
        if not d.query_exists(None):
            self.__retry(d.make_directory_with_parents, (None,))
        while dir_uris:
            try:
                uri = dir_uris.pop(0)
                album = uri.replace(self._uri, "")
                d = Gio.File.new_for_uri(self._uri+"/"+album)
                infos = d.enumerate_children(
                    'standard::name,standard::type',
                    Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
                    None)
                for info in infos:
                    if info.get_file_type() == Gio.FileType.DIRECTORY:
                        if info.get_name() != "unsync":
                            dir_uris.append(uri+info.get_name())
                    else:
                        track = info.get_name()
                        if not track.endswith('m3u'):
                            children.append("%s/%s/%s" % (self._uri,
                                                          album,
                                                          track))
            except Exception as e:
                print("MtpSync::_get_track_files():", e, uri)
        return children

    def __copy_to_device(self, playlists):
        """
            Copy file from playlist to device
            @param playlists as [str]
        """
        for playlist in playlists:
            m3u = None
            stream = None
            if playlist != Type.NONE:
                try:
                    playlist_name = Lp().playlists.get_name(playlist)
                    # Create playlist
                    m3u = Gio.File.new_for_path(
                        "/tmp/lollypop_%s.m3u" % (playlist_name,))
                    self.__retry(m3u.replace_contents, (b'#EXTM3U\n', None,
                                 False,
                                 Gio.FileCreateFlags.REPLACE_DESTINATION,
                                 None))
                    stream = m3u.open_readwrite(None)
                except Exception as e:
                    print("DeviceWidget::_copy_to_device(): %s" % e)
            # Get tracks
            if playlist == Type.NONE:
                track_ids = []
                album_ids = Lp().albums.get_synced_ids()
                for album_id in album_ids:
                    track_ids += Lp().albums.get_track_ids(album_id)
            else:
                track_ids = Lp().playlists.get_track_ids(playlist)
            # Start copying
            for track_id in track_ids:
                if track_id is None:
                    continue
                if not self._syncing:
                    self._fraction = 1.0
                    self.__in_thread = False
                    return
                track = Track(track_id)
                album_name = escape(track.album_name.lower())
                if track.album.artist_ids[0] == Type.COMPILATIONS:
                    artists = escape(", ".join(track.artists).lower())
                else:
                    artists = escape(", ".join(track.album.artists).lower())
                on_device_album_uri = "%s/%s_%s" %\
                                      (self._uri,
                                       artists,
                                       album_name)

                d = Gio.File.new_for_uri(on_device_album_uri)
                if not d.query_exists(None):
                    self.__retry(d.make_directory_with_parents, (None,))
                # Copy album art
                art = Lp().art.get_album_artwork_path(track.album)
                if art is not None:
                    src_art = Gio.File.new_for_path(art)
                    art_uri = "%s/cover.jpg" % on_device_album_uri
                    self.__copied_art_uris.append(art_uri)
                    dst_art = Gio.File.new_for_uri(art_uri)
                    if not dst_art.query_exists(None):
                        self.__retry(src_art.copy,
                                     (dst_art, Gio.FileCopyFlags.OVERWRITE,
                                      None, None))

                filepath = GLib.filename_from_uri(track.uri)[0]
                track_name = escape(GLib.basename(filepath))
                # Check extension, if not mp3, convert
                ext = os.path.splitext(filepath)[1]
                if (ext != ".mp3" or self.__normalize) and self.__convert:
                    convertion_needed = True
                    track_name = track_name.replace(ext, ".mp3")
                else:
                    convertion_needed = False
                src_track = Gio.File.new_for_uri(track.uri)
                info = src_track.query_info('time::modified',
                                            Gio.FileQueryInfoFlags.NONE,
                                            None)
                # Prefix track with mtime to make sure updating it later
                mtime = info.get_attribute_as_string('time::modified')
                dst_uri = "%s/%s_%s" % (on_device_album_uri,
                                        mtime, track_name)
                if stream is not None:
                    line = "%s_%s/%s_%s\n" %\
                            (artists,
                             album_name,
                             mtime,
                             track_name)
                    self.__retry(stream.get_output_stream().write,
                                 (line.encode(encoding='UTF-8'), None))
                dst_track = Gio.File.new_for_uri(dst_uri)
                if not dst_track.query_exists(None):
                    if convertion_needed:
                        mp3_uri = "file:///tmp/%s" % track_name
                        mp3_file = Gio.File.new_for_uri(mp3_uri)
                        pipeline = self.__convert_to_mp3(src_track, mp3_file)
                        # Check if encoding is finished
                        if pipeline is not None:
                            bus = pipeline.get_bus()
                            bus.add_signal_watch()
                            bus.connect('message::eos', self.__on_bus_eos)
                            self.__encoding = True
                            while self.__encoding and self.__sync:
                                sleep(1)
                            bus.disconnect_by_func(self.__on_bus_eos)
                            pipeline.set_state(Gst.State.PAUSED)
                            pipeline.set_state(Gst.State.READY)
                            pipeline.set_state(Gst.State.NULL)
                            self.__retry(
                                    mp3_file.move,
                                    (dst_track, Gio.FileCopyFlags.OVERWRITE,
                                     None, None))
                            # To be sure
                            try:
                                mp3_file.delete(None)
                            except:
                                pass
                    else:
                        self.__retry(src_track.copy,
                                     (dst_track, Gio.FileCopyFlags.OVERWRITE,
                                      None, None))
                else:
                    self.__done += 1
                self.__done += 1
                self._fraction = self.__done/self.__total
            if stream is not None:
                stream.close()
            if m3u is not None:
                playlist_name = escape(playlist_name)
                dst = Gio.File.new_for_uri(self._uri+'/'+playlist_name+'.m3u')
                self.__retry(m3u.move,
                             (dst, Gio.FileCopyFlags.OVERWRITE, None, None))

    def __remove_from_device(self, playlists):
        """
            Delete files not available in playlist
        """
        track_uris = []
        track_ids = []

        # Get tracks
        if playlists[0] == Type.NONE:
            track_ids = []
            album_ids = Lp().albums.get_synced_ids()
            for album_id in album_ids:
                track_ids += Lp().albums.get_track_ids(album_id)
        else:
            for playlist in playlists:
                track_ids += Lp().playlists.get_track_ids(playlist)

        # Get tracks uris
        for track_id in track_ids:
            if not self._syncing:
                self._fraction = 1.0
                self.__in_thread = False
                return
            track = Track(track_id)
            album_name = escape(track.album_name.lower())
            if track.album.artist_ids[0] == Type.COMPILATIONS:
                artists = escape(", ".join(track.artists).lower())
            else:
                artists = escape(", ".join(track.album.artists).lower())
            album_uri = "%s/%s_%s" % (self._uri,
                                      artists,
                                      album_name)
            filepath = GLib.filename_from_uri(track.uri)[0]
            track_name = escape(GLib.basename(filepath))
            # Check extension, if not mp3, convert
            ext = os.path.splitext(filepath)[1]
            if ext != ".mp3" and self.__convert:
                track_name = track_name.replace(ext, ".mp3")
            on_disk = Gio.File.new_for_path(filepath)
            info = on_disk.query_info('time::modified',
                                      Gio.FileQueryInfoFlags.NONE,
                                      None)
            # Prefix track with mtime to make sure updating it later
            mtime = info.get_attribute_as_string('time::modified')
            dst_uri = "%s/%s_%s" % (album_uri, mtime, track_name)
            track_uris.append(dst_uri)

        on_mtp_files = self.__get_track_files()

        # Delete file on device and not in playlists
        for uri in on_mtp_files:
            if not self._syncing:
                self._fraction = 1.0
                self.__in_thread = False
                return

            if uri not in track_uris and uri not in self.__copied_art_uris:
                to_delete = Gio.File.new_for_uri(uri)
                self.__retry(to_delete.delete, (None,))
            self.__done += 1
            self._fraction = self.__done/self.__total

    def __convert_to_mp3(self, src, dst):
        """
            Convert file to mp3
            @param src as Gio.File
            @param dst as Gio.File
            @return Gst.Pipeline
        """
        try:
            # We need to escape \ in path
            src_path = src.get_path().replace("\\", "\\\\\\")
            dst_path = dst.get_path().replace("\\", "\\\\\\")
            if self.__normalize:
                pipeline = Gst.parse_launch(
                                        'filesrc location="%s" ! decodebin\
                                        ! audioconvert\
                                        ! rgvolume pre-amp=6.0 headroom=10.0\
                                        ! rglimiter ! audioconvert\
                                        ! lamemp3enc ! id3v2mux\
                                        ! filesink location="%s"'
                                        % (src_path, dst_path))
            else:
                pipeline = Gst.parse_launch(
                                        'filesrc location="%s" ! decodebin\
                                        ! audioconvert ! lamemp3enc ! id3v2mux\
                                        ! filesink location="%s"'
                                        % (src_path, dst_path))
            pipeline.set_state(Gst.State.PLAYING)
            return pipeline
        except Exception as e:
            print("MtpSync::_convert_to_mp3(): %s" % e)
            return None

    def __on_bus_eos(self, bus, message):
        """
            Stop encoding
            @param bus as Gst.Bus
            @param message as Gst.Message
        """
        self.__encoding = False

    def __on_errors(self):
        """
            Show something to the user. Do nothing.
        """
        pass
