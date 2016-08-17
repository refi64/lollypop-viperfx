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

from gi.repository import Gtk, GLib

from cgi import escape
from threading import Thread

from lollypop.define import Lp, ArtSize, Type
from lollypop.objects import Track, Album
from lollypop.pop_menu import TrackMenuPopover, TrackMenu
from lollypop.pop_album import AlbumPopover


class SearchRow(Gtk.ListBoxRow):
    """
        Album/Track search row
    """

    def __init__(self):
        """
            Init row widgets
        """
        Gtk.ListBoxRow.__init__(self)
        self.__id = None
        self.__is_track = True
        self.__artist_ids = None
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/SearchRow.ui')
        builder.connect_signals(self)
        self.set_property('has-tooltip', True)
        self.connect('query-tooltip', self.__on_query_tooltip)
        self.__row_widget = builder.get_object('row')
        self.__row_widget.set_margin_top(2)
        self.__row_widget.set_margin_end(2)
        self.__artist = builder.get_object('artist')
        self.__title = builder.get_object('item')
        self.__cover = builder.get_object('cover')
        self.add(self.__row_widget)
        self.show()

    def get_id(self):
        """
            Return row id
            @return int
        """
        return self.__id

    def set_id(self, rowid, is_track):
        """
            Set row id
            @param rowid as int
            @param is track as bool
        """
        self.__id = rowid
        self.__is_track = is_track
        if self.__is_track:
            self.__title.set_text("♫ " + Track(self.__id).name)
        else:
            self.__title.set_text(Album(self.__id).name)

    def get_artist_ids(self):
        """
            Return row artist ids
            @return artist ids as [int]
        """
        return self.__artist_ids

    def set_artist_ids(self, artist_ids):
        """
            Set row artist ids
        """
        self.__artist_ids = artist_ids
        artists = []
        for artist_id in artist_ids:
            artists.append(Lp().artists.get_name(artist_id))
        self.__artist.set_text(", ".join(artists))

    def set_cover(self, surface):
        """
            Set cover surface
            @param surface as cairo surface
        """
        self.__cover.set_from_surface(surface)
        del surface

    def is_track(self):
        """
            True if a track
            @return bool
        """
        return self.__is_track

    def exists(self, items):
        """
            Return True if self exists in items
            @param: items as array of searchObject
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

#######################
# PROTECTED           #
#######################
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
        if self.__is_track:
            Lp().player.append_to_queue(self.__id)
        else:
            for track in Lp().albums.get_track_ids(self.__id, [], []):
                Lp().player.append_to_queue(track)
        button.set_sensitive(False)
        button.set_opacity(0.4)

#######################
# PRIVATE             #
#######################
    def __on_query_tooltip(self, widget, x, y, keyboard, tooltip):
        """
            Show tooltip if needed
            @param widget as Gtk.Widget
            @param x as int
            @param y as int
            @param keyboard as bool
            @param tooltip as Gtk.Tooltip
        """
        layout_title = self.__title.get_layout()
        layout_artist = self.__artist.get_layout()
        if layout_title.is_ellipsized() or layout_artist.is_ellipsized():
            artist = escape(self.__artist.get_text())
            title = escape(self.__title.get_text())
            self.set_tooltip_markup("<b>%s</b>\n%s" % (artist, title))
        else:
            self.set_tooltip_text('')


class SearchObject:
    """
        Represent a search object
    """
    def __init__(self):
        self.id = None
        self.is_track = False
        self.artist_ids = []


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
            GLib.timeout_add(100, self.__on_search_changed, widget)

        if self.__timeout:
            GLib.source_remove(self.__timeout)
            self.__timeout = None

        self.__current_search = widget.get_text().strip()
        if self.__current_search != "":
            self.__new_btn.set_sensitive(True)
            self.__timeout = GLib.timeout_add(100,
                                              self.__on_search_changed_thread)
        else:
            self.__new_btn.set_sensitive(False)
            self.__clear([])

#######################
# PRIVATE             #
#######################
    def __clear(self, results):
        """
            Remove row not existing in view, thread safe
        """
        for child in self.__view.get_children():
            if not results or not child.exists(results):
                GLib.idle_add(child.destroy)

    def __exists(self, item):
        """
            Return True if item exist in rows
            @param: item as SearchObject
        """
        found = False
        for child in self.__view.get_children():
            if item.is_track and child.is_track():
                if item.id == child.get_id():
                    found = True
                    break
            elif not item.is_track and not child.is_track():
                if item.id == child.get_id():
                    found = True
                    break
        return found

    def __populate(self):
        """
            Populate searching items
            in db based on text entry current text
        """
        results = []
        albums = []
        tracks_non_album_artist = []

        # Get all albums for all artists and non album_artist tracks
        for artist_id in Lp().artists.search(self.__current_search):
            for album_id in Lp().albums.get_ids([artist_id], []):
                if (album_id, artist_id) not in albums:
                    albums.append((album_id, artist_id))
            for track_id, track_name in Lp().tracks.get_as_non_album_artist(
                                                        artist_id):
                tracks_non_album_artist.append((track_id, track_name))

        for album_id, artist_id in albums:
            search_obj = SearchObject()
            search_obj.id = album_id
            search_obj.is_track = False
            search_obj.artist_ids = [artist_id]
            results.append(search_obj)

        albums = Lp().albums.search(self.__current_search)
        for album_id in albums:
            search_obj = SearchObject()
            search_obj.id = album_id
            search_obj.is_track = False
            search_obj.artist_ids = Lp().albums.get_artist_ids(album_id)
            results.append(search_obj)

        for track_id, track_name in Lp().tracks.search(
                        self.__current_search) + tracks_non_album_artist:
            search_obj = SearchObject()
            search_obj.id = track_id
            search_obj.is_track = True
            search_obj.artist_ids = Lp().tracks.get_artist_ids(track_id)
            results.append(search_obj)

        if not self.__stop_thread:
            self.__clear(results)
            GLib.idle_add(self.__add_rows, results)
        else:
            self.__in_thread = False
            self.__stop_thread = False

    def __add_rows(self, results):
        """
            Add a rows recursively
            @param results as array of SearchObject
        """
        if results:
            result = results.pop(0)
            if not self.__exists(result):
                search_row = SearchRow()
                if result.is_track:
                    obj = Track(result.id)
                    album_id = obj.album_id
                else:
                    obj = Album(result.id)
                    album_id = obj.id
                search_row.set_id(result.id, result.is_track)
                search_row.set_artist_ids(result.artist_ids)
                search_row.set_cover(
                        Lp().art.get_album_artwork(
                                     Album(album_id),
                                     ArtSize.MEDIUM,
                                     self.get_scale_factor()))
                self.__view.add(search_row)
            if self.__stop_thread:
                self.__in_thread = False
                self.__stop_thread = False
            else:
                GLib.idle_add(self.__add_rows, results)
        else:
            self.__in_thread = False
            self.__stop_thread = False

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
            if child.is_track():
                track_ids.append(child.get_id())
            else:
                album_tracks = Lp().albums.get_track_ids(child.get_id())
                if not is_track and child.get_id() == object_id and\
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
                tracks.append(Track(child.get_id()))
            else:
                for track_id in Lp().albums.get_track_ids(
                                                       child.get_id(), [],
                                                       child.get_artist_ids()):
                    tracks.append(Track(track_id))
        if tracks:
            playlist_id = Lp().playlists.get_id(self.__current_search)
            if playlist_id == Type.NONE:
                Lp().playlists.add(self.__current_search)
                playlist_id = Lp().playlists.get_id(self.__current_search)
            Lp().playlists.add_tracks(playlist_id, tracks)

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

    def __on_search_changed_thread(self):
        """
            Populate widget
        """
        self.__timeout = None
        self.__in_thread = True
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
            if row.is_track():
                if Lp().player.locked:
                    if row.get_id() in Lp().player.get_queue():
                        Lp().player.del_from_queue(row.get_id())
                    else:
                        Lp().player.append_to_queue(row.get_id())
                    row.destroy()
                else:
                    Lp().player.load(Track(row.get_id()))
            elif Gtk.get_minor_version() > 16:
                popover = AlbumPopover(row.get_id(), [], [])
                popover.set_relative_to(row)
                popover.show()
            else:
                t = Thread(target=self.__play_search, args=(row.get_id(),
                                                            row.is_track()))
                t.daemon = True
                t.start()
        else:
            t = Thread(target=self.__play_search, args=(row.get_id(),
                                                        row.is_track()))
            t.daemon = True
            t.start()

    def __on_button_press(self, widget, event):
        """
            Store pressed button
            @param widget as Gtk.ListBox
            @param event as Gdk.EventButton
        """
        if event.button != 1:
            rect = widget.get_allocation()
            rect.x = event.x
            rect.y = event.y
            rect.width = rect.height = 1
            row = widget.get_row_at_y(event.y)
            if row.is_track():
                popover = TrackMenuPopover(row.get_id(),
                                           TrackMenu(row.get_id()))
                popover.set_relative_to(widget)
                popover.set_pointing_to(rect)
                popover.show()
            else:
                popover = AlbumPopover(row.get_id(), [],
                                       row.get_artist_ids())
                popover.set_relative_to(widget)
                popover.set_pointing_to(rect)
                popover.show()
