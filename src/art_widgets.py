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

from gi.repository import Gtk, Gdk, GLib, Gio, GdkPixbuf

from threading import Thread
from gettext import gettext as _

from lollypop.cache import InfoCache
from lollypop.define import Lp, ArtSize


class ArtworkSearch(Gtk.Bin):
    """
        Search for artwork
    """

    def __init__(self, artist_id, album):
        """
            Init search
            @param artist id as int/None
            @param album as Album/None
        """
        Gtk.Bin.__init__(self)
        self.connect('unmap', self._on_self_unmap)
        self._timeout_id = None
        self._loading = False
        self._album = album
        self._artist_id = artist_id
        self._artist = Lp().artists.get_name(artist_id)
        self._datas = {}
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/ArtworkSearch.ui')
        builder.connect_signals(self)
        self._infobar = builder.get_object('infobar')
        self._infobar_label = builder.get_object('infobarlabel')
        widget = builder.get_object('widget')
        self._stack = builder.get_object('stack')
        self._entry = builder.get_object('entry')
        self._api_entry = builder.get_object('api_entry')

        self._view = Gtk.FlowBox()
        self._view.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._view.connect('child-activated', self._on_activate)
        self._view.set_max_children_per_line(100)
        self._view.set_property('row-spacing', 10)
        self._view.show()

        self._popover = builder.get_object('popover')

        self._label = builder.get_object('label')
        self._label.set_text(_("Select artwork"))

        builder.get_object('viewport').add(self._view)

        self._spinner = builder.get_object('spinner')
        self._stack.add_named(builder.get_object('scrolled'), 'main')
        self._stack.set_visible_child_name('main')
        self.add(widget)
        self.set_size_request(700, 400)

    def populate(self):
        """
            Populate view
        """
        image = Gtk.Image()
        surface = Lp().art.get_default_icon('edit-clear-all-symbolic',
                                            ArtSize.BIG,
                                            self.get_scale_factor())
        image.set_from_surface(surface)
        image.set_property('valign', Gtk.Align.CENTER)
        image.set_property('halign', Gtk.Align.CENTER)
        image.get_style_context().add_class('cover-frame')
        image.show()
        self._view.add(image)

        # First load local files
        if self._album is not None:
            paths = Lp().art.get_album_artworks(self._album)
            for path in paths:
                try:
                    f = Gio.File.new_for_path(path)
                    (status, data, tag) = f.load_contents()
                    self._add_pixbuf(data)
                except Exception as e:
                    print("ArtworkSearch::populate()", e)
        # Then duckduckgo
        self._loading = True
        t = Thread(target=self._populate)
        t.daemon = True
        t.start()

    def stop(self):
        """
            Stop loading
        """
        self._loading = False

