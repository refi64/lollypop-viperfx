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

from gi.repository import Gio, GLib, GdkPixbuf

from lollypop.utils import escape
from lollypop.define import App
from lollypop.logger import Logger


class InformationStore:
    """
        Generic class to cache text and images
    """
    _INFO_PATH = GLib.get_user_data_dir() + "/lollypop/info"
    _CACHE_PATH = GLib.get_user_cache_dir() + "/lollypop_info"

    WEBSERVICES = [("lastfm", "_get_lastfm_artist_artwork_uri",
                    "_get_lastfm_album_artwork"),
                   ("spotify", "_get_spotify_artist_artwork_uri",
                    "_get_spotify_album_artwork"),
                   ("deezer", "_get_deezer_artist_artwork_uri",
                    "_get_deezer_album_artwork")]

    def init():
        """
            Init store
        """
        try:
            d = Gio.File.new_for_path(InformationStore._INFO_PATH)
            if not d.query_exists():
                d.make_directory_with_parents()
        except:
            Logger.info("Can't create %s" % InformationStore._INFO_PATH)
        try:
            d = Gio.File.new_for_path(InformationStore._CACHE_PATH)
            if not d.query_exists():
                d.make_directory_with_parents()
        except:
            Logger.info("Can't create %s" % InformationStore._CACHE_PATH)

    def artwork_exists(artist):
        """
            True if artwork exists
            @param artist as str
            @return bool
        """
        filepath = "%s/%s.jpg" % (InformationStore._INFO_PATH,
                                  escape(artist))
        return GLib.file_test(filepath, GLib.FileTest.EXISTS)

    def get_artwork_path(artist, size, scale_factor):
        """
            Return path for artwork
            @param artist as string
            @param size as int
            @param scale_factor as int
            @return path as string/None
        """
        try:
            size *= scale_factor
            extract = None
            filepath = "%s/%s.jpg" % (
                InformationStore._INFO_PATH,
                escape(artist))
            filepath_at_size = "%s/%s_%s.jpg" % (
                InformationStore._CACHE_PATH,
                escape(artist),
                size)
            f = Gio.File.new_for_path(filepath)
            if not f.query_exists():
                return None
            info = f.query_info(
                "standard::size",
                Gio.FileQueryInfoFlags.NONE)
            if info.get_size() == 0:
                return None
            # Make cache for this size
            f = Gio.File.new_for_path(filepath_at_size)
            if not f.query_exists():
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(filepath,
                                                                size,
                                                                size)
                if pixbuf.get_height() > pixbuf.get_width():
                    vertical = True
                elif pixbuf.get_height() < pixbuf.get_width():
                    vertical = False
                else:
                    extract = pixbuf
                if extract is None:
                    extract = GdkPixbuf.Pixbuf.new(
                        GdkPixbuf.Colorspace.RGB,
                        True, 8,
                        size, size)
                    if vertical:
                        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                            filepath,
                            size,
                            -1,
                            True)
                        diff = pixbuf.get_height() - size
                        pixbuf.copy_area(0, diff / 2,
                                         pixbuf.get_width(),
                                         size,
                                         extract,
                                         0, 0)
                    else:
                        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                            filepath,
                            -1,
                            size,
                            True)
                        diff = pixbuf.get_width() - size
                        pixbuf.copy_area(diff / 2, 0,
                                         size,
                                         pixbuf.get_height(),
                                         extract,
                                         0, 0)
                extract.savev(filepath_at_size, "jpeg",
                              ["quality"], [str(App().settings.get_value(
                                            "cover-quality").get_int32())])
            return filepath_at_size
        except Exception as e:
            Logger.error("InformationStore::get_artwork_path(): %s" % e)
            return None

    def get_bio(artist):
        """
            Get content from cache
            @param artist as str
            @return content as bytes
        """
        filepath = "%s/%s.txt" % (InformationStore._INFO_PATH,
                                  escape(artist))
        content = None
        f = Gio.File.new_for_path(filepath)
        if f.query_exists():
            (status, content, tag) = f.load_contents()
        return content

    def add_artist_artwork(artist, data):
        """
            Add artist artwork to store
            @param artist as str
            @param data as bytes
        """
        filepath = "%s/%s.jpg" % (InformationStore._INFO_PATH, escape(artist))
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

    def add_artist_bio(artist, content):
        """
            Add artist bio to store
            @param artist as str
            @param content as str
        """
        filepath = "%s/%s.txt" % (InformationStore._INFO_PATH,
                                  escape(artist))
        if content is not None:
            f = Gio.File.new_for_path(filepath)
            fstream = f.replace(None, False,
                                Gio.FileCreateFlags.REPLACE_DESTINATION, None)
            if fstream is not None:
                fstream.write(content, None)
                fstream.close()

    def uncache_artwork(artist):
        """
            Remove artwork from cache
            @param artist as str
        """
        try:
            from pathlib import Path
            search = "%s*.jpg" % escape(artist)
            for p in Path(InformationStore._CACHE_PATH).glob(search):
                p.unlink()
        except Exception as e:
            Logger.error("InformationStore::uncache_artwork(): %s" % e)
