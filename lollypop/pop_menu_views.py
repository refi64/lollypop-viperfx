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

from gi.repository import Gtk, Gio, GLib

from gettext import gettext as _
from hashlib import sha256

from lollypop.define import Type, App, SelectionListMask
from lollypop.shown import ShownLists, ShownPlaylists


class ViewsMenuPopover(Gtk.Popover):
    """
        Configure defaults items
    """

    def __init__(self, widget, rowid, mask):
        """
            Init menu
            @param widget as Gtk.Widget
            @param rowid as int
            @param mask as SelectionListMask
        """
        Gtk.Popover.__init__(self)
        self.__widget = widget
        self.__rowid = rowid
        self.__mask = mask
        menu = Gio.Menu()
        self.bind_model(menu, None)
        # Startup menu
        if rowid in [Type.POPULARS, Type.RADIOS, Type.LOVED,
                     Type.ALL, Type.RECENTS, Type.YEARS,
                     Type.RANDOMS, Type.NEVER,
                     Type.PLAYLISTS, Type.ARTISTS] and\
                not App().settings.get_value("save-state"):
            startup_menu = Gio.Menu()
            if self.__mask & SelectionListMask.LIST_TWO:
                exists = rowid in App().startup_ids2
            else:
                exists = rowid in App().startup_ids1
            action = Gio.SimpleAction.new_stateful(
                                           "default_selection_id",
                                           None,
                                           GLib.Variant.new_boolean(exists))
            App().add_action(action)
            action.connect("change-state",
                           self.__on_default_change_state,
                           rowid)
            item = Gio.MenuItem.new(_("Default on startup"),
                                    "app.default_selection_id")
            startup_menu.append_item(item)
            menu.insert_section(0, _("Startup"), startup_menu)
        # Shown menu
        shown_menu = Gio.Menu()
        if mask & SelectionListMask.PLAYLISTS:
            lists = ShownPlaylists.get(True)
            wanted = App().settings.get_value("shown-playlists")
        else:
            lists = ShownLists.get(mask, True)
            wanted = App().settings.get_value("shown-album-lists")
        for item in lists:
            exists = item[0] in wanted
            encoded = sha256(item[1].encode("utf-8")).hexdigest()
            action = Gio.SimpleAction.new_stateful(
                encoded,
                None,
                GLib.Variant.new_boolean(exists))
            action.connect("change-state",
                           self.__on_shown_change_state,
                           item[0])
            App().add_action(action)
            shown_menu.append(item[1], "app.%s" % encoded)
        # Translators: shown => items
        menu.insert_section(1, _("Shown"), shown_menu)

#######################
# PRIVATE             #
#######################
    def __on_shown_change_state(self, action, variant, rowid):
        """
            Set action value
            @param action as Gio.SimpleAction
            @param variant as GLib.Variant
            @param rowid as int
        """
        action.set_state(variant)
        if self.__mask & SelectionListMask.PLAYLISTS:
            option = "shown-playlists"
        else:
            option = "shown-album-lists"
        wanted = list(App().settings.get_value(option))
        if variant:
            wanted.append(rowid)
        else:
            wanted.remove(rowid)
        App().settings.set_value(option, GLib.Variant("ai", wanted))
        if self.__mask & SelectionListMask.PLAYLISTS:
            items = ShownPlaylists.get(True)
        else:
            items = ShownLists.get(self.__mask, True)
        if variant:
            for item in items:
                if item[0] == rowid:
                    self.__widget.add_value(item)
                    break
        else:
            self.__widget.remove_value(rowid)
            if self.__mask & SelectionListMask.LIST_ONE:
                ids = App().startup_ids1
                if rowid in ids:
                    ids.remove(rowid)
                App().set_startup_ids(ids, [])
        self.popdown()

    def __on_default_change_state(self, action, variant, rowid):
        """
            Add to playlists
            @param action as Gio.SimpleAction
            @param variant as GVariant
            @param rowid as int
        """
        if self.__mask & SelectionListMask.LIST_ONE:
            if variant:
                App().set_startup_ids([rowid], [])
            else:
                App().set_startup_ids([], [])
        elif self.__mask & SelectionListMask.LIST_TWO:
            if variant:
                App().set_startup_ids(None, [rowid])
            else:
                App().set_startup_ids(None, [])
        self.popdown()
