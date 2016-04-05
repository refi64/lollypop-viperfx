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
        return InfoCache.get_artwork(prefix, "lastfm") != "" or\
            InfoCache.get_artwork(prefix, "wikipedia") != ""

    def get_artwork(prefix, suffix):
        """
            Return path for artwork, empty if none
            @param prefix as string
            @param suffix as string
            @return path as string
        """
        filepath = "%s/%s_%s.jpg" % (InfoCache.CACHE_PATH,
                                     escape(prefix),
                                     suffix)
        if path.exists(filepath):
            return filepath
        else:
            return ""

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
            if status and path.exists(filepath+".jpg"):
                f = Gio.File.new_for_path(filepath+".jpg")
                (status, data, tag) = f.load_contents()
                if not status:
                    data = None
        if content is None:
            return (None, None)
        else:
            return (content, data)

    def cache(prefix, content, data, suffix):
        """
            Cache datas
            @param prefix as str
            @param content as str
            @param data as bytes
            @param suffix as str
        """
        if content is None:
            return

        filepath = "%s/%s_%s" % (InfoCache.CACHE_PATH,
                                 escape(prefix),
                                 suffix)
        f = Gio.File.new_for_path(filepath+".txt")
        fstream = f.replace(None, False,
                            Gio.FileCreateFlags.REPLACE_DESTINATION, None)
        if fstream is not None:
            fstream.write(content, None)
            fstream.close()
        if data is not None:
            stream = Gio.MemoryInputStream.new_from_data(data, None)
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(stream,
                                                               800,
                                                               -1,
                                                               True,
                                                               None)
            pixbuf.savev(filepath+".jpg", "jpeg", ["quality"], ["90"])
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
        filepath = "%s/%s_%s" % (InfoCache.CACHE_PATH,
                                 escape(prefix),
                                 suffix)
        f = Gio.File.new_for_path(filepath)
        try:
            f.delete(None)
        except:
            pass
