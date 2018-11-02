# Copyright (c) 2014-2018 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# Copyright (c) 2013 Vadim Rutkovsky <vrutkovs@redhat.com>
# Copyright (c) 2013 Arnel A. Borja <kyoushuu@yahoo.com>
# Copyright (c) 2013 Seif Lotfy <seif@lotfy.com>
# Copyright (c) 2013 Guillaume Quintard <guillaume.quintard@gmail.com>
# Copyright (c) 2013 Lubosz Sarnecki <lubosz@gmail.com>
# Copyright (c) 2013 Sai Suman Prayaga <suman.sai14@gmail.com>
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

from gi.repository import Gtk, Gdk, GObject, GdkPixbuf, Gio, GLib

from lollypop.define import ArtSize, App, TAG_EDITORS
from lollypop.logger import Logger


class BaseArt(GObject.GObject):
    """
        Base art manager
    """
    _CACHE_PATH = GLib.get_user_cache_dir() + "/lollypop"
    # Fallback when album dir is readonly
    _STORE_PATH = GLib.get_user_data_dir() + "/lollypop/store"
    __gsignals__ = {
        "album-artwork-changed": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        "artist-artwork-changed": (GObject.SignalFlags.RUN_FIRST,
                                   None, (str,)),
        "radio-artwork-changed": (GObject.SignalFlags.RUN_FIRST, None, (str,))
    }

    def __init__(self):
        """
            Init base art
        """
        GObject.GObject.__init__(self)
        self.__kid3_available = False
        self.__tag_editor = App().settings.get_value("tag-editor").get_string()
        self.__kid3_cli_search()
        self.__tag_editor_search()

    def update_art_size(self):
        """
            Update value with some check
        """
        value = App().settings.get_value("cover-size").get_int32()
        # Check value as user can enter bad value via dconf
        if value < ArtSize.SMALL or value > ArtSize.MAX:
            value = 200
        ArtSize.BIG = value
        # For a 200 album artwork, we want a 60 artist artwork
        ArtSize.ARTIST_SMALL = ArtSize.BIG * 60 / 200

    def clean_store(self, filename):
        """
            @param filename as str
        """
        try:
            filepath = self._STORE_PATH + "/" + filename + ".jpg"
            f = Gio.File.new_for_path(filepath)
            if f.query_exists():
                f.delete()
        except Exception as e:
            Logger.error("Art::clean_store(): %s" % e)

    def get_default_icon(self, icon_name, size, scale):
        """
            Construct an empty cover album,
            code forked Gnome Music, see copyright header
            @param icon_name as str
            @param size as int
            @param scale factor as int
            @return pixbuf as cairo.Surface
        """
        try:
            # First look in cache
            cache_path_jpg = self._get_default_icon_path(size, icon_name)
            f = Gio.File.new_for_path(cache_path_jpg)
            if f.query_exists():
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    cache_path_jpg,
                    size,
                    size,
                    False)
            else:
                # get a small pixbuf with the given path
                icon_size = size / 4
                icon = Gtk.IconTheme.get_default().load_icon(icon_name,
                                                             icon_size, 0)
                # create an empty pixbuf with the requested size
                pixbuf = GdkPixbuf.Pixbuf.new(icon.get_colorspace(),
                                              True,
                                              icon.get_bits_per_sample(),
                                              size,
                                              size)
                pixbuf.fill(0xffffffff)
                icon.composite(pixbuf,
                               icon_size * 3 / 2,
                               icon_size * 3 / 2,
                               icon_size,
                               icon_size,
                               icon_size * 3 / 2,
                               icon_size * 3 / 2,
                               1, 1,
                               GdkPixbuf.InterpType.NEAREST, 255)
                # Gdk < 3.15 was missing save method
                # > 3.15 is missing savev method
                try:
                    pixbuf.save(cache_path_jpg, "jpeg",
                                ["quality"], [str(App().settings.get_value(
                                              "cover-quality").get_int32())])
                except:
                    pixbuf.savev(cache_path_jpg, "jpeg",
                                 ["quality"], [str(App().settings.get_value(
                                     "cover-quality").get_int32())])
            surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf, scale, None)
            return surface
        except:
            return self.get_default_icon("computer-fail-symbolic",
                                         ArtSize.MEDIUM,
                                         scale)

    @property
    def kid3_available(self):
        """
            True if kid3 is available
            @return bool
        """
        return self.__kid3_available

    @property
    def tag_editor(self):
        """
            Get tag editor
            @return bool
        """
        return self.__tag_editor

