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

from gi.repository import Gio, GLib, GdkPixbuf

from os import mkdir, path, rename

from lollypop.utils import escape
from lollypop.define import ArtSize, Lp
from lollypop.lio import Lio


class InfoCache:
    """
        Generic class to cache text and images
    """
    if GLib.getenv("XDG_DATA_HOME") is None:
        _INFO_PATH = GLib.get_home_dir() + "/.local/share/lollypop/info"
    else:
        _INFO_PATH = GLib.getenv("XDG_DATA_HOME") + "/lollypop/info"
    if GLib.getenv("XDG_CACHE_HOME") is None:
        _CACHE_PATH = GLib.get_home_dir() + "/.cache/lollypop_info"
    else:
        _CACHE_PATH = GLib.getenv("XDG_CACHE_HOME") + "/lollypop_info"

    WEBSERVICES = [("lastfm", "_get_lastfm_artist_info",
                    "_get_lastfm_album_artwork"),
                   ("spotify", "_get_spotify_artist_info",
                    "_get_spotify_album_artwork"),
                   ("deezer", "_get_deezer_artist_info",
                    "_get_deezer_album_artwork"),
                   ("wikipedia", "_get_wp_artist_info",
                    None)]

    def init():
        """
            Init cache
        """
        if not path.exists(InfoCache._INFO_PATH):
            try:
                mkdir(InfoCache._INFO_PATH)
            except:
                print("Can't create %s" % InfoCache._INFO_PATH)
        if not path.exists(InfoCache._CACHE_PATH):
            try:
                mkdir(InfoCache._CACHE_PATH)
            except:
                print("Can't create %s" % InfoCache._CACHE_PATH)

    def exists(prefix):
        """
            Return True if an info is cached
            @param prefix as string
        """
        exists = False
        for (suffix, helper1, helper2) in InfoCache.WEBSERVICES:
            filepath = "%s/%s_%s.jpg" % (InfoCache._INFO_PATH,
                                         escape(prefix),
                                         suffix)
            if path.exists(filepath):
                exists = True
            else:
                # FIXME Remove this code, support for old lollypop versions
                #
                old_path = "%s/%s_%s_%s.jpg" % (InfoCache._CACHE_PATH,
                                                escape(prefix),
                                                suffix,
                                                ArtSize.ARTIST)
                if path.exists(old_path):
                    rename(old_path, filepath)
                    exists = True
                #
                ##########################################################
        return exists

    def get_artwork(prefix, suffix, size):
        """
            Return path for artwork
            @param prefix as string
            @param suffix as string
            @param size as int
            @return path as string/None
        """
        try:
            for (suffix, helper1, helper2) in InfoCache.WEBSERVICES:
                extract = None
                filepath = "%s/%s_%s.jpg" % (InfoCache._INFO_PATH,
                                             escape(prefix),
                                             suffix)
                filepath_at_size = "%s/%s_%s_%s.jpg" % (InfoCache._CACHE_PATH,
                                                        escape(prefix),
                                                        suffix,
                                                        size)
                if not path.exists(filepath) or path.getsize(filepath) == 0:
                    filepath_at_size = None
                    continue
                # Make cache for this size
                if not path.exists(filepath_at_size):
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
                        del pixbuf
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
                            pixbuf.copy_area(0, diff/2,
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
                            pixbuf.copy_area(diff/2, 0,
                                             size,
                                             pixbuf.get_height(),
                                             extract,
                                             0, 0)
                        del pixbuf
                    extract.savev(filepath_at_size, "jpeg",
                                  ["quality"], [str(Lp().settings.get_value(
                                                "cover-quality").get_int32())])
                    del extract
                return filepath_at_size
        except Exception as e:
            print("InfoCache::get_artwork():", e)
            return None

    def get(prefix, suffix):
        """
            Get content from cache
            @param prefix as str
            @param suffix as str
            @return (content as string, data as bytes)
        """
        filepath = "%s/%s_%s" % (InfoCache._INFO_PATH,
                                 escape(prefix),
                                 suffix)
        content = None
        data = None
        if path.exists(filepath+".txt"):
            f = Lio.File.new_for_path(filepath+".txt")
            (status, content, tag) = f.load_contents()
            if not status:
                content = None
            image_path = filepath+".jpg"
            if path.exists(image_path):
                f = Lio.File.new_for_path(image_path)
                (status, data, tag) = f.load_contents()
                if not status:
                    data = None
        return (content, data)

    def add(prefix, content, data, suffix):
        """
            Add info to store
            @param prefix as str
            @param content as str
            @param data as bytes
            @param suffix as str
        """
        filepath = "%s/%s_%s" % (InfoCache._INFO_PATH,
                                 escape(prefix),
                                 suffix)
        if content is not None:
            f = Lio.File.new_for_path(filepath+".txt")
            fstream = f.replace(None, False,
                                Gio.FileCreateFlags.REPLACE_DESTINATION, None)
            if fstream is not None:
                fstream.write(content, None)
                fstream.close()
        if data is None:
            f = Lio.File.new_for_path(filepath+".jpg")
            fstream = f.replace(None, False,
                                Gio.FileCreateFlags.REPLACE_DESTINATION, None)
            fstream.close()
        else:
            stream = Gio.MemoryInputStream.new_from_data(data, None)
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(stream,
                                                               ArtSize.ARTIST,
                                                               -1,
                                                               True,
                                                               None)
            stream.close()
            pixbuf.savev(filepath+".jpg",
                         "jpeg", ["quality"], [str(Lp().settings.get_value(
                                               "cover-quality").get_int32())])
            del pixbuf

    def remove(prefix, suffix):
        """
            Remove info from store
            @param prefix as str
            @param suffix as str
        """
        filepath = "%s/%s_%s.txt" % (InfoCache._INFO_PATH,
                                     escape(prefix),
                                     suffix)
        f = Lio.File.new_for_path(filepath)
        try:
            f.delete(None)
        except:
            pass
        filepath = "%s/%s_%s.jpg" % (InfoCache._INFO_PATH,
                                     escape(prefix),
                                     suffix)
        f = Lio.File.new_for_path(filepath)
        try:
            f.delete(None)
        except:
            pass

    def uncache_artwork(prefix, suffix, scale):
        """
            Remove artwork from cache
            @param prefix as str
            @param suffix as str
            @param scale factor as int
        """
        for i in [1, 2]:
            filepath = "%s/%s_%s_%s.jpg" % (InfoCache._CACHE_PATH,
                                            escape(prefix),
                                            suffix,
                                            ArtSize.ARTIST_SMALL*scale*i)
            f = Lio.File.new_for_path(filepath)
            try:
                f.delete(None)
            except:
                pass
