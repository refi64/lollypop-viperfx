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

from gi.repository import Gtk, Gdk, Gio, GLib, GObject, Pango

from gettext import gettext as _
from locale import strcoll
from hashlib import sha256

from lollypop.cellrenderer import CellRendererArtist
from lollypop.fastscroll import FastScroll
from lollypop.define import Type, App, ArtSize


class ShownAlbumlists:
    """
        Handle shown album lists
    """
    def get(mask, get_all=False):
        """
            Get list
            @param mask as bit mask
            @param get_all as bool
        """
        wanted = App().settings.get_value("shown-album-lists")
        lists = []
        if mask & SelectionList.Type.LIST_ONE:
            if get_all or Type.POPULARS in wanted:
                lists.append((Type.POPULARS, _("Popular albums")))
            if get_all or (App().albums.has_loves() and Type.LOVED in wanted):
                lists.append((Type.LOVED, _("Loved albums")))
            if get_all or Type.RECENTS in wanted:
                lists.append((Type.RECENTS, _("Recently added albums")))
            if get_all or Type.RANDOMS in wanted:
                lists.append((Type.RANDOMS, _("Random albums")))
            if get_all or Type.NEVER in wanted:
                lists.append((Type.NEVER, _("Unplayed albums")))
            if get_all or Type.PLAYLISTS in wanted:
                lists.append((Type.PLAYLISTS, _("Playlists")))
            if get_all or Type.RADIOS in wanted:
                lists.append((Type.RADIOS, _("Radios")))
            if get_all or Type.ALL in wanted:
                if mask & SelectionList.Type.ARTISTS:
                    lists.append((Type.ALL, _("All albums")))
                else:
                    lists.append((Type.ALL, _("All artists")))
        if get_all or (mask & SelectionList.Type.COMPILATIONS and
                       Type.COMPILATIONS in wanted):
            lists.append((Type.COMPILATIONS, _("Compilations")))
        if get_all:
            lists.append((Type.USB_DISKS, _("USB disks")))
        return lists


class ShownPlaylists:
    """
        Handle shown playlists
    """
    def get(get_all=False):
        """
            get list
            @param get_all as bool
        """
        wanted = App().settings.get_value("shown-playlists")
        lists = []
        if get_all or Type.POPULARS in wanted:
            lists.append((Type.POPULARS, _("Popular tracks")))
        if get_all or Type.LOVED in wanted:
            lists.append((Type.LOVED, App().playlists.LOVED))
        if get_all or Type.RECENTS in wanted:
            lists.append((Type.RECENTS, _("Recently played")))
        if get_all or Type.NEVER in wanted:
            lists.append((Type.NEVER, _("Unplayed")))
        if get_all or Type.RANDOMS in wanted:
            lists.append((Type.RANDOMS, _("Random tracks")))
        if get_all or Type.NOPARTY in wanted:
            lists.append((Type.NOPARTY, _("Not in party")))
        return lists


class DefaultItemsMenu(Gio.Menu):
    """
        Configure defaults items
    """

    def __init__(self, rowid, list_type):
        """
            Init menu
            @param rowid as int
            @param lists as [int]
            @param list_type as SelectionList.Type
        """
        Gio.Menu.__init__(self)
        self.__rowid = rowid
        self.__list_type = list_type
        # Startup menu
        if rowid in [Type.POPULARS, Type.RADIOS, Type.LOVED,
                     Type.ALL, Type.RECENTS,
                     Type.RANDOMS, Type.NEVER,
                     Type.PLAYLISTS]:
            startup_menu = Gio.Menu()
            action = Gio.SimpleAction(name="default_selection_id")
            App().add_action(action)
            action.connect('activate',
                           self.__on_action_clicked,
                           rowid)
            item = Gio.MenuItem.new(_("Default on startup"),
                                    "app.default_selection_id")
            startup_menu.append_item(item)
            self.insert_section(0, _("Startup"), startup_menu)
        # Shown menu
        shown_menu = Gio.Menu()
        if list_type & SelectionList.Type.PLAYLISTS:
            lists = ShownPlaylists.get(True)
            wanted = App().settings.get_value("shown-playlists")
        else:
            lists = ShownAlbumlists.get(list_type, True)
            wanted = App().settings.get_value("shown-album-lists")
        for item in lists:
            exists = item[0] in wanted
            encoded = sha256(item[1].encode("utf-8")).hexdigest()
            action = Gio.SimpleAction.new_stateful(
                encoded,
                None,
                GLib.Variant.new_boolean(exists))
            action.connect("change-state",
                           self.__on_action_change_state,
                           item[0])
            App().add_action(action)
            shown_menu.append(item[1], "app.%s" % encoded)
        # Translators: shown => items
        self.insert_section(1, _("Shown"), shown_menu)

