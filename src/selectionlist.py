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

from gi.repository import Gtk, Gdk, GLib, GObject, Pango

from cgi import escape
from gettext import gettext as _
from locale import strcoll

from lollypop.cellrenderer import CellRendererArtist
from lollypop.define import Type, Lp, SelectionMode, ArtSize


class SelectionPopover(Gtk.Popover):
    """
        Show a popover with text
    """

    def __init__(self):
        """
            Init popover
        """
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

    def set_text(self, text):
        """
            Set popover text
            @param text as string
        """
        self._label.set_markup('<span size="large"><b>%s</b></span>' % text)

    def do_grab_focus(self):
        """
            Ignore
        """
        pass


class MotionEvent:
    """
        Keep track of last motion event coordonates
    """
    x = 0.0
    y = 0.0


class SelectionList(Gtk.ScrolledWindow):
    """
        A list for artists/genres
    """
    __gsignals__ = {
        'item-selected': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'populated': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, mode):
        """
            Init Selection list ui
            @param mode as SelectionMode
        """
        Gtk.ScrolledWindow.__init__(self)
        self.set_policy(Gtk.PolicyType.NEVER,
                        Gtk.PolicyType.AUTOMATIC)
        self._mode = mode
        self._last_motion_event = None
        self._previous_motion_y = 0.0
        self._timeout = None
        self._to_select_ids = []
        self._modifier = False
        self._updating = False       # Sort disabled if False
        self._is_artists = False
        self._popover = SelectionPopover()
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/SelectionList.ui')
        builder.connect_signals(self)
        self._selection = builder.get_object('selection')
        self._selection.set_select_function(self._selection_validation)
        self._model = builder.get_object('model')
        self._model.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self._model.set_sort_func(0, self._sort_items)
        self._view = builder.get_object('view')
        self._view.set_row_separator_func(self._row_separator_func)
        self._renderer0 = CellRendererArtist()
        self._renderer0.set_property('ellipsize-set', True)
        self._renderer0.set_property('ellipsize', Pango.EllipsizeMode.END)
        self._renderer1 = Gtk.CellRendererPixbuf()
        # 16px for Gtk.IconSize.MENU
        self._renderer1.set_fixed_size(16, -1)
        column = Gtk.TreeViewColumn('')
        column.set_expand(True)
        column.pack_start(self._renderer0, True)
        column.add_attribute(self._renderer0, 'text', 1)
        column.add_attribute(self._renderer0, 'artist', 1)
        column.add_attribute(self._renderer0, 'rowid', 0)
        column.pack_start(self._renderer1, False)
        column.add_attribute(self._renderer1, 'icon-name', 2)
        self._view.append_column(column)
        self._view.set_property('has_tooltip', True)
        self.add(self._view)
        self.connect('motion_notify_event', self._on_motion_notify)
        self.get_vadjustment().connect('value_changed', self._on_scroll)
        self.connect('enter-notify-event', self._on_enter_notify)
        self.connect('leave-notify-event', self._on_leave_notify)
        Lp().art.connect('artist-artwork-changed',
                         self._on_artist_artwork_changed)

    def mark_as_artists(self, is_artists):
        """
            Mark list as artists list
            @param is_artists as bool
        """
        self._is_artists = is_artists
        self._renderer0.set_is_artists(is_artists)

    def is_marked_as_artists(self):
        """
            Return True if list is marked as artists
        """
        return self._is_artists

    def populate(self, values):
        """
            Populate view with values
            @param [(int, str)], will be deleted
            @thread safe
        """
        if len(self._model) > 0:
            self._updating = True
        self._add_values(values)
        self.emit('populated')
        self._updating = False

    def remove(self, object_id):
        """
            Remove row from model
            @param object id as int
        """
        for item in self._model:
            if item[0] == object_id:
                self._model.remove(item.iter)
                break

    def add_value(self, value):
        """
            Add item to list
            @param value as (int, str)
        """
        self._updating = True
        self._add_value(value)
        self._updating = False

    def update_value(self, object_id, name):
        """
            Update object with new name
            @param object id as int
            @param name as str
        """
        self._updating = True
        found = False
        for item in self._model:
            if item[0] == object_id:
                item[1] = name
                found = True
                break
        if not found:
            self.add_value((object_id, name))
        self._updating = False

    def update_values(self, values):
        """
            Update view with values
            @param [(int, str)]
            @thread safe
        """
        self._updating = True
        # Remove not found items but not devices
        value_ids = set([v[0] for v in values])
        for item in self._model:
            if item[0] > Type.DEVICES and not item[0] in value_ids:
                self._model.remove(item.iter)
        # Add items which are not already in the list
        item_ids = set([i[0] for i in self._model])
        for value in values:
            if not value[0] in item_ids:
                self._add_value(value)
        self._updating = False

    def get_value(self, object_id):
        """
            Return value for id
            @param id as int
            @return value as string
        """
        for item in self._model:
            if item[0] == object_id:
                return item[1]
        return ''

    def will_be_selected(self):
        """
            Return True if list will select items on populate
            @return selected as bool
        """
        return self._to_select_ids

    def select_ids(self, ids):
        """
            Make treeview select first default item
            @param object id as int
        """
        self._to_select_ids = []
        if ids:
            try:
                iters = []
                for i in list(ids):
                    for item in self._model:
                        if item[0] == i:
                            iters.append(item.iter)
                            ids.remove(i)
                # Select later
                if ids:
                    self._to_select_ids = ids
                else:
                    for i in iters:
                        self._selection.select_iter(i)
            except:
                self._last_motion_event = None
                self._to_select_ids = ids
        else:
            self._selection.unselect_all()

    def get_selected_ids(self):
        """
            Get selected ids
            @return array of ids as [int]
        """
        selected_ids = []
        (model, items) = self._selection.get_selected_rows()
        if model is not None:
            for item in items:
                selected_ids.append(model[item][0])
        return selected_ids

    def clear(self):
        """
            Clear treeview
        """
        self._updating = True
        self._model.clear()
        self._updating = False

