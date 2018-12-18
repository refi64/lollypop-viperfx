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

from gi.repository import Gtk, GLib, Gio, Gdk

from gettext import gettext as _

from lollypop.define import App, ArtSize, RowListType
from lollypop.objects import Album
from lollypop.logger import Logger
from lollypop.utils import escape
from lollypop.helper_art import ArtHelperEffect
from lollypop.information_store import InformationStore
from lollypop.view_albums_list import AlbumsListView
from lollypop.view import BaseView


class Wikipedia:
    """
        Helper for wikipedia search
    """
    def __init__(self, cancellable):
        """
            Init wikipedia
            @param cancellable as Gio.Cancellable
            @raise exception  is wikipedia module not installed
        """
        self.__cancellable = cancellable
        import wikipedia
        wikipedia

    def get_content(self, string):
        """
            Get content for string
            @param string as str
            @return str/None
        """
        content = None
        try:
            name = self.__get_duckduck_name(string)
            if name is None:
                return None
            from locale import getdefaultlocale
            import wikipedia
            language = getdefaultlocale()[0][0:2]
            wikipedia.set_lang(language)
            page = wikipedia.page(name)
            if page is None:
                wikipedia.set_lang("en")
                page = wikipedia.page(name)
            if page is not None:
                content = page.content.encode(encoding="UTF-8")
        except Exception as e:
            Logger.error("Wikipedia::get_content(): %s", e)
        return content

#######################
# PRIVATE             #
#######################
    def __get_duckduck_name(self, string):
        """
            Get wikipedia duck duck name for string
            @param string as str
            @return str
        """
        name = None
        try:
            uri = "https://api.duckduckgo.com/?q=%s&format=json&pretty=1"\
                % string
            f = Gio.File.new_for_uri(uri)
            (status, data, tag) = f.load_contents(self.__cancellable)
            if status:
                import json
                decode = json.loads(data.decode("utf-8"))
                uri = decode["AbstractURL"]
                if uri:
                    name = uri.split("/")[-1]
        except Exception as e:
            Logger.error("Wikipedia::__get_duckduck_name(): %s", e)
        return name


class InformationView(BaseView, Gtk.Bin):
    """
        View with artist information
    """

    def __init__(self, minimal=False):
        """
            Init artist infos
            @param follow_player as bool
        """
        BaseView.__init__(self)
        Gtk.Bin.__init__(self)
        self.__cancellable = Gio.Cancellable()
        self.__minimal = minimal
        self.__artist_name = ""
        self.connect("unmap", self.__on_unmap)

    def populate(self, artist_id=None):
        """
            Show information for artists
            @param artist_id as int
        """
        builder = Gtk.Builder()
        builder.add_from_resource(
            "/org/gnome/Lollypop/ArtistInformation.ui")
        builder.connect_signals(self)
        self.__scrolled = builder.get_object("scrolled")
        widget = builder.get_object("widget")
        self.add(widget)
        self.__stack = builder.get_object("stack")
        self.__artist_label = builder.get_object("artist_label")
        title_label = builder.get_object("title_label")
        self.__artist_artwork = builder.get_object("artist_artwork")
        eventbox = builder.get_object("eventbox")
        eventbox.connect("button-release-event",
                         self.__on_label_button_release_event)
        self.__bio_label = builder.get_object("bio_label")
        if artist_id is None and App().player.current_track.id is not None:
            builder.get_object("header").show()
            builder.get_object("lyrics_button").show()
            builder.get_object("lyrics_button").connect(
                "clicked",
                self.__on_lyrics_button_clicked,
                App().player.current_track)
            artist_id = App().player.current_track.artist_ids[0]
            title_label.set_text(App().player.current_track.title)
        self.__artist_name = App().artists.get_name(artist_id)
        if self.__minimal:
            self.__artist_artwork.hide()
        else:
            builder.get_object("header").show()
            self.__artist_label.set_text(self.__artist_name)
            self.__artist_label.show()
            title_label.show()
            App().art_helper.set_artist_artwork(
                                    self.__artist_name,
                                    ArtSize.ARTIST_SMALL * 3,
                                    ArtSize.ARTIST_SMALL * 3,
                                    self.__artist_artwork.get_scale_factor(),
                                    self.__on_artist_artwork,
                                    ArtHelperEffect.ROUNDED)
            albums_view = AlbumsListView(RowListType.READ_ONLY)
            albums_view.set_size_request(300, -1)
            albums_view.show()
            albums_view.set_margin_start(5)
            widget.attach(albums_view, 2, 1, 1, 2)
            albums = []
            for album_id in App().albums.get_ids([artist_id], []):
                albums.append(Album(album_id))
            albums_view.populate(albums)
        App().task_helper.run(InformationStore.get_bio, self.__artist_name,
                              callback=(self.__on_get_bio,))

