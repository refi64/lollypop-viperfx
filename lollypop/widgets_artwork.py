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

from gi.repository import Gtk, GObject, Gdk, GLib, Gio, GdkPixbuf

from gettext import gettext as _
from urllib.parse import urlparse
from lollypop.widgets_utils import Popover

from lollypop.logger import Logger
try:
    import gi
    gi.require_version('WebKit2', '4.0')
    from gi.repository import WebKit2
    WEBKIT2 = True
except Exception as e:
    WEBKIT2 = False
    Logger.warning(e)

from lollypop.information_store import InformationStore
from lollypop.define import App, ArtSize, Type
from lollypop.utils import get_network_available
from lollypop.helper_task import TaskHelper


class ArtworkSearchWebView(Gtk.OffscreenWindow):
    """
        Search for image through Duckduckgo Image
    """

    __gsignals__ = {
        "populated": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self):
        """
            Init webview
        """
        Gtk.OffscreenWindow.__init__(self)
        self.__webview = WebKit2.WebView()
        self.__webview.show()
        self.add(self.__webview)
        self.__webview.connect("load-changed", self.__on_load_changed)
        self.__webview.connect("resource-load-started",
                               self.__on_resource_load_started)
        self.show()

    def search(self, terms):
        """
            Search for terms
            @param terms as str
        """
        uri = "https://duckduckgo.com/?q=%s&t=h_&iax=images&ia=images" %\
            GLib.uri_escape_string(terms, None, True)
        self.__webview.load_uri(uri)

    def do_get_preferred_size(self):
        requisition = Gtk.Requisiton()
        requisition.width = 300
        requisition.height = 300
        Gtk.Bin.do_get_preferred_size(requisition, requisition)

#######################
# PRIVATE             #
#######################
    def __on_load_changed(self, webview, event):
        """
            Stop spinner
            @param webview as WebView
            @param event as WebKit2.LoadEvent
        """
        if event == WebKit2.LoadEvent.FINISHED:
            self.emit("populated", None)

    def __on_resource_load_started(self, webview, resource, request):
        """
            Find opened google image
            @param webview as WebView
            @param resource as WebKit2.WebResource
            @param request as WebKit2.URIRequest
        """
        uri = resource.get_uri()
        parsed = urlparse(uri)
        if parsed.netloc == "proxy.duckduckgo.com":
            self.emit("populated", uri)


