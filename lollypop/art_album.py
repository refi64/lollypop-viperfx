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

from gi.repository import GLib, Gdk, GdkPixbuf, Gio, Gst

from threading import Thread
import re

from lollypop.art_base import BaseArt
from lollypop.tagreader import TagReader
from lollypop.define import Lp, ArtSize
from lollypop.objects import Album
from lollypop.utils import escape, is_readonly
from lollypop.lio import Lio
from lollypop.helper_dbus import DBusHelper


class AlbumArt(BaseArt, TagReader):
    """
         Manager album artwork
    """

    _MIMES = ("jpeg", "jpg", "png", "gif")

    def __init__(self):
        """
            Init radio art
        """
        BaseArt.__init__(self)
        TagReader.__init__(self)
        self.__favorite = Lp().settings.get_value(
                                                "favorite-cover").get_string()

    def get_album_cache_path(self, album, size):
        """
            get artwork cache path for album_id
            @param album as Album
            @param size as int
            @return cover path as string or None if no cover
        """
        filename = ""
        try:
            filename = self.get_album_cache_name(album)
            cache_path_jpg = "%s/%s_%s.jpg" % (self._CACHE_PATH,
                                               filename,
                                               size)
            f = Lio.File.new_for_path(cache_path_jpg)
            if f.query_exists():
                return cache_path_jpg
            else:
                self.get_album_artwork(album, size, 1)
                if f.query_exists():
                    return cache_path_jpg
                else:
                    return self._get_default_icon_path(
                                           size,
                                           "folder-music-symbolic")
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
            uris = [
                # Used when album.uri is readonly
                GLib.filename_to_uri(self._STORE_PATH + "/" + filename),
                # Default favorite artwork
                album.uri + "/" + self.__favorite,
                # Used when having muliple albums in same folder
                album.uri + "/" + filename
            ]
            for uri in uris:
                f = Lio.File.new_for_uri(uri)
                if f.query_exists():
                    return uri
        except:
            pass
        return None

    def get_first_album_artwork(self, album):
        """
            Get first locally available artwork for album
            @param album as Album
            @return path or None
        """
        # Folders with many albums, get_album_artwork_uri()
        if Lp().albums.get_uri_count(album.uri) > 1:
            return None
        f = Lio.File.new_for_uri(album.uri)
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
        if album.is_web:
            return []
        try:
            f = Lio.File.new_for_uri(album.uri)
            infos = f.enumerate_children(
                                     "standard::name",
                                     Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
                                     None)
            all_uris = []
            for info in infos:
                f = infos.get_child(info)
                all_uris.append(f.get_uri())
            uris = []
            for uri in filter(lambda p: p.lower().endswith(self._MIMES),
                              all_uris):
                uris.append(uri)
        except Exception as e:
            print("AlbumArt::get_album_artworks()", e)
        return uris

    def get_album_artwork(self, album, size, scale):
        """
            Return a cairo surface for album_id, covers are cached as jpg.
            @param album as Album
            @param pixbuf size as int
            @param scale factor as int
            @return cairo surface
        """
        size *= scale
        filename = self.get_album_cache_name(album)
        cache_path_jpg = "%s/%s_%s.jpg" % (self._CACHE_PATH, filename, size)
        pixbuf = None

        try:
            # Look in cache
            f = Lio.File.new_for_path(cache_path_jpg)
            if f.query_exists():
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(cache_path_jpg,
                                                                size,
                                                                size)
            else:
                # Use favorite folder artwork
                if pixbuf is None:
                    uri = self.get_album_artwork_uri(album)
                    data = None
                    if uri is not None:
                        f = Lio.File.new_for_uri(uri)
                        (status, data, tag) = f.load_contents(None)
                        ratio = self._respect_ratio(uri)
                        bytes = GLib.Bytes(data)
                        stream = Gio.MemoryInputStream.new_from_bytes(bytes)
                        bytes.unref()
                        del data
                        pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(
                                                                       stream,
                                                                       size,
                                                                       size,
                                                                       ratio,
                                                                       None)
                        stream.close()
                # Use tags artwork
                if pixbuf is None and album.tracks:
                    try:
                        pixbuf = self.pixbuf_from_tags(
                                    album.tracks[0].uri, size)
                    except Exception as e:
                        print("AlbumArt::get_album_artwork()", e)

                # Use folder artwork
                if pixbuf is None and album.uri != "":
                    uri = self.get_first_album_artwork(album)
                    # Look in album folder
                    if uri is not None:
                        f = Lio.File.new_for_uri(uri)
                        (status, data, tag) = f.load_contents(None)
                        ratio = self._respect_ratio(uri)
                        bytes = GLib.Bytes(data)
                        stream = Gio.MemoryInputStream.new_from_bytes(bytes)
                        bytes.unref()
                        del data
                        pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(
                                                                       stream,
                                                                       size,
                                                                       size,
                                                                       ratio,
                                                                       None)
                        stream.close()
                # Use default artwork
                if pixbuf is None:
                    self.cache_album_art(album.id)
                    return self.get_default_icon("folder-music-symbolic",
                                                 size,
                                                 scale)
                else:
                    pixbuf.savev(cache_path_jpg, "jpeg", ["quality"],
                                 [str(Lp().settings.get_value(
                                                "cover-quality").get_int32())])
            surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf, scale, None)
            del pixbuf
            return surface

        except Exception as e:
            print("AlbumArt::get_album_artwork()", e)
            return self.get_default_icon("folder-music-symbolic", size, scale)

    def get_album_artwork2(self, uri, size, scale):
        """
            Return a cairo surface with borders for uri
            No cache usage
            @param uri as string
            @param size as int
            @param scale as int
            @return cairo surface
        """
        size *= scale
        pixbuf = self.pixbuf_from_tags(uri, size)
        if pixbuf is not None:
            surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf, scale, None)
            del pixbuf
            return surface
        else:
            return self.get_default_icon("folder-music-symbolic", size, scale)

    def save_album_artwork(self, data, album_id):
        """
            Save data for album id
            @param data as bytes
            @param album id as int
        """
        try:
            album = Album(album_id)
            arturi = None
            save_to_tags = Lp().settings.get_value("save-to-tags") and\
                not album.is_web
            uri_count = Lp().albums.get_uri_count(album.uri)
            filename = self.get_album_cache_name(album) + ".jpg"
            if save_to_tags:
                t = Thread(target=self.__save_artwork_tags,
                           args=(data, album))
                t.daemon = True
                t.start()

            store_path = self._STORE_PATH + "/" + filename
            if album.uri == "" or is_readonly(album.uri):
                arturi = GLib.filename_to_uri(store_path)
            # Many albums with same path, suffix with artist_album name
            elif uri_count > 1:
                arturi = album.uri + "/" + filename
                favorite_uri = album.uri + "/" + self.__favorite
                favorite = Lio.File.new_for_uri(favorite_uri)
                if favorite.query_exists():
                    favorite.trash()
            else:
                arturi = album.uri + "/" + self.__favorite
            # Save cover to uri
            if not save_to_tags:
                bytes = GLib.Bytes(data)
                stream = Gio.MemoryInputStream.new_from_bytes(data)
                bytes.unref()
                pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(
                                                               stream,
                                                               ArtSize.MONSTER,
                                                               ArtSize.MONSTER,
                                                               True,
                                                               None)
                stream.close()
                pixbuf.savev(store_path, "jpeg", ["quality"],
                             [str(Lp().settings.get_value(
                                                "cover-quality").get_int32())])
                dst = Lio.File.new_for_uri(arturi)
                src = Lio.File.new_for_path(store_path)
                src.move(dst, Gio.FileCopyFlags.OVERWRITE, None, None)
                del pixbuf
                self.clean_album_cache(album)
                GLib.idle_add(self.album_artwork_update, album.id)
            else:
                dst = Lio.File.new_for_uri(arturi)
                if dst.query_exists():
                    dst.trash()
        except Exception as e:
            print("Art::save_album_artwork(): %s" % e)

    def album_artwork_update(self, album_id):
        """
            Announce album cover update
            @param album id as int
        """
        self.emit("album-artwork-changed", album_id)

    def remove_album_artwork(self, album):
        """
            Remove album artwork
            @param album as Album
        """
        for uri in self.get_album_artworks(album):
            f = Lio.File.new_for_uri(uri)
            try:
                f.trash()
            except:
                f.delete(None)
        dbus_helper = DBusHelper()
        dbus_helper.call("CanSetCover", None,
                         self.__on_remove_album_artwork, album.id)

    def clean_album_cache(self, album):
        """
            Remove cover from cache for album id
            @param album as Album
        """
        cache_name = self.get_album_cache_name(album)
        try:
            d = Lio.File.new_for_path(self._CACHE_PATH)
            infos = d.enumerate_children(
                "standard::name",
                Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
                None)
            for info in infos:
                f = infos.get_child(info)
                f = infos.get_child(info)
                basename = f.get_basename()
                if re.search("%s_.*\.jpg" % re.escape(cache_name), basename):
                    f.delete()
        except Exception as e:
            print("Art::clean_album_cache(): ", e, cache_name)

    def pixbuf_from_tags(self, uri, size):
        """
            Return cover from tags
            @param uri as str
            @param size as int
        """
        pixbuf = None
        if uri.startswith("http:") or uri.startswith("https:"):
            return
        try:
            info = self.get_info(uri)
            exist = False
            if info is not None:
                (exist, sample) = info.get_tags().get_sample_index("image", 0)
                # Some file store it in a preview-image tag
                if not exist:
                    (exist, sample) = info.get_tags().get_sample_index(
                                                            "preview-image", 0)
            if exist:
                (exist, mapflags) = sample.get_buffer().map(Gst.MapFlags.READ)
            if exist:
                bytes = GLib.Bytes(mapflags.data)
                stream = Gio.MemoryInputStream.new_from_bytes(bytes)
                bytes.unref()
                pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(stream,
                                                                   size,
                                                                   size,
                                                                   False,
                                                                   None)
                stream.close()
        except Exception as e:
            print("AlbumArt::pixbuf_from_tags():", e)
        return pixbuf

    def get_album_cache_name(self, album):
        """
            Get a uniq string for album
            @param album as Album
        """
        name = "_".join(album.artists)[:100] +\
            "_" + album.name[:100] + "_" + album.year
        return escape(name)

