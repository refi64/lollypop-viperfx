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

from lollypop.define import Objects, ArtSize

# Show a popover with album covers from the web
class PopImages(Gtk.Popover):

    """
        Init Popover ui with a text entry and a scrolled treeview
    """
    def __init__(self, album_id):
        Gtk.Popover.__init__(self)
        self._album_id = album_id

        self._stack = Gtk.Stack()
        self._stack.set_property("expand", True)
        # Don't pass resize request to parent
        self._stack.set_resize_mode(Gtk.ResizeMode.QUEUE)
        self._stack.set_transition_duration(1000)
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._stack.show()

        builder = Gtk.Builder()
        builder.add_from_resource(
                    '/org/gnome/Lollypop/PopImages.ui')

        self._view = Gtk.FlowBox()
        self._view.set_selection_mode(Gtk.SelectionMode.NONE)
        self._view.connect("child-activated", self._on_activate)
        self._view.show()

        builder.get_object('viewport').add(self._view)

        self._widget = builder.get_object('widget')
        self._spinner = builder.get_object('spinner')
        self._stack.add(self._spinner)
        self._stack.add(self._widget)
        self._stack.set_visible_child(self._spinner)
        self.add(self._stack)

    """
        Populate view
        @param searched words as string
    """
    def populate(self, string):
        self._thread = True
        start_new_thread(self._populate, (string,))

    """
        Resize popover and set signals callback
    """
    def do_show(self):
        self.set_size_request(700, 400)
        Gtk.Popover.do_show(self)

    """
        Kill thread
    """
    def do_hide(self):
        self._thread = False
        Gtk.Popover.do_hide(self)

#######################
# PRIVATE             #
#######################
    """
        Same as populate()
    """
    def _populate(self, string):
        self._urls = Objects.art.get_google_arts(string)
        self._add_pixbufs()

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
        Add stream to the view
    """
    def _add_pixbuf(self, stream):
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(
                                            stream, ArtSize.MONSTER,
                                            ArtSize.MONSTER,
                                            False,
                                            None)
            image = Gtk.Image()
            image.set_from_pixbuf(pixbuf.scale_simple(ArtSize.BIG,
                                                      ArtSize.BIG,
                                                      2))
            image.show()
            self._view.add(image)
        except Exception as e:
            print(e)
            pass
        # Remove spinner if exist
        if self._spinner is not None:
            self._stack.set_visible_child(self._widget)
            GLib.timeout_add(1000, self._spinner.destroy)
            self._spinner = None

    """
        Use pixbuf as cover
        Reset cache and use player object to announce cover change
    """
    def _on_activate(self, flowbox, child):
        pixbuf = child.get_child().get_pixbuf()
        Objects.art.save_art(pixbuf, self._album_id)
        Objects.art.clean_cache(self._album_id)
        Objects.player.announce_cover_update(self._album_id)
        self.hide()
        self._streams = {}
