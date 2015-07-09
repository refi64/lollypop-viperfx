#!/usr/bin/python
# Copyright (c) 2014-2015 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import Gtk, Gdk, GLib, GObject, Pango, cairo

from cgi import escape

from lollypop.utils import format_artist_name
from lollypop.define import Type, Lp


class SelectionPopover(Gtk.Popover):
    """
        Init popover
    """
    def __init__(self):
        Gtk.Popover.__init__(self)
        self.set_modal(False)
        self._label = Gtk.Label()
        self._label.set_property('halign', Gtk.Align.CENTER)
        self._label.set_property('valign', Gtk.Align.CENTER)
        self._label.show()
        self.get_style_context().add_class('osd-popover')
        self.set_property('width-request', 100)
        self.set_property('height-request', 50)
        self.add(self._label)

    """
        Set popover text
        @param text as string
    """
    def set_text(self, text):
        self._label.set_markup('<span size="large"><b>%s</b></span>' % text)

    """
        Ignore
    """
    def do_grab_focus(self):
        pass


# Keep track of last motion event coordonates
class MotionEvent:
    x = 0.0
    y = 0.0


# A selection list is a artists or genres scrolled treeview
class SelectionList(Gtk.ScrolledWindow):

    __gsignals__ = {
        'item-selected': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        'populated': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    """
        Init Selection list ui
    """
    def __init__(self):
        Gtk.ScrolledWindow.__init__(self)
        self.set_policy(Gtk.PolicyType.NEVER,
                        Gtk.PolicyType.AUTOMATIC)
        self._last_motion_event = MotionEvent()
        self._previous_motion_y = 0.0
        self._timeout = None
        self._to_select_id = Type.NONE
        self._updating = False       # Sort disabled if False
        self._is_artists = False  # for string translation
        self._popover = SelectionPopover()

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/SelectionList.ui')
        builder.connect_signals(self)
        self._model = builder.get_object('model')
        self._model.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self._model.set_sort_func(0, self._sort_items)
        self._view = builder.get_object('view')
        self._view.set_row_separator_func(self._row_separator_func)

        self._renderer0 = Gtk.CellRendererText()
        self._renderer0.set_property('ellipsize-set', True)
        self._renderer0.set_property('ellipsize', Pango.EllipsizeMode.END)
        renderer1 = Gtk.CellRendererPixbuf()
        column = Gtk.TreeViewColumn('')
        column.pack_start(self._renderer0, True)
        column.pack_start(renderer1, False)
        column.add_attribute(self._renderer0, 'text', 1)
        column.add_attribute(renderer1, 'icon-name', 2)
        column.set_expand(True)
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)

        self._view.append_column(column)
        self._view.connect('motion_notify_event', self._on_motion_notify)
        self._view.set_property('has_tooltip', True)

        self.add(self._view)

        adj = self.get_vadjustment()
        adj.connect('value_changed', self._on_scroll)

    """
        Mark list as artists list
        @param is_artists as bool
    """
    def mark_as_artists(self, is_artists):
        self._is_artists = is_artists

    """
        Return True if list is marked as artists
    """
    def is_marked_as_artists(self):
        return self._is_artists

    """
        Populate view with values
        @param [(int, str)], will be deleted
        @thread safe
    """
    def populate(self, values):
        if len(self._model) > 0:
            self._updating = True
        self._add_values(values)
        GLib.idle_add(self.emit, 'populated')
        self._updating = False

    """
        Remove row from model
        @param object id as int
    """
    def remove(self, object_id):
        for item in self._model:
            if item[0] == object_id:
                self._model.remove(item.iter)
                break

    """
        Add item to list
        @param value as (int, str)
    """
    def add_value(self, value):
        self._updating = True
        self._add_value(value)
        self._updating = False

    """
        Update view with values
        @param [(int, str)]
        @thread safe
    """
    def update_values(self, values):
        self._updating = True
        # Remove not found items but not devices
        value_ids = set([v[0] for v in values])
        for item in self._model:
            if item[0] > Type.DEVICES and not item[0] in value_ids:
                Gdk.threads_enter()
                self._model.remove(item.iter)
                Gdk.threads_leave()
        # Add items which are not already in the list
        item_ids = set([i[0] for i in self._model])
        for value in values:
            if not value[0] in item_ids:
                Gdk.threads_enter()
                self._add_value(value)
                Gdk.threads_leave()
        self._updating = False

    """
        Return value for id
        @param id as int
        @return value as string
    """
    def get_value(self, object_id):
        for item in self._model:
            if item[0] == object_id:
                return item[1]
        return ''

    """
        Return True if list will select an item on populate
        @return selected as bool
    """
    def will_be_selected(self):
        return self._to_select_id != Type.NONE

    """
        Make treeview select first default item
        @param object id as int
    """
    def select_id(self, object_id):
        self._to_select_id = Type.NONE
        try:
            selected = None
            for item in self._model:
                if item[0] == object_id:
                    selected = item.iter
            # Select later
            if selected is None:
                self._to_select_id = object_id
            else:
                path = self._model.get_path(selected)
                self._view.set_cursor(path, None, False)
        except:
            self._to_select_id = object_id

    """
        Get id at current position
        @return id as int
    """
    def get_selected_id(self):
        selected_id = Type.NONE
        (path, column) = self._view.get_cursor()
        if path is not None:
            iterator = self._model.get_iter(path)
            if iterator is not None:
                selected_id = self._model.get_value(iterator, 0)
        return selected_id

    """
        Clear treeview
    """
    def clear(self):
        self._updating = True
        self._model.clear()
        self._updating = False

