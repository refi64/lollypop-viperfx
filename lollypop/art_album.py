# Copyright (c) 2014-2019 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import GLib, GdkPixbuf, Gio, Gst

from random import choice

from lollypop.tagreader import TagReader
from lollypop.define import App, ArtSize, ArtBehaviour
from lollypop.objects import Album
from lollypop.logger import Logger
from lollypop.utils import escape, is_readonly
from lollypop.helper_task import TaskHelper


class AlbumArt:
    """
         Manager album artwork
         Should be inherited by a BaseArt
    """

    _MIMES = ("jpeg", "jpg", "png", "gif")

    def __init__(self):
        """
            Init album art
        """
        self.__favorite = App().settings.get_value(
            "favorite-cover").get_string()
        if not self.__favorite:
            self.__favorite = App().settings.get_default_value(
                "favorite-cover").get_string()

    def get_album_cache_path(self, album, width, height):
        """
            get artwork cache path for album_id
            @param album as Album
            @param width as int
            @param height as int
            @return cover path as string or None if no cover
        """
        filename = ""
        try:
            filename = self.get_album_cache_name(album)
            cache_path_jpg = "%s/%s_%s_%s.jpg" % (self._CACHE_PATH,
                                                  filename,
                                                  width,
                                                  height)
            f = Gio.File.new_for_path(cache_path_jpg)
            if f.query_exists():
                return cache_path_jpg
            else:
                self.get_album_artwork(album, width, height, 1)
                if f.query_exists():
                    return cache_path_jpg
        except Exception as e:
            print("Art::get_album_cache_path(): %s" % e, ascii(filename))
            return None

    def get_album_artwork_uri(self, album):
        """
            Look for artwork in dir:
            - favorite from settings first
            - Artist_Album.jpg then
            - Any any supported image otherwise
            @param album as Album
            @return cover uri as string
        """
        if album.id is None:
            return None
        try:
            filename = self.get_album_cache_name(album) + ".jpg"
            self.__update_album_uri(album)
            if album.mtime == 0:
                store_path = self._WEB_PATH + "/" + filename
            else:
                store_path = self._STORE_PATH + "/" + filename
            uris = [
                # Used when album.uri is readonly or for Web
                GLib.filename_to_uri(store_path),
                # Default favorite artwork
                album.uri + "/" + self.__favorite,
                # Used when having muliple albums in same folder
                album.uri + "/" + filename
            ]
            for uri in uris:
                f = Gio.File.new_for_uri(uri)
                if f.query_exists():
                    return uri
        except Exception as e:
            print("AlbumArt::get_album_artwork_uri():", e)
        return None

    def get_first_album_artwork(self, album):
        """
            Get first locally available artwork for album
            @param album as Album
            @return path or None
        """
        # Folders with many albums, get_album_artwork_uri()
        if App().albums.get_uri_count(album.uri) > 1:
            return None
        f = Gio.File.new_for_uri(album.uri)
        infos = f.enumerate_children("standard::name",
                                     Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
                                     None)
        all_uris = []
        for info in infos:
            f = infos.get_child(info)
            all_uris.append(f.get_uri())
        for uri in filter(lambda p: p.lower().endswith(self._MIMES), all_uris):
            return uri
        return None

    def get_album_artworks(self, album):
        """
            Get locally available artworks for album
            @param album as Album
            @return [paths]
        """
        uris = []
        try:
            f = Gio.File.new_for_uri(album.uri)
            infos = f.enumerate_children(
                "standard::name",
                Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
                None)
            all_uris = []
            for info in infos:
                f = infos.get_child(info)
                all_uris.append(f.get_uri())
            for uri in filter(lambda p: p.lower().endswith(self._MIMES),
                              all_uris):
                uris.append(uri)
        except Exception as e:
            print("AlbumArt::get_album_artworks()", e)
        return uris

    def get_album_artwork(self, album, width, height, scale_factor,
                          behaviour=ArtBehaviour.CACHE |
                          ArtBehaviour.CROP_SQUARE):
        """
            Return a cairo surface for album_id, covers are cached as jpg.
            @param album as Album
            @param width as int
            @param height as int
            @param scale_factor factor as int
            @param behaviour as ArtBehaviour
            @return cairo surface
            @thread safe
        """
        filename = self.get_album_cache_name(album)
        # Blur when reading from tags can be slow, so prefer cached version
        # Blur allows us to ignore width/height until we want CROP/CACHE
        optimized_blur = behaviour & (ArtBehaviour.BLUR |
                                      ArtBehaviour.BLUR_HARD) and\
            not behaviour & (ArtBehaviour.CACHE |
                             ArtBehaviour.CROP |
                             ArtBehaviour.CROP_SQUARE)
        if optimized_blur:
            w = ArtSize.BIG * scale_factor
            h = ArtSize.BIG * scale_factor
        else:
            w = width * scale_factor
            h = height * scale_factor
        cache_path_jpg = "%s/%s_%s_%s.jpg" % (self._CACHE_PATH, filename, w, h)
        pixbuf = None
        try:
            # Look in cache
            f = Gio.File.new_for_path(cache_path_jpg)
            if not behaviour & ArtBehaviour.NO_CACHE and f.query_exists():
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(cache_path_jpg)
                if optimized_blur:
                    pixbuf = self.load_behaviour(pixbuf, None,
                                                 width, height,
                                                 scale_factor, behaviour)
                return pixbuf
            else:
                # Use favorite folder artwork
                if pixbuf is None:
                    uri = self.get_album_artwork_uri(album)
                    data = None
                    if uri is not None:
                        f = Gio.File.new_for_uri(uri)
                        (status, data, tag) = f.load_contents(None)
                        bytes = GLib.Bytes(data)
                        stream = Gio.MemoryInputStream.new_from_bytes(bytes)
                        pixbuf = GdkPixbuf.Pixbuf.new_from_stream(
                            stream, None)
                        stream.close()
                # Use tags artwork
                if pixbuf is None and album.tracks and album.uri != "":
                    try:
                        if behaviour & (ArtBehaviour.BLUR |
                                        ArtBehaviour.BLUR_HARD):
                            track = album.tracks[0]
                        else:
                            track = choice(album.tracks)
                        pixbuf = self.pixbuf_from_tags(track.uri,
                                                       width * scale_factor,
                                                       height * scale_factor)
                    except Exception as e:
                        print("AlbumArt::get_album_artwork()", e)

                # Use folder artwork
                if pixbuf is None and album.uri != "":
                    uri = self.get_first_album_artwork(album)
                    # Look in album folder
                    if uri is not None:
                        f = Gio.File.new_for_uri(uri)
                        (status, data, tag) = f.load_contents(None)
                        bytes = GLib.Bytes(data)
                        stream = Gio.MemoryInputStream.new_from_bytes(bytes)
                        pixbuf = GdkPixbuf.Pixbuf.new_from_stream(
                            stream, None)
                        stream.close()
                if pixbuf is None:
                    self.cache_album_artwork(album.id)
                    return None
                pixbuf = self.load_behaviour(pixbuf, cache_path_jpg,
                                             width, height,
                                             scale_factor, behaviour)
                return pixbuf
        except Exception as e:
            Logger.error("AlbumArt::get_album_artwork(): %s" % e)
            return None

    def copy_from_web_to_store(self, album_id):
        """
            Copy artwork from web path to store path
            @param album_id as int
        """
        try:
            album = Album(album_id)
            filename = self.get_album_cache_name(album) + ".jpg"
            web_path = self._WEB_PATH + "/" + filename
            store_path = self._STORE_PATH + "/" + filename
            web_file = Gio.File.new_for_path(web_path)
            store_file = Gio.File.new_for_path(store_path)
            web_file.copy(store_file, Gio.FileCopyFlags.OVERWRITE,
                          None, None, None)
        except Exception as e:
            Logger.error("AlbumArt::copy_from_web_to_store(): %s", e)

    def save_album_artwork(self, data, album):
        """
            Save data for album id
            @param data as bytes
            @param album as Album
        """
        try:
            save_to_tags = App().settings.get_value("save-to-tags")
            uri_count = App().albums.get_uri_count(album.uri)
            filename = self.get_album_cache_name(album) + ".jpg"

            if album.mtime == 0:
                store_path = self._WEB_PATH + "/" + filename
                save_to_tags = False
            else:
                store_path = self._STORE_PATH + "/" + filename

            if album.uri == "" or is_readonly(album.uri):
                art_uri = GLib.filename_to_uri(store_path)
                save_to_tags = False
            # Many albums with same path, suffix with artist_album name
            elif uri_count > 1:
                art_uri = album.uri + "/" + filename
                favorite_uri = album.uri + "/" + self.__favorite
                favorite = Gio.File.new_for_uri(favorite_uri)
                if favorite.query_exists():
                    favorite.trash()
            else:
                art_uri = album.uri + "/" + self.__favorite

            # Create an empty file
            if data is None:
                f = Gio.File.new_for_uri(art_uri)
                fstream = f.replace(None, False,
                                    Gio.FileCreateFlags.REPLACE_DESTINATION,
                                    None)
                fstream.close()
            else:
                # Save cover to tags
                if save_to_tags:
                    helper = TaskHelper()
                    helper.run(self.__save_artwork_to_tags, data, album)
                # Save cover to file
                # We need to write it on save_to_tags
                dst = Gio.File.new_for_uri(art_uri)
                if not save_to_tags or dst.query_exists():
                    bytes = GLib.Bytes(data)
                    stream = Gio.MemoryInputStream.new_from_bytes(bytes)
                    pixbuf = GdkPixbuf.Pixbuf.new_from_stream(stream, None)
                    stream.close()
                    pixbuf.savev(store_path, "jpeg", ["quality"],
                                 [str(App().settings.get_value(
                                     "cover-quality").get_int32())])
                    dst = Gio.File.new_for_uri(art_uri)
                    src = Gio.File.new_for_path(store_path)
                    src.move(dst, Gio.FileCopyFlags.OVERWRITE, None, None)
                    self.clean_album_cache(album)
                    GLib.idle_add(self.album_artwork_update, album.id)
        except Exception as e:
            Logger.error("AlbumArt::save_album_artwork(): %s" % e)

    def album_artwork_update(self, album_id):
        """
            Announce album cover update
            @param album_id as int
        """
        self.emit("album-artwork-changed", album_id)

    def remove_album_artwork(self, album):
        """
            Remove album artwork
            @param album as Album
        """
        for uri in self.get_album_artworks(album):
            f = Gio.File.new_for_uri(uri)
            try:
                f.trash()
            except Exception as e:
                Logger.error("AlbumArt::remove_album_artwork(): %s" % e)
                try:
                    f.delete(None)
                except Exception as e:
                    Logger.error("AlbumArt::remove_album_artwork(): %s" % e)
        self.__write_image_to_tags("", album.id)

    def clean_album_cache(self, album):
        """
            Remove cover from cache for album id
            @param album as Album
        """
        try:
            from pathlib import Path
            name = self.get_album_cache_name(album)
            for p in Path(self._CACHE_PATH).glob("%s*.jpg" % name):
                p.unlink()
        except Exception as e:
            Logger.error("AlbumArt::clean_album_cache(): %s" % e)

    def pixbuf_from_tags(self, uri, width, height):
        """
            Return cover from tags
            @param uri as str
            @param width as int
            @param height as int
        """
        pixbuf = None
        if uri.startswith("web:"):
            return
        try:
            tag_reader = TagReader()
            info = tag_reader.get_info(uri)
            exist = False
            if info is not None:
                (exist, sample) = info.get_tags().get_sample_index("image", 0)
                if not exist:
                    (exist, sample) = info.get_tags().get_sample_index(
                        "preview-image", 0)
            if exist:
                (exist, mapflags) = sample.get_buffer().map(Gst.MapFlags.READ)
            if exist:
                bytes = GLib.Bytes(mapflags.data)
                stream = Gio.MemoryInputStream.new_from_bytes(bytes)
                pixbuf = GdkPixbuf.Pixbuf.new_from_stream(stream, None)
                stream.close()
        except Exception as e:
            Logger.error("AlbumArt::pixbuf_from_tags(): %s" % e)
        return pixbuf

    def get_album_cache_name(self, album):
        """
            Get a uniq string for album
            @param album as Album
        """
        name = "%s_%s_%s" % (" ".join(album.artists)[:100],
                             album.name[:100],
                             album.year)
        return "@ALBUM@" + escape(name)