class ArtworkSearchWidget(Gtk.Bin):
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
        self.connect("unmap", self.__on_unmap)
        self.__timeout_id = None
        self.__web_search = None
        self.__album = album
        self.__artist_id = artist_id
        self.__uris = []
        self.__cancellable = Gio.Cancellable()
        is_compilation = album is not None and\
            album.artist_ids and\
            album.artist_ids[0] == Type.COMPILATIONS
        if is_compilation:
            self.__artist = ""
        else:
            self.__artist = App().artists.get_name(artist_id)
        self.__contents = {}
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/ArtworkSearch.ui")
        builder.connect_signals(self)
        self.__infobar = builder.get_object("infobar")
        self.__infobar_label = builder.get_object("infobarlabel")
        widget = builder.get_object("widget")
        self.__stack = builder.get_object("stack")
        self.__entry = builder.get_object("entry")
        self.__api_entry = builder.get_object("api_entry")
        self.__back_button = builder.get_object("back_button")

        self.__view = Gtk.FlowBox()
        self.__view.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.__view.connect("child-activated", self.__on_activate)
        self.__view.set_max_children_per_line(100)
        self.__view.set_property("row-spacing", 10)
        self.__view.show()

        self._popover = builder.get_object("popover")

        self.__label = builder.get_object("label")
        self.__label.set_text(_("Select artwork"))

        builder.get_object("viewport").add(self.__view)

        self.__spinner = builder.get_object("spinner")
        self.__stack.add_named(builder.get_object("scrolled"), "main")
        self.__stack.set_visible_child_name("main")
        self.add(widget)
        key = App().settings.get_value("cs-api-key").get_string() or\
            App().settings.get_default_value("cs-api-key").get_string()
        self.__api_entry.set_text(key)

    def populate(self):
        """
            Populate view
        """
        self.__uris = []
        image = Gtk.Image.new_from_icon_name("edit-clear-all-symbolic",
                                             Gtk.IconSize.DIALOG)
        image.set_property("valign", Gtk.Align.CENTER)
        image.set_property("halign", Gtk.Align.CENTER)
        context = image.get_style_context()
        context.add_class("cover-frame")
        padding = context.get_padding(Gtk.StateFlags.NORMAL)
        border = context.get_border(Gtk.StateFlags.NORMAL)
        image.set_size_request(ArtSize.BIG + padding.left +
                               padding.right + border.left + border.right,
                               ArtSize.BIG + padding.top +
                               padding.bottom + border.top + border.bottom)
        image.show()
        self.__view.add(image)

        # First load local files
        if self.__album is not None:
            self.__uris = App().art.get_album_artworks(self.__album)
        self.__search_for_artwork()

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
        dialog.set_transient_for(App().window)
        self.__close_popover()
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            try:
                f = Gio.File.new_for_path(dialog.get_filename())
                (status, data, tag) = f.load_contents()
                if not status:
                    raise
                if self.__album is not None:
                    App().art.save_album_artwork(data, self.__album.id)
                else:
                    InformationStore.uncache_artwork(self.__artist)
                    InformationStore.add_artist_artwork(self.__artist, data)
                    App().art.emit("artist-artwork-changed", self.__artist)
                self._streams = {}
            except Exception as e:
                Logger.error("ArtworkSearch::_on_button_clicked(): %s" % e)
        dialog.destroy()

    def _on_reset_confirm(self, button):
        """
            Reset cover
            @param button as Gtk.Button
        """
        self.__infobar.hide()
        if self.__album is not None:
            App().art.remove_album_artwork(self.__album)
            App().art.clean_album_cache(self.__album)
            App().art.emit("album-artwork-changed", self.__album.id)
        else:
            InformationStore.uncache_artwork(self.__artist)
            InformationStore.add_artist_artwork(self.__artist, None)
            App().art.emit("artist-artwork-changed", self.__artist)
        self.__close_popover()

    def _on_info_response(self, infobar, response_id):
        """
            Hide infobar
            @param widget as Gtk.Infobar
            @param reponse id as int
        """
        if response_id == Gtk.ResponseType.CLOSE:
            self.__infobar.hide()
            self.__view.unselect_all()

    def _on_settings_button_clicked(self, button):
        """
            Show popover
            @param button as Gtk.Button
        """
        self._popover.popup()
        self.__api_entry.set_text(
            App().settings.get_value("cs-api-key").get_string())

    def _on_api_entry_changed(self, entry):
        """
            Save key
            @param entry as Gtk.Entry
        """
        value = entry.get_text().strip()
        App().settings.set_value("cs-api-key", GLib.Variant("s", value))

    def _on_back_button_clicked(self, button):
        """
            Show web view
            @param button as Gtk.Button
        """
        if self.__stack.get_visible_child_name() == "web":
            self.__stack.set_visible_child_name("main")
        else:
            self.__stack.set_visible_child_name("web")
        self.__back_button.set_sensitive(False)

