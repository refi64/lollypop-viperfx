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

from gi.repository import Gtk, Gdk, GLib, GObject, Pango

from gettext import gettext as _
from locale import strcoll

from lollypop.view import BaseView
from lollypop.cellrenderer import CellRendererArtist
from lollypop.fastscroll import FastScroll
from lollypop.define import Type, App, ArtSize, SelectionListMask
from lollypop.utils import get_icon_name
from lollypop.shown import ShownLists, ShownPlaylists


class SelectionList(BaseView, Gtk.Overlay):
    """
        A list for artists/genres
    """
    __gsignals__ = {
        "item-selected": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "populated": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "pass-focus": (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self, base_type):
        """
            Init Selection list ui
            @param base_type as SelectionListMask
        """
        Gtk.Overlay.__init__(self)
        BaseView.__init__(self)
        self.__base_type = base_type
        self.__timeout = None
        self.__modifier = False
        self.__populating = False
        self.__mask = 0
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/SelectionList.ui")
        builder.connect_signals(self)
        self.__selection = builder.get_object("selection")
        self.__selection.set_select_function(self.__selection_validation)
        self.__selection.connect("changed", self.__on_selection_changed)
        self.__model = Gtk.ListStore(int, str, str, str)
        self.__model.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.__model.set_sort_func(0, self.__sort_items)
        self.__view = builder.get_object("view")
        self.__view.set_model(self.__model)
        if base_type in [SelectionListMask.LIST_ONE,
                         SelectionListMask.LIST_TWO]:
            self.__view.get_style_context().add_class("sidebar")
        self.__view.set_row_separator_func(self.__row_separator_func)
        self.__renderer0 = CellRendererArtist()
        self.__renderer0.set_property("ellipsize-set", True)
        self.__renderer0.set_property("ellipsize", Pango.EllipsizeMode.END)
        self.__renderer1 = Gtk.CellRendererPixbuf()
        # 16px for Gtk.IconSize.MENU
        self.__renderer1.set_fixed_size(16, -1)
        column = Gtk.TreeViewColumn("")
        column.set_expand(True)
        column.pack_start(self.__renderer0, True)
        column.add_attribute(self.__renderer0, "text", 1)
        column.add_attribute(self.__renderer0, "artist", 1)
        column.add_attribute(self.__renderer0, "rowid", 0)
        column.pack_start(self.__renderer1, False)
        column.add_attribute(self.__renderer1, "icon-name", 2)
        self.__view.append_column(column)
        self.__view.set_property("has_tooltip", True)
        self.__scrolled = Gtk.ScrolledWindow()
        self.__scrolled.set_policy(Gtk.PolicyType.NEVER,
                                   Gtk.PolicyType.AUTOMATIC)
        self.__scrolled.add(self.__view)
        self.__scrolled.show()
        self.add(self.__scrolled)
        self.__fast_scroll = FastScroll(self.__view,
                                        self.__model,
                                        self.__scrolled)
        self.add_overlay(self.__fast_scroll)
        self.__scrolled.connect("enter-notify-event", self.__on_enter_notify)
        self.__scrolled.connect("leave-notify-event", self.__on_leave_notify)

        App().art.connect("artist-artwork-changed",
                          self.__on_artist_artwork_changed)

    def mark_as(self, type):
        """
            Mark list as artists list
            @param type as SelectionListMask
        """
        self.__mask = self.__base_type | type
        self.__renderer0.set_is_artists(type & SelectionListMask.ARTISTS)

    def populate(self, values):
        """
            Populate view with values
            @param [(int, str, optional str)], will be deleted
        """
        if self.__populating:
            return
        self.__populating = True
        self.__selection.disconnect_by_func(
                                         self.__on_selection_changed)
        self.clear()
        self.__add_values(values)
        self.__selection.connect("changed",
                                 self.__on_selection_changed)
        self.__populating = False
        self.emit("populated")

    def remove_value(self, object_id):
        """
            Remove row from model
            @param object id as int
        """
        for item in self.__model:
            if item[0] == object_id:
                self.__model.remove(item.iter)
                break

    def add_value(self, value):
        """
            Add item to list
            @param value as (int, str, optional str)
        """
        # Do not add value if already exists
        for item in self.__model:
            if item[0] == value[0]:
                return
        self.__add_value(value)

    def update_value(self, object_id, name):
        """
            Update object with new name
            @param object id as int
            @param name as str
        """
        found = False
        for item in self.__model:
            if item[0] == object_id:
                item[1] = name
                found = True
                break
        if not found:
            self.__add_value((object_id, name, name))

    def update_values(self, values):
        """
            Update view with values
            @param [(int, str, optional str)]
        """
        update_fast_scroll = self.__mask & SelectionListMask.ARTISTS and\
            self.__fast_scroll is not None
        if update_fast_scroll:
            self.__fast_scroll.clear()
        # Remove not found items but not devices
        value_ids = set([v[0] for v in values])
        for item in self.__model:
            if item[0] > Type.DEVICES and not item[0] in value_ids:
                self.__model.remove(item.iter)
        # Add items which are not already in the list
        item_ids = set([i[0] for i in self.__model])
        for value in values:
            if not value[0] in item_ids:
                self.__add_value(value)
        if update_fast_scroll:
            self.__fast_scroll.populate()

    def get_value(self, object_id):
        """
            Return value for id
            @param id as int
            @return value as string
        """
        for item in self.__model:
            if item[0] == object_id:
                return item[1]
        return ""

    def select_ids(self, ids=[]):
        """
            Make treeview select first default item
            @param object id as int
        """
        if ids:
            try:
                # Check if items are available for selection
                items = []
                for i in list(ids):
                    for item in self.__model:
                        if item[0] == i:
                            items.append(item)
                self.__selection.disconnect_by_func(
                                         self.__on_selection_changed)
                for item in items:
                    self.__selection.select_iter(item.iter)
                self.__selection.connect("changed",
                                         self.__on_selection_changed)
                self.emit("item-selected")
                # Scroll to first item
                if items:
                    self.__view.scroll_to_cell(items[0].path,
                                               None,
                                               True,
                                               0, 0)
            except:
                self.__last_motion_event = None
        else:
            self.__selection.unselect_all()

    def grab_focus(self):
        """
            Grab focus on treeview
        """
        self.__view.grab_focus()

    def clear(self):
        """
            Clear treeview
        """
        self.__model.clear()
        if self.__fast_scroll is not None:
            self.__fast_scroll.clear()
            self.__fast_scroll.clear_chars()
            self.__fast_scroll.hide()

    def get_headers(self, mask):
        """
            Return headers
            @param mask as SelectionListMask
            @return items as [(int, str)]
        """
        lists = ShownLists.get(mask)
        if mask & SelectionListMask.LIST_ONE and App().window.is_adaptive:
            lists += [(Type.SEARCH, _("Search"), _("Search"))]
            lists += [
                (Type.CURRENT, _("Current playlist"), _("Current playlist"))]
        if lists:
            lists.append((Type.SEPARATOR, "", ""))
        return lists

    def get_playlist_headers(self):
        """
            Return playlist headers
            @return items as [(int, str)]
        """
        lists = ShownPlaylists.get()
        if lists:
            lists.append((Type.SEPARATOR, "", ""))
        return lists

    def select_first(self):
        """
            Select first available item
        """
        self.__selection.select_iter(self.__model[0].iter)

    def redraw(self):
        """
            Redraw list
        """
        self.__view.set_model(None)
        self.__view.set_model(self.__model)

    @property
    def should_destroy(self):
        """
            True if view should be destroyed
            @return bool
        """
        return False

    @property
    def mask(self):
        """
            Get selection list type
            @return bit mask
        """
        return self.__mask

    @property
    def count(self):
        """
            Get items count in list
            @return int
        """
        return len(self.__model)

    @property
    def selected_ids(self):
        """
            Get selected ids
            @return array of ids as [int]
        """
        selected_ids = []
        (model, items) = self.__selection.get_selected_rows()
        if model is not None:
            for item in items:
                selected_ids.append(model[item][0])
        return selected_ids

#######################
# PROTECTED           #
#######################
    def _on_key_press_event(self, entry, event):
        """
            Forward to popover history listbox if needed
            @param entry as Gtk.Entry
            @param event as Gdk.Event
        """
        if event.keyval in [Gdk.KEY_Left, Gdk.KEY_Right]:
            self.emit("pass-focus")

    def _on_button_press_event(self, view, event):
        """
            Handle modifier
            @param view as Gtk.TreeView
            @param event as Gdk.Event
        """
        if event.button == 1:
            view.grab_focus()
            state = event.get_state()
            if state & Gdk.ModifierType.CONTROL_MASK or\
               state & Gdk.ModifierType.SHIFT_MASK:
                self.__modifier = True
        elif self.__base_type in [SelectionListMask.LIST_ONE,
                                  SelectionListMask.LIST_TWO]:
            info = view.get_dest_row_at_pos(event.x, event.y)
            if info is not None:
                from lollypop.pop_menu_views import ViewsMenuPopover
                (path, position) = info
                iterator = self.__model.get_iter(path)
                rowid = self.__model.get_value(iterator, 0)
                popover = ViewsMenuPopover(self, rowid, self.mask)
                popover.set_relative_to(view)
                rect = Gdk.Rectangle()
                rect.x = event.x
                rect.y = event.y
                rect.width = rect.height = 1
                popover.set_pointing_to(rect)
                popover.popup()
                return True

    def _on_button_release_event(self, view, event):
        """
            Handle modifier
            @param view as Gtk.TreeView
            @param event as Gdk.Event
        """
        self.__modifier = False

    def _on_query_tooltip(self, widget, x, y, keyboard, tooltip):
        """
            Show tooltip if needed
            @param widget as Gtk.Widget
            @param x as int
            @param y as int
            @param keyboard as bool
            @param tooltip as Gtk.Tooltip
        """
        def shown_sidebar_tooltip():
            App().shown_sidebar_tooltip = True

        if keyboard:
            return True
        (exists, tx, ty, model, path, i) = self.__view.get_tooltip_context(
            x,
            y,
            False)
        if exists:
            ctx = self.__view.get_pango_context()
            layout = Pango.Layout.new(ctx)
            iterator = self.__model.get_iter(path)
            if iterator is not None:
                text = self.__model.get_value(iterator, 1)
                column = self.__view.get_column(0)
                (position, width) = column.cell_get_position(self.__renderer0)
                if App().settings.get_value("artist-artwork") and\
                        self.__mask & SelectionListMask.ARTISTS:
                    width -= ArtSize.ARTIST_SMALL +\
                        CellRendererArtist.xshift * 2
                layout.set_ellipsize(Pango.EllipsizeMode.END)
                if self.__model.get_value(iterator, 0) < 0:
                    width -= 8
                layout.set_width(Pango.units_from_double(width))
                layout.set_text(text, -1)
                if layout.is_ellipsized():
                    tooltip.set_markup(GLib.markup_escape_text(text))
                    return True
                elif not App().shown_sidebar_tooltip:
                    GLib.timeout_add(1000, shown_sidebar_tooltip)
                    tooltip.set_markup(_("Right click to configure"))
                    return True
        return False

#######################
# PRIVATE             #
#######################
    def __add_value(self, value):
        """
            Add value to the model
            @param value as [int, str, optional str]
        """
        item_id = value[0]
        name = value[1]
        sort = value[2]
        if name == "":
            name = _("Unknown")
            icon_name = "dialog-warning-symbolic"
        icon_name = get_icon_name(item_id, self.__mask)
        if item_id > 0 and sort and\
                self.__mask & SelectionListMask.ARTISTS and\
                self.__fast_scroll is not None:
            self.__fast_scroll.add_char(sort[0])
        self.__model.append([item_id,
                            name,
                            icon_name,
                            sort])

    def __add_values(self, values):
        """
            Add values to the list
            @param items as [(int,str)]
        """
        for value in values:
            self.__add_value(value)
        if self.__mask & SelectionListMask.ARTISTS and\
                self.__fast_scroll is not None:
            self.__fast_scroll.populate()

    def __sort_items(self, model, itera, iterb, data):
        """
            Sort model
        """
        if self.__populating:
            return False
        a_index = model.get_value(itera, 0)
        b_index = model.get_value(iterb, 0)

        # Static vs static
        if a_index < 0 and b_index < 0:
            return a_index < b_index
        # Static entries always on top
        elif b_index < 0:
            return True
        # Static entries always on top
        if a_index < 0:
            return False
        # String comparaison for non static
        else:
            if self.__mask & SelectionListMask.ARTISTS:
                a = App().artists.get_sortname(a_index)
                b = App().artists.get_sortname(b_index)
            else:
                a = model.get_value(itera, 1)
                b = model.get_value(iterb, 1)
            return strcoll(a, b)

    def __row_separator_func(self, model, iterator):
        """
            Draw a separator if needed
            @param model as Gtk.TreeModel
            @param iterator as Gtk.TreeIter
        """
        return model.get_value(iterator, 0) == Type.SEPARATOR

    def __selection_validation(self, selection, model, path, current):
        """
            Check if selection is valid
            @param selection as Gtk.TreeSelection
            @param model as Gtk.TreeModel
            @param path as Gtk.TreePath
            @param current as bool
            @return bool
        """
        ids = self.selected_ids
        if not ids:
            return True
        elif self.__modifier:
            iterator = self.__model.get_iter(path)
            value = self.__model.get_value(iterator, 0)
            if value < 0 and len(ids) > 1:
                return False
            else:
                static = False
                for i in ids:
                    if i < 0:
                        static = True
                if static:
                    return False
                elif value > 0:
                    return True
                else:
                    return False
        else:
            return True

    def __on_enter_notify(self, widget, event):
        """
            Disable shortcuts
            @param widget as Gtk.widget
            @param event as Gdk.Event
        """
        if widget.get_vadjustment().get_upper() >\
                widget.get_allocated_height() and\
                self.__mask & SelectionListMask.ARTISTS and\
                self.__fast_scroll is not None:
            self.__fast_scroll.show()

    def __on_leave_notify(self, widget, event):
        """
            Hide popover
            @param widget as Gtk.widget
            @param event as GdK.Event
        """
        allocation = widget.get_allocation()
        if event.x <= 0 or\
           event.x >= allocation.width or\
           event.y <= 0 or\
           event.y >= allocation.height:
            if self.__mask & SelectionListMask.ARTISTS\
                    and self.__fast_scroll is not None:
                self.__fast_scroll.hide()

    def __on_artist_artwork_changed(self, art, artist):
        """
            Update row
        """
        if self.__mask & SelectionListMask.ARTISTS:
            self.__renderer0.on_artist_artwork_changed(artist)
            for item in self.__model:
                if item[1] == artist:
                    item[1] = artist
                    break

    def __on_selection_changed(self, selection):
        """
            Forward as "item-selected"
            @param view as Gtk.TreeSelection
        """
        self.emit("item-selected")
