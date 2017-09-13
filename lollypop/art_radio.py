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

from gi.repository import GLib, Gdk, GdkPixbuf, Gio

import re

from lollypop.art_base import BaseArt


class RadioArt(BaseArt):
    """
        Manage radio artwork
    """
    if GLib.getenv("XDG_DATA_HOME") is None:
        _RADIOS_PATH = GLib.get_home_dir() + "/.local/share/lollypop/radios"
    else:
        _RADIOS_PATH = GLib.getenv("XDG_DATA_HOME") + "/lollypop/radios"

    def __init__(self):
        """
            Init radio art
        """
        BaseArt.__init__(self)
        d = Gio.File.new_for_path(self._RADIOS_PATH)
        if not d.query_exists():
            try:
                d.make_directory_with_parents()
            except Exception as e:
                print("RadioArt.__init__(): %s" % e)

    def get_radio_cache_path(self, name, size):
        """
            get cover cache path for radio
            @param name as string
            @return cover path as string or None if no cover
        """
        filename = ""
        try:
            filename = self.__get_radio_cache_name(name)
            cache_path_png = "%s/%s_%s.png" % (self._CACHE_PATH,
                                               filename,
                                               size)
            f = Gio.File.new_for_path(cache_path_png)
            if f.query_exists():
                return cache_path_png
            else:
                self.get_radio_artwork(name, size, 1)
                if f.query_exists():
                    return cache_path_png
                else:
                    return self._get_default_icon_path(
                                           size,
                                           "audio-input-microphone-symbolic")
        except Exception as e:
            print("Art::get_radio_cache_path(): %s" % e, ascii(filename))
            return None

    def get_radio_artwork(self, name, size, scale):
        """
            Return a cairo surface for radio name
            @param radio name as string
            @param pixbuf size as int
            @param scale factor as int
            @return cairo surface
        """
        size *= scale
        filename = self.__get_radio_cache_name(name)
        cache_path_png = "%s/%s_%s.png" % (self._CACHE_PATH, filename, size)
        pixbuf = None

        try:
            # Look in cache
            f = Gio.File.new_for_path(cache_path_png)
            if f.query_exists():
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(cache_path_png,
                                                                size,
                                                                size)
            else:
                path = self.__get_radio_art_path(name)
                if path is not None:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(path,
                                                                    size,
                                                                    size)
            if pixbuf is None:
                return self.get_default_icon(
                                             "audio-input-microphone-symbolic",
                                             size,
                                             scale)
            pixbuf.savev(cache_path_png, "png", [None], [None])
            surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf, scale, None)
            return surface

        except Exception as e:
            print(e)
            return self.get_default_icon("audio-input-microphone-symbolic",
                                         size,
                                         scale)

    def copy_uri_to_cache(self, params):
        """
            Copy uri to cache at size
            @param params as (str, str, int)
            @thread safe
        """
        uri, name, size = params
        filename = self.__get_radio_cache_name(name)
        cache_path_png = "%s/%s_%s.png" % (self._CACHE_PATH, filename, size)
        s = Gio.File.new_for_uri(uri)
        d = Gio.File.new_for_path(cache_path_png)
        s.copy(d, Gio.FileCopyFlags.OVERWRITE, None, None)
        GLib.idle_add(self.emit, "radio-artwork-changed", name)

    def rename_radio(self, old_name, new_name):
        """
            Rename artwork
            @param old name as str
            @param new name as str
        """
        old = "%s/%s.png" % (self._RADIOS_PATH, old_name)
        new = "%s/%s.png" % (self._RADIOS_PATH, new_name)
        try:
            src = Gio.File.new_for_path(old)
            dst = Gio.File.new_for_path(new)
            src.move(dst, Gio.FileCopyFlags.OVERWRITE, None, None)
        except Exception as e:
            print("RadioArt::rename_radio(): %s" % e)

    def save_radio_artwork(self, pixbuf, radio):
        """
            Save pixbuf for radio
            @param pixbuf as Gdk.Pixbuf
            @param radio name as string
        """
        try:
            artpath = self._RADIOS_PATH + "/" +\
                      radio.replace("/", "-") + ".png"
            pixbuf.savev(artpath, "png", [None], [None])
        except Exception as e:
            print("RadioArt::save_radio_artwork(): %s" % e)

    def radio_artwork_update(self, name):
        """
            Announce radio logo update
            @param radio name as string
        """
        self.emit("radio-artwork-changed", name)

    def clean_radio_cache(self, name):
        """
            Remove logo from cache for radio
            @param radio name as string
        """
        cache_name = self.__get_radio_cache_name(name)
        try:
            f = Gio.File.new_for_path(self._CACHE_PATH)
            infos = f.enumerate_children(
                "standard::name",
                Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
                None)
            for info in infos:
                f = infos.get_child(info)
                basename = f.get_basename()
                if re.search("%s_.*\.png" % re.escape(cache_name), basename):
                    f.delete()
        except Exception as e:
            print("RadioArt::clean_radio_cache(): ", e, cache_name)

#######################
# PRIVATE             #
#######################
    def __get_radio_art_path(self, name):
        """
            Look for radio covers
            @param radio name as string
            @return cover file path as string
        """
        try:
            name = name.replace("/", "-")
            f = Gio.File.new_for_path(self._RADIOS_PATH + "/" + name + ".png")
            if f.query_exists():
                return self._RADIOS_PATH + "/" + name + ".png"
            return None
        except Exception as e:
            print("Art::__get_radio_art_path(): %s" % e)

    def __get_radio_cache_name(self, name):
        """
            Get a uniq string for radio
            @param album id as int
            @param sql as sqlite cursor
        """
        return "@@"+name.replace("/", "-")+"@@radio@@"