#######################
# PRIVATE             #
#######################
    def __get_current_search(self):
        """
            Return current searches
            @return str
        """
        if self.__entry.get_text() != "":
            search = self.__entry.get_text()
        elif self.__album is not None:
            search = "%s+%s" % (self.__artist, self.__album.name)
        elif self.__artist_id is not None:
            search = self.__artist
        return search

    def __search_for_artwork(self):
        """
            Search artwork on the web
            @param string as str
        """
        self.__cancellable = Gio.Cancellable()
        search = self.__get_current_search()
        if get_network_available("GOOGLE"):
            self.__spinner.start()
            uri = App().art.get_google_search_uri(search)
            helper = TaskHelper()
            helper.load_uri_content(uri,
                                    self.__cancellable,
                                    self.__on_google_content_loaded)
        elif get_network_available("DUCKDUCKGO") and WEBKIT2:
            self.__spinner.start()
            if self.__web_search is None:
                self.__web_search = ArtworkSearchWebView()
                self.__web_search.connect("populated",
                                          self.__on_web_search_populated)
            self.__web_search.search(search)
        else:
            self.__populate()
            self.__label.set_text(
                _("DuckDuckGo and Google turned off in the settings"))

    def __populate(self):
        """
            Add uris to view
        """
        if self.__cancellable.is_cancelled():
            return
        try:
            helper = TaskHelper()
            if self.__uris:
                uri = self.__uris.pop(0)
                if uri.startswith("file://"):
                    f = Gio.File.new_for_uri(uri)
                    (status, content, tag) = f.load_contents()
                    self.__add_pixbuf(uri, status,
                                      content, self.__populate)
                else:
                    helper.load_uri_content(uri,
                                            self.__cancellable,
                                            self.__add_pixbuf,
                                            self.__populate)
            else:
                self.__spinner.stop()
        except Exception as e:
            Logger.error("ArtworkSearch::__populate(): %s" % e)

    def __add_pixbuf(self, uri, loaded, content, callback, *args):
        """
            Add uri to the view and load callback
            @param uri as str
            @param loaded as bool
            @param content as bytes
            @param callback as function
        """
        try:
            if loaded:
                scale_factor = self.get_scale_factor()
                bytes = GLib.Bytes(content)
                stream = Gio.MemoryInputStream.new_from_bytes(bytes)
                if stream is not None:
                    big = GdkPixbuf.Pixbuf.new_from_stream_at_scale(
                        stream, ArtSize.BIG * scale_factor,
                        ArtSize.BIG * scale_factor,
                        True,
                        None)
                    stream.close()
                image = Gtk.Image()
                image.get_style_context().add_class("cover-frame")
                image.set_property("halign", Gtk.Align.CENTER)
                image.set_property("valign", Gtk.Align.CENTER)
                if not uri.startswith("file://"):
                    image.set_name("web")
                self.__contents[image] = content
                surface = Gdk.cairo_surface_create_from_pixbuf(
                                                       big,
                                                       scale_factor,
                                                       None)
                image.set_from_surface(surface)
                image.show()
                self.__view.add(image)
        except Exception as e:
            Logger.error("ArtworkSearch::__add_pixbuf: %s" % e)
        if not self.__cancellable.is_cancelled():
            callback(*args)

    def __close_popover(self):
        """
            Search for a popover in parents and close it
        """
        widget = self.get_parent()
        while widget is not None:
            if isinstance(widget, Popover):
                widget.hide()
                break
            widget = widget.get_parent()

    def __on_unmap(self, widget):
        """
            Cancel loading
            @param widget as Gtk.Widget
        """
        if self.__web_search is not None:
            self.__web_search.destroy()
        self.__cancellable.cancel()

    def __on_web_search_populated(self, web_search, uri):
        """
            Load available uri
            @param web_search as ArtworkSearchWebView
            @param uri as str
        """
        if uri is None:
            self.__populate()
        else:
            self.__uris.append(uri)

    def __on_google_content_loaded(self, uri, loaded, content):
        """
            Extract content
            @param uri as str
            @param loaded as bool
            @param content as bytes
        """
        if loaded:
            self.__uris += App().art.get_google_artwork(content)
        self.__populate()

    def __on_activate(self, flowbox, child):
        """
            Use pixbuf as cover
            Reset cache and use player object to announce cover change
        """
        try:
            data = self.__contents[child.get_child()]
            self.__close_popover()
            if self.__album is not None:
                App().art.save_album_artwork(data, self.__album.id)
            else:
                InformationStore.uncache_artwork(self.__artist)
                InformationStore.add_artist_artwork(self.__artist, data)
                App().art.emit("artist-artwork-changed", self.__artist)
            self._streams = {}
        except:
            self.__infobar_label.set_text(_("Reset artwork?"))
            self.__infobar.show()
            # GTK 3.20 https://bugzilla.gnome.org/show_bug.cgi?id=710888
            self.__infobar.queue_resize()

    def __on_search_timeout(self, string):
        """
            Populate widget
            @param string as str
        """
        self.__timeout_id = None
        self.__cancellable.cancel()
        for child in self.__view.get_children():
            image = child.get_child()
            if image.get_name() == "web":
                child.destroy()
        GLib.timeout_add(250, self.__search_for_artwork)
