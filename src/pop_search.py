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
from lollypop.utils import noaccents


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
        from lollypop.youtube import Youtube
        Lp().player.emit('loading-changed')
        yt = Youtube()
        if self.__item.is_track:
            yt.save_track(self.__item, DbPersistent.NONE)
        else:
            yt.save_album(self.__item, DbPersistent.NONE)

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

#######################
# PROTECTED           #
#######################
    def _on_save_clicked(self, button):
        """
            Save into collection
            @param button as Gtk.Button
        """
        from lollypop.youtube import Youtube
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
        self.__timeout = None
        self.__current_search = ''
        self.__nsearch = None
        self.__lsearch = None
        self.__added_items = []

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/SearchPopover.ui')

        self.__new_btn = builder.get_object('new_btn')

        self.__view = Gtk.ListBox()
        self.__view.set_sort_func(self.__sort_func)
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
        # Connect here because we don't want previous switch.set_state()
        # to emit a signal on init
        builder.connect_signals(self)

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
            for child in self.__view.get_children():
                GLib.idle_add(child.destroy)

    def _on_state_set(self, switch, state):
        """
            Save state
            @param switch as Gtk.switch
            @param state as bool
        """
        Lp().settings.set_boolean('network-search', state)
        Lp().window.reload_view()
        if state:
            if Lp().charts is None:
                from lollypop.charts import Charts
                Lp().charts = Charts()
            Lp().charts.update()
        else:
            Lp().charts.stop()

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
            row.destroy()
            GLib.idle_add(self.__clear, rows)

    def __populate(self):
        """
            Populate searching items
            in db based on text entry current text
        """
        self.__added_items = []
        self.__stack.set_visible_child(self.__spinner)
        self.__spinner.start()

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
        self.__stack.set_visible_child(self.__new_btn)
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
        return Lp().settings.get_value('network-search') and\
            which("youtube-dl") is not None

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
                self.__stack.set_visible_child(self.__new_btn)
                self.__spinner.stop()
            return
        item = search.items.pop(0)
        if not (item.name, item.artists) in self.__added_items:
            search_row = SearchRow(item)
            search_row.show()
            self.__added_items.append((item.name, item.artists))
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
                self.__stack.set_visible_child(self.__new_btn)
                self.__spinner.stop()
            return
        item = search.items.pop(0)
        if item.exists_in_db():
            return
        if not (item.name, item.artists) in self.__added_items:
            search_row = SearchRow(item, False)
            search_row.show()
            self.__added_items.append((item.name, item.artists))
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
        self.__reset_search()
        from lollypop.search_local import LocalSearch
        from lollypop.search_network import NetworkSearch
        self.__timeout = None
        self.__lsearch = LocalSearch()
        self.__lsearch.connect('item-found', self.__on_local_item_found)
        if self.__need_network_search():
            self.__nsearch = NetworkSearch()
            self.__nsearch.connect('item-found', self.__on_network_item_found)
        self.__populate()

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
                track = Track(row.id)
                popover = TrackMenuPopover(track,
                                           TrackMenu(track))
                popover.set_relative_to(widget)
                popover.set_pointing_to(rect)
                popover.show()
            else:
                popover = AlbumPopover(row.id, [],
                                       row.artist_ids)
                popover.set_relative_to(widget)
                popover.set_pointing_to(rect)
                popover.show()