#######################
# PROTECTED           #
#######################
    def _on_label_realize(self, eventbox):
        """
            @param eventbox as Gtk.EventBox
        """
        try:
            eventbox.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))
        except:
            Logger.warning(_("You are using a broken cursor theme!"))

    def _on_enable_network_access_state_set(self, widget, state):
        """
            Save network access state
            @param widget as Gtk.Switch
            @param state as bool
        """
        App().settings.set_value("network-access",
                                 GLib.Variant("b", state))
        self.__stack.set_visible_child_name("bio")
        self.__artist_label.hide()
        self.__bio_label.set_text(_("Loading information"))
        App().task_helper.run(
            self.__get_bio_content, callback=(self.__set_bio_content,))

#######################
# PRIVATE             #
#######################
    def __get_bio_content(self):
        """
            Get bio content and call callback
            @param content as str
        """
        content = None
        try:
            wikipedia = Wikipedia(self.__cancellable)
            content = wikipedia.get_content(self.__artist_name)
        except Exception as e:
            Logger.info("InformationPopover::__get_bio_content(): %s" % e)
        try:
            if content is None and App().lastfm is not None:
                content = App().lastfm.get_artist_bio(self.__artist_name)
        except Exception as e:
            Logger.info("InformationPopover::__get_bio_content(): %s" % e)
        return content

    def __set_bio_content(self, content):
        """
            Set bio content
            @param content as bytes
        """
        if content is not None:
            App().task_helper.run(InformationStore.add_artist_bio,
                                  self.__artist_name, content)
            self.__bio_label.set_markup(
                GLib.markup_escape_text(content.decode("utf-8")))
        else:
            self.__bio_label.set_text(
                _("No information for %s") % self.__artist_name)

    def __get_artist_artwork_path_from_cache(self, artist, size):
        """
            Get artist artwork path
            @param artist as str
            @param size as int
            @return str
        """
        path = InformationStore.get_artwork_path(
            artist, size, self.get_scale_factor())
        if path is not None:
            return path
        return None

    def __on_lyrics_button_clicked(self, button, track):
        """
            Show lyrics
            @param button as Gtk.Button
            @param track as Track
        """
        popover = self.get_ancestor(Gtk.Popover)
        if popover is not None:
            popover.popdown()
        App().window.container.show_lyrics(track)

    def __on_label_button_release_event(self, button, event):
        """
            Show information cache (for edition)
            @param button as Gtk.Button
            @param event as Gdk.Event
        """
        uri = "file://%s/%s.txt" % (InformationStore._INFO_PATH,
                                    escape(self.__artist_name))
        f = Gio.File.new_for_uri(uri)
        if not f.query_exists():
            f.replace_contents(b"", None, False,
                               Gio.FileCreateFlags.NONE, None)
        Gtk.show_uri_on_window(App().window,
                               uri,
                               Gdk.CURRENT_TIME)

    def __on_unmap(self, widget):
        """
            Cancel operations
            @param widget as Gtk.Widget
        """
        self.__cancellable.cancel()

    def __on_artist_artwork(self, surface):
        """
            Finish widget initialisation
            @param surface as cairo.Surface
        """
        if surface is None:
            self.__artist_artwork.hide()
        else:
            self.__artist_artwork.set_from_surface(surface)

    def __on_get_bio(self, content):
        """
            Set bio content or get a new one if None
            @param content as bytes
        """
        if content is not None:
            self.__bio_label.set_markup(
                GLib.markup_escape_text(content.decode("utf-8")))
        elif not App().settings.get_value("network-access"):
            if self.__minimal:
                self.__stack.set_visible_child_name("data")
                self.__artist_label.set_text(
                    _("No information for %s") % self.__artist_name)
                self.__artist_label.show()
            else:
                self.__scrolled.hide()
        else:
            self.__bio_label.set_text(_("Loading information"))
            App().task_helper.run(self.__get_bio_content,
                                  callback=(self.__set_bio_content,))
