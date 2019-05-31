# Copyright (c) 2014-2019 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from lollypop.view import LazyLoadingView
from lollypop.fastscroll import FastScroll
from lollypop.define import Type, App, ArtSize, SelectionListMask
from lollypop.define import SidebarContent, ArtBehaviour
from lollypop.logger import Logger
from lollypop.utils import get_icon_name, on_query_tooltip
from lollypop.shown import ShownLists, ShownPlaylists


class SelectionListRow(Gtk.ListBoxRow):
    """
        A selection list row
    """

    __gsignals__ = {
        "populated": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def get_best_height(widget):
        """
            Calculate widget height
            @param widget as Gtk.Widget
        """
        ctx = widget.get_pango_context()
        layout = Pango.Layout.new(ctx)
        layout.set_text("a", 1)
        font_height = int(layout.get_pixel_size()[1])
        return font_height

    def __init__(self, rowid, name, sortname, mask, height):
        """
            Init row
            @param rowid as int
            @param name as str
            @param sortname as str
            @param mask as SelectionListMask
            @param height as str
        """
        Gtk.ListBoxRow.__init__(self)
        self.__rowid = rowid
        self.__name = name
        self.__sortname = sortname
        self.__mask = mask

        if rowid == Type.SEPARATOR:
            height = -1
        elif self.__mask & SelectionListMask.ARTISTS and\
                self.__rowid >= 0 and\
                App().settings.get_value("artist-artwork"):
            self.get_style_context().add_class("row")
            if height < ArtSize.ARTIST_SMALL:
                height = ArtSize.ARTIST_SMALL
        elif App().settings.get_enum("sidebar-content") ==\
                SidebarContent.DEFAULT:
            self.get_style_context().add_class("row-big")
        else:
            self.get_style_context().add_class("row")
        self.set_size_request(-1, height)

    def populate(self):
        """
            Populate widget
        """
        if self.__rowid == Type.SEPARATOR:
            separator = Gtk.Separator.new(Gtk.Orientation.HORIZONTAL)
            separator.show()
            self.add(separator)
            self.set_sensitive(False)
            self.emit("populated")
        else:
            self.__grid = Gtk.Grid()
            self.__grid.set_column_spacing(7)
            self.__artwork = Gtk.Image.new()
            self.__label = Gtk.Label.new()
            self.__label.set_markup(GLib.markup_escape_text(self.__name))
            self.__label.set_ellipsize(Pango.EllipsizeMode.END)
            self.__label.set_property("has-tooltip", True)
            self.__label.connect("query-tooltip", on_query_tooltip)
            self.__label.show()
            self.__grid.show()
            self.__grid.show()
            self.__grid.add(self.__artwork)
            self.__grid.add(self.__label)
            self.__grid.set_margin_end(20)
            self.add(self.__grid)
            self.set_artwork()

    def set_artwork(self):
        """
            set_artwork widget
        """
        if self.__rowid == Type.SEPARATOR:
            pass
        elif self.__mask & SelectionListMask.ARTISTS and\
                self.__rowid >= 0 and\
                App().settings.get_value("artist-artwork"):
            App().art_helper.set_artist_artwork(
                                    self.__name,
                                    ArtSize.ARTIST_SMALL,
                                    ArtSize.ARTIST_SMALL,
                                    self.get_scale_factor(),
                                    ArtBehaviour.ROUNDED |
                                    ArtBehaviour.SAVE,
                                    self.__on_artist_artwork)
            self.__artwork.show()
        elif self.__rowid < 0:
            icon_name = get_icon_name(self.__rowid, self.__mask)
            self.__artwork.set_from_icon_name(icon_name,
                                              Gtk.IconSize.BUTTON)
            self.__artwork.show()
            self.emit("populated")
        else:
            self.__artwork.hide()
            self.emit("populated")

    @property
    def is_populated(self):
        """
            Return True if populated
            @return bool
        """
        return True

    @property
    def name(self):
        """
            Get row name
            @return str
        """
        return self.__name

    @property
    def sortname(self):
        """
            Get row sortname
            @return str
        """
        return self.__sortname

    @property
    def id(self):
        """
            Get row id
            @return int
        """
        return self.__rowid

#######################
# PRIVATE             #
#######################
    def __on_artist_artwork(self, surface):
        """
            Set artist artwork
            @param surface as cairo.Surface
        """
        if surface is None:
            self.__artwork.set_from_icon_name(
                                              "avatar-default-symbolic",
                                              Gtk.IconSize.DND)
        else:
            self.__artwork.set_from_surface(surface)
            self.__artwork.get_style_context().remove_class(
                "artwork-icon")
        self.emit("populated")


class SelectionList(LazyLoadingView):
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
        LazyLoadingView.__init__(self)
        self.__base_type = base_type
        self.__sort = False
        self.__mask = 0
        self.__height = SelectionListRow.get_best_height(self)
        self.__listbox = Gtk.ListBox()
        self.__listbox.connect("row-selected", self.__on_row_selected)
        self.__listbox.connect("button-release-event",
                               self.__on_button_release_event)
        self.__listbox.connect("key-press-event",
                               self.__on_key_press_event)
        self.__listbox.set_sort_func(self.__sort_func)
        self.__listbox.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self.__listbox.show()
        self._viewport.add(self.__listbox)
        self._scrolled.connect("enter-notify-event", self.__on_enter_notify)
        self._scrolled.connect("leave-notify-event", self.__on_leave_notify)
        overlay = Gtk.Overlay.new()
        overlay.set_hexpand(True)
        overlay.set_vexpand(True)
        overlay.show()
        overlay.add(self._scrolled)
        self.__fastscroll = FastScroll(self.__listbox,
                                       self._scrolled)
        overlay.add_overlay(self.__fastscroll)
        self.add(overlay)
        self.get_style_context().add_class("sidebar")
        App().art.connect("artist-artwork-changed",
                          self.__on_artist_artwork_changed)

    def mark_as(self, type):
        """
            Mark list as artists list
            @param type as SelectionListMask
        """
        self.__mask = self.__base_type | type

    def populate(self, values):
        """
            Populate view with values
            @param [(int, str, optional str)], will be deleted
        """
        self.__sort = False
        self.clear()
        self.__add_values(values)
        self._scrolled.get_vadjustment().set_value(0)

    def remove_value(self, object_id):
        """
            Remove id from list
            @param object_id as int
        """
        for child in self.__listbox.get_children():
            if child.id == object_id:
                child.destroy()
                break

    def add_value(self, value):
        """
            Add item to list
            @param value as (int, str, optional str)
        """
        self.__sort = True
        # Do not add value if already exists
        for child in self.__listbox.get_children():
            if child.id == value[0]:
                return
        row = self.__add_value(value[0], value[1], value[2])
        row.populate()

    def update_value(self, object_id, name):
        """
            Update object with new name
            @param object_id as int
            @param name as str
        """
        found = False
        for child in self.__listbox.get_children():
            if child.id == object_id:
                child.set_name(name)
                found = True
                break
        if not found:
            self.__fastscroll.clear()
            row = self.__add_value((object_id, name, name))
            row.populate()
            if self.__mask & SelectionListMask.ARTISTS:
                self.__fastscroll.populate()

    def update_values(self, values):
        """
            Update view with values
            @param [(int, str, optional str)]
        """
        if self.__mask & SelectionListMask.ARTISTS:
            self.__fastscroll.clear()
        # Remove not found items but not devices
        value_ids = set([v[0] for v in values])
        for child in self.__listbox.get_children():
            if child.id > Type.DEVICES and child.id not in value_ids:
                self.remove_value(child.id)
        # Add items which are not already in the list
        item_ids = set([child.id for child in self.__listbox.get_children()])
        for value in values:
            if not value[0] in item_ids:
                row = self.__add_value(value)
                row.populate()
        if self.__mask & SelectionListMask.ARTISTS:
            self.__fastscroll.populate()

    def select_ids(self, ids=[]):
        """
            Select listbox items
            @param ids as [int]
        """
        self.__listbox.unselect_all()
        if ids:
            first_row = None
            for row in self.__listbox.get_children():
                if row.id in ids:
                    if first_row is None:
                        first_row = row
                    self.__listbox.select_row(row)
            # Scroll to first item
            if first_row is not None:
                GLib.idle_add(self.__scroll_to_row, first_row)

    def grab_focus(self):
        """
            Grab focus on treeview
        """
        self.__listbox.grab_focus()

    def clear(self):
        """
            Clear treeview
        """
        for child in self.__listbox.get_children():
            child.destroy()
        self.__fastscroll.clear()
        self.__fastscroll.clear_chars()

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
        if lists and\
                App().settings.get_enum("sidebar-content") !=\
                SidebarContent.DEFAULT:
            lists.append((Type.SEPARATOR, "", ""))
        return lists

    def get_playlist_headers(self):
        """
            Return playlist headers
            @return items as [(int, str)]
        """
        lists = ShownPlaylists.get()
        if lists and\
                App().settings.get_enum("sidebar-content") !=\
                SidebarContent.DEFAULT:
            lists.append((Type.SEPARATOR, "", ""))
        return lists

    def select_first(self):
        """
            Select first available item
        """
        try:
            row = self.__listbox.get_children()[0]
            self.__listbox.select_row(row)
        except Exception as e:
            Logger.warning("SelectionList::select_first(): %s", e)

    def redraw(self):
        """
            Redraw list
        """
        for row in self.__listbox.get_children():
            row.set_artwork()

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
        return len(self.__listbox.get_children())

    @property
    def selected_ids(self):
        """
            Get selected ids
            @return array of ids as [int]
        """
        return [row.id for row in self.__listbox.get_selected_rows()]

#######################
# PRIVATE             #
#######################
    def __scroll_to_row(self, row):
        """
            Scroll to row
            @param row as SelectionListRow
        """
        coordinates = row.translate_coordinates(self.__listbox, 0, 0)
        if coordinates:
            self._scrolled.get_vadjustment().set_value(coordinates[1])

    def __add_values(self, values):
        """
            Add values to the list
            @param items as [(int,str)]
        """
        if values:
            (rowid, name, sortname) = values.pop(0)
            row = self.__add_value(rowid, name, sortname)
            self._lazy_queue.append(row)
            GLib.idle_add(self.__add_values, values)
        else:
            if self.__mask & SelectionListMask.ARTISTS:
                self.__fastscroll.populate()
            self.__sort = True
            self.emit("populated")
            GLib.idle_add(self.lazy_loading)

    def __add_value(self, rowid, name, sortname):
        """
            Add value to list
            @param rowid as int
            @param name as str
            @param sortname as str
            @return row as SelectionListRow
        """
        if rowid > 0 and sortname and\
                self.__mask & SelectionListMask.ARTISTS:
            self.__fastscroll.add_char(sortname[0])
        row = SelectionListRow(rowid, name, sortname,
                               self.__mask, self.__height)
        row.show()
        self.__listbox.add(row)
        return row

    def __sort_func(self, row_a, row_b):
        """
            Sort rows
            @param row_a as SelectionListRow
            @param row_b as SelectionListRow
        """
        if not self.__sort:
            return False
        a_index = row_a.id
        b_index = row_b.id

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
                a = row_a.sortname
                b = row_b.sortname
            else:
                a = row_a.name
                b = row_b.name
            return strcoll(a, b)

    def __on_key_press_event(self, entry, event):
        """
            Forward to popover history listbox if needed
            @param entry as Gtk.Entry
            @param event as Gdk.Event
        """
        if event.keyval in [Gdk.KEY_Left, Gdk.KEY_Right]:
            self.emit("pass-focus")

    def __on_button_release_event(self, listbox, event):
        """
            Handle modifier
            @param listbox as Gtk.ListBox
            @param event as Gdk.Event
        """
        if event.button != 1 and\
                self.__base_type in [SelectionListMask.LIST_ONE,
                                     SelectionListMask.LIST_TWO]:
            from lollypop.pop_menu_views import ViewsMenuPopover
            row = listbox.get_row_at_y(event.y)
            popover = ViewsMenuPopover(self, row.id, self.mask)
            popover.set_relative_to(listbox)
            rect = Gdk.Rectangle()
            rect.x = event.x
            rect.y = event.y
            rect.width = rect.height = 1
            popover.set_pointing_to(rect)
            popover.popup()
        elif event.button == 1:
            state = event.get_state()
            if state & Gdk.ModifierType.CONTROL_MASK or\
                    state & Gdk.ModifierType.SHIFT_MASK:
                return False
            else:
                listbox.unselect_all()
                row = listbox.get_row_at_y(event.y)
                row.activate()
                return True

    def __on_artist_artwork_changed(self, art, artist):
        """
            Update row
            @param art as Art
            @param artist as str
        """
        if self.__mask & SelectionListMask.ARTISTS:
            for row in self.__listbox.get_children():
                if row.id >= 0 and row.name == artist:
                    row.set_artwork()
                    break

    def __on_enter_notify(self, widget, event):
        """
            Disable shortcuts
            @param widget as Gtk.widget
            @param event as Gdk.Event
        """
        if widget.get_vadjustment().get_upper() >\
                widget.get_allocated_height() and\
                self.__mask & SelectionListMask.ARTISTS:
            self.__fastscroll.show()

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
            if self.__mask & SelectionListMask.ARTISTS:
                self.__fastscroll.hide()

    def __on_row_selected(self, listbox, row):
        """
            Emit selected item signal
        """
        if row is not None:
            self.emit("item-selected")
