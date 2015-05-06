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

from gi.repository import Gtk, GLib, GObject, Pango
from time import time
from _thread import start_new_thread

from lollypop.utils import translate_artist_name, format_artist_name
from lollypop.define import Navigation


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
        self._loading = False
        self._to_select_id = Navigation.NONE
        self._updating = False       # Sort disabled if False
        self._is_artists = False  # for string translation
        self._pop_time = 0.0      # Keep track of time when starting populate

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

        self.add(self._view)

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
            if not found and item[0] > Navigation.DEVICES:
                self._model.remove(item.iter)

        for value in values:
            self._add_value(value)
        self._updating = False

    """
        Make treeview select first default item
        @param object id as int
    """
    def select_id(self, object_id):
        self._to_select_id = Navigation.NONE
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
        selected_id = Navigation.NONE
        (path, column) = self._view.get_cursor()
        if path:
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
        elif object_id == Navigation.POPULARS:
            icon = 'emblem-favorite-symbolic'
        elif object_id == Navigation.PLAYLISTS:
            icon = 'emblem-documents-symbolic'
        elif object_id == Navigation.ALL:
            icon = 'avatar-default-symbolic'
        elif object_id == Navigation.COMPILATIONS:
            icon = 'system-users-symbolic'
        elif object_id == Navigation.RECENTS:
            icon = 'document-open-recent-symbolic'
        elif object_id == Navigation.RADIOS:
            icon = 'audio-input-microphone-symbolic'
        elif object_id < Navigation.DEVICES:
            icon = 'multimedia-player-symbolic'
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
        if not self._updating and selected_id != Navigation.NONE:
            self.emit('item-selected', selected_id)