#######################
# PRIVATE             #
#######################
    def _add_value(self, value):
        """
            Add value to the model
            @param value as [int, str]
            @thread safe
        """
        if value[1] == "":
            string = _("Unknown")
        else:
            string = value[1]
        i = self._model.append([value[0],
                                string,
                                self._get_icon_name(value[0])])
        if value[0] in self._to_select_ids:
            self._to_select_ids.remove(value[0])
            self._selection.select_iter(i)

    def _add_values(self, values):
        """
            Add values to the list
            @param items as [(int,str)]
            @thread safe
        """
        for value in values:
            self._add_value(value)
        self._to_select_ids = []

    def _get_icon_name(self, object_id):
        """
            Return pixbuf for id
            @param ojbect_id as id
        """
        icon = ''
        if object_id == Type.POPULARS:
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

    def _sort_items(self, model, itera, iterb, data):
        """
            Sort model
        """
        if not self._updating:
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
            if self._is_artists:
                a = Lp().artists.get_sortname(a_index)
                b = Lp().artists.get_sortname(b_index)
            else:
                a = model.get_value(itera, 1)
                b = model.get_value(iterb, 1)
            return strcoll(a, b)

    def _row_separator_func(self, model, iterator):
        """
            Draw a separator if needed
            @param model as Gtk.TreeModel
            @param iterator as Gtk.TreeIter
        """
        return model.get_value(iterator, 0) == Type.SEPARATOR

    def _selection_validation(self, selection, model, path, current):
        """
            Check if selection is valid
            @param selection as Gtk.TreeSelection
            @param model as Gtk.TreeModel
            @param path as Gtk.TreePath
            @param current as bool
            @return bool
        """
        ids = self.get_selected_ids()
        if not ids or self._mode == SelectionMode.NORMAL:
            return True
        elif self._modifier:
            iterator = self._model.get_iter(path)
            value = self._model.get_value(iterator, 0)
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

    def _hide_popover(self):
        """
            Hide popover
        """
        self._popover.hide()
        self._timeout = None

    def _on_button_press_event(self, view, event):
        view.grab_focus()
        state = event.get_state()
        if state & Gdk.ModifierType.CONTROL_MASK or\
           state & Gdk.ModifierType.SHIFT_MASK:
            self._modifier = True

    def _on_button_release_event(self, view, event):
        self._modifier = False

    def _on_selection_changed(self, selection):
        """
            Forward as "item-selected"
            @param view as Gtk.TreeSelection
        """
        if not self._updating and not self._to_select_ids:
            self.emit('item-selected')

    def _on_enter_notify(self, widget, event):
        """
            Disable shortcuts
            @param widget as Gtk.widget
            @param event as Gdk.Event
        """
        # FIXME Not needed with GTK >= 3.18
        Lp().window.enable_global_shorcuts(False)

    def _on_leave_notify(self, widget, event):
        """
            Hide popover
            @param widget as Gtk.widget
            @param event as GdK.Event
        """
        # FIXME Not needed with GTK >= 3.18
        Lp().window.enable_global_shorcuts(True)
        self._hide_popover()
        self._last_motion_event = None

    def _on_motion_notify(self, widget, event):
        """
            Set motion event
            @param widget as Gtk.widget
            @param event as Gdk.Event
        """
        if self._timeout is None:
            self._timeout = GLib.timeout_add(500,
                                             self._hide_popover)
        if event.x < 0.0 or event.y < 0.0:
            self._last_motion_event = None
            return
        if self._last_motion_event is None:
            self._last_motion_event = MotionEvent()
        self._last_motion_event.x = event.x
        self._last_motion_event.y = event.y

    def _on_scroll(self, adj):
        """
            Show a popover with current letter
            @param adj as Gtk.Adjustement
        """
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

        # We need to get artist sortname
        if self._is_artists:
            rowid = self._model.get_value(row_iter, 0)
            text = Lp().artists.get_sortname(rowid)
        else:
            text = self._model.get_value(row_iter, 1)
        if text:
            self._popover.set_text("  %s  " % text[0].upper())
            self._popover.set_relative_to(self)
            r = Gdk.Rectangle()
            r.x = self.get_allocated_width()
            r.y = self._last_motion_event.y
            r.width = 1
            r.height = 1
            self._popover.set_pointing_to(r)
            self._popover.set_position(Gtk.PositionType.RIGHT)
            self._popover.show()

    def _on_artist_artwork_changed(self, art, artist):
        """
            Update row
        """
        if self._is_artists:
            self._renderer0.on_artist_artwork_changed(artist)
            for item in self._model:
                if item[1] == artist:
                    item[1] = artist
                    break

    def _on_query_tooltip(self, widget, x, y, keyboard, tooltip):
        """
            Show tooltip if needed
            @param widget as Gtk.Widget
            @param x as int
            @param y as int
            @param keyboard as bool
            @param tooltip as Gtk.Tooltip
        """
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
                if Lp().settings.get_value('artist-artwork') and\
                        self._is_artists:
                    width -= ArtSize.ARTIST_SMALL +\
                             CellRendererArtist.xshift * 2
                layout.set_ellipsize(Pango.EllipsizeMode.END)
                if self._model.get_value(iterator, 0) < 0:
                    width -= 8
                layout.set_width(Pango.units_from_double(width))
                layout.set_text(text, -1)
                if layout.is_ellipsized():
                    tooltip.set_markup(escape(text))
                    return True
        return False
