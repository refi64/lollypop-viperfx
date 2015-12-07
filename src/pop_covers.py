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

from gi.repository import Gtk, Gdk, GLib, Gio, GdkPixbuf

from threading import Thread
from gettext import gettext as _

from lollypop.objects import Album
from lollypop.define import Lp, ArtSize


class CoversPopover(Gtk.Popover):
    """
        Popover with album covers from the web
        @Warning: Destroy it self on close
    """

    def __init__(self, artist_id, album_id):
        """
            Init Popover
            @param artist id as int
            @param album id as int
        """
        Gtk.Popover.__init__(self)
        self.connect('unmap', self._on_self_unmap)
        self._album = Album(album_id)
        self._orig_pixbufs = {}

        self._stack = Gtk.Stack()
        self._stack.show()

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/CoversPopover.ui')

        widget = builder.get_object('widget')
        widget.add(self._stack)

        self._view = Gtk.FlowBox()
        self._view.set_selection_mode(Gtk.SelectionMode.NONE)
        self._view.connect('child-activated', self._on_activate)
        self._view.set_max_children_per_line(100)
        self._view.set_property('row-spacing', 10)
        self._view.show()

        self._label = builder.get_object('label')
        self._label.set_text(_("Please wait..."))

        builder.get_object('viewport').add(self._view)

        self._stack.add_named(builder.get_object('spinner'), 'spinner')
        self._stack.add_named(builder.get_object('notfound'), 'notfound')
        self._stack.add_named(builder.get_object('scrolled'), 'main')
        self._stack.set_visible_child_name('spinner')
        self.add(widget)
        self.set_size_request(700, 400)

    def populate(self):
        """
            Populate view
        """
        # First load local files
        urls = Lp().art.get_album_artworks(self._album)
        for url in urls:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(url,
                                                            ArtSize.MONSTER,
                                                            ArtSize.MONSTER)
            self._add_pixbuf(pixbuf)
        if len(urls) > 0:
            self._stack.set_visible_child_name('main')
        # Then duckduckgo
        self._thread = True
        t = Thread(target=self._populate)
        t.daemon = True
        t.start()

#######################
# PRIVATE             #
#######################
    def _populate(self):
        """
            Same as populate
            @thread safe
        """
        urls = []
        if Gio.NetworkMonitor.get_default().get_network_available():
            urls = Lp().art.get_duck_arts("%s+%s" % (
                                                   self._album.artist_name,
                                                   self._album.name))
        if urls:
            self._add_pixbufs(urls)
        else:
            GLib.idle_add(self._show_not_found)

    def _add_pixbufs(self, urls):
        """
            Add urls to the view
            @parma urls as [string]
            @param duck api start as int
        """
        if urls:
            url = urls.pop(0)
            stream = None
            try:
                f = Gio.File.new_for_uri(url)
                (status, data, tag) = f.load_contents()
                if status:
                    stream = Gio.MemoryInputStream.new_from_data(data, None)
            except Exception as e:
                print("CoversPopover::_add_pixbufs: %s" % e)
            if stream is not None:
                GLib.idle_add(self._add_stream, stream)
            if self._thread:
                self._add_pixbufs(urls)

    def _show_not_found(self):
        """
            Show not found message
        """
        if len(self._view.get_children()) == 0:
            self._label.set_text(_("No cover found..."))
            self._stack.set_visible_child_name('notfound')

    def _add_stream(self, stream):
        """
            Add stream to the view
            @param stream as Gio.MemoryInputStream
        """
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(
                stream, ArtSize.MONSTER,
                ArtSize.MONSTER,
                False,
                None)
            self._add_pixbuf(pixbuf)
            self._label.set_text(_("Select a cover art for this album"))
            self._stack.set_visible_child_name('main')
        except Exception as e:
            print("CoversPopover::_add_stream: %s" % e)

    def _add_pixbuf(self, pixbuf):
        """
            Add pixbuf to the view
            @param pixbuf as Gdk.Pixbuf
        """
        image = Gtk.Image()
        self._orig_pixbufs[image] = pixbuf
        scaled_pixbuf = pixbuf.scale_simple(
            ArtSize.BIG*self.get_scale_factor(),
            ArtSize.BIG*self.get_scale_factor(),
            2)
        del pixbuf
        surface = Gdk.cairo_surface_create_from_pixbuf(scaled_pixbuf,
                                                       0,
                                                       None)
        del scaled_pixbuf
        image.set_from_surface(surface)
        del surface
        image.show()
        self._view.add(image)

    def _on_self_unmap(self, widget):
        """
            Kill thread
            @param widget as Gtk.Widget
        """
        self._thread = False
        GLib.idle_add(self.destroy)

    def _on_activate(self, flowbox, child):
        """
            Use pixbuf as cover
            Reset cache and use player object to announce cover change
        """
        pixbuf = self._orig_pixbufs[child.get_child()]
        Lp().art.save_album_artwork(pixbuf, self._album.id)
        Lp().art.clean_album_cache(self._album)
        Lp().art.album_artwork_update(self._album.id)
        self.hide()
        self._streams = {}
