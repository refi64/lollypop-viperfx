#!/usr/bin/python
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
from gettext import gettext as _
from _thread import start_new_thread

from lollypop.define import Lp, ArtSize, Type
from lollypop.track import Track


# show an album/track object with actions
class SearchRow(Gtk.ListBoxRow):
    """
        Init row widgets
        @param parent as Gtk.Widget
    """
    def __init__(self, parent):
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

    """
        Set artist and title label
        @param artist name as string
        @param item name as string
    """
    def set_text(self, artist, title):
        self._artist.set_text(artist)
        self._title.set_text(title)

    """
        Set cover surface
        @param surface as cairo surface
    """
    def set_cover(self, surface):
        self._cover.set_from_surface(surface)
        del surface

    """
        Return True if self exists in items
        @param: items as array of searchObject
    """
    def exists(self, items):
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

    """
        Prepend track to queue
        @param button as Gtk.Button
    """
    def _on_playlist_clicked(self, button):
        Lp.window.show_playlist_manager(self.id, None, not self.is_track)

    """
        Add track to queue
        @param button as Gtk.Button
    """
    def _on_queue_clicked(self, button):
        if self.is_track:
            Lp.player.append_to_queue(self.id)
        else:
            for track in Lp.albums.get_tracks(self.id, None):
                Lp.player.append_to_queue(track)
        button.hide()

    """
        Show tooltip if needed
        @param widget as Gtk.Widget
        @param x as int
        @param y as int
        @param keyboard as bool
        @param tooltip as Gtk.Tooltip
    """
    def _on_query_tooltip(self, widget, x, y, keyboard, tooltip):
        layout_title = self._title.get_layout()
        layout_artist = self._artist.get_layout()
        if layout_title.is_ellipsized() or layout_artist.is_ellipsized():
            artist = escape(self._artist.get_text())
            title = escape(self._title.get_text())
            self.set_tooltip_markup("<b>%s</b>\n%s" % (artist, title))
        else:
            self.set_tooltip_text('')


# Represent a search object
class SearchObject:
    def __init__(self):
        self.artist = None
        self.title = None
        self.count = -1
        self.id = None
        self.album_id = None
        self.is_track = False


# Show a list of search row
class SearchWidget(Gtk.Popover):

    """
        Init Popover ui with a text entry and a scrolled treeview
        @param parent as Gtk.Widget
    """
    def __init__(self, parent):
        Gtk.Popover.__init__(self)
        self._parent = parent
        self._in_thread = False
        self._stop_thread = False
        self._timeout = None

        grid = Gtk.Grid()
        grid.set_property("orientation", Gtk.Orientation.VERTICAL)

        label = Gtk.Label(label=_("Search:"))
        label.set_property("margin_start", 5)
        label.set_property("margin_end", 5)
        label.show()

        self._text_entry = Gtk.Entry()
        self._text_entry.connect("changed", self._do_filtering)
        self._text_entry.set_hexpand(True)
        self._text_entry.set_property("margin", 5)
        self._text_entry.show()

        entry_line = Gtk.Grid()
        entry_line.add(label)
        entry_line.add(self._text_entry)
        entry_line.show()

        self._view = Gtk.ListBox()
        self._view.connect("row-activated", self._on_activate)
        self._view.show()

        self._scroll = Gtk.ScrolledWindow()
        self._scroll.set_vexpand(True)
        self._scroll.set_policy(Gtk.PolicyType.AUTOMATIC,
                                Gtk.PolicyType.AUTOMATIC)
        self._scroll.add(self._view)
        self._scroll.show()

        grid.add(entry_line)
        grid.add(self._scroll)
        grid.show()
        self.add(grid)