#######################
# PRIVATE             #
#######################
    def __save_artwork_tags(self, data, album):
        """
            Save artwork in tags
            @param data as bytes
            @param album as Album
        """
        if album.is_web:
            return
        # https://bugzilla.gnome.org/show_bug.cgi?id=747431
        bytes = GLib.Bytes(data)
        stream = Gio.MemoryInputStream.new_from_bytes(data)
        bytes.unref()
        pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(stream,
                                                           ArtSize.MONSTER,
                                                           ArtSize.MONSTER,
                                                           True,
                                                           None)
        stream.close()
        pixbuf.savev("%s/lollypop_cover_tags.jpg" % self._CACHE_PATH,
                     "jpeg", ["quality"], [str(Lp().settings.get_value(
                                           "cover-quality").get_int32())])
        del pixbuf
        f = Lio.File.new_for_path("%s/lollypop_cover_tags.jpg" %
                                  self._CACHE_PATH)
        if f.query_exists():
            dbus_helper = DBusHelper()
            dbus_helper.call("CanSetCover", None,
                             self.__on_save_artwork_tags, album.id)

    def __on_save_artwork_tags(self, source, result, album_id):
        """
            Save image to tags
            @param source as GObject.Object
            @param result as Gio.AsyncResult
            @param album_id as int
        """
        try:
            can_set_cover = source.call_finish(result)
        except:
            can_set_cover = False
        if can_set_cover:
            dbus_helper = DBusHelper()
            for uri in Lp().albums.get_track_uris(album_id, [], []):
                path = GLib.filename_from_uri(uri)[0]
                dbus_helper.call("SetCover",
                                 GLib.Variant(
                                     "(ss)",
                                     (path,
                                      "%s/lollypop_cover_tags.jpg" %
                                      self._CACHE_PATH)), None, None)
            self.clean_album_cache(Album(album_id))
            # FIXME Should be better to send all covers at once and listen
            # to as signal but it works like this
            GLib.timeout_add(2000, self.album_artwork_update, album_id)
        else:
            # Lollypop-portal or kid3-cli removed?
            Lp().settings.set_value("save-to-tags", GLib.Variant("b", False))

    def __on_remove_album_artwork(self, source, result, album_id):
        """
            Remove album image from tags
            @param source as GObject.Object
            @param result as Gio.AsyncResult
            @param album_id
        """
        try:
            can_set_cover = source.call_finish(result)
        except:
            can_set_cover = False
        if can_set_cover:
            dbus_helper = DBusHelper()
            for uri in Lp().albums.get_track_uris(album_id, [], []):
                try:
                    path = GLib.filename_from_uri(uri)[0]
                    dbus_helper.call("SetCover",
                                     GLib.Variant("(ss)", (path, "")),
                                     None, None)
                except Exception as e:
                    print("AlbumArt::__on_remove_album_artwork():", e)
        else:
            # Lollypop-portal or kid3-cli removed?
            Lp().settings.set_value("save-to-tags", GLib.Variant("b", False))
