# Copyright (c) 2014-2017 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from lollypop.define import Lp


class View(Gtk.Grid):
    """
        Generic view
    """

    def __init__(self, filtered=False):
        """
            Init view
            @param filtered as bool
        """
        Gtk.Grid.__init__(self)
        self.connect("destroy", self._on_destroy)
        self.__overlayed = None
        self.set_property("orientation", Gtk.Orientation.VERTICAL)
        self.set_border_width(0)
        self.__current_signal = Lp().player.connect("current-changed",
                                                    self._on_current_changed)
        self.__duration_signal = Lp().player.connect("duration-changed",
                                                     self._on_duration_changed)
        self.__cover_signal = Lp().art.connect("album-artwork-changed",
                                               self.__on_cover_changed)

        # Stop populate thread
        self._stop = False
        self.__new_ids = []

        if filtered:
            self._filter = ""
            grid = Gtk.Grid()
            grid.set_column_spacing(2)
            self.__search_entry = Gtk.SearchEntry.new()
            self.__search_entry.connect("search-changed",
                                        self._on_search_changed)
            self.__search_entry.connect("key-press-event",
                                        self.__on_key_press)
            self.__search_entry.set_size_request(400, -1)
            self.__search_entry.show()
            button = Gtk.Button.new_from_icon_name("window-close-symbolic",
                                                   Gtk.IconSize.MENU)
            button.set_relief(Gtk.ReliefStyle.NONE)
            button.connect("clicked", self.__on_button_clicked)
            button.show()
            grid.add(self.__search_entry)
            grid.add(button)
            grid.show()
            self.__search_bar = Gtk.SearchBar.new()
            self.__search_bar.add(grid)
            self.add(self.__search_bar)
        else:
            self._filter = None

        self._scrolled = Gtk.ScrolledWindow()
        self._scrolled.connect("leave-notify-event", self.__on_leave_notify)
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

    def disable_overlay(self):
        """
            Disable overlay widget
        """
        if self.__overlayed is not None:
            self.__overlayed.show_overlay(False)

    def update_children(self):
        """
            Update children
        """
        GLib.idle_add(self.__update_widgets, self._get_children())

    def set_search_mode(self):
        """
           Set search mode
        """
        if self._filter is not None:
            enable = not self.__search_bar.get_search_mode()
            Lp().window.enable_global_shortcuts(not enable)
            self.__search_bar.show() if enable else self.__search_bar.hide()
            self.__search_bar.set_search_mode(enable)
            if enable:
                self.__search_entry.grab_focus()

    @property
    def filtered(self):
        """
            True if view filtered
            @return bool
        """
        return self._filter is not None and self._filter != ""

    def populate(self):
        pass

#######################
# PROTECTED           #
#######################
    def _filter_func(self, child):
        """
            Filter function for a Gtk.FlowBox/GtkListBox
            @param child as Gtk.FlowBoxChild/Gtk.ListBoxChild
        """
        if not self.filtered:
            return True
        filter = self._filter.lower()
        if child.filter.lower().find(filter) != -1:
            child.set_filtered(False)
            return True
        child.set_filtered(True)
        return False

    def _get_children(self):
        """
            Return view children
        """
        return []

    def _on_overlayed(self, widget, value):
        """
            Keep overlayed widget, clean previously overlayed
            @param widget as AlbumWidget
            @param value as bool
        """
        if value:
            if self.__overlayed is not None:
                self.__overlayed.show_overlay(False)
            self.__overlayed = widget
        elif self.__overlayed == widget:
            self.__overlayed = None

    def _on_current_changed(self, player):
        """
            Current song changed
            @param player as Player
        """
        GLib.idle_add(self.__update_widgets, self._get_children())

    def _on_duration_changed(self, player, track_id):
        """
            Update duration for current track
            @param player as Player
            @param track id as int
        """
        GLib.idle_add(self.__update_duration, self._get_children(), track_id)

    def _on_search_changed(self, entry):
        """
            Update filter
            @param entry as Gtk.Entry
        """
        self._filter = self.__search_entry.get_text()
        self._box.invalidate_filter()

    def _on_destroy(self, widget):
        """
            Remove signals on unamp
            @param widget as Gtk.Widget
        """
        if self.__duration_signal is not None:
            Lp().player.disconnect(self.__duration_signal)
        if self.__current_signal is not None:
            Lp().player.disconnect(self.__current_signal)
            self.__current_signal = None
        if self.__cover_signal is not None:
            Lp().art.disconnect(self.__cover_signal)
            self.__cover_signal = None

