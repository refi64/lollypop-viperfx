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

from gi.repository import GLib, Gio, Gst, GObject

from time import sleep
from re import match
import json

from lollypop.logger import Logger
from lollypop.utils import escape
from lollypop.define import App, Type
from lollypop.objects import Track, Album


class MtpSyncDb:
    """
        Synchronisation db stored on MTP device

        Some MTP devices for instance cannot properly store / retrieve file
        modification times, so we store them in a dedicated file at the root
        of the MTP device instead.

        The storage format is a simple JSON dump.
        It also implements the context manager interface, ensuring database is
        loaded before entering the scope and saving it when exiting.
    """

    def __init__(self):
        """
            Constructor for MtpSyncDb
        """
        self.__encoder = "convert_none"
        self.__normalize = False
        self.__metadata = {}

    def load(self, base_uri):
        """
            Loads the metadata db from the MTP device
            @param base_uri as str
        """
        self.__base_uri = base_uri
        self.__db_uri = self.__base_uri + "/lollypop-sync.db"
        Logger.debug("MtpSyncDb::__load_db()")
        try:
            dbfile = Gio.File.new_for_uri(self.__db_uri)
            (status, jsonraw, tags) = dbfile.load_contents(None)
            if status:
                jsondb = json.loads(jsonraw.decode("utf-8"))
                if "encoder" in jsondb:
                    self.__encoder = jsondb["encoder"]
                if "normalize" in jsondb:
                    self.__normalize = jsondb["normalize"]
                if "version" in jsondb and jsondb["version"] == 1:
                    for m in jsondb["tracks_metadata"]:
                        self.__metadata[m["uri"]] = m["metadata"]
                else:
                    Logger.info("MtpSyncDb::__load_db():"
                                " unknown sync db version")
        except Exception as e:
            Logger.error("MtpSyncDb::load(): %s" % e)

    def save(self):
        """
            Saves the metadata db to the MTP device
        """
        try:
            Logger.debug("MtpSyncDb::__save()")
            jsondb = json.dumps(
                            {"version": 1,
                             "encoder": self.__encoder,
                             "normalize": self.__normalize,
                             "tracks_metadata": [
                                 {"uri": x, "metadata": y}
                                 for x, y in sorted(self.__metadata.items())]})
            dbfile = Gio.File.new_for_uri(self.__db_uri)
            (tmpfile, stream) = Gio.File.new_tmp()
            stream.get_output_stream().write_all(jsondb.encode("utf-8"))
            tmpfile.copy(dbfile, Gio.FileCopyFlags.OVERWRITE, None, None)
            stream.close()
        except Exception as e:
            Logger.error("MtpSyncDb::__save(): %s", e)

    def set_encoder(self, encoder):
        """
            Set encoder
            @param encoder as str
        """
        self.__encoder = encoder

    def set_normalize(self, normalize):
        """
            Set normalize
            @param normalize as bool
        """
        self.__normalize = normalize

    def get_mtime(self, uri):
        """
            Get mtime for a uri on MTP device from the metadata db
            @param uri as str
        """
        return self.__metadata.get(
            self.__get_reluri(uri), {}).get("time::modified", 0)

    def set_mtime(self, uri, mtime):
        """
            Set mtime for a uri on MTP device from the metadata db
            @param uri as str
            @param mtime as int
        """
        self.__metadata.setdefault(self.__get_reluri(uri),
                                   dict())["time::modified"] = mtime

    def delete_uri(self, uri):
        """
            Deletes metadata for a uri from the on-device metadata db
            @param uri as str
        """
        if self.__get_reluri(uri) in self.__metadata:
            del self.__metadata[self.__get_reluri(uri)]

    @property
    def encoder(self):
        """
            Get encoder
            @return str
        """
        return self.__encoder

    @property
    def normalize(self):
        """
            Get normalize
            @return bool
        """
        return self.__normalize

############
# Private  #
############
    def __get_reluri(self, uri):
        """
            Returns a relative on-device uri from an absolute on-device.
            We do not want to store absolute uri in the db as the same
            peripheral could have a different path when mounted on another host
            machine.
            @param uri as str
        """
        if uri.startswith(self.__base_uri):
            uri = uri[len(self.__base_uri) + 1:]
        return uri


