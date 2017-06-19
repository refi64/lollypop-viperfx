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

from gi.repository import Gtk, Gdk, GLib, GObject, Pango

from gettext import gettext as _
from locale import strcoll

from lollypop.cellrenderer import CellRendererArtist
from lollypop.fastscroll import FastScroll
from lollypop.define import Type, Lp, ArtSize


class SelectionList(Gtk.Overlay):
    """
        A list for artists/genres
    """
    __gsignals__ = {
        "item-selected": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "populated": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "pass-focus": (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self, sidebar=True):
        """
            Init Selection list ui
            @param sidebar as bool
        """
        Gtk.Overlay.__init__(self)
        self.__was_visible = False
        self.__timeout = None
        self.__to_select_ids = []
        self.__modifier = False
        self.__populating = False
        self.__updating = False       # Sort disabled if False
        self.__is_artists = False
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/SelectionList.ui")
        builder.connect_signals(self)
        self.__selection = builder.get_object("selection")
        self.__selection.set_select_function(self.__selection_validation)
        self.__model = builder.get_object("model")
        self.__model.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.__model.set_sort_func(0, self.__sort_items)
        self.__view = builder.get_object("view")
        if sidebar:
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
        if Gtk.get_minor_version() > 14:
            self.__fast_scroll = FastScroll(self.__view,
                                            self.__model,
                                            self.__scrolled)
            self.add_overlay(self.__fast_scroll)
        else:
            self.__fast_scroll = None
        self.__scrolled.connect("enter-notify-event", self.__on_enter_notify)
        self.__scrolled.connect("leave-notify-event", self.__on_leave_notify)

        Lp().art.connect("artist-artwork-changed",
                         self.__on_artist_artwork_changed)

    def hide(self):
        """
            Hide widget, remember state
        """
        self.__was_visible = self.is_visible()
        Gtk.Bin.hide(self)

    @property
    def was_visible(self):
        """
            True if widget was visible on previous hide
        """
        return self.__was_visible

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
            @param [(int, str, optional str)], will be deleted
            @thread safe
        """
        if self.__populating:
            return
        self.__populating = True
        if len(self.__model) > 0:
            self.__updating = True
        self.__add_values(values)
        self.emit("populated")
        self.__updating = False
        self.__populating = False

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
            self.__add_value((object_id, name))
        self.__updating = False

    def update_values(self, values):
        """
            Update view with values
            @param [(int, str, optional str)]
            @thread safe
        """
        self.__updating = True
        if self.__is_artists and self.__fast_scroll is not None:
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
        if self.__is_artists and self.__fast_scroll is not None:
            self.__fast_scroll.populate()
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
        return ""

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
                items = []
                for i in list(ids):
                    for item in self.__model:
                        if item[0] == i:
                            items.append(item)
                            ids.remove(i)
                # Select later
                if ids:
                    self.__to_select_ids = ids
                else:
                    for item in items:
                        self.__selection.select_iter(item.iter)
                    # Scroll to first item
                    if items:
                        self.__view.scroll_to_cell(items[0].path,
                                                   None,
                                                   True,
                                                   0, 0)
            except:
                self.__last_motion_event = None
                self.__to_select_ids = ids
        else:
            self.__selection.unselect_all()

    def grab_focus(self):
        """
            Grab focus on treeview
        """
        self.__view.grab_focus()

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

    def clear(self):
        """
            Clear treeview
        """
        self.__updating = True
        self.__model.clear()
        if self.__is_artists and self.__fast_scroll is not None:
            self.__fast_scroll.clear()
            self.__fast_scroll.clear_chars()
            self.__fast_scroll.hide()
        self.__updating = False

    def get_headers(self):
        """
            Return headers
            @return items as [(int, str)]
        """
        items = []
        items.append((Type.POPULARS, _("Popular albums")))
        if Lp().albums.has_loves():
            items.append((Type.LOVED, _("Loved albums")))
        items.append((Type.RECENTS, _("Recently added albums")))
        items.append((Type.RANDOMS, _("Random albums")))
        items.append((Type.PLAYLISTS, _("Playlists")))
        items.append((Type.RADIOS, _("Radios")))
        if Lp().settings.get_value("show-charts") and\
                Lp().settings.get_value("network-access"):
            items.append((Type.CHARTS, _("The charts")))
        if self.__is_artists:
            items.append((Type.ALL, _("All albums")))
        else:
            items.append((Type.ALL, _("All artists")))
        return items

    def get_pl_headers(self):
        """
            Return playlist headers
            @return items as [(int, str)]
        """
        items = []
        items.append((Type.POPULARS, _("Popular tracks")))
        items.append((Type.LOVED, Lp().playlists.LOVED))
        items.append((Type.RECENTS, _("Recently played")))
        items.append((Type.NEVER, _("Never played")))
        items.append((Type.RANDOMS, _("Random tracks")))
        items.append((Type.NOPARTY, _("Not in party")))
        items.append((Type.SEPARATOR, ""))
        return items

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
        view.grab_focus()
        state = event.get_state()
        if state & Gdk.ModifierType.CONTROL_MASK or\
           state & Gdk.ModifierType.SHIFT_MASK:
            self.__modifier = True

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
                if Lp().settings.get_value("artist-artwork") and\
                        self.__is_artists:
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
        return False

    def _on_selection_changed(self, selection):
        """
            Forward as "item-selected"
            @param view as Gtk.TreeSelection
        """
        if not self.__updating and not self.__to_select_ids:
            self.emit("item-selected")

#######################
# PRIVATE             #
#######################
    def __add_value(self, value):
        """
            Add value to the model
            @param value as [int, str, optional str]
            @thread safe
        """
        if value[1] == "":
            string = _("Unknown")
            sort = string
        else:
            string = value[1]
            if len(value) == 3:
                sort = value[2]
            else:
                sort = value[1]

        if value[0] > 0 and sort and self.__is_artists and\
                self.__fast_scroll is not None:
            self.__fast_scroll.add_char(sort[0])
        icon_name = self.__get_icon_name(value[0])
        if not icon_name and string == _("Unknown"):
            icon_name = "dialog-warning-symbolic"
        i = self.__model.append([value[0],
                                string,
                                icon_name,
                                sort])
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
        if self.__is_artists and self.__fast_scroll is not None:
            self.__fast_scroll.populate()
        self.__to_select_ids = []

    def __get_icon_name(self, object_id):
        """
            Return pixbuf for id
            @param ojbect_id as id
        """
        icon = ""
        if object_id == Type.POPULARS:
            icon = "starred-symbolic"
        elif object_id == Type.PLAYLISTS:
            icon = "emblem-documents-symbolic"
        elif object_id == Type.ALL:
            if self.__is_artists:
                icon = "media-optical-cd-audio-symbolic"
            else:
                icon = "avatar-default-symbolic"
        elif object_id == Type.COMPILATIONS:
            icon = "system-users-symbolic"
        elif object_id == Type.RECENTS:
            icon = "document-open-recent-symbolic"
        elif object_id == Type.RADIOS:
            icon = "audio-input-microphone-symbolic"
        elif object_id < Type.DEVICES:
            icon = "multimedia-player-symbolic"
        elif object_id == Type.RANDOMS:
            icon = "media-playlist-shuffle-symbolic"
        elif object_id == Type.LOVED:
            icon = "emblem-favorite-symbolic"
        elif object_id == Type.NEVER:
            icon = "document-new-symbolic"
        elif object_id == Type.CHARTS:
            icon = "application-rss+xml-symbolic"
        elif object_id == Type.SPOTIFY:
            icon = "lollypop-spotify-symbolic"
        elif object_id == Type.ITUNES:
            icon = "lollypop-itunes-symbolic"
        elif object_id == Type.LASTFM:
            icon = "lollypop-lastfm-symbolic"
        elif object_id == Type.NOPARTY:
            icon = "emblem-music-symbolic"
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
                widget.get_allocated_height() and self.__is_artists and\
                self.__fast_scroll is not None:
            self.__fast_scroll.show()
        # FIXME Not needed with GTK >= 3.18
        Lp().window.enable_global_shortcuts(False)

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
            if self.__is_artists and self.__fast_scroll is not None:
                self.__fast_scroll.hide()
        # FIXME Not needed with GTK >= 3.18
        Lp().window.enable_global_shortcuts(True)

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
