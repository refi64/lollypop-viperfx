# Copyright (c) 2014-2017 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gettext import gettext as _

from lollypop.cache import InfoCache
from lollypop.define import Lp, ArtSize, Type
from lollypop.utils import get_network_available
from lollypop.helper_task import TaskHelper


class ArtworkSearch(Gtk.Bin):
    """
        Search for artwork
    """

    # FIXME: Missing Gio.Cancellable()

    def __init__(self, artist_id, album):
        """
            Init search
            @param artist id as int/None
            @param album as Album/None
        """
        Gtk.Bin.__init__(self)
        self.connect("unmap", self.__on_self_unmap)
        self.__timeout_id = None
        self.__album = album
        self.__artist_id = artist_id
        self.__cancellable = Gio.Cancellable()
        is_compilation = album is not None and\
            album.artist_ids and\
            album.artist_ids[0] == Type.COMPILATIONS
        if is_compilation:
            self.__artist = ""
        else:
            self.__artist = Lp().artists.get_name(artist_id)
        self.__contents = {}
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/ArtworkSearch.ui")
        builder.connect_signals(self)
        self._infobar = builder.get_object("infobar")
        self._infobar_label = builder.get_object("infobarlabel")
        widget = builder.get_object("widget")
        self._stack = builder.get_object("stack")
        self._entry = builder.get_object("entry")
        self._api_entry = builder.get_object("api_entry")

        self._view = Gtk.FlowBox()
        self._view.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._view.connect("child-activated", self.__on_activate)
        self._view.set_max_children_per_line(100)
        self._view.set_property("row-spacing", 10)
        self._view.show()

        self._popover = builder.get_object("popover")

        self._label = builder.get_object("label")
        self._label.set_text(_("Select artwork"))

        builder.get_object("viewport").add(self._view)

        self._spinner = builder.get_object("spinner")
        self._stack.add_named(builder.get_object("scrolled"), "main")
        self._stack.set_visible_child_name("main")
        self.add(widget)
        key = Lp().settings.get_value("cs-api-key").get_string() or\
            Lp().settings.get_default_value("cs-api-key").get_string()
        self._api_entry.set_text(key)
        self.set_size_request(700, 400)

    def populate(self):
        """
            Populate view
        """
        image = Gtk.Image()
        surface = Lp().art.get_default_icon("edit-clear-all-symbolic",
                                            ArtSize.BIG,
                                            self.get_scale_factor())
        image.set_from_surface(surface)
        image.set_property("valign", Gtk.Align.CENTER)
        image.set_property("halign", Gtk.Align.CENTER)
        image.get_style_context().add_class("cover-frame")
        image.show()
        self._view.add(image)

        # First load local files
        if self.__album is not None:
            uris = Lp().art.get_album_artworks(self.__album)
            for uri in uris:
                try:
                    f = Gio.File.new_for_uri(uri)
                    (status, content, tag) = f.load_contents()
                    self.__add_pixbuf(uri, status, content, print)
                except Exception as e:
                    print("ArtworkSearch::populate()", e)
        # Then google
        uri = Lp().art.get_google_search_uri(self.__get_current_search())
        helper = TaskHelper()
        helper.load_uri_content(uri,
                                self.__cancellable,
                                self.__on_google_content_loaded)

    def stop(self):
        """
            Stop loading
        """
        self.__cancellable.cancel()

#######################
# PROTECTED           #
#######################
    def _on_search_changed(self, entry):
        """
            Launch search based on current text
            @param entry as Gtk.Entry
        """
        if self.__timeout_id is not None:
            GLib.source_remove(self.__timeout_id)
        self.__timeout_id = GLib.timeout_add(1000,
                                             self.__on_search_timeout,
                                             entry.get_text())

    def _on_button_clicked(self, button):
        """
            Show file chooser
            @param button as Gtk.button
        """
        dialog = Gtk.FileChooserDialog()
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        dialog.add_buttons(Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        dialog.set_transient_for(Lp().window)
        self.__close_popover()
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            try:
                f = Gio.File.new_for_path(dialog.get_filename())
                (status, data, tag) = f.load_contents()
                if not status:
                    raise
                if self.__album is not None:
                    Lp().art.save_album_artwork(data, self.__album.id)
                else:
                    for suffix in ["lastfm", "wikipedia", "spotify"]:
                        InfoCache.uncache_artwork(self.__artist, suffix,
                                                  button.get_scale_factor())
                        InfoCache.add(self.__artist, None, data, suffix)
                    Lp().art.emit("artist-artwork-changed", self.__artist)
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
        if self.__album is not None:
            Lp().art.remove_album_artwork(self.__album)
            Lp().art.clean_album_cache(self.__album)
            Lp().art.emit("album-artwork-changed", self.__album.id)
        else:
            for suffix in ["lastfm", "wikipedia", "spotify", "deezer"]:
                InfoCache.uncache_artwork(self.__artist, suffix,
                                          button.get_scale_factor())
                InfoCache.add(self.__artist, None, None, suffix)
                Lp().art.emit("artist-artwork-changed", self.__artist)
        self.__close_popover()

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
                            Lp().settings.get_value("cs-api-key").get_string())

    def _on_api_entry_changed(self, entry):
        """
            Save key
            @param entry as Gtk.Entry
        """
        value = entry.get_text().strip()
        Lp().settings.set_value("cs-api-key", GLib.Variant("s", value))

