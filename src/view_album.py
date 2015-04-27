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

from _thread import start_new_thread

from lollypop.view import View
from lollypop.view_container import ViewContainer
from lollypop.widgets_album import AlbumSimpleWidget, AlbumDetailedWidget
from lollypop.define import Objects, Navigation, ArtSize
from lollypop.utils import translate_artist_name


# Artist view is a vertical grid with album songs widgets
class ArtistView(View):
    """
        Init ArtistView ui with a scrolled grid of AlbumDetailedWidget
        @param artist id as int
        @param show_artist_details as bool
    """
    def __init__(self, artist_id, show_artist_details):
        View.__init__(self)
        self._artist_id = artist_id
        self._signal_id = None

        if show_artist_details:
            builder = Gtk.Builder()
            builder.add_from_resource('/org/gnome/Lollypop/ArtistView.ui')
            self.attach(builder.get_object('ArtistView'),0, 0, 1, 1)
            artist_name = Objects.artists.get_name(artist_id)
            artist_name = translate_artist_name(artist_name)
            builder.get_object('artist').set_label(artist_name)

        self._show_menu = show_artist_details

        self._albumbox = Gtk.Grid()
        self._albumbox.set_row_spacing(20)
        self._albumbox.set_property("orientation", Gtk.Orientation.VERTICAL)
        self._albumbox.show()

        self._scrolledWindow.set_property('expand', True)
        self._viewport.set_property("valign", Gtk.Align.START)
        self._viewport.add(self._albumbox)
        self.add(self._scrolledWindow)

    """
        Populate the view, can be threaded
        @param navigation id as int
    """
    def populate(self, navigation_id):
        sql = Objects.db.get_cursor()
        if self._artist_id == Navigation.COMPILATIONS:
            albums = Objects.albums.get_compilations(navigation_id,
                                                     sql)
        elif navigation_id == Navigation.ALL:
            albums = Objects.albums.get_ids(self._artist_id,
                                            None,
                                            sql)
        else:
            albums = Objects.albums.get_ids(self._artist_id,
                                            navigation_id,
                                            sql)
        GLib.idle_add(self._add_albums, albums, navigation_id)
        sql.close()

#######################
# PRIVATE             #
#######################
    """
        Return view children
        @return [AlbumWidget]
    """
    def _get_children(self):
        return self._albumbox.get_children()

    """
        Pop an album and add it to the view,
        repeat operation until album list is empty
        @param [album ids as int]
        @param genre id as int
    """
    def _add_albums(self, albums, genre_id):
        size_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
        if albums and not self._stop:
            widget = AlbumDetailedWidget(albums.pop(0),
                                         genre_id,
                                         self._show_menu,
                                         False,
                                         size_group)
            widget.show()
            start_new_thread(widget.populate, ())
            self._albumbox.add(widget)
            GLib.idle_add(self._add_albums, albums, genre_id)
        else:
            self._stop = False


# Album contextual view
class AlbumContextView(View):
    """
        Init context
        @param main view widget
    """
    def __init__(self, widget):
        View.__init__(self)
        self._widget = widget
        self._viewport.add(widget)
        self._viewport.show()
        self._scrolledWindow.set_min_content_height(ArtSize.BIG+35)
        self._scrolledWindow.show()
        self.add(self._scrolledWindow)

#######################
# PRIVATE             #
#######################
    """
        Return view children
        @return [AlbumWidget]
    """
    def _get_children(self):
        return [self._widget]


# Album view is a flowbox of albums widgets with album name and artist name
class AlbumView(View):
    """
        Init album view ui with a scrolled flow box and a scrolled context view
        @param genre id as int
    """
    def __init__(self, genre_id):
        View.__init__(self)
        self._signal = None
        self._context_album_id = None
        self._genre_id = genre_id
        self._albumsongs = None
        self._context_widget = None

        self._albumbox = Gtk.FlowBox()
        self._albumbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._albumbox.connect("child-activated", self._on_album_activated)
        self._albumbox.set_max_children_per_line(100)
        self._albumbox.show()

        self._viewport.set_property("valign", Gtk.Align.START)
        self._viewport.add(self._albumbox)
        self._scrolledWindow.set_property('expand', True)

        self._context = ViewContainer(500)

        separator = Gtk.Separator()
        separator.show()

        self._paned = Gtk.Paned.new(Gtk.Orientation.VERTICAL)
        self._paned.pack1(self._scrolledWindow)
        self._paned.pack2(self._context, True, False)
        height = Objects.settings.get_value(
                                         'paned-context-height').get_int32()
        # We set a stupid max value, safe as self._context is shrinked
        if height == -1:
            height = Objects.window.get_allocated_height()
        self._paned.set_position(height)
        self._paned.connect('notify::position', self._on_position_notify)
        self._paned.show()
        self.add(self._paned)

    """
        Populate albums, thread safe
        @param is compilation as bool
    """
    def populate(self, is_compilation):
        sql = Objects.db.get_cursor()
        if self._genre_id == Navigation.ALL:
            albums = Objects.albums.get_ids(None, None, sql)
        elif self._genre_id == Navigation.POPULARS:
            albums = Objects.albums.get_populars(sql)
        elif self._genre_id == Navigation.RECENTS:
            albums = Objects.albums.get_recents(sql)
        elif is_compilation:
            albums = Objects.albums.get_compilations(self._genre_id,
                                                     sql)
        else:
            albums = Objects.albums.get_ids(None, self._genre_id, sql)
        GLib.idle_add(self._add_albums, albums)
        sql.close()

#######################
# PRIVATE             #
#######################
    """
        Return view children
        @return [AlbumWidget]
    """
    def _get_children(self):
        children = []
        for child in self._albumbox.get_children():
            for widget in child.get_children():
                children.append(widget)
        return children

    """
        populate context view
        @param album id as int
    """
    def _populate_context(self, album_id):
        size_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
        self._context_widget = AlbumDetailedWidget(album_id,
                                                   self._genre_id,
                                                   True,
                                                   True,
                                                   size_group)
        start_new_thread(self._context_widget.populate, ())
        self._context_widget.show()
        view = AlbumContextView(self._context_widget)
        view.show()
        self._context.add(view)
        self._context.set_visible_child(view)
        self._context.clean_old_views(view)

    """
        Save paned position
        @param paned as Gtk.Paned
        @param param as Gtk.Param
    """
    def _on_position_notify(self, paned, param):
        Objects.settings.set_value(
                            'paned-context-height',
                            GLib.Variant('i', paned.get_position()))
        return False

    """
        Show Context view for activated album
        @param flowbox, children
    """
    def _on_album_activated(self, flowbox, child):
        if self._context_album_id == child.get_child().get_id():
            if Objects.settings.get_value('auto-play'):
                Objects.player.play_album(self._context_album_id)
            else:
                self._context_album_id = None
                self._context.hide()
        else:
            self._context_album_id = child.get_child().get_id()
            self._populate_context(self._context_album_id)
            self._context.show()

    """
        Pop an album and add it to the view,
        repeat operation until album list is empty
        @param [album ids as int]
    """
    def _add_albums(self, albums):
        if albums and not self._stop:
            widget = AlbumSimpleWidget(albums.pop(0))
            widget.show()
            self._albumbox.insert(widget, -1)
            GLib.idle_add(self._add_albums, albums)
        else:
            self._stop = False

