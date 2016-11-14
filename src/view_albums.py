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

from gi.repository import Gtk, GLib, Gdk

from lollypop.view import LazyLoadingView
from lollypop.widgets_album import AlbumSimpleWidget
from lollypop.pop_album import AlbumPopover
from lollypop.pop_menu import AlbumMenu, AlbumMenuPopover
from lollypop.objects import Album
from lollypop.define import Type


class AlbumsView(LazyLoadingView):
    """
        Show albums in a box
    """

    def __init__(self, genre_ids, artist_ids):
        """
            Init album view
            @param genre ids as [int]
            @param artist ids as [int]
        """
        LazyLoadingView.__init__(self, True)
        self.__signal = None
        self.__current = None
        self.__context_album_id = None
        self.__genre_ids = genre_ids
        self.__artist_ids = artist_ids
        self.__press_rect = None

        self._box = Gtk.FlowBox()
        self._box.set_filter_func(self._filter_func)
        self._box.set_selection_mode(Gtk.SelectionMode.NONE)
        self._box.connect('child-activated', self.__on_album_activated)
        self._box.connect('button-press-event', self.__on_button_press)
        # Allow lazy loading to not jump up and down
        self._box.set_homogeneous(True)
        self._box.set_max_children_per_line(1000)
        self._box.show()

        self._viewport.set_property('valign', Gtk.Align.START)
        self._viewport.set_property('margin', 5)
        self._scrolled.set_property('expand', True)

        self.add(self._scrolled)

    def populate(self, albums):
        """
            Populate albums
            @param is compilation as bool
        """
        GLib.idle_add(self.__add_albums, albums)

#######################
# PROTECTED           #
#######################
    def _get_children(self):
        """
            Return view children
            @return [AlbumWidget]
        """
        children = []
        for child in self._box.get_children():
            children.append(child)
        return children

#######################
# PRIVATE             #
#######################
    def __add_albums(self, albums):
        """
            Add albums to the view
            Start lazy loading
            @param [album ids as int]
        """
        if self._stop:
            self._stop = False
            return
        if albums:
            widget = AlbumSimpleWidget(albums.pop(0),
                                       self.__genre_ids,
                                       self.__artist_ids)
            widget.connect('overlayed', self._on_overlayed)
            self._box.insert(widget, -1)
            widget.show()
            self._lazy_queue.append(widget)
            GLib.idle_add(self.__add_albums, albums)
        else:
            GLib.idle_add(self.lazy_loading)
            if self._viewport.get_child() is None:
                self._viewport.add(self._box)

    def __on_album_activated(self, flowbox, album_widget):
        """
            Show Context view for activated album
            @param flowbox as Gtk.Flowbox
            @param album_widget as AlbumSimpleWidget
        """
        cover = album_widget.get_cover()
        if cover is None:
            return
        # If widget top not on screen, popover will fail to show
        # FIXME: Report a bug and check always true
        (x, y) = album_widget.translate_coordinates(self._scrolled, 0, 0)
        if y < 0:
            y = album_widget.translate_coordinates(self._box, 0, 0)[1]
            self._scrolled.get_allocation().height + y
            self._scrolled.get_vadjustment().set_value(y)
        if self.__press_rect is not None:
            album = Album(album_widget.id)
            if self.__genre_ids and self.__genre_ids[0] == Type.CHARTS:
                popover = AlbumMenuPopover(album, None)
                popover.set_relative_to(cover)
            elif album.is_web:
                popover = AlbumMenuPopover(album, AlbumMenu(album, True))
                popover.set_relative_to(cover)
            else:
                popover = Gtk.Popover.new_from_model(cover,
                                                     AlbumMenu(album, True))
            popover.set_position(Gtk.PositionType.BOTTOM)
            popover.set_pointing_to(self.__press_rect)
        else:
            allocation = self.get_allocation()
            (x, top_height) = album_widget.translate_coordinates(self, 0, 0)
            bottom_height = allocation.height -\
                album_widget.get_allocation().height -\
                top_height
            if bottom_height > top_height:
                height = bottom_height
            else:
                height = top_height
            popover = AlbumPopover(album_widget.id,
                                   self.__genre_ids,
                                   self.__artist_ids,
                                   allocation.width,
                                   height,
                                   False)
            popover.set_relative_to(cover)
            popover.set_position(Gtk.PositionType.BOTTOM)
        album_widget.show_overlay(False)
        album_widget.lock_overlay(True)
        popover.connect('closed', self.__on_album_popover_closed, album_widget)
        popover.show()
        self.__current = album_widget
        cover.set_opacity(0.9)

    def __on_album_popover_closed(self, popover, album_widget):
        """
            Remove overlay and restore opacity
            @param popover as Gtk.Popover
            @param album_widget as AlbumWidget
        """
        album_widget.lock_overlay(False)
        album_widget.get_cover().set_opacity(1)

    def __on_button_press(self, flowbox, event):
        """
            Store pressed button
            @param flowbox as Gtk.Flowbox
            @param event as Gdk.EventButton
        """
        if event.button == 1:
            self.__press_rect = None
        else:
            self.__press_rect = Gdk.Rectangle()
            self.__press_rect.x = event.x
            self.__press_rect.y = event.y
            self.__press_rect.width = self.__press_rect.height = 1
            event.button = 1
