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

from gi.repository import Gtk, GLib, Gio, Gdk, GdkPixbuf

from gettext import gettext as _
from threading import Thread

from lollypop.define import Lp, ArtSize, Type, DbPersistent
from lollypop.objects import Track, Album
from lollypop.pop_menu import TrackMenuPopover, TrackMenu
from lollypop.view_albums import AlbumBackView
from lollypop.utils import noaccents, get_network_available
from lollypop.lio import Lio


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
        self.__uri_set = False
        self.__score = None
        builder = Gtk.Builder()
        if internal:
            builder.add_from_resource(
                                    "/org/gnome/Lollypop/InternalSearchRow.ui")
            self.__progress = None
        else:
            builder.add_from_resource(
                                    "/org/gnome/Lollypop/ExternalSearchRow.ui")
            self.__progress = builder.get_object("progress")
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
        del pixbuf
        self.__cover.set_from_surface(surface)
        del surface

    @property
    def is_loading(self):
        """
            True if is loading a track/album
            @return bool
        """
        return self.__progress is not None and\
            self.__progress.get_opacity() == 1

    def on_activated(self, persistent):
        """
            Download item
            @param persistent as DbPersistent
        """
        from lollypop.web import Web
        web = Web()
        web.connect("saved", self.__on_saved, persistent)
        if self.__item.is_track:
            web.save_track(self.__item, persistent)
        else:
            web.save_album(self.__item, persistent)
            if self.__progress is not None:
                self.__progress.set_opacity(1)
            web.connect("progress", self.__on_progress)
        self.__stack.set_visible_child_name("spinner")
        self.__stack.get_visible_child().start()

#######################
# PROTECTED           #
#######################
    def _on_save_clicked(self, button):
        """
            Save into collection
            @param button as Gtk.Button
        """
        self.on_activated(DbPersistent.EXTERNAL)

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
        del surface
        self.__artist.set_text(", ".join(artists))

    def __on_saved(self, web, item_id, persistent):
        """
            Play track
            @param web as Web
            @param item id as int
            @parma activated as DbPersistent
        """
        if self.__progress is not None:
            self.__progress.set_opacity(0)
        self.__item.id = item_id
        if persistent == DbPersistent.NONE:
            if self.__item.is_track:
                Lp().player.emit("loading-changed", True)
            self.emit("activate")
        # If no visible widget in stack, self destroyed
        visible = self.__stack.get_visible_child()
        if visible is not None:
            visible.stop()
            self.__stack.set_visible_child_name("save")
            self.__stack.get_visible_child().set_sensitive(False)

    def __on_progress(self, web, progress):
        """
            Update progress bar
            @param web as Web
            @param progress as float
        """
        if self.__progress is not None:
            self.__progress.set_fraction(progress)

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
        self.__timeout = None
        self.__current_search = ""
        self.__nsearch = None
        self.__lsearch = None
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

        self.__switch = builder.get_object("search-switch")
        if GLib.find_program_in_path("youtube-dl") is None:
            self.__switch.set_tooltip_text(_("You need to install youtube-dl"))
        else:
            self.__switch.set_state(Lp().settings.get_value("network-search"))

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
        t = Thread(target=self.__new_playlist)
        t.daemon = True
        t.start()

    def _on_search_changed(self, widget):
        """
            Timeout filtering
            @param widget as Gtk.TextEntry
        """
        self.__reset_search()
        if self.__timeout:
            GLib.source_remove(self.__timeout)
            self.__timeout = None

        self.__current_search = widget.get_text().strip()
        if self.__current_search != "":
            self.__new_btn.set_sensitive(True)
            self.__timeout = GLib.timeout_add(500,
                                              self.__on_search_changed_thread)
        else:
            self.__new_btn.set_sensitive(False)

    def _on_state_set(self, switch, state):
        """
            Save state
            @param switch as Gtk.switch
            @param state as bool
        """
        Lp().settings.set_boolean("network-search", state)
        GLib.idle_add(self._on_search_changed, self.__entry)

