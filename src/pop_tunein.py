# Copyright (c) 2014-2016 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import Gtk, GLib, Gio, GdkPixbuf, Gdk, Pango

from threading import Thread
from gettext import gettext as _
from cgi import escape

from lollypop.radios import Radios
from lollypop.tunein import TuneIn
from lollypop.define import Lp, ArtSize
from lollypop.art import Art


class TuneinPopover(Gtk.Popover):
    """
        Popover showing tunin radios
    """

    def __init__(self, radios_manager=None):
        """
            Init Popover
            @param radios_manager as Radios
        """
        Gtk.Popover.__init__(self)
        self._tunein = TuneIn()
        if radios_manager is not None:
            self._radios_manager = radios_manager
        else:
            self._radios_manager = Radios()
        self._current_url = None
        self._timeout_id = None
        self._previous_urls = []
        self._covers_to_download = []

        self._stack = Gtk.Stack()
        self._stack.set_property('expand', True)
        self._stack.show()

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/TuneinPopover.ui')
        builder.connect_signals(self)
        widget = builder.get_object('widget')
        widget.attach(self._stack, 0, 2, 5, 1)

        self._back_btn = builder.get_object('back_btn')
        self._home_btn = builder.get_object('home_btn')
        self._label = builder.get_object('label')

        self._view = Gtk.FlowBox()
        self._view.set_selection_mode(Gtk.SelectionMode.NONE)
        self._view.set_max_children_per_line(100)
        self._view.set_property('row-spacing', 10)
        self._view.set_property('expand', True)
        self._view.show()

        self._spinner = builder.get_object('spinner')

        builder.get_object('viewport').add(self._view)
        builder.get_object('viewport').set_property('margin', 10)

        self._scrolled = builder.get_object('scrolled')
        self._stack.add_named(self._spinner, 'spinner')
        self._stack.add_named(builder.get_object('notfound'), 'notfound')
        self._stack.add_named(self._scrolled, 'scrolled')
        self.add(widget)
        self.connect('map', self._on_map)
        self.connect('unmap', self._on_unmap)

    def populate(self, url=None):
        """
            Populate views
            @param url as string
        """
        if url is None and self._current_url is not None:
            return
        self._spinner.start()
        self._clear()
        self._stack.set_visible_child_name('spinner')
        self._current_url = url
        self._back_btn.set_sensitive(False)
        self._home_btn.set_sensitive(False)
        self._label.set_text(_("Please wait..."))
        t = Thread(target=self._populate, args=(url,))
        t.daemon = True
        t.start()

