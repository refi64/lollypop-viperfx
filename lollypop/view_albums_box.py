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

from gi.repository import GLib, Gtk

from gettext import gettext as _

from lollypop.view_flowbox import FlowBoxView
from lollypop.widgets_album_simple import AlbumSimpleWidget
from lollypop.define import App, Type, ViewType
from lollypop.objects import Album
from lollypop.utils import get_icon_name
from lollypop.shown import ShownLists
from lollypop.controller_view import ViewController, ViewControllerType


class AlbumsBoxView(FlowBoxView, ViewController):
    """
        Show albums in a box
    """

    def __init__(self, genre_ids, artist_ids, view_type=ViewType.SCROLLED):
        """
            Init album view
            @param genre ids as [int]
            @param artist ids as [int]
            @param view_type as ViewType
        """
        FlowBoxView.__init__(self, view_type)
        ViewController.__init__(self, ViewControllerType.ALBUM)
        self._widget_class = AlbumSimpleWidget
        self.__genre_ids = genre_ids
        self.__artist_ids = artist_ids
        if genre_ids and genre_ids[0] < 0:
            if genre_ids[0] == Type.WEB and\
                    GLib.find_program_in_path("youtube-dl") is None:
                self._empty_message = _("Missing youtube-dl command")
            else:
                self._empty_message = ShownLists.IDS[genre_ids[0]][0]
            self._empty_icon_name = get_icon_name(genre_ids[0])
        if view_type & ViewType.SMALL:
            self._scrolled.set_policy(Gtk.PolicyType.NEVER,
                                      Gtk.PolicyType.NEVER)

    def insert_album(self, album, position):
        """
            Add a new album
            @param album as Album
            @param pos as int
        """
        widget = AlbumSimpleWidget(album, self.__genre_ids,
                                   self.__artist_ids, self._view_type)
        self._box.insert(widget, position)
        widget.show()
        widget.populate()

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
                                        self.__genre_ids,
                                        self.__artist_ids,
                                        self._view_type)
        if widget is not None:
            widget.connect("overlayed", self.on_overlayed)

    def _on_album_updated(self, scanner, album_id, added):
        """
            Handles changes in collection
            @param scanner as CollectionScanner
            @param album_id as int
            @param added as bool
        """
        album_ids = App().window.container.get_view_album_ids(
                                            self.__genre_ids,
                                            self.__artist_ids)
        if album_id not in album_ids:
            return
        index = album_ids.index(album_id)
        self.insert_album(Album(album_id), index)

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
        if not self._view_type & ViewType.SMALL and\
                FlowBoxView._on_item_activated(self, flowbox, album_widget):
            return
        if album_widget.artwork is None:
            return
        App().window.container.show_view(Type.ALBUM, album_widget.album)

    def _on_map(self, widget):
        """
            Set active ids
        """
        if self._view_type & ViewType.SMALL:
            return
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
