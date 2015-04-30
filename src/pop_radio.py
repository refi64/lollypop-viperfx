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

from gi.repository import Gtk, GLib, Gio, GdkPixbuf

import urllib.request
import urllib.parse
from _thread import start_new_thread

from gettext import gettext as _

from lollypop.playlists import RadiosManager
from lollypop.define import Objects, ArtSize
from lollypop.view_container import ViewContainer

# Show a popover with radio logos from the web
class PopRadio(Gtk.Popover):
    """
        Init Popover ui with a text entry and a scrolled treeview
        @param name as string
        @param radios_manager as RadiosManager
    """
    def __init__(self, name, radios_manager):
        Gtk.Popover.__init__(self)
        self._name = name
        self._radios_manager = radios_manager

        self._stack = ViewContainer(1000)
        self._stack.show()

        builder = Gtk.Builder()
        builder.add_from_resource(
                    '/org/gnome/Lollypop/PopRadio.ui')
        builder.connect_signals(self)

        self._view = Gtk.FlowBox()
        self._view.set_selection_mode(Gtk.SelectionMode.NONE)
        self._view.connect('child-activated', self._on_activate)
        self._view.set_property('row-spacing', 10)
        self._view.show()

        builder.get_object('viewport').add(self._view)

        self._widget = builder.get_object('widget')
        self._logo = builder.get_object('logo')
        self._spinner = builder.get_object('spinner')
        self._not_found = builder.get_object('notfound')        
        self._name_entry = builder.get_object('name')
        self._uri_entry = builder.get_object('uri')
        self._stack.add(self._spinner)
        self._stack.add(self._not_found)
        self._stack.add(self._logo)
        self._stack.add(self._widget)
        self._stack.set_visible_child(self._widget)
        self.add(self._stack)

        if self._name == '':
            builder.get_object('btn').set_label(_("Add"))
        else:
            builder.get_object('btn').set_label(_("Modify"))
            self._name_entry.set_text(self._name)
            uris = self._radios_manager.get_tracks(self._name)
            if len(uris) > 0:
                self._uri_entry.set_text(uris[0])
            
    """
        Resize popover and set signals callback
    """
    def do_show(self):
        Gtk.Popover.do_show(self)
        self._name_entry.grab_focus()
        Objects.window.enable_global_shorcuts(False)
    """
        Kill thread
    """
    def do_hide(self):
        self._thread = False
        Gtk.Popover.do_hide(self)
        Objects.window.enable_global_shorcuts(True)

#######################
# PRIVATE             #
#######################
    """
        Populate view
    """
    def _populate_threaded(self):
        self._thread = True
        start_new_thread(self._populate, ())

    """
        Same as _populate_threaded()
        @thread safe
    """
    def _populate(self):
        self._urls = Objects.art.get_google_arts(self._name+"+logo")
        if self._urls:
            self._add_pixbufs()
        else:
            GLib.idle_add(self._show_not_found)

    """
        Add urls to the view
    """
    def _add_pixbufs(self):
        if self._urls:
            url = self._urls.pop()
            stream = None
            try:
                response = urllib.request.urlopen(url)
                stream = Gio.MemoryInputStream.new_from_data(
                                                response.read(), None)
            except:
                if self._thread:
                    self._add_pixbufs()
            if stream:
                GLib.idle_add(self._add_pixbuf, stream)
            if self._thread:
                self._add_pixbufs()

    """
        Show not found message
    """
    def _show_not_found(self):
        self._stack.set_visible_child(self._not_found)
        self._stack.clean_old_views(self._not_found)

    """
        Add stream to the view
    """
    def _add_pixbuf(self, stream):
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(
                                            stream, ArtSize.BIG,
                                            ArtSize.BIG,
                                            True,
                                            None)
            image = Gtk.Image()
            image.set_from_pixbuf(pixbuf)
            image.show()
            self._view.add(image)
        except Exception as e:
            print(e)
            pass
        # Remove spinner if exist
        if self._spinner is not None:
            self._stack.set_visible_child(self._logo)
            self._stack.clean_old_views(self._logo)
            self._spinner = None

    """
        Add/Modify a radio
        @param widget as Gtk.Widget
    """
    def _on_btn_clicked(self, widget):
        uri = self._uri_entry.get_text()
        new_name = self._name_entry.get_text()
        rename = self._name != '' and self._name != new_name

        if uri != '' and new_name != '':
            if rename:
                self._radios_manager.rename(new_name, self._name)
            else:
                self._radios_manager.add(new_name)
            self._radios_manager.add_track(new_name, uri)
            self._stack.remove(self._widget)
            self._stack.set_visible_child(self._spinner)
            self._name = new_name
            self._populate_threaded()
            self.set_size_request(700, 400)

    """
        Use pixbuf as cover
        Reset cache and use player object to announce cover change
    """
    def _on_activate(self, flowbox, child):
        pixbuf = child.get_child().get_pixbuf()
        Objects.art.save_radio_logo(pixbuf, self._name)
        Objects.art.clean_radio_cache(self._name)
        Objects.player.announce_logo_update(self._name)
        self.hide()
        self._streams = {}
