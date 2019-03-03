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
from random import shuffle

from lollypop.define import App, ViewType, Type, Shuffle, MARGIN_SMALL
from lollypop.view_albums_list import AlbumsListView
from lollypop.search import Search
from lollypop.view import BaseView
from lollypop.logger import Logger


class SearchView(BaseView, Gtk.Bin):
    """
        View for searching albums/tracks
    """

    def __init__(self):
        """
            Init Popover
        """
        BaseView.__init__(self)
        Gtk.Bin.__init__(self)
        self.connect("map", self.__on_map)
        self.connect("unmap", self.__on_unmap)
        self.__timeout_id = None
        self.__current_search = ""
        self.__cancellable = Gio.Cancellable()
        self.__history = []

        self.__search_type_action = Gio.SimpleAction.new_stateful(
                                               "search_type",
                                               GLib.VariantType.new("s"),
                                               GLib.Variant("s", "local"))
        self.__search_type_action.connect("change-state",
                                          self.__on_search_action_change_state)
        App().add_action(self.__search_type_action)
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/SearchView.ui")
        builder.connect_signals(self)
        self.__widget = builder.get_object("widget")
        if GLib.find_program_in_path("youtube-dl") is None:
            Logger.warning("youtube-dl is missing")
            builder.get_object("bottom_buttons").hide()
        self.__new_button = builder.get_object("new_button")
        self.__play_button = builder.get_object("play_button")
        self.__entry = builder.get_object("entry")
        self.__spinner = builder.get_object("spinner")
        self.__header_stack = builder.get_object("header_stack")
        self.__stack = builder.get_object("stack")
        self.__placeholder = builder.get_object("placeholder")
        self.__view = AlbumsListView(ViewType.SEARCH)
        self.__view.set_margin_start(MARGIN_SMALL)
        self.__view.show()
        self.__stack.add_named(self.__view, "view")
        self.__set_default_placeholder()
        self.add(self.__widget)

    def set_text(self, text):
        """
            Set search text
        """
        self.__entry.set_text(text)

#######################
# PROTECTED           #
#######################
    def _on_play_button_clicked(self, button):
        """
            Play search
            @param button as Gtk.Button
        """
        try:
            App().player.clear_albums()
            shuffle_setting = App().settings.get_enum("shuffle")
            children = self.__view.children
            if shuffle_setting == Shuffle.ALBUMS:
                shuffle(children)
            for child in children:
                App().player.add_album(child.album)
            App().player.load(App().player.albums[0].tracks[0])
        except Exception as e:
            Logger.error("SearchPopover::_on_play_button_clicked(): %s", e)

    def _on_new_button_clicked(self, button):
        """
            Create a new playlist based on search
            @param button as Gtk.Button
        """
        App().task_helper.run(self.__search_to_playlist)

    def _on_search_changed(self, widget):
        """
            Timeout filtering
            @param widget as Gtk.TextEntry
        """
        if self.__timeout_id:
            GLib.source_remove(self.__timeout_id)
            self.__timeout_id = None
        self.__cancellable.cancel()
        self.__view.stop()
        self.__current_search = widget.get_text().strip()
        self.__timeout_id = GLib.timeout_add(
                500,
                self.__on_search_changed_timeout)

