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

from gi.repository import Gtk, GLib, GdkPixbuf

import urllib.request
from _thread import start_new_thread

from lollypop.tunein import TuneIn
from lollypop.define import Lp
from lollypop.albumart import AlbumArt
from lollypop.view_container import ViewContainer


# Tunein popup
class PopTuneIn(Gtk.Popover):

    """
        Init Popover
        @param radio manager as RadioManager
    """
    def __init__(self, radio_manager):
        Gtk.Popover.__init__(self)
        self._tunein = TuneIn()
        self._radio_manager = radio_manager
        self._current_url = None
        self._previous_urls = []

        self._stack = ViewContainer(1000)
        self._stack.show()

        builder = Gtk.Builder()
        builder.add_from_resource(
                    '/org/gnome/Lollypop/PopTuneIn.ui')
        builder.connect_signals(self)

        self._view = Gtk.FlowBox()
        self._view.set_selection_mode(Gtk.SelectionMode.NONE)
        self._view.set_max_children_per_line(100)
        self._view.set_property('row-spacing', 10)
        self._view.set_property('expand', True)
        #self._view.connect('child-activated', self._on_radio_activate)
        self._view.show()

        builder.get_object('viewport').add(self._view)

        self._widget = builder.get_object('widget')
        self._spinner = builder.get_object('spinner')
        self._not_found = builder.get_object('notfound')
        self._stack.add(self._spinner)
        self._stack.add(self._not_found)
        self._stack.add(self._widget)
        self._stack.set_visible_child(self._spinner)
        self.add(self._stack)

    """
        Populate views
        @param url as string
    """
    def populate(self, url=None):
        self._current_url = url
        start_new_thread(self._populate, (url,))

    """
        Resize popover and set signals callback
    """
    def do_show(self):
        size_setting = Lp.settings.get_value('window-size')
        if isinstance(size_setting[1], int):
            self.set_size_request(700, size_setting[1]*0.7)
        else:
            self.set_size_request(700, 400)
        Gtk.Popover.do_show(self)

#######################
# PRIVATE             #
#######################
    """
        Show not found message
    """
    def _show_not_found(self):
        self._stack.set_visible_child(self._not_found)

    """
        Same as populate()
        @param url as string
        @thread safe
    """
    def _populate(self, url):
        if url is None:
            items = self._tunein.get_items()
        else:
            items = self._tunein.get_items(url)

        if items:
            self._add_items(items)
        else:
            GLib.idle_add(self._show_not_found)

    """
        Add items to headers
        @param items as [TuneItem]
        @thread safe
    """
    def _add_items(self, items):
        for item in items:
            GLib.idle_add(self._add_item, item)

    """
        Add item to the headers
        @param item as TuneItem
    """
    def _add_item(self, item):
        child = Gtk.LinkButton.new_with_label(item.URL, item.TEXT)
        child.connect('activate-link',
                      self._on_activate_link,
                      item)
        child.show()                
        self._view.add(child)
        # Remove spinner if exist
        if self._spinner == self._stack.get_visible_child():
            self._stack.set_visible_child(self._widget)

    """
        Clear view
    """
    def _clear(self):
        for child in self._view.get_children():
            self._view.remove(child)
            child.destroy()

    """
        Add selected radio
        @param item as TuneIn Item
    """
    def _add_radio(self, item):
        # Get cover art
        try:
            cache = AlbumArt._RADIOS_PATH
            response = urllib.request.urlretrieve(item.LOGO,
                                                  cache+"/%s.png" % item.TEXT)
        except Exception as e:
            print("PopTuneIn::_add_radio: %s" %e)
        url = item.URL
        # Tune in embbed uri in ashx files, so get content if possible
        try:
            response = urllib.request.urlopen(url)
            url = response.read().decode('utf-8')
        except Exception as e:
            print("PopTuneIn::_add_radio: %s" %e)
        self._radio_manager.add(item.TEXT)
        self._radio_manager.add_track(item.TEXT,
                                      url)
        GLib.idle_add(self.destroy)

    """
        Go to previous URL
        @param btn as Gtk.Button
    """
    def _on_back_btn_clicked(self, btn):
        url = None
        if self._previous_urls:
            self._stack.set_visible_child(self._spinner)
            url = self._previous_urls.pop()

        self._clear()
        start_new_thread(self.populate, (url,))

    """
        Update header with new link
        @param link as Gtk.LinkButton
        @param item as TuneIn Item
    """
    def _on_activate_link(self, link, item):
        if item.TYPE == "link":
            self._stack.set_visible_child(self._spinner)
            self._clear()
            if self._current_url is not None:
                self._previous_urls.append(self._current_url)
            start_new_thread(self.populate, (item.URL,))
        elif item.TYPE == "audio":
            start_new_thread(self._add_radio, (item,))
            self.hide()
        return True

