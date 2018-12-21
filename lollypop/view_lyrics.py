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
from lollypop.define import App, Sizing, Type
from lollypop.controller_information import InformationController
from lollypop.utils import escape
from lollypop.logger import Logger
from lollypop.helper_task import TaskHelper
from lollypop.helper_art import ArtHelperEffect


class LyricsView(View, InformationController):
    """
        Show lyrics for track
    """

    def __init__(self):
        """
            Init view
        """
        View.__init__(self)
        InformationController.__init__(self, False,
                                       ArtHelperEffect.BLUR_HARD |
                                       ArtHelperEffect.NO_RATIO)
        self.__current_changed_id = None
        self.__size_allocate_timeout_id = None
        self.__downloads_running = 0
        self.__lyrics_text = ""
        self.__current_width = self.__current_height = 0
        self.__cancellable = Gio.Cancellable()
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/LyricsView.ui")
        builder.connect_signals(self)
        self._artwork = builder.get_object("cover")
        self.__lyrics_label = builder.get_object("lyrics_label")
        self.__translate_button = builder.get_object("translate_button")
        # We do not use View scrolled window because it does not work with
        # an overlay
        self.add(builder.get_object("widget"))
        self.connect("size-allocate", self.__on_size_allocate)

    def populate(self, track):
        """
            Set lyrics
            @param track as Track
        """
        self.__current_track = track
        self.update_artwork(self.__current_width, self.__current_height)
        self.__lyrics_text = ""
        self.__update_lyrics_style()
        self.__lyrics_label.set_text(_("Loading…"))
        self.__cancellable.cancel()
        self.__cancellable.reset()
        # First try to get lyrics from tags
        from lollypop.tagreader import TagReader
        reader = TagReader()
        try:
            info = reader.get_info(self.__current_track.uri)
        except:
            info = None
        if info is not None:
            tags = info.get_tags()
            self.__lyrics_text = reader.get_lyrics(tags)
        if self.__lyrics_text:
            self.__lyrics_label.set_label(self.__lyrics_text)
        else:
            self.__download_wikia_lyrics()
            self.__download_genius_lyrics()

##############
# PROTECTED  #
##############
    def _on_translate_toggled(self, button):
        """
            Translate lyrics
            @param button as Gtk.Button
        """
        if button.get_active():
            App().task_helper.run(self.__get_blob, self.__lyrics_text,
                                  callback=(self.__lyrics_label.set_text,))
        else:
            self.__lyrics_label.set_text(self.__lyrics_text)

    def _on_map(self, widget):
        """
            Set active ids
        """
        if App().settings.get_value("show-sidebar"):
            App().window.emit("can-go-back-changed", True)
            App().window.emit("show-can-go-back", True)
        self.__current_changed_id = App().player.connect(
            "current-changed", self.__on_current_changed)

    def __on_unmap(self, widget):
        """
            Connect player signal
        """
        if self.__current_changed_id is not None:
            App().player.disconnect(self.__current_changed_id)
            self.__current_changed_id = None

############
# PRIVATE  #
############
    def __get_blob(self, text):
        """
            Translate text with current user locale
            @param text as str
        """
        try:
            locales = GLib.get_language_names()
            user_code = locales[0].split(".")[0]
            try:
                from textblob.blob import TextBlob
            except:
                return _("You need to install python3-textblob module")
            blob = TextBlob(text)
            return str(blob.translate(to=user_code))
        except Exception as e:
            Logger.error("LyricsView::__get_blob(): %s", e)
            return _("Can't translate this lyrics")

    def __download_wikia_lyrics(self):
        """
            Downloas lyrics from wikia
        """
        self.__downloads_running += 1
        # Update lyrics
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
        helper = TaskHelper()
        helper.load_uri_content(uri,
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
        if self.__current_track.id == Type.RADIOS:
            split = App().player.current_track.name.split(" - ")
            if len(split) < 2:
                return
            artist = split[0]
            title = split[1]
        else:
            artist = self.__current_track.artists
            title = self.__current_track.name
        string = escape("%s %s" % (artist, title))
        uri = "https://genius.com/%s-lyrics" % string.replace(" ", "-")
        helper = TaskHelper()
        helper.load_uri_content(uri,
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
        if width > Sizing.LARGE:
            context.add_class("lyrics-x-large")
        elif width > Sizing.MONSTER:
            context.add_class("lyrics-large")
        elif width > Sizing.BIG:
            context.add_class("lyrics-medium")

    def __handle_size_allocation(self):
        """
            Update style and resize cover
        """
        self.__size_allocate_timeout_id = None
        self.__update_lyrics_style()
        self.update_artwork(self.__current_width, self.__current_height)

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
        if self.__lyrics_text:
            return
        if status:
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(data, 'html.parser')
                self.__lyrics_text = soup.find_all(
                    "div", class_=cls)[0].get_text(separator=separator)
                self.__lyrics_label.set_text(self.__lyrics_text)
            except Exception as e:
                Logger.warning("LyricsView::__on_lyrics_downloaded(): %s", e)
        if not self.__lyrics_text and self.__downloads_running == 0:
            self.__lyrics_label.set_text(_("No lyrics found ") + "😓")
            self.__translate_button.set_sensitive(False)

    def __on_current_changed(self, player):
        """
            Update lyrics
            @param player as Player
        """
        self.populate(App().player.current_track)
        self.__translate_button.set_sensitive(True)