#######################
# PRIVATE             #
#######################
    def __update_album_uri(self, album):
        """
            Check if album uri exists, update if not
            @param album as Album
        """
        if not album.uri:
            return
        d = Gio.File.new_for_uri(album.uri)
        if not d.query_exists():
            if album.tracks:
                track_uri = album.tracks[0].uri
                f = Gio.File.new_for_uri(track_uri)
                p = f.get_parent()
                parent_uri = "" if p is None else p.get_uri()
                album.set_uri(parent_uri)

    def __save_artwork_to_tags(self, data, album):
        """
            Save artwork to tags
            @param data as bytes
            @param album as Album
        """
        # https://bugzilla.gnome.org/show_bug.cgi?id=747431
        bytes = GLib.Bytes(data)
        stream = Gio.MemoryInputStream.new_from_bytes(bytes)
        pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(stream,
                                                           ArtSize.MONSTER,
                                                           ArtSize.MONSTER,
                                                           True,
                                                           None)
        stream.close()
        pixbuf.savev("%s/lollypop_cover_tags.jpg" % self._CACHE_PATH,
                     "jpeg", ["quality"], [str(App().settings.get_value(
                                           "cover-quality").get_int32())])
        self.__write_image_to_tags("%s/lollypop_cover_tags.jpg" %
                                   self._CACHE_PATH, album.id)

    def __write_image_to_tags(self, path, album_id):
        """
            Save album at path to album tags
            @param path as str
            @param album_id as int
        """
        if self.kid3_available:
            files = []
            for uri in App().albums.get_track_uris(album_id):
                try:
                    files.append(GLib.filename_from_uri(uri)[0])
                except:
                    pass
            cover = "%s/lollypop_cover_tags.jpg" % self._CACHE_PATH
            if GLib.find_program_in_path("flatpak-spawn") is not None:
                argv = ["flatpak-spawn", "--host", "kid3-cli",
                        "-c", "set picture:'%s' ''" % cover]
            else:
                argv = ["kid3-cli", "-c", "set picture:'%s' ''" % cover]
            argv += files
            try:
                (pid, stdin, stdout, stderr) = GLib.spawn_async(
                    argv, flags=GLib.SpawnFlags.SEARCH_PATH |
                    GLib.SpawnFlags.STDOUT_TO_DEV_NULL,
                    standard_input=False,
                    standard_output=False,
                    standard_error=False
                )
            except Exception as e:
                Logger.error("AlbumArt::__on_kid3_result(): %s" % e)
            self.clean_album_cache(Album(album_id))
            # FIXME Should be better to send all covers at once and listen
            # to as signal but it works like this
            GLib.timeout_add(2000, self.album_artwork_update, album_id)