#######################
# PRIVATE             #
#######################
    def __update_widgets(self, widgets):
        """
            Update all widgets
            @param widgets as AlbumWidget/PlaylistWidget
        """
        if widgets:
            widget = widgets.pop(0)
            widget.update_state()
            widget.update_playing_indicator()
            GLib.idle_add(self.__update_widgets, widgets)

    def __update_duration(self, widgets, track_id):
        """
            Update duration on all widgets
            @param widgets as AlbumWidget/PlaylistWidget
        """
        if widgets:
            widget = widgets.pop(0)
            widget.update_duration(track_id)
            GLib.idle_add(self.__update_duration, widgets, track_id)

    def __on_button_clicked(self, widget):
        """
            Hide widget, why GTK doesn"t do that?
            Otherwise, we get an ugly frame
            @param widget as Gtk.Button
        """
        self.__search_entry.set_text("")
        self.__search_bar.set_search_mode(False)
        self.__search_bar.hide()

    def __on_key_press(self, widget, event):
        """
            If Esc, hide widget, why GTK doesn"t do that?
            Otherwise, we get an ugly frame
            @param widget as Gtk.SearchEntry
            @param event as Gdk.Event
        """
        if event.keyval == 65307:
            self.__search_entry.set_text("")
            self.__search_bar.set_search_mode(False)
            self.__search_bar.hide()
            return True

    def __on_leave_notify(self, widget, event):
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
            self.disable_overlay()

    def __on_cover_changed(self, art, album_id):
        """
            Update album cover in view
            @param art as Art
            @param album id as int
        """
        for widget in self._get_children():
            if album_id == widget.id:
                widget.update_cover()


class LazyLoadingView(View):
    """
        Lazy loading for view
    """

    def __init__(self, filtered=False):
        """
            Init lazy loading
            @param filtered as bool
        """
        View.__init__(self, filtered)
        self._lazy_queue = []  # Widgets not initialized
        self._scroll_value = 0
        self.__prev_scroll_value = 0
        self._scrolled.get_vadjustment().connect("value-changed",
                                                 self._on_value_changed)

    def stop(self):
        """
            Stop loading
        """
        self._lazy_queue = []
        View.stop(self)

    def append(self, widget):
        """
            Append row to lazy queue
            @param row as Gtk.Widget
        """
        self._lazy_queue.append(widget)

    def lazy_loading(self, widgets=[], scroll_value=0):
        """
            Load the view in a lazy way:
                - widgets first
                - _waiting_init then
            @param widgets as [Gtk.Widget]
            @param scroll_value as float
        """
        GLib.idle_add(self.__lazy_loading, widgets, scroll_value)

#######################
# PROTECTED           #
#######################
    def _on_value_changed(self, adj):
        """
            Update scroll value and check for lazy queue
            @param adj as Gtk.Adjustment
        """
        if not self._lazy_queue:
            return False
        scroll_value = adj.get_value()
        self.__prev_scroll_value = scroll_value
        GLib.idle_add(self.__lazy_or_not, scroll_value)

#######################
# PRIVATE             #
#######################
    def __lazy_loading(self, widgets=[], scroll_value=0):
        """
            Load the view in a lazy way:
                - widgets first
                - _waiting_init then
            @param widgets as [Gtk.Widget]
            @param scroll_value as float
        """
        widget = None
        if self._stop or self._scroll_value != scroll_value:
            return False
        if widgets:
            widget = widgets.pop(0)
            if widget in self._lazy_queue:
                self._lazy_queue.remove(widget)
        elif self._lazy_queue:
            widget = self._lazy_queue.pop(0)
        if widget is not None:
            widget.populate()
            if widgets:
                GLib.timeout_add(10, self.lazy_loading, widgets, scroll_value)
            else:
                GLib.idle_add(self.lazy_loading, widgets, scroll_value)

    def __is_visible(self, widget):
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

    def __lazy_or_not(self, scroll_value):
        """
            Add visible widgets to lazy queue
            @param scroll value as float
        """
        self._scroll_value = scroll_value
        widgets = []
        for child in self._lazy_queue:
            if self._stop or self._scroll_value != scroll_value:
                return
            if self.__is_visible(child):
                widgets.append(child)
        if self._stop or self._scroll_value != scroll_value:
            return
        GLib.idle_add(self.lazy_loading, widgets, self._scroll_value)