#######################
# PRIVATE             #
#######################
    def _show_not_found(self, message=""):
        """
            Show not found message
            @param message as str
        """
        # TODO Add a string
        self._label.set_text(message)
        self._stack.set_visible_child_name('notfound')
        self._home_btn.set_sensitive(True)

    def _populate(self, url):
        """
            Same as populate()
            @param url as string
            @thread safe
        """
        try:
            if url is None:
                items = self._tunein.get_items(
                                    "http://opml.radiotime.com/Browse.ashx?c=")
            else:
                items = self._tunein.get_items(url)

            if self._current_url == url:
                if items:
                    self._add_items(items, url)
                else:
                    GLib.idle_add(self._show_not_found)
        except:
            GLib.idle_add(self._show_not_found,
                          _("Can't connect to TuneIn..."))

    def _add_items(self, items, url):
        """
            Add current items
            @param items as [TuneItem]
            @parma url as str
            @thread safe
        """
        GLib.idle_add(self._add_item, items, url)

    def _add_item(self, items, url):
        """
            Add item
            @param items as [TuneItem]
            @param url as str
        """
        if url != self._current_url:
            return
        if not items:
            self._home_btn.set_sensitive(self._current_url is not None)
            t = Thread(target=self._download_images, args=(url,))
            t.daemon = True
            t.start()
            return
        item = items.pop(0)
        child = Gtk.Grid()
        child.set_column_spacing(5)
        child.set_property('halign', Gtk.Align.START)
        child.show()
        link = Gtk.LinkButton.new_with_label(item.URL, item.TEXT)
        # Hack
        link.get_children()[0].set_ellipsize(Pango.EllipsizeMode.END)
        link.connect('activate-link', self._on_activate_link, item)
        link.show()
        if item.TYPE == "audio":
            link.set_tooltip_text(_("Play"))
            button = Gtk.Button.new_from_icon_name('list-add-symbolic',
                                                   Gtk.IconSize.MENU)
            button.connect('clicked', self._on_button_clicked, item)
            button.set_relief(Gtk.ReliefStyle.NONE)
            button.set_property('valign', Gtk.Align.CENTER)
            button.set_tooltip_text(_("Add"))
            button.show()
            child.add(button)
            image = Gtk.Image.new()
            image.set_property('width-request', ArtSize.MEDIUM)
            image.set_property('height-request', ArtSize.MEDIUM)
            image.show()
            child.add(image)
            self._covers_to_download.append((item, image))
        else:
            link.set_tooltip_text('')
        child.add(link)

        self._view.add(child)

        # Remove spinner if exist
        if self._stack.get_visible_child_name() == 'spinner':
            self._stack.set_visible_child_name('scrolled')
            self._spinner.stop()
            self._label.set_text("")
            if self._current_url is not None:
                self._back_btn.set_sensitive(True)
        GLib.idle_add(self._add_items, items, url)

    def _download_images(self, url):
        """
            Download and set image for TuneItem
            @param url as str
            @thread safe
        """
        while self._covers_to_download and url == self._current_url:
            (item, image) = self._covers_to_download.pop(0)
            try:
                f = Gio.File.new_for_uri(item.LOGO)
                (status, data, tag) = f.load_contents()
                if status:
                    stream = Gio.MemoryInputStream.new_from_data(data, None)
                    if stream is not None:
                        GLib.idle_add(self._set_image, image, stream)
            except Exception as e:
                GLib.idle_add(image.set_from_icon_name,
                              "image-missing",
                              Gtk.IconSize.LARGE_TOOLBAR)
                print("TuneinPopover::_download_images: %s" % e)

    def _set_image(self, image, stream):
        """
            Set image with stream
            @param image as Gtk.Image
            @param stream as Gio.MemoryInputStream
        """
        pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(stream,
                                                           ArtSize.MEDIUM,
                                                           ArtSize.MEDIUM,
                                                           True,
                                                           None)
        surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf,
                                                       0,
                                                       None)
        del pixbuf
        image.set_from_surface(surface)
        del surface

    def _clear(self):
        """
            Clear view
        """
        for child in self._view.get_children():
            self._view.remove(child)
            child.destroy()

    def _add_radio(self, item):
        """
            Add selected radio
            @param item as TuneIn Item
        """
        # Get cover art
        try:
            cache = Art._RADIOS_PATH
            s = Gio.File.new_for_uri(item.LOGO)
            d = Gio.File.new_for_path(cache+"/%s.png" %
                                      item.TEXT.replace('/', '-'))
            s.copy(d, Gio.FileCopyFlags.OVERWRITE, None, None)
        except Exception as e:
            print("TuneinPopover::_add_radio: %s" % e)
        url = item.URL
        # Tune in embbed uri in ashx files, so get content if possible
        try:
            f = Gio.File.new_for_uri(url)
            (status, data, tag) = f.load_contents()
            if status:
                url = data.decode('utf-8').split('\n')[0]
        except Exception as e:
            print("TuneinPopover::_add_radio: %s" % e)
        self._radios_manager.add(item.TEXT.replace('/', '-'), url)

    def _on_map(self, widget):
        """
            Resize and disable global shortcuts
            @param widget as Gtk.Widget
        """
        # FIXME Not needed with GTK >= 3.18
        Lp().window.enable_global_shorcuts(False)
        size = Lp().window.get_size()
        self.set_size_request(size[0]*0.5, size[1]*0.7)

    def _on_unmap(self, widget):
        """
            Enable global shorcuts
            @param widget as Gtk.Widget
        """
        # FIXME Not needed with GTK >= 3.18
        Lp().window.enable_global_shorcuts(True)

    def _on_back_btn_clicked(self, btn):
        """
            Go to previous URL
            @param btn as Gtk.Button
        """
        url = None
        self._current_url = None
        if self._previous_urls:
            url = self._previous_urls.pop()
        self._stack.set_visible_child_name('spinner')
        self._spinner.start()
        self._clear()
        self.populate(url)

    def _on_home_btn_clicked(self, btn):
        """
            Go to root URL
            @param btn as Gtk.Button
        """
        self._current_url = None
        self._previous_urls = []
        self.populate()

    def _on_activate_link(self, link, item):
        """
            Update header with new link
            @param link as Gtk.LinkButton
            @param item as TuneIn Item
        """
        if item.TYPE == "link":
            self._scrolled.get_vadjustment().set_value(0.0)
            if self._current_url is not None:
                self._previous_urls.append(self._current_url)
            self.populate(item.URL)
        elif item.TYPE == "audio":
            # Only toolbar will get this one, so only create small in cache
            if Gio.NetworkMonitor.get_default().get_network_available():
                t = Thread(target=Lp().art.copy_uri_to_cache,
                           args=(item.LOGO, item.TEXT,
                                 Lp().window.toolbar.artsize))
                t.daemon = True
                t.start()
                t = Thread(target=Lp().art.copy_uri_to_cache,
                           args=(item.LOGO, item.TEXT,
                                 ArtSize.BIG))
                t.daemon = True
                t.start()
            Lp().player.load_external(item.URL, item.TEXT)
            Lp().player.play_this_external(item.URL)
        return True

    def _on_button_clicked(self, button, item):
        """
            Play the radio
            @param link as Gtk.Button
            @param item as TuneIn Item
        """
        self._timeout_id = None
        t = Thread(target=self._add_radio, args=(item,))
        t.daemon = True
        t.start()
        self.hide()

    def _on_search_changed(self, widget):
        """
            Timeout filtering, call _really_do_filterting()
            after timeout
            @param widget as Gtk.TextEntry
        """
        self._current_url = None
        if self._timeout_id is not None:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = None

        text = widget.get_text()
        if text != "":
            self._home_btn.set_sensitive(True)
            self._timeout_id = GLib.timeout_add(1000,
                                                self._on_search_timeout,
                                                text)
        else:
            self._home_btn.set_sensitive(False)
            self._timeout_id = GLib.timeout_add(1000,
                                                self._on_home_btn_clicked,
                                                None)

    def _on_search_timeout(self, string):
        """
            Populate widget
            @param string as str
        """
        self._timeout_id = None
        url = "http://opml.radiotime.com/Search.ashx?query=%s" % escape(string)
        self.populate(url)