#######################
# PRIVATE             #
#######################
    def __get_current_search(self):
        """
            Return current searches
            @return str
        """
        if self._entry.get_text() != "":
            search = self._entry.get_text()
        elif self.__album is not None:
            search = "%s+%s" % (self.__artist, self.__album.name)
        elif self.__artist_id is not None:
            search = self.__artist
        return search

    def __populate(self, uris):
        """
            Add uris to view
            @param uris as [str]
        """
        if self.__cancellable.is_cancelled():
            return
        helper = TaskHelper()
        # Fallback to link extraction
        if uris is None:
            self._label.set_text(_("Low quality, missing API key…"))
            uri = "https://www.google.fr/search?q=%s&tbm=isch" %\
                GLib.uri_escape_string(self.__get_current_search(), None, True)
            helper.load_uri_content(uri,
                                    self.__cancellable,
                                    self.__extract_links)
        # Populate the view
        elif uris:
            uri = uris.pop(0)
            helper.load_uri_content(uri,
                                    self.__cancellable,
                                    self.__add_pixbuf,
                                    self.__populate,
                                    uris)
        # Nothing to load, stop
        else:
            self._spinner.stop()

    def __add_pixbuf(self, uri, loaded, content, callback, *args):
        """
            Add uri to the view and load callback
            @param uri as str
            @param loaded as bool
            @param content as bytes
            @param callback as function
        """
        if self.__cancellable.is_cancelled():
            return
        try:
            if loaded:
                bytes = GLib.Bytes(content)
                stream = Gio.MemoryInputStream.new_from_bytes(bytes)
                bytes.unref()
                if stream is not None:
                    big = GdkPixbuf.Pixbuf.new_from_stream_at_scale(
                        stream, ArtSize.BIG,
                        ArtSize.BIG,
                        True,
                        None)
                    stream.close()
                image = Gtk.Image()
                image.get_style_context().add_class("cover-frame")
                image.set_property("halign", Gtk.Align.CENTER)
                image.set_property("valign", Gtk.Align.CENTER)
                self.__contents[image] = content
                surface = Gdk.cairo_surface_create_from_pixbuf(big,
                                                               0,
                                                               None)
                image.set_from_surface(surface)
                image.show()
                self._view.add(image)
        except Exception as e:
            print("ArtworkSearch::__add_pixbuf: %s" % e)
        callback(*args)

    def __extract_links(self, uri, loaded, content):
        """
            Extract links from content
            @param uri as str
            @param loaded as bool
            @param content as bytes
            @param callback as function
        """
        uris = []
        try:
            from bs4 import BeautifulSoup
            if loaded:
                html = content.decode("latin-1")
                soup = BeautifulSoup(html, "html.parser")
                for link in soup.findAll("img"):
                    try:
                        uris.append(link.attrs["src"])
                    except:
                        pass
        except Exception as e:
            print("ArtworkSearch::__extract_links: %s" % e)
        self.__populate(uris)

    def __close_popover(self):
        """
            Search for a popover in parents and close it
        """
        widget = self.get_parent()
        while widget is not None:
            if isinstance(widget, Gtk.Popover):
                widget.hide()
                break
            widget = widget.get_parent()

    def __on_self_unmap(self, widget):
        """
            Cancel loading
            @param widget as Gtk.Widget
        """
        self.__cancellable.cancel()

    def __on_google_content_loaded(self, uri, loaded, content):
        """
            Extract content
            @param uri as str
            @param loaded as bool
            @param content as bytes
        """
        if loaded:
            uris = Lp().art.get_google_artwork(content)
            self.__populate(uris)

    def __on_activate(self, flowbox, child):
        """
            Use pixbuf as cover
            Reset cache and use player object to announce cover change
        """
        try:
            data = self.__contents[child.get_child()]
            self.__close_popover()
            if self.__album is not None:
                Lp().art.save_album_artwork(data, self.__album.id)
            else:
                for suffix in ["lastfm", "wikipedia", "spotify"]:
                    InfoCache.uncache_artwork(self.__artist, suffix,
                                              flowbox.get_scale_factor())
                    InfoCache.add(self.__artist, None, data, suffix)
                Lp().art.emit("artist-artwork-changed", self.__artist)
            self._streams = {}
        except:
            self._infobar_label.set_text(_("Reset artwork?"))
            self._infobar.show()
            # GTK 3.20 https://bugzilla.gnome.org/show_bug.cgi?id=710888
            self._infobar.queue_resize()

    def __on_search_timeout(self, string):
        """
            Populate widget
            @param string as str
        """
        self.__cancellable.cancel()
        for child in self._view.get_children():
            child.destroy()
        self._spinner.start()
        self._spinner.show()
        self.__timeout_id = None
        self.__loading = True
        self.__cancellable.reset()
        if get_network_available():
            uri = Lp().art.get_google_search_uri(string)
            helper = TaskHelper()
            helper.load_uri_content(uri,
                                    self.__cancellable,
                                    self.__on_google_content_loaded)
