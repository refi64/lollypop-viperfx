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

from gi.repository import Gtk, GLib, GObject

from lollypop.view import LazyLoadingView, View
from lollypop.view_container import ViewContainer
from lollypop.define import Lp, Type
from lollypop.widgets_album import AlbumDetailedWidget


class ArtistAlbumsView(LazyLoadingView):
    """
        Show artist albums and tracks
    """
    __gsignals__ = {
        'populated': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, artist_ids, genre_ids, show_cover=True):
        """
            Init ArtistAlbumsView
            @param artist ids as [int]
            @param genre ids as [int]
            @param show cover as bool
        """
        LazyLoadingView.__init__(self)
        self._artist_ids = artist_ids
        self._genre_ids = genre_ids
        self._show_cover = show_cover
        self._albums_count = 0

        self._albumbox = Gtk.Grid()
        self._albumbox.set_row_spacing(20)
        self._albumbox.set_property("orientation", Gtk.Orientation.VERTICAL)
        self._albumbox.show()

        self._scrolled.set_property('expand', True)
        self._viewport.set_property("valign", Gtk.Align.START)
        self.attach(self._scrolled, 0, 1, 1, 1)

    def populate(self, albums):
        """
            Populate the view
            @param albums as [int]
        """
        if albums:
            self._albums_count = len(albums)
            self._add_albums(albums)

    def jump_to_current(self):
        """
            Jump to current album
        """
        widget = None
        for child in self._albumbox.get_children():
            if child.get_id() == Lp().player.current_track.album.id:
                widget = child
                break
        if widget is not None:
            y = widget.get_current_ordinate(self._albumbox)
            self._scrolled.get_vadjustment().set_value(y)

    def stop(self):
        """
            Stop loading
        """
        self._lazy_queue = []
        LazyLoadingView.stop(self)

    @property
    def requested_height(self):
        """
            Requested height for children
            @return height as int
        """
        height = 0
        for child in self._albumbox.get_children():
            height += child.requested_height
        return height

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
            widget.connect('populated', self._on_populated,
                           widgets, scroll_value)
            widget.populate()

    def _get_children(self):
        """
            Return view children
            @return [AlbumWidget]
        """
        return self._albumbox.get_children()

    def _add_albums(self, albums):
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
                                         self._show_cover)
            self._lazy_queue.append(widget)
            # Not needed if only one album
            if self._albums_count == 1:
                widget.disable_play_all()
            widget.show()
            self._albumbox.add(widget)
            GLib.idle_add(self._add_albums, albums)
        else:
            if self._viewport.get_child() is None:
                self._viewport.add(self._albumbox)
            self.emit('populated')
            GLib.idle_add(self.lazy_loading)

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
        self.connect('destroy', self._on_destroy)
        self._artist_ids = []
        self._album_id = Type.NONE

    def populate(self, artist_ids, album_id):
        """
            Populate the view
            @param artist ids as [int]
            @param album id as int
            @thread safe
        """
        if (artist_ids, album_id) != (self._artist_ids, self._album_id):
            self._artist_ids = artist_ids
            self._album_id = album_id
            if album_id == Type.NONE:
                albums = self._get_albums(artist_ids)
            else:
                # FIXME
                albums = [album_id]
            GLib.idle_add(self._populate, albums)

    def jump_to_current(self):
        """
            Jump to current track
        """
        self.get_visible_child().jump_to_current()

#######################
# PRIVATE             #
#######################
    def _on_destroy(self, widget):
        """
            Disconnect signal
            @param widget as Gtk.Widget
        """
        self.clean_old_views(None)

    def _populate(self, albums):
        """
            Populate view and make it visible
            @param albums as [albums ids as int]
        """
        # Add a loading indicator
        view = View()
        spinner = Gtk.Spinner()
        spinner.set_hexpand(True)
        spinner.set_vexpand(True)
        spinner.set_size_request(100, 100)
        spinner.set_property('halign', Gtk.Align.CENTER)
        spinner.set_property('valign', Gtk.Align.CENTER)
        spinner.start()
        view.add(spinner)
        view.show_all()
        self.add(view)
        self.set_visible_child(view)
        self.clean_old_views(view)

        # Populate artist albums view
        view = ArtistAlbumsView(self._artist_ids, [])
        view.connect('populated', self._on_populated, spinner)
        view.show()
        view.populate(albums)

    def _get_albums(self, artist_ids):
        """
            Get albums
            @param artist ids as [int]
            @return album ids as [int]
        """
        if artist_ids[0] == Type.COMPILATIONS:
            albums = [Lp().player.current_track.album_id]
        else:
            albums = Lp().artists.get_albums(artist_ids)
        return albums

    def _on_populated(self, view, spinner):
        """
            Show the view
            @param view as View
            @param spinner as Gtk.Spinner
        """
        spinner.stop()
        self.add(view)
        self.set_visible_child(view)
        self.clean_old_views(view)
