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

from lollypop.view import View
from lollypop.view_container import ViewContainer
from lollypop.define import Lp, Type
from lollypop.widgets_album import AlbumDetailedWidget


class ArtistAlbumsView(View):
    """
        Show artist albums and tracks
    """

    def __init__(self, artist_ids, genre_ids):
        """
            Init ArtistAlbumsView
            @param artist ids as [int]
            @param genre ids as [int]
        """
        View.__init__(self)
        self._artist_ids = artist_ids
        self._genre_ids = genre_ids
        self._albums = []
        self._albums_count = 0

        self._albumbox = Gtk.Grid()
        self._albumbox.set_row_spacing(20)
        self._albumbox.set_property("orientation", Gtk.Orientation.VERTICAL)
        self._albumbox.show()

        self._scrolled.set_property('expand', True)
        self._viewport.set_property("valign", Gtk.Align.START)
        self._viewport.add(self._albumbox)
        self.attach(self._scrolled, 0, 1, 1, 1)

    def populate(self, albums):
        """
            Populate the view
        """
        self._albums = list(albums)
        if albums:
            self._albums_count = len(albums)
            self._add_albums()

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
        for child in self._get_children():
            child.stop()

#######################
# PRIVATE             #
#######################
    def _get_children(self):
        """
            Return view children
            @return [AlbumWidget]
        """
        return self._albumbox.get_children()

    def _add_albums(self):
        """
            Pop an album and add it to the view,
            repeat operation until album list is empty
            @param [album ids as int]
        """
        widget = AlbumDetailedWidget(self._albums.pop(0),
                                     self._genre_ids,
                                     self._artist_ids)
        widget.connect('populated', self._on_populated)
        # Not needed if only one album
        if self._albums_count == 1:
            widget.disable_play_all()
        widget.show()
        widget.populate()
        self._albumbox.add(widget)

    def _on_populated(self, widget):
        """
            Add another album/disc
            @param widget as AlbumDetailedWidget
        """
        if not widget.is_populated():
            widget.populate()
        elif self._albums and not self._stop:
            self._add_albums()
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
        self._current = (Type.NONE, Type.NONE)

    def populate(self, artist_id, album_id):
        """
            Populate the view
            @thread safe
        """
        if (artist_id, album_id) != self._current:
            self._current = (artist_id, album_id)
            if album_id == Type.NONE:
                albums = self._get_albums(artist_id)
            else:
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
        view = ArtistAlbumsView([self._current[0]], [])
        view.show()
        view.populate(albums)
        self.add(view)
        self.set_visible_child(view)
        self.clean_old_views(view)

    def _get_albums(self, artist_id):
        """
            Get albums
            @return album ids as [int]
        """
        if artist_id == Type.COMPILATIONS:
            albums = [Lp().player.current_track.album_id]
        else:
            albums = Lp().artists.get_albums(artist_id)
        return albums

    def do_get_preferred_width(self):
        """
            Set 0 to force popover to not expand
        """
        return (0, 0)