#######################
# PRIVATE             #
#######################
    def _populate(self, search=""):
        """
            Same as populate
            @param search as str
            @thread safe
        """
        urls = []
        if Gio.NetworkMonitor.get_default().get_network_available():
            if search != "":
                urls = Lp().art.get_google_arts(search)
            elif self._album is not None:
                urls = Lp().art.get_google_arts("%s+%s" % (
                                               self._artist,
                                               self._album.name))
            elif self._artist_id is not None:
                for album_id in Lp().artists.get_albums([self._artist_id]):
                    for genre_id in Lp().albums.get_genre_ids(album_id):
                        genre = Lp().genres.get_name(genre_id)
                        urls += Lp().art.get_google_arts("%s+%s" % (
                                                                  self._artist,
                                                                  genre))
                urls += Lp().art.get_google_arts(self._artist)
        if urls:
            self._add_pixbufs(urls, search)
        else:
            GLib.idle_add(self._show_not_found)

    def _add_pixbufs(self, urls, search):
        """
            Add urls to the view
            @param urls as [string]
            @param search as str
            @param duck api start as int
        """
        if search != self._entry.get_text():
            return
        if urls and self._loading:
            url = urls.pop(0)
            try:
                f = Gio.File.new_for_uri(url)
                (status, data, tag) = f.load_contents()
                if status:
                    GLib.idle_add(self._add_pixbuf, data)
            except Exception as e:
                print("ArtworkSearch::_add_pixbufs: %s" % e)
            if self._loading:
                self._add_pixbufs(urls, search)
        else:
            self._spinner.stop()

    def _show_not_found(self):
        """
            Show not found message
        """
        self._popover.show()
        self._api_entry.set_text(
                            Lp().settings.get_value('cs-api-key').get_string())
        self._spinner.stop()

    def _add_pixbuf(self, data):
        """
            Add pixbuf to the view
            @param data as bytes
        """
        try:
            stream = Gio.MemoryInputStream.new_from_data(data, None)
            if stream is not None:
                monster = GdkPixbuf.Pixbuf.new_from_stream_at_scale(
                    stream, ArtSize.MONSTER,
                    ArtSize.MONSTER,
                    True,
                    None)
            stream = Gio.MemoryInputStream.new_from_data(data, None)
            if stream is not None:
                big = GdkPixbuf.Pixbuf.new_from_stream_at_scale(
                    stream, ArtSize.BIG,
                    ArtSize.BIG,
                    True,
                    None)
            image = Gtk.Image()
            image.get_style_context().add_class('cover-frame')
            image.set_property('halign', Gtk.Align.CENTER)
            image.set_property('valign', Gtk.Align.CENTER)
            self._datas[image] = data
            surface = Gdk.cairo_surface_create_from_pixbuf(big,
                                                           0,
                                                           None)
            del monster
            del big
            image.set_from_surface(surface)
            del surface
            image.show()
            self._view.add(image)
        except Exception as e:
            print("ArtworkSearch::_add_pixbuf: %s" % e)

    def _close_popover(self):
        """
            Search for a popover in parents and close it
        """
        widget = self.get_parent()
        while widget is not None:
            if isinstance(widget, Gtk.Popover):
                widget.hide()
                break
            widget = widget.get_parent()

    def _on_self_unmap(self, widget):
        """
            Kill thread
            @param widget as Gtk.Widget
        """
        self.stop()

    def _on_activate(self, flowbox, child):
        """
            Use pixbuf as cover
            Reset cache and use player object to announce cover change
        """
        try:
            data = self._datas[child.get_child()]
            self._close_popover()
            if self._album is not None:
                Lp().art.save_album_artwork(data, self._album.id)
            else:
                for suffix in ["lastfm", "wikipedia", "spotify"]:
                    InfoCache.uncache_artwork(self._artist, suffix,
                                              flowbox.get_scale_factor())
                    InfoCache.cache(self._artist, None, data, suffix)
                Lp().art.emit('artist-artwork-changed', self._artist)
            self._streams = {}
        except:
            self._infobar_label.set_text(_("Reset artwork?"))
            self._infobar.show()
            # GTK 3.20 https://bugzilla.gnome.org/show_bug.cgi?id=710888
            self._infobar.queue_resize()

    def _on_search_changed(self, entry):
        """
            Launch search based on current text
            @param entry as Gtk.Entry
        """
        if self._timeout_id is not None:
            GLib.source_remove(self._timeout_id)
        self._timeout_id = GLib.timeout_add(1000,
                                            self._on_search_timeout,
                                            entry.get_text())

    def _on_search_timeout(self, string):
        """
            Populate widget
            @param string as str
        """
        for child in self._view.get_children():
            child.destroy()
        self._spinner.start()
        self._spinner.show()
        self._timeout_id = None
        self._loading = True
        t = Thread(target=self._populate, args=(string,))
        t.daemon = True
        t.start()

    def _on_button_clicked(self, button):
        """
            Show file chooser
            @param button as Gtk.button
        """
        dialog = Gtk.FileChooserDialog()
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        dialog.add_buttons(Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        dialog.set_transient_for(Lp().window)
        self._close_popover()
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            try:
                f = Gio.File.new_for_path(dialog.get_filename())
                (status, data, tag) = f.load_contents()
                if not status:
                    raise
                if self._album is not None:
                    Lp().art.save_album_artwork(data, self._album.id)
                else:
                    for suffix in ["lastfm", "wikipedia", "spotify"]:
                        InfoCache.uncache_artwork(self._artist, suffix,
                                                  button.get_scale_factor())
                        InfoCache.cache(self._artist, None, data, suffix)
                    Lp().art.emit('artist-artwork-changed', self._artist)
                self._streams = {}
            except Exception as e:
                print("ArtworkSearch::_on_button_clicked():", e)
        dialog.destroy()

    def _on_reset_confirm(self, button):
        """
            Reset cover
            @param button as Gtk.Button
        """
        self._infobar.hide()
        if self._album is not None:
            Lp().art.remove_album_artwork(self._album)
            Lp().art.clean_album_cache(self._album)
            Lp().art.emit('album-artwork-changed', self._album.id)
        else:
            for suffix in ["lastfm", "wikipedia", "spotify"]:
                InfoCache.uncache_artwork(self._artist, suffix,
                                          button.get_scale_factor())
                InfoCache.cache(self._artist, None, None, suffix)
                Lp().art.emit('artist-artwork-changed', self._artist)
        self._close_popover()

    def _on_info_response(self, infobar, response_id):
        """
            Hide infobar
            @param widget as Gtk.Infobar
            @param reponse id as int
        """
        if response_id == Gtk.ResponseType.CLOSE:
            self._infobar.hide()
            self._view.unselect_all()

    def _on_settings_button_clicked(self, button):
        """
            Show popover
            @param button as Gtk.Button
        """
        self._popover.show()
        self._api_entry.set_text(
                            Lp().settings.get_value('cs-api-key').get_string())

    def _on_api_entry_changed(self, entry):
        """
            Save key
            @param entry as Gtk.Entry
        """
        Lp().settings.set_value('cs-api-key',
                                GLib.Variant('s', entry.get_text()))
