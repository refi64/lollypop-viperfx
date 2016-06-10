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
        self._scrolled.connect('leave-notify-event', self._on_leave_notify)
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

    def disable_overlays(self):
        """
            Disable children's overlay
        """
        GLib.idle_add(self._disable_overlays, self._get_children())

    def populate(self):
        pass

#######################
# PRIVATE             #
#######################
    def _disable_overlays(self, widgets):
        """
            Disable children's overlay
            @param widgets as AlbumWidget
        """
        if widgets:
            widget = widgets.pop(0)
            widget.show_overlay(False)
            GLib.idle_add(self._disable_overlays, widgets)

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

    def _on_leave_notify(self, widget, event):
        """
            Update overlays as internal widget may not have received the signal
            @param widget as Gtk.Widget
            @param event as Gdk.event
        """
        allocation = widget.get_allocation()
        if event.x <= 0 or\
           event.x >= allocation.width or\
           event.y <= 0 or\
           event.y >= allocation.height:
            self.disable_overlays()

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
            if album_id == widget.get_id():
                widget.update_cover()

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
        self._prev_scroll_value = 0
        self._scrolled.get_vadjustment().connect('value-changed',
                                                 self._on_value_changed)

    def append(self, row):
        """
            Append row to lazy queue
            @param row as Row
        """
        self._lazy_queue.append(row)

    def lazy_loading(self, widgets=[], scroll_value=0):
        """
            Load the view in a lazy way:
                - widgets first
                - _waiting_init then
            @param widgets as [AlbumSimpleWidgets]
            @param scroll_value as float
        """
        GLib.idle_add(self._lazy_loading, widgets, scroll_value)

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
            return False
        if widgets:
            widget = widgets.pop(0)
            self._lazy_queue.remove(widget)
        elif self._lazy_queue:
            widget = self._lazy_queue.pop(0)
        if widget is not None:
            widget.populate()
            if widgets:
                GLib.timeout_add(10, self.lazy_loading, widgets, scroll_value)
            else:
                GLib.idle_add(self.lazy_loading, widgets, scroll_value)

    def _is_visible(self, widget):
        """
            Is widget visible in scrolled
            @param widget as Gtk.Widget
        """
        widget_alloc = widget.get_allocation()
        scrolled_alloc = self._scrolled.get_allocation()
        try:
            (x, y) = widget.translate_coordinates(self._scrolled, 0, 0)
            return (y > -widget_alloc.height or y >= 0) and\
                y < scrolled_alloc.height
        except:
            return True

    def _lazy_or_not(self, scroll_value):
        """
            Add visible widgets to lazy queue
            @param scroll value as float
        """
        self._scroll_value = scroll_value
        widgets = []
        for child in self._lazy_queue:
            if self._is_visible(child):
                widgets.append(child)
        GLib.idle_add(self.lazy_loading, widgets, self._scroll_value)

    def _on_value_changed(self, adj):
        """
            Update scroll value and check for lazy queue
            @param adj as Gtk.Adjustment
        """
        if not self._lazy_queue:
            return False
        scroll_value = adj.get_value()
        diff = self._prev_scroll_value - scroll_value
        if diff > ArtSize.BIG or diff < -ArtSize.BIG:
            self._prev_scroll_value = scroll_value
            GLib.idle_add(self._lazy_or_not,
                          scroll_value)
