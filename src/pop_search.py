# Copyright (c) 2014-2016 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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
from cgi import escape
from threading import Thread
from shutil import which

from lollypop.define import Lp, ArtSize, Type, DbPersistent
from lollypop.objects import Track, Album
from lollypop.pop_menu import TrackMenuPopover, TrackMenu
from lollypop.pop_album import AlbumPopover
from lollypop.search_item import SearchItem
from lollypop.search_network import NetworkSearch
from lollypop.youtube import Youtube


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
        builder = Gtk.Builder()
        if internal:
            builder.add_from_resource(
                                    '/org/gnome/Lollypop/InternalSearchRow.ui')
        else:
            builder.add_from_resource(
                                    '/org/gnome/Lollypop/ExternalSearchRow.ui')
        builder.connect_signals(self)
        self.set_property('has-tooltip', True)
        self.connect('query-tooltip', self.__on_query_tooltip)
        self.__row_widget = builder.get_object('row')
        self.__row_widget.set_margin_top(2)
        self.__row_widget.set_margin_end(2)
        self.__artist = builder.get_object('artist')
        self.__name = builder.get_object('item')
        self.__cover = builder.get_object('cover')
        self.add(self.__row_widget)
        self.__init()

    @property
    def id(self):
        """
            Return row id
            @return int
        """
        return self.__item.id

    @property
    def artist_ids(self):
        """
            Return row artist ids
            @return artist ids as [int]
        """
        return self.__item.artist_ids

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
            if item.is_track and self.__is_track:
                if item.id == self.__id:
                    found = True
                    break
            elif not item.is_track and not self.__is_track:
                if item.id == self.__id:
                    found = True
                    break
        return found

    def play(self):
        """
            Play row
        """
        yt = Youtube()
        if self.__item.is_track:
            yt.save_track(self.__item, DbPersistent.NONE)
        else:
            yt.save_album(self.__item, DbPersistent.NONE)

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