#######################
# PRIVATE             #
#######################
    """
        Add value to the model
        @param value as [int, str]
        @thread safe
    """
    def _add_value(self, value):
        self._model.append([value[0],
                            value[1],
                            self._get_icon_name(value[0])])
        if value[0] == self._to_select_id:
            GLib.idle_add(self.select_id, self._to_select_id)

    """
        Add values to the list
        @param items as [(int,str)]
        @thread safe
    """
    def _add_values(self, values):
        for value in values:
            Gdk.threads_enter()
            self._add_value(value)
            Gdk.threads_leave()

    """
        Return pixbuf for id
        @param ojbect_id as id
    """
    def _get_icon_name(self, object_id):
        icon = ''
        if object_id >= 0:
            icon = 'go-next-symbolic'
        elif object_id == Type.POPULARS:
            icon = 'starred-symbolic'
        elif object_id == Type.PLAYLISTS:
            icon = 'emblem-documents-symbolic'
        elif object_id == Type.ALL:
            if self._is_artists:
                icon = 'media-optical-cd-audio-symbolic'
            else:
                icon = 'avatar-default-symbolic'
        elif object_id == Type.COMPILATIONS:
            icon = 'system-users-symbolic'
        elif object_id == Type.RECENTS:
            icon = 'document-open-recent-symbolic'
        elif object_id == Type.RADIOS:
            icon = 'audio-input-microphone-symbolic'
        elif object_id < Type.DEVICES:
            icon = 'multimedia-player-symbolic'
        elif object_id == Type.RANDOMS:
            icon = 'media-playlist-shuffle-symbolic'
        elif object_id == Type.LOVED:
            icon = 'emblem-favorite-symbolic'
        elif object_id == Type.NEVER:
            icon = 'document-new-symbolic'
        return icon

    """
        Sort model
    """
    def _sort_items(self, model, itera, iterb, data):
        if not self._updating:
            return False

        a_index = model.get_value(itera, 0)
        b_index = model.get_value(iterb, 0)
        a = format_artist_name(model.get_value(itera, 1))
        b = format_artist_name(model.get_value(iterb, 1))

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
            return a.lower() > b.lower()

    """
        Draw a separator if needed
        @param model as Gtk.TreeModel
        @param iterator as Gtk.TreeIter
    """
    def _row_separator_func(self, model, iterator):
        return model.get_value(iterator, 0) == Type.SEPARATOR

    """
        Forward "cursor-changed" as "item-selected" with item id as arg
        @param view as Gtk.TreeView
    """
    def _on_cursor_changed(self, view):
        selected_id = self.get_selected_id()
        if not self._updating and selected_id != Type.NONE:
            self._to_select_id = Type.NONE
            self.emit('item-selected', selected_id)

    """
        Disable shortcuts
        @param widget as Gtk.widget
        @param event as GdK.Event
    """
    def _on_focus_in_event(self, widget, event):
        Lp.window.enable_global_shorcuts(False)

    """
        Enable shortcuts
        @param widget as Gtk.widget
        @param event as GdK.Event
    """
    def _on_focus_out_event(self, widget, event):
        Lp.window.enable_global_shorcuts(True)

    """
        Hide popover
        @param widget as Gtk.widget
        @param event as GdK.Event
    """
    def _on_leave_event(self, widget=None, event=None):
        self._popover.hide()
        self._timeout = None

    """
        Set motion event
        @param widget as Gtk.widget
        @param event as GdK.Event
    """
    def _on_motion_notify(self, widget, event):
        if self._timeout is None:
            self._timeout = GLib.timeout_add(500,
                                             self._on_leave_event)
        if event.x < 0.0 or event.y < 0.0:
            return
        self._last_motion_event.x = event.x
        self._last_motion_event.y = event.y

    """
        Show a popover with current letter
        @param adj as Gtk.Adjustement
    """
    def _on_scroll(self, adj):
        # Only show if scrolled window is huge
        if adj.get_upper() < adj.get_page_size() * 3:
            return
        if self._last_motion_event is None:
            return

        if self._timeout is not None:
            GLib.source_remove(self._timeout)
            self._timeout = None

        dest_row = self._view.get_dest_row_at_pos(self._last_motion_event.x,
                                                  self._last_motion_event.y)
        if dest_row is None:
            return

        row = dest_row[0]

        if row is None:
            return

        row_iter = self._model.get_iter(row)
        if row_iter is None or self._model.get_value(row_iter, 0) < 0:
            return

        text = self._model.get_value(row_iter, 1)
        if text:
            if self._is_artists:
                text = format_artist_name(text)
            self._popover.set_text("  %s  " % text[0].upper())
            self._popover.set_relative_to(self)
            r = cairo.RectangleInt()
            r.x = self.get_allocated_width()
            r.y = self._last_motion_event.y
            r.width = 1
            r.height = 1
            self._popover.set_pointing_to(r)
            self._popover.set_position(Gtk.PositionType.RIGHT)
            self._popover.show()

    """
        Show tooltip if needed
        @param widget as Gtk.Widget
        @param x as int
        @param y as int
        @param keyboard as bool
        @param tooltip as Gtk.Tooltip
    """
    def _on_query_tooltip(self, widget, x, y, keyboard, tooltip):
        if keyboard:
            return True

        (exists, tx, ty, model, path, i) = self._view.get_tooltip_context(
                                                x,
                                                y,
                                                False)
        if exists:
            ctx = self._view.get_pango_context()
            layout = Pango.Layout.new(ctx)
            iterator = self._model.get_iter(path)
            if iterator is not None:
                text = self._model.get_value(iterator, 1)
                column = self._view.get_column(0)
                (position, width) = column.cell_get_position(self._renderer0)
                layout.set_ellipsize(Pango.EllipsizeMode.END)
                layout.set_width(Pango.units_from_double(width-8))
                layout.set_text(text, -1)
                if layout.is_ellipsized():
                    tooltip.set_markup(escape(text))
                    return True
        return False
