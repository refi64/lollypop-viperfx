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

from gi.repository import GLib, Gdk, GdkPixbuf, Gio, Gst

import re
import os

from lollypop.art_base import BaseArt
from lollypop.art_downloader import ArtDownloader
from lollypop.tagreader import TagReader
from lollypop.define import Lp
from lollypop.objects import Album


class AlbumArt(BaseArt, ArtDownloader, TagReader):
    """
         Manager album artwork
    """

    _MIMES = ("jpeg", "jpg", "png", "gif")

    def __init__(self):
        """
            Init radio art
        """
        BaseArt.__init__(self)
        ArtDownloader.__init__(self)
        TagReader.__init__(self)
        self._favorite = Lp.settings.get_value('favorite-cover').get_string()

    def get_album_cache_path(self, album, size):
        """
            get cover cache path for album_id
            @param album as Album
            @param size as int
            @return cover path as string or None if no cover
        """
        filename = ''
        try:
            filename = self._get_album_cache_name(album)
            cache_path_jpg = "%s/%s_%s.jpg" % (self._CACHE_PATH,
                                               filename,
                                               size)
            if os.path.exists(cache_path_jpg):
                return cache_path_jpg
            else:
                self.get_album(album, size)
                if os.path.exists(cache_path_jpg):
                    return cache_path_jpg
                else:
                    return None
        except Exception as e:
            print("Art::get_album_cache_path(): %s" % e, ascii(filename))
            return None

    def get_album_art_path(self, album, sql=None):
        """
            Look for covers in dir:
            - favorite from settings first
            - Artist_Album.jpg then
            - Any any supported image otherwise
            @param album as Album
            @return cover file path as string
        """
        if album is None:
            return None
        try:
            paths = [
                os.path.join(album.path, self._favorite),
                # Used when having muliple albums in same folder
                os.path.join(album.path, "{}_{}.jpg".format(album.artist_name,
                                                            album.name))
            ]
            for path in paths:
                if os.path.exists(path):
                    return path
            return self.get_locally_available_cover(album)
        except:
            return None

    def get_locally_available_cover(self, album):
        """
            Get first locally available cover for album
            @param album as Album
            @return path or None
        """
        all_paths = [os.path.join(album.path, f) for f in os.listdir(
                                                                album.path)]
        for path in filter(lambda p: p.lower().endswith(self._MIMES),
                           all_paths):
            return path

    def get_locally_available_covers(self, album):
        """
            Get locally available covers for album
            @param album as Album
            @return [paths]
        """
        all_paths = [os.path.join(album.path, f) for f in os.listdir(
                                                                album.path)]
        paths = []
        for path in filter(lambda p: p.lower().endswith(self._MIMES),
                           all_paths):
            if not path.endswith(self._favorite):
                paths.append(path)
        return paths

    def get_cover_for_uri(self, uri, size):
        """
            Return a cairo surface with borders for uri
            No cache usage
            @param uri as string
            @param size as int
            @return cairo surface
        """
        pixbuf = self.pixbuf_from_tags(GLib.filename_from_uri(uri)[0], size)
        if pixbuf is not None:
            surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf, 0, None)
            del pixbuf
            return surface
        else:
            return self._get_default_icon(size, 'folder-music-symbolic')

    def get_album(self, album, size):
        """
            Return a cairo surface for album_id, covers are cached as jpg.
            @param album as Album
            @param pixbuf size as int
            @return cairo surface
        """
        filename = self._get_album_cache_name(album)
        cache_path_jpg = "%s/%s_%s.jpg" % (self._CACHE_PATH, filename, size)
        pixbuf = None

        try:
            # Look in cache
            if os.path.exists(cache_path_jpg):
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(cache_path_jpg,
                                                                size,
                                                                size)
            else:
                path = self.get_album_art_path(album)
                # Look in album folder
                if path is not None:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path,
                                                                     size,
                                                                     size,
                                                                     False)
                # Try to get from tags
                else:
                    try:
                        if album.tracks:
                            pixbuf = self.pixbuf_from_tags(
                                        album.tracks[0].path, size)
                    except Exception as e:
                        pass
                # No cover, use default one
                if pixbuf is None:
                    self.download_album_art(album.id)
                    return self._get_default_icon(size,
                                                  'folder-music-symbolic')
                else:
                    # Gdk < 3.15 was missing save method
                    # > 3.15 is missing savev method
                    try:
                        pixbuf.save(cache_path_jpg, "jpeg",
                                    ["quality"], ["90"])
                    except:
                        pixbuf.savev(cache_path_jpg, "jpeg",
                                     ["quality"], ["90"])
            surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf, 0, None)
            del pixbuf
            return surface

        except Exception as e:
            print(e)
            return self._get_default_icon(size, 'folder-music-symbolic')

    def save_album_art(self, pixbuf, album_id, sql=None):
        """
            Save pixbuf for album id
            @param pixbuf as Gdk.Pixbuf
            @param album id as int
            @param sql as sqlite cursor
        """
        try:
            artpath = self.get_album_art_filepath(album_id, sql)
            # Gdk < 3.15 was missing save method
            try:
                pixbuf.save(artpath, "jpeg", ["quality"], ["90"])
            # > 3.15 is missing savev method :(
            except:
                pixbuf.savev(artpath, "jpeg", ["quality"], ["90"])
        except Exception as e:
            print("Art::save_album_art(): %s" % e)

    def get_album_art_filepath(self, album_id, sql=None):
        """
            Get album art filepath
            @param album_id as int
            @param sql as sqlite cursor
            @thread safe
        """
        album = Album(album_id)
        path_count = Lp.albums.get_path_count(album.path, sql)
        # Many albums with same path, suffix with artist_album name
        if path_count > 1:
            artpath = os.path.join(album.path, "{}_{}.jpg".format(
                                   album.artist_name, album.name))
            if os.path.exists(os.path.join(album.path, self._favorite)):
                os.remove(os.path.join(album.path, self._favorite))
        else:
            artpath = os.path.join(album.path, self._favorite)
        return artpath

    def announce_cover_update(self, album_id):
        """
            Announce album cover update
            @param album id as int
        """
        self.emit('cover-changed', album_id)

    def clean_album_cache(self, album, sql=None):
        """
            Remove cover from cache for album id
            @param album as Album
            @param sql as sqlite cursor
        """
        filename = self._get_album_cache_name(album, sql)
        try:
            for f in os.listdir(self._CACHE_PATH):
                if re.search('%s_.*\.jpg' % re.escape(filename), f):
                    os.remove(os.path.join(self._CACHE_PATH, f))
        except Exception as e:
            print("Art::clean_album_cache(): ", e, filename)

    def pixbuf_from_tags(self, filepath, size):
        """
            Return cover from tags
            @param filepath as str
            @param size as int
        """
        pixbuf = None
        infos = self.get_infos(filepath)
        exist = False
        if infos is not None:
            (exist, sample) = infos.get_tags().get_sample_index('image', 0)
        if exist:
            (exist, mapflags) = sample.get_buffer().map(Gst.MapFlags.READ)
        if exist:
            stream = Gio.MemoryInputStream.new_from_data(mapflags.data,
                                                         None)
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(stream,
                                                                   size,
                                                                   size,
                                                                   False,
                                                                   None)
            except:
                pass
        return pixbuf

#######################
# PRIVATE             #
#######################
    def _get_album_cache_name(self, album, sql=None):
        """
            Get a uniq string for album
            @param album as Album
            @param sql as sqlite cursor
        """
        path = album.name + "_" + album.artist_name
        return path[0:240].replace("/", "_")
