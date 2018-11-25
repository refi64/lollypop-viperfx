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
from lollypop.radios import Radios
from lollypop.pop_tunein import TuneinPopover
from lollypop.controller_view import ViewController, ViewControllerType
from lollypop.view import MessageView


class RadiosView(FlowBoxView, ViewController):
    """
        Show radios flow box
    """

    def __init__(self):
        """
            Init view
        """
        FlowBoxView.__init__(self)
        ViewController.__init__(self, ViewControllerType.RADIO)
        self._widget_class = RadioWidget
        self.__radios = Radios()
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/RadiosView.ui")
        builder.connect_signals(self)
        self.insert_row(0)
        self.attach(builder.get_object("widget"), 0, 0, 1, 1)
        self.__pop_tunein = TuneinPopover(self.__radios)
        self.__pop_tunein.set_relative_to(builder.get_object("search_btn"))

    def populate(self, radio_ids):
        """
            Add radio widgets
            @param radio_ids as [int]
        """
        if radio_ids:
            FlowBoxView.populate(self, radio_ids)
        else:
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
        widget = FlowBoxView._add_items(self, radio_ids, self.__radios)
        if widget is not None:
            widget.connect("overlayed", self.on_overlayed)

    def _on_new_clicked(self, widget):
        """
            Show popover for adding a new radio
            @param widget as Gtk.Widget
        """
        from lollypop.pop_radio import RadioPopover
        popover = RadioPopover(None, self.__radios)
        popover.set_relative_to(widget)
        popover.popup()

    def _on_search_clicked(self, widget):
        """
            Show popover for searching radios
            @param widget as Gtk.Widget
        """
        self.__pop_tunein.populate()
        self.__pop_tunein.show()

    def _on_artwork_changed(self, artwork, name):
        """
            Update children artwork if matching name
            @param artwork as Artwork
            @param name as str
        """
        for child in self._box.get_children():
            if name == child.name:
                child.set_artwork()

    def _on_map(self, widget):
        """
            Set active ids
        """
        self.__signal_id = self.__radios.connect("radio-changed",
                                                 self.__on_radio_changed)
        App().settings.set_value("state-one-ids",
                                 GLib.Variant("ai", [Type.RADIOS]))
        App().settings.set_value("state-two-ids",
                                 GLib.Variant("ai", []))

    def _on_unmap(self, widget):
        """
            Destroy popover
            @param widget as Gtk.Widget
        """
        if self.__signal_id is not None:
            self.__radios.disconnect(self.__signal_id)
            self.__signal_id = None
        self.__pop_tunein.destroy()

#######################
# PRIVATE             #
#######################
    def __add_radio(self, radio_id):
        """
            Add radio
            @param radio_id as int
        """
        widget = RadioWidget(radio_id, self.__radios)
        self._box.insert(widget, 0)
        widget.populate()
        widget.show()

    def __on_radio_changed(self, radios, radio_id):
        """
            Update view based on radio_id status
            @param radios as Radios
            @param radio_id as int
        """
        exists = radios.exists(radio_id)
        if exists:
            item = None
            for child in self._box.get_children():
                if child.id == radio_id:
                    item = child
                    break
            if item is None:
                self.__add_radio(radio_id)
            else:
                name = self.__radios.get_name(radio_id)
                item.rename(name)
        else:
            for child in self._box.get_children():
                if child.id == radio_id:
                    child.destroy()