#######################
# PRIVATE             #
#######################
    def __on_action_change_state(self, action, param, rowid):
        """
            Set action value
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
            @param rowid as int
        """
        action.set_state(param)
        if self.__list_type & SelectionList.Type.PLAYLISTS:
            option = "shown-playlists"
        else:
            option = "shown-album-lists"
        wanted = list(App().settings.get_value(option))
        if param:
            wanted.append(rowid)
        else:
            wanted.remove(rowid)
        App().settings.set_value(option, GLib.Variant("ai", wanted))
        if self.__list_type & SelectionList.Type.LIST_ONE:
            App().window.container.update_list_one()
        elif self.__list_type & SelectionList.Type.LIST_TWO:
            App().window.container.update_list_two()

    def __on_action_clicked(self, action, variant, rowid):
        """
            Add to playlists
            @param Gio.SimpleAction
            @param GVariant
            @param rowid as int
        """
        if self.__list_type & SelectionList.Type.LIST_ONE:
            App().settings.set_value(
                "list-one-ids",
                GLib.Variant("ai", [rowid]))
        elif self.__list_type & SelectionList.Type.LIST_TWO:
            App().settings.set_value(
                "list-two-ids",
                GLib.Variant("ai", [rowid]))


class SelectionList(Gtk.Overlay):
    """
        A list for artists/genres
    """
    __gsignals__ = {
        "item-selected": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "populated": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "pass-focus": (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    class Type:
        LIST_ONE = 1 << 1
        LIST_TWO = 1 << 2
        LIST_DEVICE = 1 << 3
        ARTISTS = 1 << 4
        GENRE = 1 << 5
        PLAYLISTS = 1 << 6
        COMPILATIONS = 1 << 7

    def __init__(self, base_type):
        """
            Init Selection list ui
            @param base_type as SelectionList.Type
        """
        Gtk.Overlay.__init__(self)
        self.__base_type = base_type
        self.__was_visible = False
        self.__timeout = None
        self.__modifier = False
        self.__populating = False
        self.__type = 0
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/SelectionList.ui")
        builder.connect_signals(self)
        self.__selection = builder.get_object("selection")
        self.__selection.set_select_function(self.__selection_validation)
        self.__selection.connect("changed", self.__on_selection_changed)
        self.__model = builder.get_object("model")
        self.__model.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.__model.set_sort_func(0, self.__sort_items)
        self.__view = builder.get_object("view")
        if base_type in [SelectionList.Type.LIST_ONE,
                         SelectionList.Type.LIST_TWO]:
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

    def hide(self):
        """
            Hide widget, remember state
        """
        self.__was_visible = self.is_visible()
        Gtk.Bin.hide(self)

    def show(self, force=False):
        """
            Show widget if wanted
            @param force as bool
        """
        if force or App().settings.get_value("show-sidebar"):
            Gtk.Bin.show(self)

    def mark_as(self, type):
        """
            Mark list as artists list
            @param type as SelectionList.Type
        """
        self.__type = self.__base_type | type
        self.__renderer0.set_is_artists(type & self.Type.ARTISTS)

    def populate(self, values):
        """
            Populate view with values
            @param [(int, str, optional str)], will be deleted
            @thread safe
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
            self.__add_value((object_id, name))

    def update_values(self, values):
        """
            Update view with values
            @param [(int, str, optional str)]
            @thread safe
        """
        update_fast_scroll = self.__type & self.Type.ARTISTS and\
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

    def select_ids(self, ids):
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
        if self.__type & self.Type.ARTISTS and self.__fast_scroll is not None:
            self.__fast_scroll.clear()
            self.__fast_scroll.clear_chars()
            self.__fast_scroll.hide()

    def get_headers(self):
        """
            Return headers
            @return items as [(int, str)]
        """
        lists = ShownAlbumlists.get(self.__type)
        lists.append((Type.SEPARATOR, ""))
        return lists

    def get_playlist_headers(self):
        """
            Return playlist headers
            @return items as [(int, str)]
        """
        lists = ShownPlaylists.get()
        lists.append((Type.SEPARATOR, ""))
        return lists

    @property
    def type(self):
        """
            Get selection list type
            @return bit mask
        """
        return self.__type

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

    @property
    def was_visible(self):
        """
            True if widget was visible on previous hide
        """
        return self.__was_visible

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
        elif self.__base_type in [SelectionList.Type.LIST_ONE,
                                  SelectionList.Type.LIST_TWO]:
            info = view.get_dest_row_at_pos(event.x, event.y)
            if info is not None and self.__type & SelectionList.Type.LIST_ONE:
                App().settings.set_value("shown-sidebar-tooltip",
                                         GLib.Variant("b", True))
                (path, position) = info
                iterator = self.__model.get_iter(path)
                rowid = self.__model.get_value(iterator, 0)
                menu = DefaultItemsMenu(rowid, self.type)
                popover = Gtk.Popover.new_from_model(view, menu)
                rect = Gdk.Rectangle()
                rect.x = event.x
                rect.y = event.y
                rect.width = rect.height = 1
                popover.set_pointing_to(rect)
                popover.show()
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
        if keyboard:
            return True
        elif not App().settings.get_value("shown-sidebar-tooltip"):
            tooltip.set_markup(_("Right click to configure"))
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
                        self.__type & self.Type.ARTISTS:
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

        if value[0] > 0 and sort and self.__type & self.Type.ARTISTS and\
                self.__fast_scroll is not None:
            self.__fast_scroll.add_char(sort[0])
        icon_name = self.__get_icon_name(value[0])
        if not icon_name and string == _("Unknown"):
            icon_name = "dialog-warning-symbolic"
        self.__model.append([value[0],
                            string,
                            icon_name,
                            sort])

    def __add_values(self, values):
        """
            Add values to the list
            @param items as [(int,str)]
            @thread safe
        """
        for value in values:
            self.__add_value(value)
        if self.__type & self.Type.ARTISTS and self.__fast_scroll is not None:
            self.__fast_scroll.populate()

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
            if self.__type & self.Type.ARTISTS:
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
            icon = "audio-speakers-symbolic"
        elif object_id == Type.NOPARTY:
            icon = "emblem-music-symbolic"
        return icon

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
            if self.__type & self.Type.ARTISTS:
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
                self.__type & self.Type.ARTISTS and\
                self.__fast_scroll is not None:
            self.__fast_scroll.show()
        # FIXME Not needed with GTK >= 3.18
        App().window.enable_global_shortcuts(False)

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
            if self.__type & self.Type.ARTISTS\
                    and self.__fast_scroll is not None:
                self.__fast_scroll.hide()
        # FIXME Not needed with GTK >= 3.18
        App().window.enable_global_shortcuts(True)

    def __on_artist_artwork_changed(self, art, artist):
        """
            Update row
        """
        if self.__type & self.Type.ARTISTS:
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
