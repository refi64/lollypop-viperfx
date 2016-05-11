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

from gi.repository import Gio, GdkPixbuf

from os import mkdir, path

from lollypop.utils import escape
from lollypop.define import ArtSize


class InfoCache:
    """
        Generic class to cache text and images
    """
    CACHE_PATH = path.expanduser("~") + "/.cache/lollypop_info"

    def init():
        """
            Init cache
        """
        if not path.exists(InfoCache.CACHE_PATH):
            try:
                mkdir(InfoCache.CACHE_PATH)
            except:
                print("Can't create %s" % InfoCache.CACHE_PATH)

    def exists_in_cache(prefix):
        """
            Return True if an info is cached
            @param prefix as string
        """
        exists = False
        for suffix in ["lastfm", "wikipedia", "spotify"]:
            filepath = "%s/%s_%s_%s.jpg" % (InfoCache.CACHE_PATH,
                                            escape(prefix),
                                            suffix,
                                            ArtSize.ARTIST)
            if path.exists(filepath):
                exists = True
        return exists

    def get_artwork(prefix, suffix, size=ArtSize.ARTIST):
        """
            Return path for artwork
            @param prefix as string
            @param suffix as string
            @param size as int
            @return path as string/None
        """
        try:
            extract = None
            filepath = "%s/%s_%s_%s.jpg" % (InfoCache.CACHE_PATH,
                                            escape(prefix),
                                            suffix,
                                            ArtSize.ARTIST)
            filepath_at_size = "%s/%s_%s_%s.jpg" % (InfoCache.CACHE_PATH,
                                                    escape(prefix),
                                                    suffix,
                                                    size)
            if not path.exists(filepath) or path.getsize(filepath) == 0:
                return None
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
                    extract = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB,
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
                extract.savev(filepath_at_size, "jpeg", ["quality"], ["90"])
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
        filepath = "%s/%s_%s" % (InfoCache.CACHE_PATH,
                                 escape(prefix),
                                 suffix)
        content = None
        data = None
        if path.exists(filepath+".txt"):
            f = Gio.File.new_for_path(filepath+".txt")
            (status, content, tag) = f.load_contents()
            if not status:
                content = None
            image_path = filepath+"_"+str(ArtSize.ARTIST)+".jpg"
            if path.exists(image_path):
                f = Gio.File.new_for_path(image_path)
                (status, data, tag) = f.load_contents()
                if not status:
                    data = None
        return (content, data)

    def cache(prefix, content, data, suffix):
        """
            Cache datas
            @param prefix as str
            @param content as str
            @param data as bytes
            @param suffix as str
        """
        filepath = "%s/%s_%s" % (InfoCache.CACHE_PATH,
                                 escape(prefix),
                                 suffix)
        if content is not None:
            f = Gio.File.new_for_path(filepath+".txt")
            fstream = f.replace(None, False,
                                Gio.FileCreateFlags.REPLACE_DESTINATION, None)
            if fstream is not None:
                fstream.write(content, None)
                fstream.close()
        if data is None:
            f = Gio.File.new_for_path(filepath+"_"+str(ArtSize.ARTIST)+".jpg")
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
            pixbuf.savev(filepath+"_"+str(ArtSize.ARTIST)+".jpg",
                         "jpeg", ["quality"], ["90"])
            del pixbuf

    def uncache(prefix, suffix):
        """
            Remove info from cache
            @param prefix as str
            @param suffix as str
        """
        filepath = "%s/%s_%s.txt" % (InfoCache.CACHE_PATH,
                                     escape(prefix),
                                     suffix)
        f = Gio.File.new_for_path(filepath)
        try:
            f.delete(None)
        except:
            pass
        filepath = "%s/%s_%s_%s.jpg" % (InfoCache.CACHE_PATH,
                                        escape(prefix),
                                        suffix,
                                        ArtSize.ARTIST)
        f = Gio.File.new_for_path(filepath)
        try:
            f.delete(None)
        except:
            pass

    def uncache_artwork(prefix, suffix, scale):
        """
            Remove info from cache
            @param prefix as str
            @param suffix as str
            @param scale factor as int
        """
        for i in [1, 2]:
            filepath = "%s/%s_%s_%s.jpg" % (InfoCache.CACHE_PATH,
                                            escape(prefix),
                                            suffix,
                                            ArtSize.ARTIST_SMALL*scale*i)
            f = Gio.File.new_for_path(filepath)
            try:
                f.delete(None)
            except:
                pass
