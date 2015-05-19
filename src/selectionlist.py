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

from gi.repository import Gtk, GLib, GObject, Pango, cairo
from time import time
from _thread import start_new_thread

from lollypop.utils import translate_artist_name, format_artist_name
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
        self.get_style_context().add_class('selection-popover')
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
        self._loading = False
        self._timeout = None
        self._to_select_id = Type.NONE
        self._updating = False       # Sort disabled if False
        self._is_artists = False  # for string translation
        self._pop_time = 0.0      # Keep track of time when starting populate
        self._popover = SelectionPopover()

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/SelectionList.ui')
        builder.connect_signals(self)
        self._model = builder.get_object('model')
        self._model.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self._model.set_sort_func(0, self._sort_items)
        self._view = builder.get_object('view')

        renderer0 = Gtk.CellRendererText()
        renderer0.set_property('ellipsize-set', True)
        renderer0.set_property('ellipsize', Pango.EllipsizeMode.END)
        column0 = Gtk.TreeViewColumn('', renderer0)
        column0.add_attribute(renderer0, 'text', 1)
        column0.set_expand(True)
        column0.set_sizing(Gtk.TreeViewColumnSizing.FIXED)

        renderer1 = Gtk.CellRendererPixbuf()
        column1 = Gtk.TreeViewColumn('', renderer1)
        column1.add_attribute(renderer1, 'icon-name', 2)
        column1.set_sizing(Gtk.TreeViewColumnSizing.FIXED)

        self._view.append_column(column0)
        self._view.append_column(column1)
        self._view.connect('motion_notify_event', self._on_motion_notify)

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
        self._pop_time = time()
        start_new_thread(self._populate, (values,))

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
    """
    def update_values(self, values):
        self._updating = True
        for item in self._model:
            found = False
            for value in values:
                if item[1] == value[1]:
                    found = True
                    break
            # Remove not found items but not devices
            if not found and item[0] > Type.DEVICES:
                self._model.remove(item.iter)

        for value in values:
            self._add_value(value)
        self._updating = False

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
            if iterator:
                selected_id = self._model.get_value(iterator, 0)
        return selected_id

    """
        Return true if view is being populated
    """
    def is_populating(self):
        return self._pop_time != 0

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
    """
    def _add_value(self, value):
        found = False
        for item in self._model:
            if value[0] == item[0]:
                found = True
                break
        if not found:
            if self._is_artists:
                string = translate_artist_name(value[1])
            else:
                string = value[1]
            self._model.append([value[0],
                                string,
                                self._get_icon_name(value[0])])
            if value[0] == self._to_select_id:
                self.select_id(self._to_select_id)

    """
        Populate view with values
        @param [(int, str)], will be deleted
        @thread safe
    """
    def _populate(self, values):
        GLib.idle_add(self._add_values, values, self._pop_time)

    """
        Add values to the list
        @param items as [(int,str)]
        @param time as float
    """
    def _add_values(self, values, time):
        if time != self._pop_time:
            del values
            values = None
            return
        elif not values:
            self.emit("populated")
            del values
            values = None
            self._pop_time = 0
            return

        value = values.pop(0)
        self._add_value(value)
        GLib.idle_add(self._add_values, values, time)

    """
        Return pixbuf for id
        @param ojbect_id as id
    """
    def _get_icon_name(self, object_id):
        icon = ''
        if object_id >= 0:
            icon = 'go-next-symbolic'
        elif object_id == Type.POPULARS:
            icon = 'emblem-favorite-symbolic'
        elif object_id == Type.PLAYLISTS:
            icon = 'emblem-documents-symbolic'
        elif object_id == Type.ALL:
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
        Forward "cursor-changed" as "item-selected" with item id as arg
        @param view as Gtk.TreeView
    """
    def _new_item_selected(self, view):
        selected_id = self.get_selected_id()
        if not self._updating and selected_id != Type.NONE:
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
        Hide popover later
    """
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
