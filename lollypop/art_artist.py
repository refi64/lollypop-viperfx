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

from gi.repository import GLib, GdkPixbuf, Gio

from lollypop.define import App, ArtHelperEffect
from lollypop.logger import Logger
from lollypop.utils import escape


class ArtistArt:
    """
         Manage artist artwork
         Should be inherited by a BaseArt
    """

    _INFO_PATH = GLib.get_user_data_dir() + "/lollypop/info"

    def __init__(self):
        """
            Init album art
        """
        try:
            d = Gio.File.new_for_path(self._INFO_PATH)
            if not d.query_exists():
                d.make_directory_with_parents()
        except:
            Logger.info("Can't create %s" % self._INFO_PATH)

    def artist_artwork_exists(self, artist):
        """
            True if artist artwork exists
            @param artist as str
            @return (bool, path)
        """
        escaped_artist = escape(artist)
        # Search in store
        paths = ["%s/%s.jpg" % (
                 self._INFO_PATH,
                 escaped_artist),
                 "%s/web_%s.jpg" % (
                 self._INFO_PATH,
                 escaped_artist)]
        for path in paths:
            if GLib.file_test(path, GLib.FileTest.EXISTS):
                return (True, path)
        return (False, None)

    def add_artist_artwork(self, artist, data, is_web=False):
        """
            Add artist artwork to store
            @param artist as str
            @param data as bytes
            @param is_web as bool
        """
        self.uncache_artist_artwork(artist)
        if is_web:
            filepath = "%s/web_%s.jpg" % (self._INFO_PATH,
                                          escape(artist))
        else:
            filepath = "%s/%s.jpg" % (self._INFO_PATH,
                                      escape(artist))
        if data is None:
            f = Gio.File.new_for_path(filepath)
            fstream = f.replace(None, False,
                                Gio.FileCreateFlags.REPLACE_DESTINATION, None)
            fstream.close()
        else:
            bytes = GLib.Bytes(data)
            stream = Gio.MemoryInputStream.new_from_bytes(bytes)
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream(stream, None)
            stream.close()
            pixbuf.savev(filepath, "jpeg", ["quality"], ["100"])

    def get_artist_artwork(self, artist, width, height, scale,
                           effect=ArtHelperEffect.SAVE):
        """
            Return a cairo surface for album_id, covers are cached as jpg.
            @param artist as str
            @param width as int
            @param height as int
            @param scale factor as int
            @param effect as ArtHelperEffect
            @return cairo surface
            @thread safe
        """
        width *= scale
        height *= scale
        filename = self.get_artist_cache_name(artist)
        cache_path_jpg = "%s/%s_%s_%s.jpg" % (self._CACHE_PATH, filename,
                                              width, height)
        pixbuf = None

        try:
            # Look in cache
            f = Gio.File.new_for_path(cache_path_jpg)
            if not effect & ArtHelperEffect.NO_CACHE and f.query_exists():
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(cache_path_jpg)
                return pixbuf
            else:
                (exists, path) = self.artist_artwork_exists(artist)
                if exists:
                    f = Gio.File.new_for_path(path)
                    (status, data, tag) = f.load_contents(None)
                    bytes = GLib.Bytes(data)
                    stream = Gio.MemoryInputStream.new_from_bytes(bytes)
                    pixbuf = GdkPixbuf.Pixbuf.new_from_stream(
                        stream, None)
                    stream.close()
                # Pixbuf will be resized, cropping not needed
                if pixbuf is not None and not effect & ArtHelperEffect.RESIZE:
                    pixbuf = self._crop_pixbuf(pixbuf)
                    pixbuf = pixbuf.scale_simple(width, height,
                                                 GdkPixbuf.InterpType.BILINEAR)
                if pixbuf is not None and effect & ArtHelperEffect.SAVE:
                    pixbuf.savev(cache_path_jpg, "jpeg", ["quality"],
                                 [str(App().settings.get_value(
                                     "cover-quality").get_int32())])
            return pixbuf

        except Exception as e:
            Logger.error("ArtistArt::get_artist_artwork(): %s" % e)
            return None

    def get_artist_cache_name(self, artist):
        """
            Get a uniq string for artist
            @param artist as str
        """
        name = "@ARTIST@_%s" % (escape(artist))
        return name

    def uncache_artist_artwork(self, artist):
        """
            Remove artwork from cache
            @param artist as str
        """
        try:
            from pathlib import Path
            search = "%s*.jpg" % self.get_artist_cache_name(artist)
            for p in Path(self._CACHE_PATH).glob(search):
                p.unlink()
        except Exception as e:
            Logger.error("ArtistArt::uncache_artist_artwork(): %s" % e)

#######################
# PRIVATE             #
#######################
