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

from threading import Thread

from lollypop.view import View
from lollypop.view_container import ViewContainer
from lollypop.define import Lp, Type
from lollypop.widgets_album import AlbumDetailedWidget


class ArtistAlbumsView(View):
    """
        Show artist albums and tracks
    """

    def __init__(self, artist_id, genre_id):
        """
            Init ArtistAlbumsView
            @param artist id as int (Current if None)
            @param genre id as int
        """
        View.__init__(self)
        self._artist_id = artist_id
        self._genre_id = genre_id

        self._albumbox = Gtk.Grid()
        self._albumbox.set_row_spacing(20)
        self._albumbox.set_property("orientation", Gtk.Orientation.VERTICAL)
        self._albumbox.show()

        self._scrolledWindow.set_property('expand', True)
        self._viewport.set_property("valign", Gtk.Align.START)
        self._viewport.add(self._albumbox)
        self.attach(self._scrolledWindow, 0, 1, 1, 1)

    def populate(self, albums):
        """
            Populate the view
        """
        if albums:
            self._add_albums(albums)

#######################
# PRIVATE             #
#######################
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
        size_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
        widget = AlbumDetailedWidget(albums.pop(0),
                                     self._genre_id,
                                     self._artist_id is not None,
                                     size_group)
        widget.connect('finished', self._on_album_finished, albums)
        widget.show()
        t = Thread(target=widget.populate)
        t.daemon = True
        t.start()
        self._albumbox.add(widget)

    def _on_album_finished(self, album, albums):
        """
            Add another album
            @param album as AlbumDetailedWidget
            @param [album ids as int]
        """
        if albums and not self._stop:
            self._add_albums(albums)
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
        view = ArtistAlbumsView(None, None)
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
            albums = [Lp.player.current_track.album_id]
        else:
            albums = Lp.artists.get_albums(artist_id)
        return albums

    def do_get_preferred_width(self):
        """
            Set 0 to force popover to not expand
        """
        return (0, 0)
