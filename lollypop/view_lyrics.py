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

from gi.repository import Gtk, GLib, Gio, Pango

from gettext import gettext as _

from lollypop.view import View
from lollypop.define import App, WindowSize
from lollypop.utils import escape
from lollypop.helper_task import TaskHelper


class LyricsView(View):
    """
        Show lyrics for track
    """

    def __init__(self):
        """
            Init view
        """
        View.__init__(self)
        self.__lyrics_set = False
        self.__cancellable = Gio.Cancellable()
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_vexpand(True)
        scrolled_window.set_hexpand(True)
        scrolled_window.show()
        self.__lyrics_label = Gtk.Label()
        self.__lyrics_label.set_line_wrap_mode(Pango.WrapMode.WORD)
        self.__lyrics_label.set_line_wrap(True)
        self.__lyrics_label.set_property("halign", Gtk.Align.CENTER)
        self.__lyrics_label.set_property("valign", Gtk.Align.CENTER)
        self.__lyrics_label.get_style_context().add_class("lyrics")
        scrolled_window.add(self.__lyrics_label)
        self.add(scrolled_window)

    def populate(self):
        """
            Set lyrics
        """
        self.__lyrics_set = False
        self.__lyrics_label.hide()
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
        else:
            self.__download_wikia_lyrics()
            self.__download_genius_lyrics()

##############
# PROTECTED  #
##############
    def _on_current_changed(self, player):
        """
            Update lyrics
            @param player as Player
        """
        self.populate()

############
# PRIVATE  #
############
    def __download_wikia_lyrics(self):
        """
            Downloas lyrics from wikia
        """
        # Update lyrics
        task_helper = TaskHelper()
        artist = GLib.uri_escape_string(
            App().player.current_track.artists[0],
            None,
            False)
        title = GLib.uri_escape_string(
            App().player.current_track.name,
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
        # Update lyrics
        task_helper = TaskHelper()
        string = escape("%s %s" % (App().player.current_track.artists[0],
                                   App().player.current_track.name))
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
        context = self.__lyrics_label.get_style_context()
        for cls in context.list_classes():
            context.remove_class(cls)
        context.add_class("lyrics")
        width = self.get_allocated_width()
        if width > WindowSize.XXLARGE:
            context.add_class("lyrics-xx-large")
        elif width > WindowSize.MONSTER:
            context.add_class("lyrics-x-large")
        elif width > WindowSize.BIG:
            context.add_class("lyrics-large")

    def __on_lyrics_downloaded(self, uri, status, data, cls, separator):
        """
            Show lyrics
            @param uri as str
            @param status as bool
            @param data as bytes
            @param cls as str
            @param separator as str
        """
        if self.__lyrics_set:
            return
        self.__update_lyrics_style()
        self.__lyrics_label.show()
        if status:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(data, 'html.parser')
            try:
                lyrics_text = soup.find_all(
                    "div", class_=cls)[0].get_text(separator=separator)
                self.__lyrics_label.set_text(lyrics_text)
                self.__lyrics_set = True
            except Exception as e:
                self.__lyrics_label.set_text(_("No lyrics found ") + "😐")
        else:
            self.__lyrics_label.set_text(_("No lyrics found ") + "😐")