#######################
# PROTECTED           #
#######################
    def _preserve_ratio(self, uri):
        """
            Preserve the cover’s aspect ratio
            @param uri as str
            @return respect aspect ratio as bool
        """
        if App().settings.get_value("preserve-aspect-ratio"):
            return True
        f = Gio.File.new_for_uri(uri)
        (status, data, tag) = f.load_contents(None)
        bytes = GLib.Bytes(data)
        stream = Gio.MemoryInputStream.new_from_bytes(bytes)
        cover = GdkPixbuf.Pixbuf.new_from_stream(stream, None)
        stream.close()
        cover_width = cover.get_width()
        cover_height = cover.get_height()
        del cover
        if cover_width == cover_height:
            return True
        elif cover_width < cover_height:
            cut = cover_height / 5
            return cover_width < cover_height - cut
        else:
            cut = cover_width / 5
            return cover_height < cover_width - cut

    def _create_store(self):
        """
            Create store dir
        """
        d = Gio.File.new_for_path(self._STORE_PATH)
        if not d.query_exists():
            try:
                d.make_directory_with_parents()
            except:
                Logger.info("Can't create %s" % self._STORE_PATH)

    def _create_cache(self):
        """
            Create cache dir
        """
        d = Gio.File.new_for_path(self._CACHE_PATH)
        if not d.query_exists():
            try:
                d.make_directory_with_parents()
            except:
                Logger.info("Can't create %s" % self._CACHE_PATH)

    def _get_default_icon_path(self, size, icon_name):
        """
            Return default icon path
            @return path as string
        """
        return "%s/%s_%s.jpg" % (self._CACHE_PATH, icon_name, size)

#######################
# PRIVATE             #
#######################
    def __tag_editor_search(self, editors=TAG_EDITORS):
        """
            Search for tag editor
        """
        # Search for available tag editors
        if not self.__tag_editor and editors:
            editor = editors.pop(0)
            if GLib.find_program_in_path("flatpak-spawn") is not None:
                argv = ["flatpak-spawn", "--host",
                        "sh", "-c", 'command -v %s' % editor]
            elif GLib.find_program_in_path(editor) is not None:
                self.__tag_editor = editor
                return
            try:
                (pid, stdin, stdout, stderr) = GLib.spawn_async(
                    argv, flags=GLib.SpawnFlags.SEARCH_PATH |
                    GLib.SpawnFlags.STDOUT_TO_DEV_NULL |
                    GLib.SpawnFlags.DO_NOT_REAP_CHILD,
                    standard_input=False,
                    standard_output=False,
                    standard_error=False
                )
                GLib.child_watch_add(GLib.PRIORITY_DEFAULT_IDLE, pid,
                                     self.__on_tag_editor_result,
                                     editor, editors)
            except:
                self.__on_tag_editor_result(None, 1, editor, editors)

    def __kid3_cli_search(self):
        """
            Search for kid3-cli
        """
        if GLib.find_program_in_path("flatpak-spawn") is not None:
            argv = ["flatpak-spawn", "--host",
                    "sh", "-c", 'command -v kid3-cli']
        elif GLib.find_program_in_path("kid3-cli") is not None:
            self.__kid3_available = True
            return
        try:
            (pid, stdin, stdout, stderr) = GLib.spawn_async(
                argv, flags=GLib.SpawnFlags.SEARCH_PATH |
                GLib.SpawnFlags.STDOUT_TO_DEV_NULL |
                GLib.SpawnFlags.DO_NOT_REAP_CHILD,
                standard_input=False,
                standard_output=False,
                standard_error=False
            )
            GLib.child_watch_add(GLib.PRIORITY_DEFAULT_IDLE, pid,
                                 self.__on_kid3_result)
        except:
            self.__on_kid3_result(None, 1)

    def __on_tag_editor_result(self, pid, status, editor, editors):
        """
            Set editor
            @param pid as int
            @param status as bool
            @param editor as str
            @param editors as [str]
        """
        if pid is not None:
            GLib.spawn_close_pid(pid)
        if status == 0:
            self.__tag_editor = editor
        else:
            self.__tag_editor_search(editors)

    def __on_kid3_result(self, pid, status):
        """
            Set state
            @param pid as int
            @param status as bool
        """
        if pid is not None:
            GLib.spawn_close_pid(pid)
        self.__kid3_available = status == 0
