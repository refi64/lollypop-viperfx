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

from lollypop.define import App, ResponsiveType, Type
from lollypop.helper_task import TaskHelper
from lollypop.view_albums_list import AlbumsListView
from lollypop.search import Search


class SearchPopover(Gtk.Popover):
    """
        Popover allowing user to search for tracks/albums
    """

    def __init__(self):
        """
            Init Popover
        """
        Gtk.Popover.__init__(self)
        self.set_position(Gtk.PositionType.BOTTOM)
        self.connect("map", self.__on_map)
        self.connect("unmap", self.__on_unmap)
        self.__timeout_id = None
        self.__current_search = ""
        self.__cancellable = Gio.Cancellable()
        self.__history = []

        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/SearchPopover.ui")
        self.__widget = builder.get_object("widget")
        self.__new_btn = builder.get_object("new_btn")
        self.__entry = builder.get_object("entry")

        self.__spinner = builder.get_object("spinner")
        self.__header_stack = builder.get_object("stack")

        # Connect here because we don"t want previous switch.set_state()
        # to emit a signal on init
        builder.connect_signals(self)

        self.__view = AlbumsListView(ResponsiveType.SEARCH)
        self.__view.show()
        self.__widget.attach(self.__view, 0, 1, 2, 1)

        self.add(self.__widget)

    def set_text(self, text):
        """
            Set search text
        """
        self.__entry.set_text(text)

#######################
# PROTECTED           #
#######################
    def _on_new_btn_clicked(self, button):
        """
            Create a new playlist based on search
            @param button as Gtk.Button
        """
        button.set_sensitive(False)
        helper = TaskHelper()
        helper.run(self.__search_to_playlist)

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
        if self.__current_search != "":
            self.__new_btn.set_sensitive(True)
            self.__timeout_id = GLib.timeout_add(
                                              500,
                                              self.__on_search_changed_timeout)
        else:
            self.__new_btn.set_sensitive(False)

#######################
# PRIVATE             #
#######################
    def __populate(self):
        """
            Populate searching items
            in db based on text entry current text
        """
        self.__cancellable.reset()
        self.__header_stack.set_visible_child(self.__spinner)
        self.__spinner.start()
        self.__history = []
        search = Search()
        search.get(self.__current_search,
                   self.__cancellable,
                   callback=(self.__on_search_get,))

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

    def __on_search_get(self, albums):
        """
            Add rows for internal results
            @param albums as [Album]
        """
        if albums is not None:
            self.__view.populate(albums)
            self.__header_stack.set_visible_child(self.__new_btn)
        GLib.idle_add(self.__spinner.stop)

    def __on_map(self, widget):
        """
            Disable global shortcuts and resize
            @param widget as Gtk.Widget
        """
        # FIXME Not needed with GTK >= 3.18
        App().window.enable_global_shortcuts(False)
        height = App().window.get_size()[1]
        self.set_size_request(450, height*0.7)

    def __on_unmap(self, widget):
        """
            Enable global shortcuts
            @param widget as Gtk.Widget
        """
        # FIXME Not needed with GTK >= 3.18
        App().window.enable_global_shortcuts(True)
        self.__cancellable.cancel()
        self.__view.stop()
        self.__header_stack.set_visible_child(self.__new_btn)
        self.__spinner.stop()

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