class MtpSync(GObject.Object):
    """
        Synchronisation to MTP devices
    """
    __gsignals__ = {
        "sync-progress": (GObject.SignalFlags.RUN_FIRST, None, (float,)),
        "sync-finished": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "sync-errors": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    __ENCODE_START = 'filesrc location="%s" ! decodebin\
                            ! audioconvert\
                            ! audioresample\
                            ! audio/x-raw,rate=44100,channels=2'
    __ENCODE_END = ' ! filesink location="%s"'
    __NORMALIZE = " ! rgvolume pre-amp=6.0 headroom=10.0\
                    ! rglimiter ! audioconvert"
    __EXTENSION = {"convert_none": None,
                   "convert_mp3": ".mp3",
                   "convert_vorbis": ".ogg",
                   "convert_flac": ".flac",
                   "convert_aac": ".m4a"}
    __ENCODERS = {"convert_none": None,
                  "convert_mp3": " ! lamemp3enc target=bitrate\
                                   cbr=true bitrate=%s ! id3v2mux",
                  "convert_vorbis": " ! vorbisenc max-bitrate=%s\
                                      ! oggmux",
                  "convert_flac": " ! flacenc",
                  "convert_aac": " ! faac bitrate=%s ! mp4mux"}
    _GST_ENCODER = {"convert_mp3": "lamemp3enc",
                    "convert_ogg": "vorbisenc",
                    "convert_flac": "flacenc",
                    "convert_aac": "faac"}

    def __init__(self):
        """
            Init MTP synchronisation
        """
        GObject.Object.__init__(self)
        self.__cancellable = Gio.Cancellable()
        self.__cancellable.cancel()
        self.__errors_count = 0
        self.__on_mtp_files = []
        self.__last_error = ""
        self.__uri = None
        self.__total = 0  # Total files to sync
        self.__done = 0   # Handled files on sync
        self.__mtp_syncdb = MtpSyncDb()

    def check_encoder_status(self, encoder):
        """
            Check encoder status
            @param encoder as str
            @return bool
        """
        if Gst.ElementFactory.find(self._GST_ENCODER[encoder]):
            return True
        return False

    def sync(self, uri):
        """
            Sync playlists with device. If playlists contains Type.NONE,
            sync albums marked as to be synced
            @param uri as str
        """
        try:
            self.__cancellable.reset()
            self.__uri = uri
            self.__on_mtp_files = self.__get_track_files()
            self.__cancellable.reset()
            self.__convert_bitrate = App().settings.get_value(
                "convert-bitrate").get_int32()
            self.__errors_count = 0
            # For progress bar
            self.__total = 0
            self.__done = 0
            playlists = []

            Logger.debug("Get new tracks before sync")
            # New tracks for synced albums
            album_ids = App().albums.get_synced_ids()
            for album_id in album_ids:
                album = Album(album_id)
                self.__total += len(album.track_ids)
            # New tracks for playlists
            playlist_ids = App().playlists.get_synced_ids()
            for playlist_id in playlist_ids:
                playlists.append(App().playlists.get_name(playlist_id))
                if App().playlists.get_smart(playlist_id):
                    request = App().playlists.get_smart_sql(playlist_id)
                    track_ids = App().db.execute(request)
                else:
                    track_ids = App().playlists.get_track_ids(playlist_id)
                self.__total += len(track_ids)

            Logger.debug("Get old tracks")
            self.__total += len(self.__on_mtp_files)

            # Copy new tracks to device
            if not self.__cancellable.is_cancelled():
                Logger.debug("Sync albums")
                self.__sync_albums()
                Logger.debug("Sync playlists")
                self.__sync_playlists(playlist_ids)

            # Remove old tracks from device
            if not self.__cancellable.is_cancelled():
                Logger.debug("Remove from device")
                self.__remove_from_device(playlist_ids)

            # Remove empty dirs
            if not self.__cancellable.is_cancelled():
                Logger.debug("Remove empty dirs")
                self.__remove_empty_dirs()

            if not self.__cancellable.is_cancelled():
                Logger.debug("Remove old playlists")
                # Remove old playlists
                d = Gio.File.new_for_uri(self.__uri)
                infos = d.enumerate_children(
                    "standard::name",
                    Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
                    None)
                for info in infos:
                    name = info.get_name()
                    if name.endswith(".m3u") and name[:-4] not in playlists:
                        f = infos.get_child(info)
                        self.__retry(f.delete, (None,))

            Logger.debug("Create unsync")
            d = Gio.File.new_for_uri(self.__uri + "/unsync")
            if not d.query_exists():
                self.__retry(d.make_directory_with_parents, (None,))
        except Exception as e:
            Logger.error("MtpSync::__sync(): %s" % e)
        finally:
            Logger.debug("Save sync db")
            self.__mtp_syncdb.save()
            self.__cancellable.cancel()
            if self.__errors_count != 0:
                Logger.debug("Sync errors")
                GLib.idle_add(self.emit, "sync-errors", self.__last_error)
            Logger.debug("Sync finished")
            GLib.idle_add(self.emit, "sync-finished")

    @property
    def cancellable(self):
        """
            Get cancellable
            @return Gio.Cancellable
        """
        return self.__cancellable

    @property
    def db(self):
        """
            Get sync db
        """
        return self.__mtp_syncdb

############
# Private  #
############
    def __retry(self, func, args):
        """
            Try to execute func and handle errors
            @param func as function
            @param args as tuple
        """
        # Max allowed errors
        if self.__errors_count > 5:
            self.__cancellable.cancel()
            return
        try:
            func(*args)
        except Exception as e:
            Logger.error("MtpSync::_retry(%s, %s): %s" % (func, args, e))
            self.__last_error = e
            self.__errors_count += 1
            sleep(1)

    def __remove_empty_dirs(self):
        """
            Delete empty dirs
        """
        to_delete = []
        dir_uris = [self.__uri]
        try:
            # First get all directories
            while dir_uris:
                if self.__cancellable.is_cancelled():
                    break
                uri = dir_uris.pop(0)
                d = Gio.File.new_for_uri(uri)
                infos = d.enumerate_children(
                    "standard::name,standard::type",
                    Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
                    None)
                for info in infos:
                    if self.__cancellable.is_cancelled():
                        break
                    if info.get_file_type() == Gio.FileType.DIRECTORY:
                        if info.get_name() != "unsync":
                            f = infos.get_child(info)
                            # We need to check for dir to be empty
                            # On some device, Gio.File.delete() remove
                            # non empty directories #828
                            subinfos = f.enumerate_children(
                                "standard::name,standard::type",
                                Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
                                None)
                            subfiles = False
                            for info in subinfos:
                                subfiles = True
                                dir_uris.append(f.get_uri())
                                break
                            if not subfiles:
                                to_delete.append(f.get_uri())
            # Then delete
            for d in to_delete:
                if self.__cancellable.is_cancelled():
                    break
                d = Gio.File.new_for_uri(d)
                try:
                    d.delete()
                except:
                    pass
        except Exception as e:
            Logger.error("MtpSync::__remove_empty_dirs(): %s, %s" % (e, uri))

    def __get_track_files(self):
        """
            Return files in self.__uri/tracks
            @return [str]
        """
        children = []
        dir_uris = [self.__uri]
        d = Gio.File.new_for_uri(self.__uri)
        if not d.query_exists():
            self.__retry(d.make_directory_with_parents, (None,))
        while dir_uris:
            if self.__cancellable.is_cancelled():
                break
            try:
                uri = dir_uris.pop(0)
                d = Gio.File.new_for_uri(uri)
                infos = d.enumerate_children(
                    "standard::name,standard::type",
                    Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
                    None)
                for info in infos:
                    if self.__cancellable.is_cancelled():
                        break
                    if info.get_file_type() == Gio.FileType.DIRECTORY:
                        if info.get_name() != "unsync":
                            f = infos.get_child(info)
                            dir_uris.append(f.get_uri())
                    else:
                        if info.get_name() == "lollypop-sync.db":
                            continue
                        f = infos.get_child(info)
                        if not f.get_uri().endswith(".m3u"):
                            children.append(f.get_uri())
            except Exception as e:
                Logger.error("MtpSync::__get_track_files(): %s, %s" % (e, uri))
        return children

    def __sync_track_id(self, track):
        """
            Sync track to device
            @param track as Track
            @return (str, str, str, bool)
        """
        Logger.debug("MtpSync::__sync_track_id(): %s" % track.uri)
        album_name = escape(track.album_name.lower())
        is_compilation = track.album.artist_ids[0] == Type.COMPILATIONS
        if is_compilation:
            artists = None
            on_device_album_uri = "%s/%s" %\
                                  (self.__uri,
                                   album_name)
        else:
            artists = escape(", ".join(track.album.artists).lower())
            on_device_album_uri = "%s/%s_%s" %\
                                  (self.__uri,
                                   artists,
                                   album_name)

        d = Gio.File.new_for_uri(on_device_album_uri)
        if not d.query_exists():
            self.__retry(d.make_directory_with_parents, (None,))
        # Copy album art
        art = App().art.get_album_artwork_uri(track.album)
        Logger.debug("MtpSync::__sync_track_id(): %s" % art)
        if art is not None:
            src_art = Gio.File.new_for_uri(art)
            art_uri = "%s/cover.jpg" % on_device_album_uri
            # To be sure to get uri correctly escaped for Gio
            f = Gio.File.new_for_uri(art_uri)
            dst_art = Gio.File.new_for_uri(art_uri)
            if dst_art.get_uri() in self.__on_mtp_files:
                self.__on_mtp_files.remove(dst_art.get_uri())
            if not dst_art.query_exists():
                self.__retry(src_art.copy,
                             (dst_art, Gio.FileCopyFlags.OVERWRITE,
                              None, None))
        f = Gio.File.new_for_uri(track.uri)
        track_name = escape(f.get_basename())
        # Check extension, if not mp3, convert
        m = match(r".*(\.[^.]*)", track.uri)
        ext = m.group(1)
        convert_ext = self.__EXTENSION[self.__mtp_syncdb.encoder]
        if (convert_ext is not None and
                ext != convert_ext) or self.__mtp_syncdb.normalize:
            convertion_needed = True
            track_name = track_name.replace(ext, convert_ext)
        else:
            convertion_needed = False
        src_track = Gio.File.new_for_uri(track.uri)
        info = src_track.query_info("time::modified",
                                    Gio.FileQueryInfoFlags.NONE,
                                    None)
        # Prefix track with mtime to make sure updating it later
        mtime = info.get_attribute_uint64("time::modified")
        dst_uri = "%s/%s" % (on_device_album_uri,
                             track_name)
        dst_track = Gio.File.new_for_uri(dst_uri)
        if dst_track.get_uri() in self.__on_mtp_files:
            self.__on_mtp_files.remove(dst_track.get_uri())
        if not dst_track.query_exists() or\
            self.__mtp_syncdb.get_mtime(
                dst_track.get_uri()) < mtime:
            if convertion_needed:
                convert_uri = "file:///tmp/%s" % track_name
                convert_file = Gio.File.new_for_uri(convert_uri)
                pipeline = self.__convert(src_track,
                                          convert_file)
                # Check if encoding is finished
                if pipeline is not None:
                    bus = pipeline.get_bus()
                    bus.add_signal_watch()
                    bus.connect("message::eos", self.__on_bus_eos)
                    self.__encoding = True
                    while self.__encoding and\
                            not self.__cancellable.is_cancelled():
                        sleep(1)
                    bus.disconnect_by_func(self.__on_bus_eos)
                    pipeline.set_state(Gst.State.PAUSED)
                    pipeline.set_state(Gst.State.READY)
                    pipeline.set_state(Gst.State.NULL)
                    self.__retry(
                        convert_file.move,
                        (dst_track, Gio.FileCopyFlags.OVERWRITE,
                         None, None))
                    # To be sure
                    try:
                        convert_file.delete(None)
                    except:
                        pass
            else:
                self.__retry(src_track.copy,
                             (dst_track, Gio.FileCopyFlags.OVERWRITE,
                              None, None))
            self.__mtp_syncdb.set_mtime(dst_track.get_uri(), mtime)
        self.__done += 1
        GLib.idle_add(self.emit, "sync-progress",
                      self.__done / self.__total)
        return (track_name, artists, album_name, is_compilation)

    def __sync_albums(self):
        """
            Sync albums to device
        """
        album_ids = App().albums.get_synced_ids()
        for album_id in album_ids:
            album = Album(album_id)
            for track_id in album.track_ids:
                if self.__cancellable.is_cancelled():
                    return
                self.__sync_track_id(Track(track_id))

    def __sync_playlists(self, playlist_ids):
        """
            Sync file from playlist to device
            @param playlist_ids as [int]
        """
        for playlist_id in playlist_ids:
            if self.__cancellable.is_cancelled():
                break
            m3u = None
            stream = None
            playlist = App().playlists.get_name(playlist_id)
            try:
                # Create playlist
                m3u = Gio.File.new_for_path(
                    "/tmp/lollypop_%s.m3u" % (playlist,))
                self.__retry(
                    m3u.replace_contents,
                    (b"#EXTM3U\n",
                     None,
                     False,
                     Gio.FileCreateFlags.REPLACE_DESTINATION,
                     None))
                stream = m3u.open_readwrite(None)
            except Exception as e:
                Logger.error("DeviceWidget::__sync_playlists(): %s" % e)
            if App().playlists.get_smart(playlist_id):
                request = App().playlists.get_smart_sql(playlist_id)
                track_ids = App().db.execute(request)
            else:
                track_ids = App().playlists.get_track_ids(playlist_id)
            # Start copying
            for track_id in track_ids:
                if self.__cancellable.is_cancelled():
                    break
                if track_id is None:
                    self.__done += 1
                    continue
                track = Track(track_id)
                (track_name, artists, album_name, is_compilation) =\
                    self.__sync_track_id(track)
                if stream is not None:
                    if is_compilation:
                        line = "%s/%s\n" %\
                            (album_name,
                             track_name)
                    else:
                        line = "%s_%s/%s\n" %\
                            (artists,
                             album_name,
                             track_name)
                    self.__retry(stream.get_output_stream().write,
                                 (line.encode(encoding="UTF-8"), None))
            if stream is not None:
                stream.close()
            if m3u is not None:
                playlist = escape(playlist)
                dst = Gio.File.new_for_uri(
                    self.__uri + "/" + playlist + ".m3u")
                self.__retry(m3u.move,
                             (dst, Gio.FileCopyFlags.OVERWRITE, None, None))

    def __remove_from_device(self, playlist_ids):
        """
            Delete files not available in playlist
            @param playlist_ids as [int]
        """
        # Delete unwanted files on mtp device
        for uri in self.__on_mtp_files:
            if self.__cancellable.is_cancelled():
                return
            Logger.debug("MtpSync::__remove_from_device(): deleting %s" %
                         uri)
            to_delete = Gio.File.new_for_uri(uri)
            self.__retry(to_delete.delete, (None,))
            self.__mtp_syncdb.delete_uri(uri)
            self.__done += 1
            GLib.idle_add(self.emit, "sync-progress",
                          self.__done / self.__total)

    def __convert(self, src, dst):
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
            pipeline_str = self.__ENCODE_START % src_path
            if self.__mtp_syncdb.normalize:
                pipeline_str += self.__NORMALIZE
            if self.__mtp_syncdb.encoder in ["convert_vorbis", "convert_aac"]:
                convert_bitrate = self.__convert_bitrate * 1000
            else:
                convert_bitrate = self.__convert_bitrate
            try:
                pipeline_str += self.__ENCODERS[self.__mtp_syncdb.encoder] %\
                    convert_bitrate
            except:
                pipeline_str += self.__ENCODERS[self.__mtp_syncdb.encoder]
            pipeline_str += self.__ENCODE_END % dst_path
            pipeline = Gst.parse_launch(pipeline_str)
            pipeline.set_state(Gst.State.PLAYING)
            return pipeline
        except Exception as e:
            Logger.error("MtpSync::__convert(): %s" % e)
            return None

    def __on_bus_eos(self, bus, message):
        """
            Stop encoding
            @param bus as Gst.Bus
            @param message as Gst.Message
        """
        self.__encoding = False
