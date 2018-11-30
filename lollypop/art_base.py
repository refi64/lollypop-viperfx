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

from gi.repository import GObject, GdkPixbuf, Gio, GLib

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
    def _preserve_ratio(self, pixbuf, w, h):
        """
            Return scaled pixbuf if needed
            @param uri as str
            @param w as int
            @param h as int
            @return GdkPixbuf.Pixbuf
        """
        if App().settings.get_value("preserve-aspect-ratio"):
            return pixbuf
        width = pixbuf.get_width()
        height = pixbuf.get_height()
        if width == height:
            preserve = True
        elif width < height:
            cut = height / 5
            preserve = width < height - cut
        else:
            cut = width / 5
            preserve = height < width - cut
        if preserve:
            return pixbuf
        else:
            return pixbuf.scale_simple(w, h, GdkPixbuf.InterpType.BILINEAR)

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
