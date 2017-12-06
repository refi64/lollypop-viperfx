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

from gi.repository import Gtk, GLib, Gio, Gdk

from lollypop.define import Lp, ArtSize, Type
from lollypop.objects import Track, Album
from lollypop.pop_menu import TrackMenuPopover, TrackMenu
from lollypop.view_albums import AlbumBackView
from lollypop.utils import noaccents
from lollypop.helper_task import TaskHelper
from lollypop.search import Search


class SearchRow(Gtk.ListBoxRow):
    """
        Album/Track search row
    """

    def __init__(self, item, internal=True):
        """
            Init row widgets
            @param item as SearchItem
            @param internal as bool
        """
        Gtk.ListBoxRow.__init__(self)
        self.__item = item
        self.__score = None
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/SearchRow.ui")
        self.__stack = builder.get_object("stack")
        builder.connect_signals(self)
        self.set_property("has-tooltip", True)
        self.connect("query-tooltip", self.__on_query_tooltip)
        self.__row_widget = builder.get_object("row")
        self.__row_widget.set_margin_top(2)
        self.__row_widget.set_margin_end(2)
        self.__artist = builder.get_object("artist")
        self.__name = builder.get_object("item")
        self.__cover = builder.get_object("cover")
        self.add(self.__row_widget)
        self.__init()

    @property
    def id(self):
        """
            Get row id
            @return int
        """
        return self.__item.id

    @property
    def score(self):
        """
            Get row score
            @return int
        """
        return self.__score

    @property
    def name(self):
        """
            Get row name
            @return str
        """
        return self.__name.get_text()

    @property
    def year(self):
        """
            Get year
            @return int
        """
        return self.__item.year

    @property
    def artist_ids(self):
        """
            Return row artist ids
            @return artist ids as [int]
        """
        return self.__item.artist_ids

    @property
    def artists(self):
        """
            Return row artist ids
            @return artist ids as [int]
        """
        return self.__item.artists

    @property
    def is_track(self):
        """
            True if a track
            @return bool
        """
        return self.__item.is_track

    def exists(self, items):
        """
            Return True if self exists in items
            @param: items as array of SearchItem
        """
        found = False
        for item in items:
            if item.is_track and self.__item.is_track:
                if item.id == self.__id:
                    found = True
                    break
            elif not item.is_track and not self.__item.is_track:
                if item.id == self.__id:
                    found = True
                    break
        return found

    def set_score(self, score):
        """
            Set score
            @param score as int
        """
        self.__score = score

    def set_cover(self, pixbuf):
        """
            Set cover
            @param pixbuf as GdkPixbuf.Pixbuf
        """
        surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf,
                                                       self.get_scale_factor(),
                                                       None)
        self.__cover.set_from_surface(surface)

#######################
# PROTECTED           #
#######################
    def _on_artist_label_realize(self, eventbox):
        """
            Change cursor on label
            @param eventbox as Gtk.EventBox
        """
        eventbox.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))

    def _on_artist_label_button_press_event(self, eventbox, event):
        """
            Jump to artist
            @param eventbox as Gtk.EventBox
            @param event as Gdk.Event
        """
        Lp().window.show_artists_albums(self.__item.artist_ids)
        self.get_ancestor(Gtk.Popover).popdown()
        return True

    def _on_playlist_clicked(self, button):
        """
            Prepend track to queue
            @param button as Gtk.Button
        """
        Lp().window.show_playlist_manager(self.__item.id, [], [],
                                          not self.__item.is_track)

    def _on_queue_clicked(self, button):
        """
            Add track to queue
            @param button as Gtk.Button
        """
        if self.__item.is_track:
            Lp().player.append_to_queue(self.__item.id)
        else:
            for track in Lp().albums.get_track_ids(self.__item.id, [], []):
                Lp().player.append_to_queue(track)
        button.set_sensitive(False)
        button.set_opacity(0.4)

