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

from lollypop.define import Lp, ArtSize


class View(Gtk.Grid):
    """
        Generic view
    """

    def __init__(self):
        """
            Init view
        """
        Gtk.Grid.__init__(self)
        self.connect('destroy', self._on_destroy)
        self.set_property('orientation', Gtk.Orientation.VERTICAL)
        self.set_border_width(0)
        self._current_signal = Lp().player.connect('current-changed',
                                                   self._on_current_changed)
        self._cover_signal = Lp().art.connect('album-artwork-changed',
                                              self._on_cover_changed)

        # Stop populate thread
        self._stop = False
        self._new_ids = []

        self._scrolled = Gtk.ScrolledWindow()
        self._scrolled.connect('leave-notify-event', self._on_leave_event)
        self._scrolled.show()
        self._viewport = Gtk.Viewport()
        self._scrolled.add(self._viewport)
        self._viewport.show()

    def stop(self):
        """
            Stop populating
        """
        self._stop = True
        for child in self._get_children():
            child.stop()

    def update_children(self):
        """
            Update children
        """
        GLib.idle_add(self._update_widgets, self._get_children())

    def update_overlays(self):
        """
            Update overlays
        """
        GLib.idle_add(self._update_overlays, self._get_children())

    def populate(self):
        pass

#######################
# PRIVATE             #
#######################
    def _on_leave_event(self, widget, event):
        """
            Update children's overlay
        """
        allocation = widget.get_allocation()
        if event.x < 5 or\
           event.x > allocation.width - 5 or\
           event.y < 5 or\
           event.y > allocation.height - 5:
            self._update_overlays(self._get_children())

    def _update_overlays(self, widgets):
        """
            Update children's overlay
            @param widgets as AlbumWidget
        """
        if widgets:
            widget = widgets.pop(0)
            widget.update_overlay()
            GLib.idle_add(self._update_overlays, widgets)

    def _update_widgets(self, widgets):
        """
            Update all widgets
            @param widgets as AlbumWidget
        """
        if widgets:
            widget = widgets.pop(0)
            widget.update_state()
            widget.update_playing_indicator()
            GLib.idle_add(self._update_widgets, widgets)

    def _get_children(self):
        """
            Return view children
        """
        return []

    def _on_destroy(self, widget):
        """
            Remove signals on unamp
            @param widget as Gtk.Widget
        """
        if self._current_signal:
            Lp().player.disconnect(self._current_signal)
            self._current_signal = None
        if self._cover_signal:
            Lp().art.disconnect(self._cover_signal)
            self._cover_signal = None

    def _on_cover_changed(self, art, album_id):
        """
            Update album cover in view
            @param art as Art
            @param album id as int
        """
        for widget in self._get_children():
            widget.update_cover(album_id)

    def _on_current_changed(self, player):
        """
            Current song changed
            @param player as Player
        """
        GLib.idle_add(self._update_widgets, self._get_children())


class LazyLoadingView(View):
    """
        Lazy loading for view
    """
    def __init__(self):
        """
            Init lazy loading
        """
        View.__init__(self)
        self._lazy_queue = []  # Widgets not initialized
        self._scroll_value = 0
        self._timeout_id = None
        self._scrolled.get_vadjustment().connect('value-changed',
                                                 self._on_value_changed)

#######################
# PRIVATE             #
#######################
    def _lazy_loading(self, widgets=[], scroll_value=0):
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
            widget.init_widget()
            if self._timeout_id is None:
                GLib.idle_add(self._lazy_loading, widgets, scroll_value)
            else:
                GLib.timeout_add(50, self._lazy_loading,
                                 widgets, scroll_value)

    def _is_visible(self, widget):
        """
            Is widget visible in scrolled
            @param widget as Gtk.Widget
        """
        widget_alloc = widget.get_allocation()
        scrolled_alloc = self._scrolled.get_allocation()
        try:
            (x, y) = widget.translate_coordinates(self._scrolled, 0, 0)
            return (y > -widget_alloc.height-ArtSize.BIG or y >= 0) and\
                y < scrolled_alloc.height+ArtSize.BIG
        except:
            return True

    def _lazy_or_not(self, adj):
        """
            Add visible widgets to lazy queue
            @param adj as Gtk.Adjustment
        """
        self._timeout_id = None
        self._scroll_value = adj.get_value()
        widgets = []
        for child in self._lazy_queue:
            if self._is_visible(child):
                widgets.append(child)
        GLib.idle_add(self._lazy_loading, widgets, self._scroll_value)

    def _on_value_changed(self, adj):
        """
            Update scroll value and check for lazy queue
            @param adj as Gtk.Adjustment
        """
        if self._timeout_id is not None:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = None
        if not self._lazy_queue:
            return
        self._timeout_id = GLib.timeout_add(250, self._lazy_or_not, adj)
