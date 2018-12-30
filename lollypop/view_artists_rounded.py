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

from gi.repository import GLib

from lollypop.view_flowbox import FlowBoxView
from lollypop.define import App, Type, ArtSize
from locale import strcoll
from lollypop.widgets_artist_rounded import RoundedArtistWidget


class RoundedArtistsView(FlowBoxView):
    """
        Show artists in a FlowBox
    """

    def __init__(self):
        """
            Init decade view
        """
        FlowBoxView.__init__(self)
        self.__lazy_queue_backup = None
        self._widget_class = RoundedArtistWidget
        self.connect("realize", self.__on_realize)
        self.connect("unrealize", self.__on_unrealize)
        self.connect("destroy", self.__on_destroy)

    def add_value(self, item):
        """
            Insert item
            @param item as (int, str, str)
        """
        for child in self._box.get_children():
            if child.data == item[0]:
                return
        # Setup sort on insert
        self._box.set_sort_func(self.__sort_func)
        widget = RoundedArtistWidget(item, ArtSize.BIG)
        widget.populate()
        widget.show()
        self._box.insert(widget, -1)

    def remove_value(self, item_id):
        """
            Remove item from devices
            @param item_id as int
        """
        for child in self._box.get_children():
            if child.data == item_id:
                child.destroy()
                break

    def stop(self):
        """
            We want this view to be populated anyway (no sidebar mode)
        """
        if self._lazy_queue is not None:
            self.__lazy_queue_backup = self._lazy_queue
        FlowBoxView.stop(self)

    @property
    def should_destroy(self):
        return False

#######################
# PROTECTED           #
#######################
    def _add_items(self, items, *args):
        """
            Add artists to the view
            Start lazy loading
            @param items as [(int, str, str)]
        """
        if App().window.is_adaptive:
            FlowBoxView._add_items(self, items, ArtSize.LARGE)
        else:
            FlowBoxView._add_items(self, items, ArtSize.BIG)

    def _on_item_activated(self, flowbox, widget):
        """
            Show artist albums
            @param flowbox as Gtk.Flowbox
            @param widget as ArtistRoundedWidget
        """
        App().window.container.show_view(widget.data)

    def _on_map(self, widget):
        """
            Set active ids
        """
        # Restore lazy loading queue
        if self.__lazy_queue_backup:
            self._lazy_queue = self.__lazy_queue_backup
            self.__lazy_queue_backup = None
        elif self._items:
            self._lazy_queue = []
        # Force reloading remaining items
        # If empty, it will load lazy loading queue anyway
        if self._items:
            self._add_items(self._items)
        App().settings.set_value("state-one-ids",
                                 GLib.Variant("ai", [Type.ARTISTS]))
        App().settings.set_value("state-two-ids",
                                 GLib.Variant("ai", []))

#######################
# PRIVATE             #
#######################
    def __sort_func(self, widget1, widget2):
        """
            Sort function
            @param widget1 as RoundedArtistWidget
            @param widget2 as RoundedArtistWidget
        """
        # Static vs static
        if widget1.data < 0 and widget2.data < 0:
            return widget1.data < widget2.data
        # Static entries always on top
        elif widget2.data < 0:
            return True
        # Static entries always on top
        if widget1.data < 0:
            return False
        # String comparaison for non static
        else:
            return strcoll(widget1.sortname, widget2.sortname)

    def __on_destroy(self, widget):
        """
            Stop loading
            @param widget as Gtk.Widget
        """
        RoundedArtistsView.stop(self)

    def __on_artist_artwork_changed(self, art, prefix):
        """
            Update artwork if needed
            @param art as Art
            @param prefix as str
        """
        for child in self._box.get_children():
            if child.name == prefix:
                child.set_artwork()

    def __on_realize(self, widget):
        """
            Connect signals
            @param widget as Gtk.Widget
        """
        self.__art_signal_id = App().art.connect(
                                              "artist-artwork-changed",
                                              self.__on_artist_artwork_changed)

    def __on_unrealize(self, widget):
        """
            Connect signals
            @param widget as Gtk.Widget
        """
        if self.__art_signal_id is not None:
            App().art.disconnect(self.__art_signal_id)