#######################
# PRIVATE             #
#######################
    def __init(self):
        """
            Init row
        """
        artists = []
        if self.__item.is_track:
            obj = Track(self.__item.id)
            album_id = obj.album_id
        else:
            obj = Album(self.__item.id)
            album_id = obj.id

        if self.__item.id is None:
            if self.__item.is_track:
                self.__name.set_text("♫ " + self.__item.name)
            else:
                self.__name.set_text(self.__item.name)
            artists = self.__item.artists
            surface = Lp().art.get_default_icon("emblem-music-symbolic",
                                                ArtSize.MEDIUM,
                                                self.get_scale_factor())
        else:
            if self.__item.is_track:
                self.__name.set_text("♫ " + Track(self.__item.id).name)
            else:
                self.__name.set_text(Album(self.__item.id).name)
            for artist_id in self.__item.artist_ids:
                artists.append(Lp().artists.get_name(artist_id))
            surface = Lp().art.get_album_artwork(Album(album_id),
                                                 ArtSize.MEDIUM,
                                                 self.get_scale_factor())
        self.__cover.set_from_surface(surface)
        self.__artist.set_text(", ".join(artists))

    def __on_query_tooltip(self, widget, x, y, keyboard, tooltip):
        """
            Show tooltip if needed
            @param widget as Gtk.Widget
            @param x as int
            @param y as int
            @param keyboard as bool
            @param tooltip as Gtk.Tooltip
        """
        layout_title = self.__name.get_layout()
        layout_artist = self.__artist.get_layout()
        if layout_title.is_ellipsized() or layout_artist.is_ellipsized():
            artist = GLib.markup_escape_text(self.__artist.get_text())
            title = GLib.markup_escape_text(self.__name.get_text())
            self.set_tooltip_markup("<b>%s</b>\n%s" % (artist, title))
        else:
            self.set_tooltip_text("")


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

        self.__new_btn = builder.get_object("new_btn")
        self.__entry = builder.get_object("entry")

        self.__view = Gtk.ListBox()
        self.__view.set_sort_func(self.__sort_func)
        self.__view.connect("button-press-event", self.__on_button_press)
        self.__view.connect("row-activated", self.__on_row_activated)
        self.__view.set_selection_mode(Gtk.SelectionMode.NONE)
        self.__view.set_activate_on_single_click(True)
        self.__view.show()

        self.__spinner = builder.get_object("spinner")
        self.__header_stack = builder.get_object("stack")

        self.__scrolled = builder.get_object("scrolled")
        self.__scrolled.add(self.__view)
        # Connect here because we don"t want previous switch.set_state()
        # to emit a signal on init
        builder.connect_signals(self)

        self.__stack = Gtk.Stack()
        self.__stack.set_transition_duration(250)
        self.__stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.__stack.show()
        self.__stack.add_named(builder.get_object("widget"), "search")
        self.add(self.__stack)

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
        helper = TaskHelper()
        helper.run(self.__new_playlist)

    def _on_search_changed(self, widget):
        """
            Timeout filtering
            @param widget as Gtk.TextEntry
        """
        self.__cancellable.reset()
        if self.__timeout_id:
            GLib.source_remove(self.__timeout_id)
            self.__timeout_id = None

        self.__current_search = widget.get_text().strip()
        if self.__current_search != "":
            self.__new_btn.set_sensitive(True)
            self.__timeout_id = GLib.timeout_add(
                                              200,
                                              self.__on_search_changed_timeout)
        else:
            self.__new_btn.set_sensitive(False)

