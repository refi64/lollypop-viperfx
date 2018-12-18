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

from time import time

from lollypop.logger import Logger
from lollypop.adaptive import AdaptiveView


class BaseView(AdaptiveView):
    """
        Common views members
    """

    def __init__(self):
        AdaptiveView.__init__(self)

    def populate(self):
        pass

    def stop(self):
        pass

    def disable_overlay(self):
        pass


class View(BaseView, Gtk.Grid):
    """
        Generic view
    """

    def __init__(self, filtered=False):
        """
            Init view
            @param filtered as bool
        """
        BaseView.__init__(self)
        Gtk.Grid.__init__(self)
        self.__overlayed = None
        self.set_property("orientation", Gtk.Orientation.VERTICAL)
        self.set_border_width(0)
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
            self.__search_entry.set_size_request(300, -1)
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
        self._viewport.connect("destroy", self.__on_destroy)
        self._scrolled.add(self._viewport)
        self._viewport.show()
        self.connect("map", self._on_map)
        self.connect("unmap", self._on_unmap)

    def enable_filter(self):
        """
           Filter the view
        """
        if self._filter is not None:
            enable = not self.__search_bar.get_search_mode()
            self.__search_bar.show() if enable else self.__search_bar.hide()
            self.__search_bar.set_search_mode(enable)
            if enable:
                self.__search_entry.grab_focus()

    def disable_overlay(self):
        """
            Disable overlay widget
        """
        if self.__overlayed is not None:
            self.__overlayed.show_overlay(False)

    def on_overlayed(self, widget, value):
        """
            Disable overlay on previous overlayed widget
            @param widget as AlbumWidget
            @param value as bool
        """
        if value:
            if self.__overlayed is not None:
                self.__overlayed.show_overlay(False)
            self.__overlayed = widget
        elif self.__overlayed == widget:
            self.__overlayed = None

    @property
    def filtered(self):
        """
            True if view filtered
            @return bool
        """
        return self._filter is not None and self._filter != ""

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

    def _on_search_changed(self, entry):
        """
            Update filter
            @param entry as Gtk.Entry
        """
        self._filter = self.__search_entry.get_text()
        self._box.invalidate_filter()

    def _on_map(self, widget):
        pass

    def _on_unmap(self, widget):
        pass

#######################
# PRIVATE             #
#######################
    def __update_widgets(self, widgets):
        """
            Update all widgets
            @param widgets as BaseWidget
        """
        if widgets:
            widget = widgets.pop(0)
            widget.update_state()
            widget.update_playing_indicator()
            GLib.idle_add(self.__update_widgets, widgets)

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

    def __on_destroy(self, viewport):
        """
            Mark widget as destroyed
            @param viewport as Gtk.Viewport
        """
        self._viewport = None


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
        self.__priority_queue = []
        self.__scroll_timeout_id = None
        self._scrolled.get_vadjustment().connect("value-changed",
                                                 self._on_value_changed)
        self.__start_time = time()

    def stop(self):
        """
            Stop loading
        """
        self._lazy_queue = None
        View.stop(self)

    def lazy_loading(self):
        """
            Load the view in a lazy way
        """
        widget = None
        if self._lazy_queue is None:
            return
        if self.__priority_queue:
            widget = self.__priority_queue.pop(0)
            self._lazy_queue.remove(widget)
        elif self._lazy_queue:
            widget = self._lazy_queue.pop(0)
        if widget is not None:
            widget.connect("populated", self._on_populated)
            widget.populate()
        else:
            Logger.debug("LazyLoadingView::lazy_loading(): %s",
                         time() - self.__start_time)

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
        if self.__scroll_timeout_id is not None:
            GLib.source_remove(self.__scroll_timeout_id)
        self.__scroll_timeout_id = GLib.timeout_add(200, self.__lazy_or_not)

    def _on_populated(self, widget):
        """
            Add another album/disc
            @param widget as AlbumWidget/TracksView
        """
        if self._lazy_queue is None:
            return
        if not widget.is_populated:
            widget.populate()
        else:
            self.lazy_loading()

#######################
# PRIVATE             #
#######################
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

    def __lazy_or_not(self):
        """
            Add visible widgets to lazy queue
        """
        self.__scroll_timeout_id = None
        self.__priority_queue = []
        if self._lazy_queue is None:
            return
        for child in self._lazy_queue:
            if self.__is_visible(child):
                self.__priority_queue.append(child)
        GLib.idle_add(self.lazy_loading)


class MessageView(View):
    """
        Show a message to user
    """

    def __init__(self, text):
        """
            Init view
            @param text as str
        """
        View.__init__(self)
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/DeviceManagerView.ui")
        self.add(builder.get_object("message"))
        builder.get_object("label").set_text(text)
