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

from gi.repository import Gtk, GLib

import os

from gettext import gettext as _

from lollypop.objects import Track
from lollypop.widgets_rating import RatingWidget
from lollypop.define import Lp
from lollypop.art import Art


# Show a popover with radio logos from the web
class RadioPopover(Gtk.Popover):
    """
        Popover with radio logos from the web
        @Warning: destroy it self on close
    """

    def __init__(self, name, radios_manager):
        """
            Init Popover
            @param name as string
            @param radios_manager as RadiosManager
        """
        Gtk.Popover.__init__(self)
        self.connect('map', self._on_map)
        self.connect('unmap', self._on_unmap)
        self._name = name
        self._radios_manager = radios_manager
        self._start = 0
        self._orig_pixbufs = {}

        self._stack = Gtk.Stack()
        self._stack.set_transition_duration(1000)
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._stack.show()

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/RadioPopover.ui')
        builder.connect_signals(self)

        self._name_entry = builder.get_object('name')
        self._uri_entry = builder.get_object('uri')
        self._btn_add_modify = builder.get_object('btn_add_modify')
        self._stack.add_named(builder.get_object('widget'), 'widget')
        self._stack.set_visible_child_name('widget')
        self.add(self._stack)

        track = Track()
        track.set_radio(name, '')
        rating = RatingWidget(track)
        rating.show()
        builder.get_object('widget').attach(rating, 0, 2, 2, 1)

        if self._name == '':
            builder.get_object('btn_add_modify').set_label(_("Add"))
        else:
            builder.get_object('btn_add_modify').set_label(_("Modify"))
            builder.get_object('btn_delete').show()
            self._name_entry.set_text(self._name)
            url = self._radios_manager.get_url(self._name)
            if url:
                self._uri_entry.set_text(url)

#######################
# PRIVATE             #
#######################
    def _on_map(self, widget):
        """
            Grab focus/Disable global shortcuts
            @param widget as Gtk.Widget
        """
        self._name_entry.grab_focus()
        Lp().window.enable_global_shorcuts(False)

    def _on_unmap(self, widget):
        """
            Enable global shortcuts, destroy
            @param widget as Gtk.Widget
        """
        self._thread = False
        Lp().window.enable_global_shorcuts(True)
        GLib.idle_add(self.destroy)

    def _on_btn_add_modify_clicked(self, widget):
        """
            Add/Modify a radio
            @param widget as Gtk.Widget
        """
        uri = self._uri_entry.get_text()
        new_name = self._name_entry.get_text()
        rename = self._name != '' and self._name != new_name

        if uri != '' and new_name != '':
            self._stack.get_visible_child().hide()
            if rename:
                self._radios_manager.rename(self._name, new_name)
                Lp().art.rename_radio(self._name, new_name)
            else:
                self._radios_manager.add(new_name, uri.lstrip().rstrip())
            self._name = new_name
        self.hide()

    def _on_btn_delete_clicked(self, widget):
        """
            Delete a radio
            @param widget as Gtk.Widget
        """
        self.hide()
        if self._name != '':
            cache = Art._RADIOS_PATH
            self._radios_manager.delete(self._name)
            Lp().art.clean_radio_cache(self._name)
            if os.path.exists(cache+"/%s.png" % self._name):
                os.remove(cache+"/%s.png" % self._name)

    def _on_entry_changed(self, entry):
        """
            Update modify/add button
            @param entry as Gtk.Entry
        """
        uri = self._uri_entry.get_text()
        name = self._name_entry.get_text()
        if name != '' and uri.find('://') != -1:
            self._btn_add_modify.set_sensitive(True)
        else:
            self._btn_add_modify.set_sensitive(False)