#######################
# PROTECTED           #
#######################
    def _on_save_clicked(self, button):
        """
            Save into collection
            @param button as Gtk.Button
        """
        yt = Youtube()
        if self.__item.is_track:
            yt.save_track(self.__item, DbPersistent.EXTERNAL)
        else:
            yt.save_album(self.__item, DbPersistent.EXTERNAL)
        self.destroy()

    def _on_playlist_clicked(self, button):
        """
            Prepend track to queue
            @param button as Gtk.Button
        """
        Lp().window.show_playlist_manager(self.__id, [], [],
                                          not self.__is_track)

    def _on_queue_clicked(self, button):
        """
            Add track to queue
            @param button as Gtk.Button
        """
        if self.__item.is_track:
            Lp().player.append_to_queue(self.__id)
        else:
            for track in Lp().albums.get_track_ids(self.__id, [], []):
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
            surface = Lp().art.get_default_icon('emblem-music-symbolic',
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
            artist = escape(self.__artist.get_text())
            title = escape(self.__name.get_text())
            self.set_tooltip_markup("<b>%s</b>\n%s" % (artist, title))
        else:
            self.set_tooltip_text('')


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
        self.connect('map', self.__on_map)
        self.connect('unmap', self.__on_unmap)
        self.__in_thread = False
        self.__stop_thread = False
        self.__timeout = None
        self.__current_search = ''
        self.__search = None

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/SearchPopover.ui')
        builder.connect_signals(self)

        self.__new_btn = builder.get_object('new_btn')

        self.__view = Gtk.ListBox()
        self.__view.connect("button-press-event", self.__on_button_press)
        self.__view.connect("row-activated", self.__on_row_activated)
        self.__view.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.__view.set_activate_on_single_click(True)
        self.__view.show()

        self.__spinner = builder.get_object('spinner')
        self.__stack = builder.get_object('stack')

        switch = builder.get_object('search-switch')
        if which("youtube-dl") is None:
            switch.set_sensitive(False)
            switch.set_tooltip_text(_("You need to install youtube-dl"))
        else:
            switch.set_state(Lp().settings.get_value('network-search'))
        builder.get_object('scrolled').add(self.__view)
        self.add(builder.get_object('widget'))

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
        if self.__in_thread:
            self.__stop_thread = True
            self.__reset_search()
            self.__stack.set_visible_child(self.__new_btn)
            self.__spinner.stop()
            GLib.timeout_add(100, self._on_search_changed, widget)

        if self.__timeout:
            GLib.source_remove(self.__timeout)
            self.__timeout = None

        self.__current_search = widget.get_text().strip()
        if self.__current_search != "":
            self.__new_btn.set_sensitive(True)
            self.__timeout = GLib.timeout_add(100,
                                              self.__on_search_changed_thread)
        else:
            self.__reset_search()
            self.__stack.set_visible_child(self.__new_btn)
            self.__spinner.stop()
            self.__new_btn.set_sensitive(False)
            for child in self.__view.get_children():
                GLib.idle_add(child.destroy)

    def _on_state_set(self, switch, state):
        """
            Save state
            @param switch as Gtk.switch
            @param state as bool
        """
        Lp().settings.set_boolean('network-search', state)

#######################
# PRIVATE             #
#######################
    def __clear(self):
        """
            Clear search view
            @warning not thread safe
        """
        for child in self.__view.get_children():
            child.destroy()

    def __populate(self):
        """
            Populate searching items
            in db based on text entry current text
        """
        GLib.idle_add(self.__clear)

        # Network Search
        t = Thread(target=self.__network_search)
        t.daemon = True
        t.start()

        # Local search
        results = []
        added_album_ids = []
        added_track_ids = []
        search_items = [self.__current_search]
        # search_items += self.__current_search.split()
        for item in search_items:
            albums = []
            tracks_non_album_artist = []
            # Get all albums for all artists and non album_artist tracks
            for artist_id in Lp().artists.search(item):
                for album_id in Lp().albums.get_ids([artist_id], []):
                    if (album_id, artist_id) not in albums:
                        albums.append((album_id, artist_id))
                for track_id, track_name in Lp(
                                   ).tracks.get_as_non_album_artist(artist_id):
                    tracks_non_album_artist.append((track_id, track_name))

            for album_id, artist_id in albums:
                if album_id in added_album_ids:
                    continue
                search_item = SearchItem()
                search_item.id = album_id
                added_album_ids.append(album_id)
                search_item.is_track = False
                search_item.artist_ids = [artist_id]
                results.append(search_item)

            albums = Lp().albums.search(item)
            for album_id in albums:
                if album_id in added_album_ids:
                    continue
                search_item = SearchItem()
                search_item.id = album_id
                added_album_ids.append(album_id)
                search_item.is_track = False
                search_item.artist_ids = Lp().albums.get_artist_ids(album_id)
                results.append(search_item)

            for track_id, track_name in Lp().tracks.search(
                                               item) + tracks_non_album_artist:
                if track_id in added_track_ids:
                    continue
                search_item = SearchItem()
                search_item.id = track_id
                added_track_ids.append(track_id)
                search_item.is_track = True
                search_item.artist_ids = Lp().tracks.get_artist_ids(track_id)
                results.append(search_item)
        if not self.__stop_thread:
            GLib.idle_add(self.__add_rows_internal, results)
        else:
            self.__in_thread = False
            self.__stop_thread = False
            if not self.__need_network_search():
                self.__stack.set_visible_child(self.__new_btn)
                self.__spinner.stop()

    def __network_search(self):
        """
            Search on network
        """
        if self.__need_network_search():
            self.__search.do(self.__current_search)

    def __add_rows_internal(self, results):
        """
            Add rows for internal results
            @param results as array of SearchItem
        """
        if results:
            result = results.pop(0)
            search_row = SearchRow(result)
            search_row.show()
            self.__view.add(search_row)
            if self.__stop_thread:
                self.__in_thread = False
                self.__stop_thread = False
            else:
                GLib.idle_add(self.__add_rows_internal, results)
        else:
            self.__in_thread = False
            self.__stop_thread = False
            if not self.__need_network_search():
                self.__stack.set_visible_child(self.__new_btn)
                self.__spinner.stop()

    def __download_cover(self, uri, row):
        """
            Download row covers
            @param uri as str
            @param row as SearchRow
        """
        try:
            f = Gio.File.new_for_uri(uri)
            (status, data, tag) = f.load_contents(None)
            if status:
                stream = Gio.MemoryInputStream.new_from_data(data,
                                                             None)
                pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(
                                                   stream,
                                                   ArtSize.MEDIUM,
                                                   -1,
                                                   True,
                                                   None)
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

    def __play_search(self, object_id=None, is_track=True):
        """
            Play tracks based on search
            @param started object id as int
            @param is track as bool
        """
        track_ids = []
        track_id = None
        for child in self.__view.get_children():
            if child.is_track:
                track_ids.append(child.id)
            else:
                album_tracks = Lp().albums.get_track_ids(child.id)
                if not is_track and child.id == object_id and\
                        album_tracks:
                    track_id = album_tracks[0]
                for tid in album_tracks:
                    track_ids.append(tid)
        if track_ids:
            if object_id is not None and is_track:
                track_id = object_id
            elif track_id is None:
                track_id = track_ids[0]
            GLib.idle_add(self.__populate_user_playlist_by_tracks,
                          track_ids, track_id)

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
        if self.__search is not None:
            self.__search.disconnect_by_func(self.__on_item_found)
            self.__search.stop()
            self.__search = None

    def __need_network_search(self):
        """
            Return True if network search needed
            @return True
        """
        return Lp().settings.get_value('network-search') and\
            which("youtube-dl") is not None

    def __item_exists_in_db(self, item):
        """
            Search if item exists in db
            @return bool
        """
        artist_ids = []
        for artist in item.artists:
            artist_id = Lp().artists.get_id(artist)
            artist_ids.append(artist_id)
        if item.is_track:
            for track_id in Lp().tracks.get_ids_for_name(item.name):
                db_artist_ids = Lp().tracks.get_artist_ids(track_id)
                union = list(set(artist_ids) & set(db_artist_ids))
                if union == db_artist_ids:
                    return True
        else:
            album_ids = Lp().albums.get_ids(artist_ids, [])
            for album_id in album_ids:
                album_name = Lp().albums.get_name(album_id)
                if album_name == item.album_name:
                    return True
        return False

    def __on_item_found(self, search):
        """
            Add rows for internal results
            @param search as NetworkSearch
        """
        if self.__search != search:
            return
        if search.finished:
            self.__stack.set_visible_child(self.__new_btn)
            self.__spinner.stop()
        if not search.items:
            return
        item = search.items.pop(0)
        if self.__item_exists_in_db(item):
            return
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
        # FIXME Not needed with GTK >= 3.18
        Lp().window.enable_global_shorcuts(False)
        height = Lp().window.get_size()[1]
        self.set_size_request(400, height*0.7)

    def __on_unmap(self, widget):
        """
            Enable global shortcuts
            @param widget as Gtk.Widget
        """
        # FIXME Not needed with GTK >= 3.18
        Lp().window.enable_global_shorcuts(True)
        self.__reset_search()
        self.__stack.set_visible_child(self.__new_btn)
        self.__spinner.stop()

    def __on_search_changed_thread(self):
        """
            Populate widget
        """
        self.__timeout = None
        self.__in_thread = True
        self.__search = NetworkSearch()
        self.__search.connect('item-found', self.__on_item_found)
        self.__stack.set_visible_child(self.__spinner)
        self.__spinner.start()
        t = Thread(target=self.__populate)
        t.daemon = True
        t.start()

    def __on_row_activated(self, widget, row):
        """
            Play searched item when selected
            @param widget as Gtk.ListBox
            @param row as SearchRow
        """
        if Lp().player.is_party or Lp().player.locked:
            # External track/album
            if row.id is None:
                pass
            elif row.is_track:
                if Lp().player.locked:
                    if row.id in Lp().player.get_queue():
                        Lp().player.del_from_queue(row.id)
                    else:
                        Lp().player.append_to_queue(row.id)
                    row.destroy()
                else:
                    Lp().player.load(Track(row.id))
            elif Gtk.get_minor_version() > 16:
                popover = AlbumPopover(row.id, [], [])
                popover.set_relative_to(row)
                popover.show()
            else:
                t = Thread(target=self.__play_search, args=(row.id,
                                                            row.is_track))
                t.daemon = True
                t.start()
        else:
            if row.id is None:
                row.play()
            else:
                t = Thread(target=self.__play_search, args=(row.id,
                                                            row.is_track))
                t.daemon = True
                t.start()

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
                popover = TrackMenuPopover(row.id,
                                           TrackMenu(row.id))
                popover.set_relative_to(widget)
                popover.set_pointing_to(rect)
                popover.show()
            else:
                popover = AlbumPopover(row.id, [],
                                       row.artist_ids())
                popover.set_relative_to(widget)
                popover.set_pointing_to(rect)
                popover.show()
