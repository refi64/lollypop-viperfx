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

from lollypop.view import View, LazyLoadingView
from lollypop.widgets_album import AlbumSimpleWidget
from lollypop.pop_album import AlbumPopover
from lollypop.pop_menu import AlbumMenu
from lollypop.objects import Album


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
        LazyLoadingView.__init__(self)
        self._signal = None
        self._context_album_id = None
        self._genre_ids = genre_ids
        self._artist_ids = artist_ids
        self._press_rect = None

        self._albumbox = Gtk.FlowBox()
        self._albumbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._albumbox.connect('child-activated', self._on_album_activated)
        self._albumbox.connect('button-press-event', self._on_button_press)
        self._albumbox.set_homogeneous(True)
        self._albumbox.set_max_children_per_line(1000)
        self._albumbox.show()

        self._viewport.set_property('valign', Gtk.Align.START)
        self._viewport.set_property('margin', 5)
        self._scrolled.set_property('expand', True)
        self.add(self._scrolled)

    def populate(self, albums):
        """
            Populate albums
            @param is compilation as bool
        """
        GLib.idle_add(self._add_albums, albums)

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
    def _disable_overlays(self, widgets):
        """
            Disable children's overlay
            @param widgets as AlbumWidget
        """
        View._disable_overlays(self, widgets)

    def _get_children(self):
        """
            Return view children
            @return [AlbumWidget]
        """
        children = []
        for child in self._albumbox.get_children():
            children.append(child)
        return children

    def _add_albums(self, albums):
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
                                       self._genre_ids,
                                       self._artist_ids)
            self._albumbox.insert(widget, -1)
            widget.show()
            self._lazy_queue.append(widget)
            GLib.idle_add(self._add_albums, albums)
        else:
            GLib.idle_add(self.lazy_loading)
            if self._viewport.get_child() is None:
                self._viewport.add(self._albumbox)

    def _on_album_activated(self, flowbox, album_widget):
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
            y = album_widget.translate_coordinates(self._albumbox, 0, 0)[1]
            self._scrolled.get_allocation().height + y
            self._scrolled.get_vadjustment().set_value(y)
        if self._press_rect is not None:
            pop_menu = AlbumMenu(Album(album_widget.get_id()))
            popover = Gtk.Popover.new_from_model(cover, pop_menu)
            popover.set_position(Gtk.PositionType.BOTTOM)
            popover.set_pointing_to(self._press_rect)
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
            popover = AlbumPopover(album_widget.get_id(),
                                   self._genre_ids,
                                   self._artist_ids,
                                   allocation.width,
                                   height,
                                   False)
            popover.set_relative_to(cover)
            popover.set_position(Gtk.PositionType.BOTTOM)
        album_widget.show_overlay(False)
        album_widget.lock_overlay(True)
        popover.connect('closed', self._on_popover_closed, album_widget)
        popover.show()
        cover.set_opacity(0.9)

    def _on_popover_closed(self, popover, album_widget):
        """
            @param popover as Gtk.Popover
            @param album_widget as AlbumWidget
        """
        album_widget.lock_overlay(False)
        album_widget.get_cover().set_opacity(1)

    def _on_button_press(self, flowbox, event):
        """
            Store pressed button
            @param flowbox as Gtk.Flowbox
            @param event as Gdk.EventButton
        """
        if event.button == 1:
            self._press_rect = None
        else:
            self._press_rect = Gdk.Rectangle()
            self._press_rect.x = event.x
            self._press_rect.y = event.y
            self._press_rect.width = self._press_rect.height = 1
            event.button = 1
