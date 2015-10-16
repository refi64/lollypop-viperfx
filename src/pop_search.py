# Copyright (c) 2014-2015 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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


class SearchRow(Gtk.ListBoxRow):
    """
        Album/Track search row
    """

    def __init__(self, parent):
        """
            Init row widgets
            @param parent as Gtk.Widget
        """
        Gtk.ListBoxRow.__init__(self)
        self._parent = parent
        self.id = None
        self.is_track = False
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/SearchRow.ui')
        builder.connect_signals(self)
        self.set_property('has-tooltip', True)
        self.connect('query-tooltip', self._on_query_tooltip)
        self._row_widget = builder.get_object('row')
        self._artist = builder.get_object('artist')
        self._title = builder.get_object('item')
        self._cover = builder.get_object('cover')
        self.add(self._row_widget)
        self.show()

    def set_text(self, artist, title):
        """
            Set artist and title label
            @param artist name as string
            @param item name as string
        """
        self._artist.set_text(artist)
        self._title.set_text(title)

    def set_cover(self, surface):
        """
            Set cover surface
            @param surface as cairo surface
        """
        self._cover.set_from_surface(surface)
        del surface

    def exists(self, items):
        """
            Return True if self exists in items
            @param: items as array of searchObject
        """
        found = False
        for item in items:
            if item.is_track and self.is_track:
                if item.id == self.id:
                    found = True
                    break
            elif not item.is_track and not self.is_track:
                if item.id == self.id:
                    found = True
                    break
        return found

#######################
# PRIVATE             #
#######################
    def _on_playlist_clicked(self, button):
        """
            Prepend track to queue
            @param button as Gtk.Button
        """
        Lp.window.show_playlist_manager(self.id, None, not self.is_track)

    def _on_queue_clicked(self, button):
        """
            Add track to queue
            @param button as Gtk.Button
        """
        if self.is_track:
            Lp.player.append_to_queue(self.id)
        else:
            for track in Lp.albums.get_tracks(self.id, None):
                Lp.player.append_to_queue(track)
        button.hide()

    def _on_query_tooltip(self, widget, x, y, keyboard, tooltip):
        """
            Show tooltip if needed
            @param widget as Gtk.Widget
            @param x as int
            @param y as int
            @param keyboard as bool
            @param tooltip as Gtk.Tooltip
        """
        layout_title = self._title.get_layout()
        layout_artist = self._artist.get_layout()
        if layout_title.is_ellipsized() or layout_artist.is_ellipsized():
            artist = escape(self._artist.get_text())
            title = escape(self._title.get_text())
            self.set_tooltip_markup("<b>%s</b>\n%s" % (artist, title))
        else:
            self.set_tooltip_text('')


class SearchObject:
    """
        Represent a search object
    """
    def __init__(self):
        self.artist = None
        self.title = None
        self.count = -1
        self.id = None
        self.album_id = None
        self.is_track = False


class SearchPopover(Gtk.Popover):
    """
        Popover allowing user to search for tracks/albums
    """

    def __init__(self, parent):
        """
            Init Popover
            @param parent as Gtk.Widget
        """
        Gtk.Popover.__init__(self)
        self.connect('map', self._on_map)
        self.connect('unmap', self._on_unmap)
        self._parent = parent
        self._in_thread = False
        self._stop_thread = False
        self._timeout = None
        self._current_search = ''

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/SearchPopover.ui')
        builder.connect_signals(self)

        self._play_btn = builder.get_object('play_btn')
        self._new_btn = builder.get_object('new_btn')

        self._view = Gtk.ListBox()
        self._view.connect("row-activated", self._on_activate)
        self._view.show()

        builder.get_object('scrolled').add(self._view)
        self.add(builder.get_object('widget'))

        size_setting = Lp.settings.get_value('window-size')
        if isinstance(size_setting[1], int):
            self.set_size_request(400, size_setting[1]*0.7)
        else:
            self.set_size_request(400, 600)

