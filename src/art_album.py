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

from gi.repository import GLib, GdkPixbuf, Gio, Gst

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

    def get_album_artwork_path(self, album, size):
        """
            Get album artwork path
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
            self._cache_album(album, size)
            if os.path.exists(cache_path_jpg):
                return cache_path_jpg
            else:
                return self._cache_default_icon(size, 'folder-music-symbolic')
        except Exception as e:
            print("Art::get_album_artwork_path(): %s" % e, ascii(filename))
            return None

    def get_album_artwork_path2(self, uri, size):
        """
            Get album artwork path for uri
            @param uri as string
            @param size as int
            @return path as str
        """
        path = GLib.filename_from_uri(uri).replace('/', '_')
        cache_path_jpg = "%s/%s_%s.jpg" % (self._CACHE_PATH, path, size)
        if os.path.exists(cache_path_jpg):
            return cache_path_jpg
        else:
            pixbuf = self.pixbuf_from_tags(GLib.filename_from_uri(uri)[0],
                                           size)
            if pixbuf is not None:
                pixbuf.savev(cache_path_jpg, "jpeg", ["quality"], ["90"])
                return cache_path_jpg
        return self._cache_default_icon(size, 'folder-music-symbolic')

    def get_album_favorite_artwork_path(self, album, sql=None):
        """
            Look for artworks in album dir:
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
            return self.get_album_first_artwork_path(album)
        except:
            return None

    def get_album_first_artwork_path(self, album):
        """
            Get first locally available artwork for album
            @param album as Album
            @return path or None
        """
        all_paths = [os.path.join(album.path, f) for f in os.listdir(
                                                                album.path)]
        for path in filter(lambda p: p.lower().endswith(self._MIMES),
                           all_paths):
            return path

    def get_album_all_artwork_paths(self, album):
        """
            Get locally available artworks for album
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

    def save_album_artwork(self, pixbuf, album_id, sql=None):
        """
            Save pixbuf for album id
            @param pixbuf as Gdk.Pixbuf
            @param album id as int
            @param sql as sqlite cursor
        """
        try:
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
            pixbuf.savev(artpath, "jpeg", ["quality"], ["90"])
        except Exception as e:
            print("Art::save_album_artwork(): %s" % e)

    def album_artwork_update(self, album_id):
        """
            Announce album artwork update
            @param album id as int
        """
        self.emit('album-artwork-changed', album_id)

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
    def _cache_album(self, album, size):
        """
            Create cache for album at size
            @param album as Album
            @param pixbuf size as int
            @return cairo surface
        """
        filename = self._get_album_cache_name(album)
        cache_path_jpg = "%s/%s_%s.jpg" % (self._CACHE_PATH, filename, size)
        pixbuf = None

        try:
            if not os.path.exists(cache_path_jpg):
                path = self.get_album_favorite_artwork_path(album)
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
                else:
                    pixbuf.savev(cache_path_jpg, "jpeg", ["quality"], ["90"])
        except Exception as e:
            print("AlbumArt::_cache(): ", e)

    def _get_album_cache_name(self, album, sql=None):
        """
            Get a uniq string for album
            @param album as Album
            @param sql as sqlite cursor
        """
        path = album.name + "_" + album.artist_name
        return path[0:240].replace("/", "_")
