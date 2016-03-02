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

from shutil import rmtree
from os import mkdir, path

from lollypop.art_album import AlbumArt
from lollypop.art_radio import RadioArt


class Art(AlbumArt, RadioArt):
    """
        Global artwork manager
    """

    def __init__(self):
        """
            Create cache path
        """
        AlbumArt.__init__(self)
        RadioArt.__init__(self)
        self._create_cache()

    def clean_all_cache(self):
        """
            Remove all covers from cache
        """
        try:
            rmtree(self._CACHE_PATH)
            self._create_cache()
        except Exception as e:
            print("Art::clean_all_cache(): ", e)


# TODO Add a cache.py file and move all cache code(artist, covers) here
class ArtistCache:
    """
        Cache artist code
    """
    CACHE_PATH = path.expanduser("~") + "/.cache/lollypop_infos"

    def init():
        """
            Init cache
        """
        if not path.exists(ArtistCache.CACHE_PATH):
            try:
                mkdir(ArtistCache.CACHE_PATH)
            except:
                print("Can't create %s" % ArtistCache.CACHE_PATH)

    def exists_in_cache(artist):
        """
            Return True if an artist is cached
            @param artist as string
        """
        return ArtistCache.get_artwork(artist, "lastfm") != "" or\
            ArtistCache.get_artwork(artist, "wikipedia") != ""

    def get_artwork(artist, suffix):
        """
            Return path for artwork, empty if none
            @param artist as string
            @param suffix as string
            @return path as string
        """
        filepath = "%s/%s_%s.jpg" % (ArtistCache.CACHE_PATH,
                                     "".join([c for c in artist if
                                              c.isalpha() or
                                              c.isdigit() or
                                              c == ' ']).rstrip(),
                                     suffix)
        if path.exists(filepath):
            return filepath
        else:
            return ""

    def get(artist, suffix):
        """
            Get content from cache
            @return (content as string, data as bytes)
        """
        filepath = "%s/%s_%s" % (ArtistCache.CACHE_PATH,
                                 "".join([c for c in artist if
                                          c.isalpha() or
                                          c.isdigit() or c == ' ']).rstrip(),
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

    def cache(artist, content, data, suffix):
        """
            Cache datas
            @param content as string
            @param data as bytes
            @param suffix as string
        """
        if content is None:
            return

        filepath = "%s/%s_%s" % (ArtistCache.CACHE_PATH,
                                 "".join([c for c in artist if
                                          c.isalpha() or
                                          c.isdigit() or c == ' ']).rstrip(),
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

    def uncache(artist, suffix):
        """
            Remove artist from cache
            @param artist as string
            @param suffix as string
        """
        filepath = "%s/%s_%s.txt" % (ArtistCache.CACHE_PATH,
                                     "".join(
                                        [c for c in artist if
                                         c.isalpha() or
                                         c.isdigit() or c == ' ']).rstrip(),
                                     suffix)
        f = Gio.File.new_for_path(filepath)
        try:
            f.delete(None)
        except:
            pass
        filepath = "%s/%s_%s" % (ArtistCache.CACHE_PATH,
                                 "".join([c for c in artist if
                                          c.isalpha() or
                                          c.isdigit() or c == ' ']).rstrip(),
                                 suffix)
        f = Gio.File.new_for_path(filepath)
        try:
            f.delete(None)
        except:
            pass
