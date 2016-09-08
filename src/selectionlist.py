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
        self.__label = Gtk.Label()
        self.__label.set_property('halign', Gtk.Align.CENTER)
        self.__label.set_property('valign', Gtk.Align.CENTER)
        self.__label.show()
        self.get_style_context().add_class('osd-popover')
        self.set_property('width-request', 100)
        self.set_property('height-request', 50)
        self.add(self.__label)

    def set_text(self, text):
        """
            Set popover text
            @param text as string
        """
        self.__label.set_markup('<span size="large"><b>%s</b></span>' % text)

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
        self.__mode = mode
        self.__last_motion_event = None
        self.__previous_motion_y = 0.0
        self.__timeout = None
        self.__to_select_ids = []
        self.__modifier = False
        self.__updating = False       # Sort disabled if False
        self.__is_artists = False
        self.__popover = SelectionPopover()
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/SelectionList.ui')
        builder.connect_signals(self)
        self.__selection = builder.get_object('selection')
        self.__selection.set_select_function(self.__selection_validation)
        self.__model = builder.get_object('model')
        self.__model.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.__model.set_sort_func(0, self.__sort_items)
        self.__view = builder.get_object('view')
        self.__view.set_row_separator_func(self.__row_separator_func)
        self.__renderer0 = CellRendererArtist()
        self.__renderer0.set_property('ellipsize-set', True)
        self.__renderer0.set_property('ellipsize', Pango.EllipsizeMode.END)
        self.__renderer1 = Gtk.CellRendererPixbuf()
        # 16px for Gtk.IconSize.MENU
        self.__renderer1.set_fixed_size(16, -1)
        column = Gtk.TreeViewColumn('')
        column.set_expand(True)
        column.pack_start(self.__renderer0, True)
        column.add_attribute(self.__renderer0, 'text', 1)
        column.add_attribute(self.__renderer0, 'artist', 1)
        column.add_attribute(self.__renderer0, 'rowid', 0)
        column.pack_start(self.__renderer1, False)
        column.add_attribute(self.__renderer1, 'icon-name', 2)
        self.__view.append_column(column)
        self.__view.set_property('has_tooltip', True)
        self.add(self.__view)
        self.connect('motion_notify_event', self.__on_motion_notify)
        self.get_vadjustment().connect('value_changed', self.__on_scroll)
        self.connect('enter-notify-event', self.__on_enter_notify)
        self.connect('leave-notify-event', self.__on_leave_notify)
        Lp().art.connect('artist-artwork-changed',
                         self.__on_artist_artwork_changed)

    def mark_as_artists(self, is_artists):
        """
            Mark list as artists list
            @param is_artists as bool
        """
        self.__is_artists = is_artists
        self.__renderer0.set_is_artists(is_artists)

    def is_marked_as_artists(self):
        """
            Return True if list is marked as artists
        """
        return self.__is_artists

    def populate(self, values):
        """
            Populate view with values
            @param [(int, str)], will be deleted
            @thread safe
        """
        if len(self.__model) > 0:
            self.__updating = True
        self.__add_values(values)
        self.emit('populated')
        self.__updating = False

    def remove_value(self, object_id):
        """
            Remove row from model
            @param object id as int
        """
        for item in self.__model:
            if item[0] == object_id:
                self.__model.remove(item.iter)
                break
        # We force selection of first item
        self.__selection.unselect_all()
        self.__selection.select_iter(self.__model[0].iter)

    def add_value(self, value):
        """
            Add item to list
            @param value as (int, str)
        """
        self.__updating = True
        self.__add_value(value)
        self.__updating = False

    def update_value(self, object_id, name):
        """
            Update object with new name
            @param object id as int
            @param name as str
        """
        self.__updating = True
        found = False
        for item in self.__model:
            if item[0] == object_id:
                item[1] = name
                found = True
                break
        if not found:
            self.add_value((object_id, name))
        self.__updating = False

    def update_values(self, values):
        """
            Update view with values
            @param [(int, str)]
            @thread safe
        """
        self.__updating = True
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
        self.__updating = False

    def get_value(self, object_id):
        """
            Return value for id
            @param id as int
            @return value as string
        """
        for item in self.__model:
            if item[0] == object_id:
                return item[1]
        return ''

    def will_be_selected(self):
        """
            Return True if list will select items on populate
            @return selected as bool
        """
        return self.__to_select_ids

    def select_ids(self, ids):
        """
            Make treeview select first default item
            @param object id as int
        """
        self.__to_select_ids = []
        if ids:
            try:
                # Check if items are available for selection
                iters = []
                for i in list(ids):
                    for item in self.__model:
                        if item[0] == i:
                            iters.append(item.iter)
                            ids.remove(i)
                # Select later
                if ids:
                    self.__to_select_ids = ids
                else:
                    for i in iters:
                        self.__selection.select_iter(i)
            except:
                self.__last_motion_event = None
                self.__to_select_ids = ids
        else:
            self.__selection.unselect_all()

    def get_selected_ids(self):
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

    def clear(self):
        """
            Clear treeview
        """
        self.__updating = True
        self.__model.clear()
        self.__updating = False