#######################
# PRIVATE             #
#######################
    def __enable_network_search(self):
        """
            True if shoud enable network search
            @return bool
        """
        return GLib.find_program_in_path("youtube-dl") is not None and\
            get_network_available()

    def __calculate_score(self, row):
        """
            Calculate score for row
            @param row as SearchRow
        """
        if row.score is not None:
            return
        # Network search score less
        if row.id is None:
            score = 0
            artists = row.artists
        else:
            score = 1
            artists = []
            for artist_id in row.artist_ids:
                artists.append(Lp().artists.get_name(artist_id))

        for item in self.__current_search.split():
            try:
                year = int(item)
                if year == int(row.year):
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

    def __clear(self, rows):
        """
            Clear search view
            @param items as [SearchRow]
            @warning not thread safe
        """
        if rows:
            row = rows.pop(0)
            self.__view.remove(row)
            row.destroy()
            GLib.idle_add(self.__clear, rows)

    def __populate(self):
        """
            Populate searching items
            in db based on text entry current text
        """
        self.__header_stack.set_visible_child(self.__spinner)
        self.__spinner.start()
        self.__history = []
        # Network Search
        if self.__need_network_search():
            t = Thread(target=self.__nsearch.do, args=(self.__current_search,))
            t.daemon = True
            t.start()

        # Local Search
        search_items = [self.__current_search]
        for item in self.__current_search.split():
            if len(item) >= 3:
                search_items.append(item)
        GLib.idle_add(self.__clear, self.__view.get_children())
        t = Thread(target=self.__lsearch.do, args=(search_items,))
        t.daemon = True
        t.start()

    def __download_cover(self, uri, row):
        """
            Download row covers
            @param uri as str
            @param row as SearchRow
        """
        try:
            f = Lio.File.new_for_uri(uri)
            (status, data, tag) = f.load_contents(None)
            if status:
                bytes = GLib.Bytes(data)
                stream = Gio.MemoryInputStream.new_from_bytes(bytes)
                bytes.unref()
                pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(
                                                   stream,
                                                   ArtSize.MEDIUM,
                                                   -1,
                                                   True,
                                                   None)
                stream.close()
                GLib.idle_add(row.set_cover, pixbuf)
        except:
            pass

    def __populate_user_playlist_by_tracks(self, track_ids, track_id):
        """
            Set user playlist
            @param track_ids as [int]
            @param track id as int
            @thread safe
        """
        Lp().player.load(Track(track_id))
        Lp().player.populate_user_playlist_by_tracks(track_ids, [Type.SEARCH])

    def __new_playlist(self):
        """
            Create a new playlist based on search
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

    def __reset_search(self):
        """
            Reset search object
        """
        self.__header_stack.set_visible_child(self.__new_btn)
        self.__spinner.stop()
        if self.__nsearch is not None:
            self.__nsearch.disconnect_by_func(self.__on_network_item_found)
            self.__nsearch.stop()
            self.__nsearch = None
        if self.__lsearch is not None:
            self.__lsearch.disconnect_by_func(self.__on_local_item_found)
            self.__lsearch.stop()
            self.__lsearch = None

    def __need_network_search(self):
        """
            Return True if network search needed
            @return True
        """
        return Lp().settings.get_value("network-search") and\
            GLib.find_program_in_path("youtube-dl") is not None

    def __on_local_item_found(self, search):
        """
            Add rows for internal results
            @param search as LocalSearch
        """
        if self.__lsearch != search:
            return
        if not search.items:
            if self.__lsearch.finished and\
                    (self.__nsearch is None or self.__nsearch.finished):
                self.__header_stack.set_visible_child(self.__new_btn)
                self.__spinner.stop()
            return
        item = search.items.pop(0)
        search_row = SearchRow(item)
        search_row.show()
        self.__view.add(search_row)

    def __on_network_item_found(self, search):
        """
            Add rows for internal results
            @param search as NetworkSearch
        """
        if self.__nsearch != search:
            return
        if not search.items:
            if self.__nsearch.finished and self.__lsearch.finished:
                self.__header_stack.set_visible_child(self.__new_btn)
                self.__spinner.stop()
            return
        item = search.items.pop(0)
        if item.exists_in_db()[0]:
            return
        if item.is_track:
            history = "♫" + item.name + item.artists[0]
        else:
            history = item.name + item.artists[0]
        if history.lower() not in self.__history:
            self.__history.append(history.lower())
            search_row = SearchRow(item, False)
            search_row.show()
            self.__view.add(search_row)
            t = Thread(target=self.__download_cover,
                       args=(item.smallcover, search_row))
            t.daemon = True
            t.start()

    def __on_map(self, widget):
        """
            Disable global shortcuts and resize
            @param widget as Gtk.Widget
        """
        self.__switch.set_sensitive(self.__enable_network_search())
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
        self.__reset_search()
        self.__header_stack.set_visible_child(self.__new_btn)
        self.__spinner.stop()

    def __on_search_changed_thread(self):
        """
            Populate widget
        """
        self.__reset_search()
        from lollypop.search_local import LocalSearch
        from lollypop.search_network import NetworkSearch
        self.__timeout = None
        self.__lsearch = LocalSearch()
        self.__lsearch.connect("item-found", self.__on_local_item_found)
        if self.__need_network_search():
            self.__nsearch = NetworkSearch()
            self.__nsearch.connect("item-found", self.__on_network_item_found)
        self.__populate()

    def __on_row_activated(self, widget, row):
        """
            Play searched item when selected
            @param widget as Gtk.ListBox
            @param row as SearchRow
        """
        if row.is_loading:
            return
        if row.id is None:
            row.on_activated(DbPersistent.NONE)
        elif row.is_track:
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
