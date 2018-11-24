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

from gi.repository import Gtk, GLib

from gettext import gettext as _

from lollypop.define import App, Type
from lollypop.view_flowbox import FlowBoxView
from lollypop.widgets_radio import RadioWidget
from lollypop.pop_radio import RadioPopover
from lollypop.pop_tunein import TuneinPopover
from lollypop.controller_view import ViewController
from lollypop.view import MessageView


class RadiosView(FlowBoxView, ViewController):
    """
        Show radios flow box
    """

    def __init__(self, radios):
        """
            Init view
            @param radios as Radios
        """
        FlowBoxView.__init__(self)
        ViewController.__init__(self)
        self._widget_class = RadioWidget
        self.__radios = radios
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/RadiosView.ui")
        builder.connect_signals(self)
        self.insert_row(0)
        self.attach(builder.get_object("widget"), 0, 0, 1, 1)

        self.__pop_tunein = TuneinPopover(self.__radios)
        self.__pop_tunein.set_relative_to(builder.get_object("search_btn"))
        self.connect_current_changed_signal()
        self.connect_artwork_changed_signal("radio")

    def show_warning(self):
        """
            Show a message to user
        """
        self._scrolled.hide()
        view = MessageView(_("No favorite radios"))
        view.show()
        self.add(view)

#######################
# PROTECTED           #
#######################
    def _add_items(self, radio_ids):
        """
            Add radios to the view
            Start lazy loading
            @param radio ids as [int]
        """
        FlowBoxView._add_items(self, radio_ids, self.__radios)

    def _on_new_clicked(self, widget):
        """
            Show popover for adding a new radio
            @param widget as Gtk.Widget
        """
        popover = RadioPopover("", self.__radios)
        popover.set_relative_to(widget)
        popover.popup()

    def _on_search_clicked(self, widget):
        """
            Show popover for searching radios
            @param widget as Gtk.Widget
        """
        self.__pop_tunein.populate()
        self.__pop_tunein.show()

    def _on_artwork_changed(self, artwork, title):
        """
            Update children artwork if matching name
            @param artwork as Artwork
            @param title as str
        """
        for child in self._box.get_children():
            if title == child.title:
                child.set_artwork()

    def _on_map(self, widget):
        """
            Set active ids
        """
        App().settings.set_value("state-one-ids",
                                 GLib.Variant("ai", [Type.RADIOS]))
        App().settings.set_value("state-two-ids",
                                 GLib.Variant("ai", []))

    def _on_unmap(self, widget):
        """
            Destroy popover
            @param widget as Gtk.Widget
        """
        self.__pop_tunein.destroy()

#######################
# PRIVATE             #
#######################
    def __on_logo_changed(self, player, name):
        """
            Update radio logo
            @param player as Plyaer
            @param name as string
        """
        for child in self._box.get_children():
            if child.title == name:
                child.update_cover()