#######################
# PROTECTED           #
#######################
    def _on_button_press_event(self, view, event):
        view.grab_focus()
        state = event.get_state()
        if state & Gdk.ModifierType.CONTROL_MASK or\
           state & Gdk.ModifierType.SHIFT_MASK:
            self.__modifier = True

    def _on_button_release_event(self, view, event):
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
                if Lp().settings.get_value('artist-artwork') and\
                        self.__is_artists:
                    width -= ArtSize.ARTIST_SMALL +\
                             CellRendererArtist.xshift * 2
                layout.set_ellipsize(Pango.EllipsizeMode.END)
                if self.__model.get_value(iterator, 0) < 0:
                    width -= 8
                layout.set_width(Pango.units_from_double(width))
                layout.set_text(text, -1)
                if layout.is_ellipsized():
                    tooltip.set_markup(escape(text))
                    return True
        return False

    def _on_selection_changed(self, selection):
        """
            Forward as "item-selected"
            @param view as Gtk.TreeSelection
        """
        if not self.__updating and not self.__to_select_ids:
            self.emit('item-selected')

#######################
# PRIVATE             #
#######################
    def __add_value(self, value):
        """
            Add value to the model
            @param value as [int, str]
            @thread safe
        """
        if value[1] == "":
            string = _("Unknown")
        else:
            string = value[1]
        i = self.__model.append([value[0],
                                string,
                                self.__get_icon_name(value[0])])
        if value[0] in self.__to_select_ids:
            self.__to_select_ids.remove(value[0])
            self.__selection.select_iter(i)

    def __add_values(self, values):
        """
            Add values to the list
            @param items as [(int,str)]
            @thread safe
        """
        for value in values:
            self.__add_value(value)
        self.__to_select_ids = []

    def __get_icon_name(self, object_id):
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
            if self.__is_artists:
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

    def __sort_items(self, model, itera, iterb, data):
        """
            Sort model
        """
        if not self.__updating:
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
            if self.__is_artists:
                a = Lp().artists.get_sortname(a_index)
                b = Lp().artists.get_sortname(b_index)
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
        ids = self.get_selected_ids()
        if not ids or self.__mode == SelectionMode.NORMAL:
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

    def __hide_popover(self):
        """
            Hide popover
        """
        self.__popover.hide()
        self.__timeout = None

    def __on_enter_notify(self, widget, event):
        """
            Disable shortcuts
            @param widget as Gtk.widget
            @param event as Gdk.Event
        """
        # FIXME Not needed with GTK >= 3.18
        Lp().window.enable_global_shorcuts(False)

    def __on_leave_notify(self, widget, event):
        """
            Hide popover
            @param widget as Gtk.widget
            @param event as GdK.Event
        """
        # FIXME Not needed with GTK >= 3.18
        Lp().window.enable_global_shorcuts(True)
        self.__hide_popover()
        self.__last_motion_event = None

    def __on_motion_notify(self, widget, event):
        """
            Set motion event
            @param widget as Gtk.widget
            @param event as Gdk.Event
        """
        if self.__timeout is None:
            self.__timeout = GLib.timeout_add(500,
                                              self.__hide_popover)
        if event.x < 0.0 or event.y < 0.0:
            self.__last_motion_event = None
            return
        if self.__last_motion_event is None:
            self.__last_motion_event = MotionEvent()
        self.__last_motion_event.x = event.x
        self.__last_motion_event.y = event.y

    def __on_scroll(self, adj):
        """
            Show a popover with current letter
            @param adj as Gtk.Adjustement
        """
        # Only show if scrolled window is huge
        if adj.get_upper() < adj.get_page_size() * 3:
            return
        if self.__last_motion_event is None:
            return

        if self.__timeout is not None:
            GLib.source_remove(self.__timeout)
            self.__timeout = None

        dest_row = self.__view.get_dest_row_at_pos(self.__last_motion_event.x,
                                                   self.__last_motion_event.y)
        if dest_row is None:
            return

        row = dest_row[0]

        if row is None:
            return

        row_iter = self.__model.get_iter(row)
        if row_iter is None or self.__model.get_value(row_iter, 0) < 0:
            return

        # We need to get artist sortname
        if self.__is_artists:
            rowid = self.__model.get_value(row_iter, 0)
            text = Lp().artists.get_sortname(rowid)
        else:
            text = self.__model.get_value(row_iter, 1)
        if text:
            self.__popover.set_text("  %s  " % text[0].upper())
            self.__popover.set_relative_to(self)
            r = Gdk.Rectangle()
            r.x = self.get_allocated_width()
            r.y = self.__last_motion_event.y
            r.width = 1
            r.height = 1
            self.__popover.set_pointing_to(r)
            self.__popover.set_position(Gtk.PositionType.RIGHT)
            self.__popover.show()

    def __on_artist_artwork_changed(self, art, artist):
        """
            Update row
        """
        if self.__is_artists:
            self.__renderer0.on_artist_artwork_changed(artist)
            for item in self.__model:
                if item[1] == artist:
                    item[1] = artist
                    break