#######################
# PRIVATE             #
#######################
    def __calculate_score(self, row):
        """
            Calculate score for row
            @param row as SearchRow
        """
        if row.score is not None:
            return
        score = 0
        artists = []
        for artist_id in row.artist_ids:
            artists.append(Lp().artists.get_name(artist_id))

        for item in self.__current_search.split():
            try:
                year = int(item)
                if year == row.year:
                    score += 2
            except:
                pass
            for artist in artists:
                if noaccents(artist.lower()).find(
                                                noaccents(item).lower()) != -1:
                    score += 2
                    if not row.is_track:
                        score += 1
            if noaccents(row.name).lower().find(
                                                noaccents(item).lower()) != -1:
                score += 1
                if row.is_track:
                    score += 1
        row.set_score(score)

    def __sort_func(self, row1, row2):
        """
            Sort rows
            @param row as SearchRow
            @param row as SearchRow
        """
        self.__calculate_score(row1)
        self.__calculate_score(row2)
        return row1.score < row2.score

    def __clear(self):
        """
            Clear view
        """
        self.__view.forall(lambda x: self.__view.remove(x))

    def __populate(self):
        """
            Populate searching items
            in db based on text entry current text
        """
        self.__clear()
        self.__header_stack.set_visible_child(self.__spinner)
        self.__spinner.start()
        self.__history = []
        search_items = [self.__current_search]
        for item in self.__current_search.split():
            if len(item) >= 3 and item not in search_items:
                search_items.append(item)
        search = Search()
        search.get(search_items,
                   self.__cancellable,
                   callback=(self.__on_search_get,))

    def __new_playlist(self, params):
        """
            Create a new playlist based on search
            @params as ()
        """
        tracks = []
        for child in self.__view.get_children():
            if child.is_track:
                tracks.append(Track(child.id))
            else:
                for track_id in Lp().albums.get_track_ids(
                                                       child.id, [],
                                                       child.artist_ids):
                    tracks.append(Track(track_id))
        if tracks:
            playlist_id = Lp().playlists.get_id(self.__current_search)
            if playlist_id == Type.NONE:
                Lp().playlists.add(self.__current_search)
                playlist_id = Lp().playlists.get_id(self.__current_search)
            Lp().playlists.add_tracks(playlist_id, tracks)

    def __on_search_get(self, items):
        """
            Add rows for internal results
            @param items as [SearchItem]
        """
        if items:
            item = items.pop(0)
            search_row = SearchRow(item)
            search_row.show()
            self.__view.add(search_row)
            GLib.idle_add(self.__on_search_get, items)
        else:
            GLib.idle_add(self.__spinner.stop)
            GLib.idle_add(self.__header_stack.set_visible_child,
                          self.__new_btn)

    def __on_map(self, widget):
        """
            Disable global shortcuts and resize
            @param widget as Gtk.Widget
        """
        # FIXME Not needed with GTK >= 3.18
        Lp().window.enable_global_shortcuts(False)
        height = Lp().window.get_size()[1]
        self.set_size_request(450, height*0.7)

    def __on_unmap(self, widget):
        """
            Enable global shortcuts
            @param widget as Gtk.Widget
        """
        # FIXME Not needed with GTK >= 3.18
        Lp().window.enable_global_shortcuts(True)
        self.__cancellable.cancel()
        self.__header_stack.set_visible_child(self.__new_btn)
        self.__spinner.stop()

    def __on_search_changed_timeout(self):
        """
            Populate widget
        """
        self.__timeout_id = None
        self.__cancellable.cancel()
        self.__cancellable.reset()
        self.__populate()

    def __on_row_activated(self, widget, row):
        """
            Play searched item when selected
            @param widget as Gtk.ListBox
            @param row as SearchRow
        """
        if row.is_track:
            # Add to queue, and play (so remove from queue)
            # Allow us to not change user current playlist
            if not Lp().player.is_party:
                Lp().player.insert_in_queue(row.id, 0, False)
            Lp().player.load(Track(row.id))
        else:
            album_view = AlbumBackView(row.id, [], [])
            album_view.connect("back-clicked", self.__on_back_clicked)
            album_view.show()
            self.__stack.add(album_view)
            self.__stack.set_visible_child(album_view)

    def __on_back_clicked(self, view):
        """
            Show search
        """
        search = self.__stack.get_child_by_name("search")
        self.__stack.set_visible_child(search)
        GLib.timeout_add(5000, view.destroy)

    def __on_button_press(self, widget, event):
        """
            Store pressed button
            @param widget as Gtk.ListBox
            @param event as Gdk.EventButton
        """
        rect = widget.get_allocation()
        rect.x = event.x
        rect.y = event.y
        rect.width = rect.height = 1
        row = widget.get_row_at_y(event.y)
        # Internal track/album
        if event.button != 1 and row.id is not None:
            if row.is_track:
                track = Track(row.id)
                popover = TrackMenuPopover(track,
                                           TrackMenu(track))
                popover.set_relative_to(widget)
                popover.set_pointing_to(rect)
                popover.show()