#######################
# PRIVATE             #
#######################
    """
        Give focus to text entry on show
    """
    def do_show(self):
        size_setting = Lp.settings.get_value('window-size')
        if isinstance(size_setting[1], int):
            self.set_size_request(400, size_setting[1]*0.7)
        else:
            self.set_size_request(400, 600)
        Gtk.Popover.do_show(self)
        Lp.window.enable_global_shorcuts(False)
        self._text_entry.grab_focus()

    """
        Restore global shortcuts
    """
    def do_hide(self):
        Gtk.Popover.do_hide(self)
        Lp.window.enable_global_shorcuts(True)

    """
        Remove row not existing in view, thread safe
    """
    def _clear(self, results):
        for child in self._view.get_children():
            if not results or not child.exists(results):
                GLib.idle_add(child.destroy)

    """
        Return True if item exist in rows
        @param: item as SearchObject
    """
    def _exists(self, item):
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

    """
        Timeout filtering, call _really_do_filterting() after a small timeout
    """
    def _do_filtering(self, data=None):
        if self._in_thread:
            self._stop_thread = True
            GLib.timeout_add(100, self._do_filtering)

        if self._timeout:
            GLib.source_remove(self._timeout)
            self._timeout = None

        if self._text_entry.get_text() != "":
            self._timeout = GLib.timeout_add(100, self._do_filtering_thread)
        else:
            self._clear([])

    """
        Just run _really_do_filtering in a thread
    """
    def _do_filtering_thread(self):
        self._timeout = None
        self._in_thread = True
        start_new_thread(self._really_do_filtering, ())

    """
        Populate treeview searching items
        in db based on text entry current text
    """
    def _really_do_filtering(self):
        sql = Lp.db.get_cursor()
        results = []
        albums = []

        searched = self._text_entry.get_text()

        tracks_non_aartist = []

        # Get all albums for all artists and non aartist tracks
        for artist_id in Lp.artists.search(searched, sql):
            for album_id in Lp.albums.get_ids(artist_id, None, sql):
                if (album_id, artist_id) not in albums:
                    albums.append((album_id, artist_id))
            for track_id, track_name in Lp.tracks.get_as_non_aartist(artist_id,
                                                                     sql):
                tracks_non_aartist.append((track_id, track_name))

        albums += Lp.albums.search(searched, sql)

        for album_id, artist_id in albums:
            search_obj = SearchObject()
            search_obj.artist = Lp.artists.get_name(artist_id, sql)
            search_obj.title = Lp.albums.get_name(album_id, sql)
            search_obj.count = Lp.albums.get_count(album_id, None, sql)
            search_obj.id = album_id
            search_obj.album_id = album_id
            results.append(search_obj)

        for track_id, track_name in Lp.tracks.search(searched, sql) +\
                tracks_non_aartist:
            search_obj = SearchObject()
            search_obj.title = track_name
            search_obj.id = track_id
            search_obj.album_id = Lp.tracks.get_album_id(track_id, sql)
            search_obj.is_track = True

            artist_id = Lp.albums.get_artist_id(search_obj.album_id,
                                                sql)
            if artist_id == Type.COMPILATIONS:
                search_obj.artist = Lp.tracks.get_artist_names(track_id, sql)
            else:
                search_obj.artist = Lp.artists.get_name(artist_id, sql)

            results.append(search_obj)

        if not self._stop_thread:
            self._clear(results)
            GLib.idle_add(self._add_rows, results)
        else:
            self._in_thread = False
            self._stop_thread = False

        sql.close()

    """
        Add a rows recursively
        @param results as array of SearchObject
    """
    def _add_rows(self, results):
        if results:
            result = results.pop(0)
            if not self._exists(result):
                search_row = SearchRow(self._parent)
                if result.count != -1:
                    result.title += " (%s)" % result.count
                search_row.set_text(result.artist, result.title)
                search_row.set_cover(Lp.art.get_album(result.album_id,
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

    """
        Play searched item when selected
        If item is an album, play first track
    """
    def _on_activate(self, widget, row):
        value_id = row.id
        if row.is_track:
            Lp.player.load(Track(value_id))
        else:
            Lp.player.play_album(value_id)