#######################
# PRIVATE             #
#######################
    def _clear(self, results):
        """
            Remove row not existing in view, thread safe
        """
        for child in self._view.get_children():
            if not results or not child.exists(results):
                GLib.idle_add(child.destroy)

    def _exists(self, item):
        """
            Return True if item exist in rows
            @param: item as SearchObject
        """
        found = False
        for child in self._view.get_children():
            if item.is_track and child.is_track:
                if item.id == child.id:
                    found = True
                    break
            elif not item.is_track and not child.is_track:
                if item.id == child.id:
                    found = True
                    break
        return found

    def _populate(self):
        """
            Populate treeview searching items
            in db based on text entry current text
        """
        results = []
        albums = []

        tracks_non_album_artist = []

        # Get all albums for all artists and non album_artist tracks
        for artist_id in Lp.artists.search(self._current_search):
            for album_id in Lp.albums.get_ids(artist_id, None):
                if (album_id, artist_id) not in albums:
                    albums.append((album_id, artist_id))
            for track_id, track_name in Lp.tracks.get_as_non_album_artist(
                                                        artist_id):
                tracks_non_album_artist.append((track_id, track_name))

        albums += Lp.albums.search(self._current_search)

        for album_id, artist_id in albums:
            search_obj = SearchObject()
            search_obj.artist = Lp.artists.get_name(artist_id)
            search_obj.title = Lp.albums.get_name(album_id)
            search_obj.count = Lp.albums.get_count(album_id, None)
            search_obj.id = album_id
            search_obj.album_id = album_id
            results.append(search_obj)

        for track_id, track_name in Lp.tracks.search(
                        self._current_search) + tracks_non_album_artist:
            search_obj = SearchObject()
            search_obj.title = track_name
            search_obj.id = track_id
            search_obj.album_id = Lp.tracks.get_album_id(track_id)
            search_obj.is_track = True

            artist_id = Lp.albums.get_artist_id(search_obj.album_id)
            if artist_id == Type.COMPILATIONS:
                search_obj.artist = Lp.tracks.get_artist_names(track_id)
            else:
                search_obj.artist = Lp.artists.get_name(artist_id)

            results.append(search_obj)

        if not self._stop_thread:
            self._clear(results)
            GLib.idle_add(self._add_rows, results)
        else:
            self._in_thread = False
            self._stop_thread = False

    def _add_rows(self, results):
        """
            Add a rows recursively
            @param results as array of SearchObject
        """
        if results:
            result = results.pop(0)
            if not self._exists(result):
                search_row = SearchRow(self._parent)
                if result.count != -1:
                    result.title += " (%s)" % result.count
                search_row.set_text(result.artist, result.title)
                search_row.set_cover(
                        Lp.art.get_album_artwork(
                                     Album(result.album_id),
                                     ArtSize.MEDIUM*self.get_scale_factor()))
                search_row.id = result.id
                search_row.is_track = result.is_track
                self._view.add(search_row)
            if self._stop_thread:
                self._in_thread = False
                self._stop_thread = False
            else:
                GLib.idle_add(self._add_rows, results)
        else:
            self._in_thread = False
            self._stop_thread = False

    def _set_user_playlist(self, tracks, track_id):
        """
            Set user playlist
            @param tracks as [Track]
            @param track id as int
            @thread safe
        """
        track = Lp.player.set_user_playlist(tracks, track_id)
        Lp.player.load(track)

    def _play_search(self, object_id=None, is_track=True):
        """
            Play tracks based on search
            @param started object id as int
            @param is track as bool
        """
        tracks = []
        track_id = None
        for child in self._view.get_children():
            if child.is_track:
                tracks.append(Track(child.id))
            else:
                album_tracks = Lp.albums.get_tracks(child.id, None)
                if not is_track and child.id == object_id and album_tracks:
                    track_id = album_tracks[0]
                for tid in album_tracks:
                    tracks.append(Track(tid))
        if tracks:
            GLib.idle_add(Lp.player.set_party, False)
            if object_id is not None and is_track:
                track_id = object_id
            elif track_id is None:
                track_id = tracks[0].id
            GLib.idle_add(self._set_user_playlist, tracks, track_id)

    def _new_playlist(self):
        """
            Create a new playlist based on search
        """
        tracks = []
        for child in self._view.get_children():
            if child.is_track:
                tracks.append(Track(child.id))
            else:
                for track_id in Lp.albums.get_tracks(child.id, None):
                    tracks.append(Track(child.id))

        if tracks:
            playlist_id = Lp.playlists.get_id(self._current_search)
            if playlist_id == Type.NONE:
                Lp.playlists.add(self._current_search)
            Lp.playlists.add_tracks(playlist_id, tracks)

    def _on_map(self, widget):
        """
            Disable global shortcuts
            @param widget as Gtk.Widget
        """
        Lp.window.enable_global_shorcuts(False)

    def _on_unmap(self, widget):
        """
            Enable global shortcuts
            @param widget as Gtk.Widget
        """
        Lp.window.enable_global_shorcuts(True)

    def _on_search_changed(self, widget):
        """
            Timeout filtering, call _really_do_filterting()
            after timeout
            @param widget as Gtk.TextEntry
        """
        if self._in_thread:
            self._stop_thread = True
            GLib.timeout_add(100, self._on_search_changed, widget)

        if self._timeout:
            GLib.source_remove(self._timeout)
            self._timeout = None

        self._current_search = widget.get_text()
        if self._current_search != "":
            self._play_btn.set_sensitive(True)
            self._new_btn.set_sensitive(True)
            self._timeout = GLib.timeout_add(100,
                                             self._on_search_changed_thread)
        else:
            self._play_btn.set_sensitive(False)
            self._new_btn.set_sensitive(False)
            self._clear([])

    def _on_search_changed_thread(self):
        """
            Just run _reallyon_entry_changed in a thread
        """
        self._timeout = None
        self._in_thread = True
        t = Thread(target=self._populate)
        t.daemon = True
        t.start()

    def _on_activate(self, widget, row):
        """
            Play searched item when selected
            If item is an album, play first track
            @param widget as Gtk.ListBox
            @param row as SearchRow
        """
        Lp.player.set_party(False)
        t = Thread(target=self._play_search, args=(row.id, row.is_track))
        t.daemon = True
        t.start()

    def _on_play_btn_clicked(self, button):
        """
            Start playback base on current search
            @param button as Gtk.Button
        """
        t = Thread(target=self._play_search)
        t.daemon = True
        t.start()

    def _on_new_btn_clicked(self, button):
        """
            Create a new playlist based on search
            @param button as Gtk.Button
        """
        t = Thread(target=self._new_playlist)
        t.daemon = True
        t.start()
