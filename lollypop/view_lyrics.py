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

from gi.repository import Gtk, GLib, Gio

from gettext import gettext as _

from lollypop.view import View
from lollypop.define import App, WindowSize, Type
from lollypop.controllers import InfoController
from lollypop.utils import escape
from lollypop.helper_task import TaskHelper


class LyricsView(View, InfoController):
    """
        Show lyrics for track
    """

    def __init__(self):
        """
            Init view
        """
        View.__init__(self)
        InfoController.__init__(self)
        self.__size_allocate_timeout_id = None
        self.__downloads_running = 0
        self.__lyrics_set = False
        self.__current_width = self.__current_height = 0
        self.__cancellable = Gio.Cancellable()
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/LyricsView.ui")
        builder.connect_signals(self)
        self._cover = builder.get_object("cover")
        self.__lyrics_label = builder.get_object("lyrics_label")
        self.add(builder.get_object("widget"))
        self.connect("size-allocate", self.__on_size_allocate)

    def populate(self, track):
        """
            Set lyrics
            @param track as Track
        """
        self.__current_track = track
        self.update_artwork(self.__current_width,
                            self.__current_height,
                            True)
        self.__lyrics_set = False
        self.__update_lyrics_style()
        self.__lyrics_label.set_text(_("Loading…"))
        self.__cancellable.cancel()
        self.__cancellable.reset()
        # First try to get lyrics from tags
        from lollypop.tagreader import TagReader
        lyrics = None
        reader = TagReader()
        try:
            info = reader.get_info(self.__current_track.uri)
        except:
            info = None
        if info is not None:
            tags = info.get_tags()
            lyrics = reader.get_lyrics(tags)
        if lyrics:
            self.__lyrics_label.set_label(lyrics)
        elif App().settings.get_value("network-access"):
            self.__download_wikia_lyrics()
            self.__download_genius_lyrics()
        else:
            self.__lyrics_label.set_label(_("Network access disabled"))

##############
# PROTECTED  #
##############
    def _on_current_changed(self, player):
        """
            Update lyrics
            @param player as Player
        """
        self.populate(App().player.current_track)

############
# PRIVATE  #
############
    def __download_wikia_lyrics(self):
        """
            Downloas lyrics from wikia
        """
        self.__downloads_running += 1
        # Update lyrics
        task_helper = TaskHelper()
        if self.__current_track.id == Type.RADIOS:
            split = self.__current_track.name.split(" - ")
            if len(split) < 2:
                return
            artist = GLib.uri_escape_string(
                split[0],
                None,
                False)
            title = GLib.uri_escape_string(
                split[1],
                None,
                False)
        else:
            artist = GLib.uri_escape_string(
                self.__current_track.name,
                None,
                False)
            title = GLib.uri_escape_string(
                self.__current_track.name,
                None,
                False)
        uri = "http://lyrics.wikia.com/wiki/%s:%s" % (artist, title)
        task_helper.load_uri_content(
            uri,
            self.__cancellable,
            self.__on_lyrics_downloaded,
            "lyricbox",
            "\n")

    def __download_genius_lyrics(self):
        """
            Download lyrics from genius
        """
        self.__downloads_running += 1
        # Update lyrics
        task_helper = TaskHelper()
        if self.__current_track.id == Type.RADIOS:
            split = App().player.current_track.name.split(" - ")
            if len(split) < 2:
                return
            artist = split[0]
            title = split[1]
        else:
            artist = self.__current_track.artists[0]
            title = self.__current_track.name
        string = escape("%s %s" % (artist, title))
        uri = "https://genius.com/%s-lyrics" % string.replace(" ", "-")
        task_helper.load_uri_content(
            uri,
            self.__cancellable,
            self.__on_lyrics_downloaded,
            "song_body-lyrics",
            "")

    def __update_lyrics_style(self):
        """
            Update lyrics style based on current view width
        """
        context = self.get_style_context()
        for cls in context.list_classes():
            context.remove_class(cls)
        context.add_class("lyrics")
        width = self.get_allocated_width()
        if width > WindowSize.XXLARGE:
            context.add_class("lyrics-x-large")
        elif width > WindowSize.MONSTER:
            context.add_class("lyrics-large")
        elif width > WindowSize.BIG:
            context.add_class("lyrics-medium")

    def __handle_size_allocation(self):
        """
            Update style and resize cover
        """
        self.__size_allocate_timeout_id = None
        self.__update_lyrics_style()
        self.update_artwork(self.__current_width,
                            self.__current_height,
                            True)

    def __on_size_allocate(self, widget, allocation):
        """
            Update cover size
            @param widget as Gtk.Widget
            @param allocation as Gtk.Allocation
        """
        if (self.__current_width,
                self.__current_height) == (allocation.width,
                                           allocation.height):
            return
        (self.__current_width,
         self.__current_height) = (allocation.width,
                                   allocation.height)
        if self.__size_allocate_timeout_id is not None:
            GLib.source_remove(self.__size_allocate_timeout_id)
        self.__size_allocate_timeout_id = GLib.idle_add(
            self.__handle_size_allocation)

    def __on_lyrics_downloaded(self, uri, status, data, cls, separator):
        """
            Show lyrics
            @param uri as str
            @param status as bool
            @param data as bytes
            @param cls as str
            @param separator as str
        """
        self.__downloads_running -= 1
        if self.__lyrics_set:
            return
        if status:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(data, 'html.parser')
            try:
                lyrics_text = soup.find_all(
                    "div", class_=cls)[0].get_text(separator=separator)
                self.__lyrics_label.set_text(lyrics_text)
                self.__lyrics_set = True
            except:
                pass
        if not self.__lyrics_set and self.__downloads_running == 0:
            self.__lyrics_label.set_text(_("No lyrics found ") + "😐")
