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

from gi.repository import Gtk, GLib, Gdk

from threading import Thread

from lollypop.view import View
from lollypop.view_container import ViewContainer
from lollypop.define import Lp, Type
import lollypop.widgets_album
import lollypop.pop_infos


class ArtistView(View):
    """
        Show artist albums and tracks
    """

    def __init__(self, artist_id, genre_id):
        """
            Init ArtistView
            @param artist id as int (Current if None)
            @param genre id as int
        """
        View.__init__(self)
        self._artist_id = artist_id
        self._genre_id = genre_id
        self._signal_id = None

        if artist_id is not None:
            self._popover = lollypop.pop_infos.InfosPopover(artist_id, False)
            builder = Gtk.Builder()
            builder.add_from_resource('/org/gnome/Lollypop/ArtistView.ui')
            builder.connect_signals(self)
            self.attach(builder.get_object('ArtistView'), 0, 0, 1, 1)
            builder.get_object('artist').set_label(
                                                Lp.artists.get_name(artist_id))

        self._albumbox = Gtk.Grid()
        self._albumbox.set_row_spacing(20)
        self._albumbox.set_property("orientation", Gtk.Orientation.VERTICAL)
        self._albumbox.show()

        self._scrolledWindow.set_property('expand', True)
        self._viewport.set_property("valign", Gtk.Align.START)
        self._viewport.add(self._albumbox)
        self.add(self._scrolledWindow)

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
        widget = lollypop.widgets_album.AlbumDetailedWidget(
                                                albums.pop(0),
                                                self._genre_id,
                                                self._artist_id is not None,
                                                False,
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

    def _on_label_realize(self, eventbox):
        """
            Change pointer on label
            @param eventbox as Gtk.EventBox
        """
        if lollypop.pop_infos.InfosPopover.should_be_shown() and\
                self._artist_id != Type.COMPILATIONS:
            eventbox.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND1))

    def _on_label_button_release(self, eventbox, event):
        """
            On clicked label, show artist informations in a popover
            @param eventbox as Gtk.EventBox
            @param event as Gdk.Event
        """
        if lollypop.pop_infos.InfosPopover.should_be_shown() and\
                self._artist_id != Type.COMPILATIONS:
            self._popover.set_relative_to(eventbox)
            self._popover.show()


class CurrentArtistView(ViewContainer):
    """
        Show albums from current artist
    """

    def __init__(self, artist_id=None):
        """
            Init popover
        """
        ViewContainer.__init__(self, 1000)
        self.connect('destroy', self._on_destroy)
        self._artist_id = artist_id
        self._on_screen_id = None
        self._signal1_id = Lp.player.connect("current-changed",
                                             self._update_content)
        if self._artist_id is None:
            self._signal2_id = Lp.player.connect("current-changed",
                                                 self._update_content)
        else:
            self._signal2_id = None

    def populate(self):
        """
            Populate the view
            @thread safe
        """
        if self._artist_id is None:
            if Lp.player.current_track.album_artist_id == Type.COMPILATIONS:
                new_id = Lp.player.current_track.album_id
            else:
                new_id = Lp.player.current_track.album_artist_id
        else:
            new_id = self._artist_id
        if self._on_screen_id != new_id:
            self._on_screen_id = new_id
            albums = self._get_albums(new_id)
            GLib.idle_add(self._populate, albums)

#######################
# PRIVATE             #
#######################
    def _on_destroy(self, widget):
        """
            Disconnect signal
            @param widget as Gtk.Widget
        """
        self._on_screen_id = None
        if self._signal1_id is not None:
            Lp.player.disconnect(self._signal1_id)
        if self._signal2_id is not None:
            Lp.player.disconnect(self._signal2_id)

    def _populate(self, albums):
        """
            Populate view and make it visible
            @param albums as [albums ids as int]
        """
        view = ArtistView(None, None)
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
        sql = Lp.db.get_cursor()
        if artist_id == Type.COMPILATIONS:
            albums = [Lp.player.current_track.album_id]
        else:
            albums = Lp.artists.get_albums(artist_id, sql)
        sql.close()
        return albums

    def _update_content(self, player):
        """
            Update the content view
            @param player as Player
            @param track id as int
        """
        if self.is_visible():
            self.populate()

    def do_get_preferred_width(self):
        """
            Set 0 to force popover to not expand
        """
        return (0, 0)
