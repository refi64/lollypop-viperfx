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

from gi.repository import Gtk, GLib

from lollypop.view_flowbox import FlowBoxView
from lollypop.widgets_album_simple import AlbumSimpleWidget
from lollypop.define import ArtSize, App
from lollypop.controller_view import ViewController, ViewControllerType


class AlbumsBoxView(FlowBoxView, ViewController):
    """
        Show albums in a box
    """

    def __init__(self, genre_ids, artist_ids):
        """
            Init album view
            @param genre ids as [int]
            @param artist ids as [int]
        """
        FlowBoxView.__init__(self)
        ViewController.__init__(self, ViewControllerType.ALBUM)
        self._widget_class = AlbumSimpleWidget
        self.__genre_ids = genre_ids
        self.__artist_ids = artist_ids

#######################
# PROTECTED           #
#######################
    def _add_items(self, album_ids):
        """
            Add albums to the view
            Start lazy loading
            @param album ids as [int]
        """
        widget = FlowBoxView._add_items(self, album_ids,
                                        self.__genre_ids, self.__artist_ids)
        if widget is not None:
            widget.connect("overlayed", self.on_overlayed)

    def _on_artwork_changed(self, artwork, album_id):
        """
            Update children artwork if matching album id
            @param artwork as Artwork
            @param album_id as int
        """
        for child in self._box.get_children():
            if child.album.id == album_id:
                child.set_artwork()

    def _on_item_activated(self, flowbox, album_widget):
        """
            Show Context view for activated album
            @param flowbox as Gtk.Flowbox
            @param album_widget as AlbumSimpleWidget
        """
        if FlowBoxView._on_item_activated(self, flowbox, album_widget):
            return
        if album_widget.artwork is None:
            return
        # If widget top not on screen, popover will fail to show
        # FIXME: Report a bug and check always true
        (x, y) = album_widget.translate_coordinates(self._scrolled, 0, 0)
        if y < 0:
            y = album_widget.translate_coordinates(self._box, 0, 0)[1]
            self._scrolled.get_allocation().height + y
            self._scrolled.get_vadjustment().set_value(y)
        from lollypop.pop_album import AlbumPopover
        popover = AlbumPopover(album_widget.album, ArtSize.NONE)
        popover.set_relative_to(album_widget.artwork)
        popover.set_position(Gtk.PositionType.BOTTOM)
        album_widget.show_overlay(False)
        album_widget.lock_overlay(True)
        popover.connect("closed", self.__on_album_popover_closed, album_widget)
        popover.popup()
        album_widget.artwork.set_opacity(0.9)

    def _on_map(self, widget):
        """
            Set active ids
        """
        if self.__genre_ids:
            App().settings.set_value("state-one-ids",
                                     GLib.Variant("ai", self.__genre_ids))
            App().settings.set_value("state-two-ids",
                                     GLib.Variant("ai", self.__artist_ids))
        else:
            App().settings.set_value("state-one-ids",
                                     GLib.Variant("ai", self.__artist_ids))
            App().settings.set_value("state-two-ids",
                                     GLib.Variant("ai", []))

#######################
# PRIVATE             #
#######################
    def __on_album_popover_closed(self, popover, album_widget):
        """
            Remove overlay and restore opacity
            @param popover as Popover
            @param album_widget as AlbumWidget
        """
        album_widget.lock_overlay(False)
        album_widget.artwork.set_opacity(1)
