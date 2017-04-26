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

from gi.repository import Gtk, GLib, GObject

from gettext import gettext as _

from lollypop.view import LazyLoadingView, View
from lollypop.view_container import ViewContainer
from lollypop.define import Lp, Type, ArtSize
from lollypop.objects import Track
from lollypop.widgets_album_detailed import AlbumDetailedWidget


class ArtistAlbumsView(LazyLoadingView):
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

        self._albumbox = Gtk.Grid()
        self._albumbox.set_row_spacing(5)
        self._albumbox.set_property("orientation", Gtk.Orientation.VERTICAL)
        self._albumbox.show()
        self._viewport.add(self._albumbox)

        self._albumbox.set_property("valign", Gtk.Align.START)
        self._overlay = Gtk.Overlay.new()
        self._overlay.add(self._scrolled)
        self._overlay.add_overlay(self.__spinner)
        self._overlay.show()
        self.add(self._overlay)

    def populate(self, albums):
        """
            Populate the view
            @param albums as [int]
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
            self._albumbox.add(label)

    def jump_to_current(self):
        """
            Jump to current album
        """
        widget = None
        for child in self._albumbox.get_children():
            if child.id == Lp().player.current_track.album.id:
                widget = child
                break
        if widget is not None:
            y = widget.get_current_ordinate(self._albumbox)
            self._scrolled.get_vadjustment().set_value(y)

    @property
    def children(self):
        """
            View children
            @return [AlbumDetailedWidget]
        """
        return self._get_children()

#######################
# PROTECTED           #
#######################
    def _on_search_changed(self, entry):
        """
            Update filter
            @param entry as Gtk.Entry
        """
        self._filter = entry.get_text()
        for child in self._get_children():
            for box in child.boxes:
                box.invalidate_filter()

    def _on_populated(self, widget, widgets, scroll_value):
        """
            Add another album/disc
            @param widget as AlbumDetailedWidget
            @param widgets as pending AlbumDetailedWidgets
            @param scroll value as float
        """
        if not widget.is_populated():
            widget.populate()
        elif not self._stop:
            GLib.idle_add(self.lazy_loading, widgets, scroll_value)
        else:
            self._stop = False

    def _get_children(self):
        """
            Return view children
            @return [AlbumDetailedWidget]
        """
        children = []
        for child in self._albumbox.get_children():
            if isinstance(child, AlbumDetailedWidget):
                children.append(child)
        return children

#######################
# PRIVATE             #
#######################
    def lazy_loading(self, widgets=[], scroll_value=0):
        """
            Load the view in a lazy way:
                - widgets first
                - _waiting_init then
            @param widgets as [AlbumSimpleWidgets]
            @param scroll_value as float
        """
        widget = None
        if self._stop or self._scroll_value != scroll_value:
            return
        if widgets:
            widget = widgets.pop(0)
            self._lazy_queue.remove(widget)
        elif self._lazy_queue:
            widget = self._lazy_queue.pop(0)
        if widget is not None:
            widget.connect("populated", self._on_populated,
                           widgets, scroll_value)
            widget.populate()

    def __add_albums(self, albums):
        """
            Pop an album and add it to the view,
            repeat operation until album list is empty
            @param [album ids as int]
        """
        if albums and not self._stop:
            album_id = albums.pop(0)
            widget = AlbumDetailedWidget(album_id,
                                         self._genre_ids,
                                         self._artist_ids,
                                         self.__art_size)
            widget.set_filter_func(self._filter_func)
            widget.connect("overlayed", self._on_overlayed)
            self._lazy_queue.append(widget)
            widget.show()
            self._albumbox.add(widget)
            GLib.idle_add(self.__add_albums, albums)
        else:
            self.__spinner.stop()
            self.__spinner.hide()
            self.emit("populated")
            GLib.idle_add(self.lazy_loading)


class CurrentArtistAlbumsView(ViewContainer):
    """
        Show albums from artist
        Show current artist if no artist specified
    """

    def __init__(self):
        """
            Init popover
        """
        ViewContainer.__init__(self, 1000)
        self.connect("destroy", self.__on_destroy)
        self.__track = Track()

    def populate(self, track):
        """
            Populate the view
            @param track as Track
            @thread safe
        """
        new_artist_ids = list(set(track.album.artist_ids) |
                              set(track.artist_ids))
        if new_artist_ids != self.__get_artist_ids():
            self.__track = track
            albums = self.__get_albums()
            GLib.idle_add(self.__populate, albums)

    def stop(self):
        """
            Stop loading
        """
        self.get_visible_child().stop()

    def jump_to_current(self):
        """
            Jump to current track
        """
        self.get_visible_child().jump_to_current()

#######################
# PRIVATE             #
#######################
    def __on_destroy(self, widget):
        """
            Disconnect signal
            @param widget as Gtk.Widget
        """
        self.clean_old_views(None)

    def __populate(self, albums):
        """
            Populate view and make it visible
            @param albums as [albums ids as int]
        """
        # Add a loading indicator
        view = View()
        spinner = Gtk.Spinner()
        spinner.set_hexpand(True)
        spinner.set_vexpand(True)
        spinner_size = int(ArtSize.BIG / 3)
        spinner.set_size_request(spinner_size, spinner_size)
        spinner.set_property("halign", Gtk.Align.CENTER)
        spinner.set_property("valign", Gtk.Align.CENTER)
        spinner.start()
        view.add(spinner)
        view.show_all()
        self.add(view)
        self.set_transition_type(Gtk.StackTransitionType.NONE)
        self.set_visible_child(view)
        self.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.clean_old_views(view)

        # Populate artist albums view
        view = ArtistAlbumsView(self.__track.artist_ids, [], ArtSize.BIG)
        view.connect("populated", self.__on_populated, spinner)
        view.show()
        view.populate(albums)

    def __get_artist_ids(self):
        """
            Return current artist ids
            @return artist ids as [int]
        """
        artist_ids = list(set(self.__track.album.artist_ids) |
                          set(self.__track.artist_ids))
        if Type.COMPILATIONS in artist_ids:
            artist_ids.remove(Type.COMPILATIONS)
        return artist_ids

    def __get_albums(self):
        """
            Get albums
            @return album ids as [int]
        """
        albums = []
        if self.__track.album.artist_ids[0] == Type.COMPILATIONS:
            albums += [self.__track.album.id]
        albums += Lp().artists.get_albums(self.__get_artist_ids())
        # Charts album playing
        if Lp().player.current_track.album.id not in albums:
            albums.append(Lp().player.current_track.album.id)
        return albums

    def __on_populated(self, view, spinner):
        """
            Show the view
            @param view as View
            @param spinner as Gtk.Spinner
        """
        spinner.stop()
        self.add(view)
        self.set_visible_child(view)
        self.clean_old_views(view)