#######################
# PRIVATE             #
#######################
    def __set_no_result_placeholder(self):
        """
            Set placeholder for no result
        """
        self.__placeholder.set_markup(
            _("<big>No results for this search</big>"))

    def __set_default_placeholder(self):
        """
            Set placeholder for no result
        """
        self.__placeholder.set_markup(
            _("<big>Search for artists, albums and tracks</big>"))

    def __populate(self):
        """
            Populate searching items
            in db based on text entry current text
        """
        self.__cancellable.reset()
        self.__header_stack.set_visible_child(self.__spinner)
        self.__history = []
        if len(self.__current_search) > 2:
            self.__spinner.start()
            state = self.__search_type_action.get_state().get_string()
            current_search = self.__current_search.lower()
            if state == "local":
                search = Search()
                search.get(current_search,
                           self.__cancellable,
                           callback=(self.__on_search_get, current_search))
            elif state == "web":
                App().task_helper.run(App().spotify.search,
                                      current_search,
                                      self.__cancellable)
        else:
            self.__stack.set_visible_child_name("placeholder")
            self.__set_default_placeholder()
            self.__header_stack.set_visible_child(self.__new_button)
            GLib.idle_add(self.__spinner.stop)

    def __search_to_playlist(self):
        """
            Create a new playlist based on search
        """
        tracks = []
        for child in self.__view.children:
            tracks += child.album.tracks
        if tracks:
            playlist_id = App().playlists.get_id(self.__current_search)
            if playlist_id == Type.NONE:
                App().playlists.add(self.__current_search)
                playlist_id = App().playlists.get_id(self.__current_search)
            App().playlists.add_tracks(playlist_id, tracks)
        GLib.idle_add(self.__show_playlist, playlist_id)

    def __show_playlist(self, playlist_id):
        """
            Hide if in a popover and show playlist
        """
        if App().settings.get_value("show-sidebar"):
            App().window.container.show_lists([Type.PLAYLISTS],
                                              [playlist_id])
        else:
            App().window.container.show_view(Type.PLAYLISTS, [playlist_id])
        popover = self.get_ancestor(Gtk.Popover)
        if popover is not None:
            popover.hide()
        else:
            self.destroy()

    def __on_search_get(self, result, search):
        """
            Add rows for internal results
            @param result as [(int, Album, bool)]
        """
        self.__on_search_finished(None, search)
        if result:
            albums = []
            reveal_albums = []
            for (album, in_tracks) in result:
                albums.append(album)
                if in_tracks:
                    reveal_albums.append(album.id)
            self.__view.set_reveal(reveal_albums)
            self.__view.populate(albums)
            self.__stack.set_visible_child_name("view")

    def __on_map(self, widget):
        """
            Init signals and grab focus
            @param widget as Gtk.Widget
        """
        App().spotify.connect("new-album", self.__on_new_spotify_album)
        App().spotify.connect("search-finished", self.__on_search_finished)
        GLib.idle_add(self.__entry.grab_focus)

    def __on_unmap(self, widget):
        """
            Clean up
            @param widget as Gtk.Widget
        """
        App().spotify.disconnect_by_func(self.__on_new_spotify_album)
        App().spotify.disconnect_by_func(self.__on_search_finished)
        self.__cancellable.cancel()
        self.__view.stop()
        self.__header_stack.set_visible_child(self.__new_button)
        self.__spinner.stop()

    def __on_new_spotify_album(self, spotify, album):
        """
            Add album
            @param spotify as SpotifyHelper
            @param albumas Album
        """
        self.__view.add_album(album, len(album.tracks) == 1)
        self.__stack.set_visible_child_name("view")

    def __on_search_finished(self, api, search):
        """
            Stop spinner
            @param api ignored
            @param search as str
        """
        if self.__current_search != search:
            return
        self.__spinner.stop()
        self.__header_stack.set_visible_child(self.__new_button)
        if not self.__view.children:
            self.__stack.set_visible_child_name("placeholder")
            self.__set_no_result_placeholder()

    def __on_search_changed_timeout(self):
        """
            Populate widget
        """
        if self.__view.children:
            self.__view.stop()
            self.__view.clear()
            return True
        self.__timeout_id = None
        self.__populate()
        if self.__current_search != "":
            self.__new_button.set_sensitive(True)
        else:
            self.__new_button.set_sensitive(False)

    def __on_search_action_change_state(self, action, value):
        """
            Update action value
            @param action as Gio.SimpleAction
            @param value as GLib.Variant
        """
        def delayed_action(state):
            self.__cancellable.reset()
            if state == "local":
                self.__new_button.show()
                self.__header_stack.set_visible_child(self.__new_button)
            else:
                self.__new_button.hide()
            if state == "charts":
                self.__entry.set_sensitive(False)
                self.__entry.set_opacity(0)
                self.__play_button.set_sensitive(True)
                self.__header_stack.set_visible_child(self.__spinner)
                self.__history = []
                self.__spinner.start()
                self.__stack.set_visible_child_name("view")
                App().task_helper.run(App().spotify.charts,
                                      self.__cancellable)
            else:
                self.__entry.set_opacity(1)
                self.__entry.set_sensitive(True)
                self.__populate()
                GLib.idle_add(self.__entry.grab_focus)
        self.__cancellable.cancel()
        self.__view.stop()
        self.__view.clear()
        action.set_state(value)
        state = value.get_string()
        # Let cancellable cancel
        GLib.timeout_add(500, delayed_action, state)
