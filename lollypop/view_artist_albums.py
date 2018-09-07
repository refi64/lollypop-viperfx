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

from gi.repository import Gtk, GLib, GObject

from gettext import gettext as _

from lollypop.view import LazyLoadingView
from lollypop.define import App, ArtSize
from lollypop.widgets_album_detailed import AlbumDetailedWidget
from lollypop.controller_view import ViewController


class ArtistAlbumsView(LazyLoadingView, ViewController):
    """
        Show artist albums and tracks
    """
    __gsignals__ = {
        "populated": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, artist_ids, genre_ids, art_size):
        """
            Init ArtistAlbumsView
            @param artist ids as [int]
            @param genre ids as [int]
            @param art size as ArtSize
        """
        LazyLoadingView.__init__(self, True)
        ViewController.__init__(self)
        self.__current_loading_widget = None
        self._artist_ids = artist_ids
        self._genre_ids = genre_ids
        self.__art_size = art_size
        self.__spinner = Gtk.Spinner()
        self.__spinner.set_hexpand(True)
        self.__spinner.set_vexpand(True)
        spinner_size = int(ArtSize.BIG / 3)
        self.__spinner.set_size_request(spinner_size, spinner_size)
        self.__spinner.set_property("halign", Gtk.Align.CENTER)
        self.__spinner.set_property("valign", Gtk.Align.CENTER)
        self.__spinner.show()

        self._album_box = Gtk.Grid()
        self._album_box.set_row_spacing(5)
        self._album_box.set_property("orientation", Gtk.Orientation.VERTICAL)
        self._album_box.show()
        self._viewport.add(self._album_box)

        self._album_box.set_property("valign", Gtk.Align.START)
        self._overlay = Gtk.Overlay.new()
        self._overlay.add(self._scrolled)
        self._overlay.add_overlay(self.__spinner)
        self._overlay.show()
        self.add(self._overlay)

        self.connect_current_changed_signal()
        self.connect_artwork_changed_signal("album")

    def populate(self, albums):
        """
            Populate the view
            @param albums as [Album]
        """
        if albums:
            if len(albums) != 1:
                self.__spinner.start()
            self.__add_albums(albums)
        else:
            label = Gtk.Label.new()
            string = GLib.markup_escape_text(_("Network access disabled"))
            label.set_markup(
                '<span font_weight="bold" size="xx-large">' +
                string +
                "</span>")
            label.set_property("halign", Gtk.Align.CENTER)
            label.set_hexpand(True)
            label.show()
            self.set_sensitive(False)
            self._album_box.add(label)

    def lazy_loading(self, widgets=[], scroll_value=0):
        """
            Load the view in a lazy way
            @param widgets as [AlbumSimpleWidgets]
            @param scroll_value as float
        """
        self.__current_loading_widget = None
        if self._lazy_queue is None or self._scroll_value != scroll_value:
            return
        if widgets:
            self.__current_loading_widget = widgets.pop(0)
            self._lazy_queue.remove(self.__current_loading_widget)
        elif self._lazy_queue:
            self.__current_loading_widget = self._lazy_queue.pop(0)
        if self.__current_loading_widget is not None:
            self.__current_loading_widget.connect("populated",
                                                  self._on_populated,
                                                  widgets,
                                                  scroll_value)
            self.__current_loading_widget.populate()

    def stop(self):
        """
            Stop current loading widget
        """
        if self.__current_loading_widget is not None:
            self.__current_loading_widget.stop()

    def jump_to_current(self):
        """
            Jump to current album
        """
        widget = None
        for child in self._album_box.get_children():
            if child.id == App().player.current_track.album.id:
                widget = child
                break
        if widget is not None:
            y = widget.get_current_ordinate(self._album_box)
            self._scrolled.get_vadjustment().set_value(y)

    @property
    def children(self):
        """
            Get children
            @return AlbumDetailedwidget
        """
        children = []
        for child in self._album_box.get_children():
            if isinstance(child, AlbumDetailedWidget):
                children.append(child)
        return children

#######################
# PROTECTED           #
#######################
    def _on_current_changed(self, player):
        """
            Update children state
            @param player as Player
        """
        for child in self.children:
            child.set_selection()
            child.set_playing_indicator()

    def _on_artwork_changed(self, artwork, album_id):
        """
            Update children artwork if matching album id
            @param artwork as Artwork
            @param album_id as int
        """
        for child in self.children:
            child.set_artwork(album_id)

    def _on_search_changed(self, entry):
        """
            Update filter
            @param entry as Gtk.Entry
        """
        self._filter = entry.get_text()
        for child in self.children:
            for box in child.boxes:
                box.invalidate_filter()

    def _on_populated(self, widget, widgets, scroll_value):
        """
            Add another album/disc
            @param widget as AlbumDetailedWidget
            @param widgets as pending AlbumDetailedWidgets
            @param scroll value as float
        """
        if self._lazy_queue is None:
            return
        if not widget.is_populated():
            widget.populate()
        else:
            GLib.idle_add(self.lazy_loading, widgets, scroll_value)

#######################
# PRIVATE             #
#######################
    def __add_albums(self, albums):
        """
            Pop an album and add it to the view,
            repeat operation until album list is empty
            @param albums as [Album]
        """
        if self._lazy_queue is None:
            return
        if albums:
            album = albums.pop(0)
            widget = AlbumDetailedWidget(album,
                                         self._genre_ids,
                                         self._artist_ids,
                                         self.__art_size)
            widget.set_filter_func(self._filter_func)
            widget.connect("overlayed", self._on_overlayed)
            self._lazy_queue.append(widget)
            widget.show()
            self._album_box.add(widget)
            GLib.idle_add(self.__add_albums, albums)
        else:
            self.__spinner.stop()
            self.__spinner.hide()
            self.emit("populated")
            GLib.idle_add(self.lazy_loading)
