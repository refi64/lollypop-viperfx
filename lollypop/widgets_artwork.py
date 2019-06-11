# Copyright (c) 2014-2019 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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
from lollypop.widgets_utils import Popover

from lollypop.logger import Logger

from lollypop.define import App, ArtSize, Type, ArtBehaviour


class ArtworkSearchChild(Gtk.FlowBoxChild):
    """
        Child for ArtworkSearch
    """

    def __init__(self, api=None):
        """
            Init child
            @param api as str
        """
        Gtk.FlowBoxChild.__init__(self)
        self.__bytes = None
        self.__api = api
        self.__image = Gtk.Image()
        self.__image.show()
        self.__label = Gtk.Label()
        self.__label.show()
        grid = Gtk.Grid()
        grid.set_orientation(Gtk.Orientation.VERTICAL)
        grid.show()
        grid.add(self.__image)
        grid.add(self.__label)
        grid.set_row_spacing(5)
        self.__image.get_style_context().add_class("cover-frame")
        self.set_property("halign", Gtk.Align.CENTER)
        self.set_property("valign", Gtk.Align.CENTER)
        self.add(grid)

    def populate(self, bytes):
        """
            Populate images with bytes
            @param bytes as bytes
            @return bool if success
        """
        try:
            scale_factor = self.get_scale_factor()
            gbytes = GLib.Bytes(bytes)
            stream = Gio.MemoryInputStream.new_from_bytes(gbytes)
            if stream is not None:
                pixbuf = GdkPixbuf.Pixbuf.new_from_stream(stream, None)
                if self.__api is None:
                    text = "%sx%s" % (pixbuf.get_width(),
                                      pixbuf.get_height())
                else:
                    text = "%s: %sx%s" % (self.__api,
                                          pixbuf.get_width(),
                                          pixbuf.get_height())
                self.__label.set_text(text)
                pixbuf = App().art.load_behaviour(pixbuf,
                                                  None,
                                                  ArtSize.BIG,
                                                  ArtSize.BIG,
                                                  scale_factor,
                                                  ArtBehaviour.CROP)
                stream.close()
            self.__bytes = bytes
            surface = Gdk.cairo_surface_create_from_pixbuf(
                                                   pixbuf,
                                                   scale_factor,
                                                   None)
            self.__image.set_from_surface(surface)
            return True
        except Exception as e:
            Logger.error("ArtworkSearch::__get_image: %s" % e)
        return False

    @property
    def bytes(self):
        """
            Get bytes associated to widget
            @return bytes
        """
        return self.__bytes


class ArtworkSearchWidget(Gtk.Bin):
    """
        Search for artwork
    """

    def __init__(self, artist_id, album):
        """
            Init search
            @param artist_id as int/None
            @param album as Album/None
        """
        Gtk.Bin.__init__(self)
        self.connect("map", self.__on_map)
        self.connect("unmap", self.__on_unmap)
        self.__timeout_id = None
        self.__uri_artwork_id = None
        self.__album = album
        self.__artist_id = artist_id
        self.__uris = []
        self.__count = 0
        self.__cancellable = Gio.Cancellable()
        is_compilation = album is not None and\
            album.artist_ids and\
            album.artist_ids[0] == Type.COMPILATIONS
        if is_compilation:
            self.__artist = ""
        else:
            self.__artist = App().artists.get_name(artist_id)
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
        try:
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
            uris = []
            if self.__album is None:
                (exists, path) = App().art.artist_artwork_exists(self.__artist)
                if exists:
                    uris = [GLib.filename_to_uri(path)]
            else:
                uris = App().art.get_album_artworks(self.__album)
            # Direct load, not using loopback because not many items
            for uri in uris:
                child = ArtworkSearchChild(_("Local"))
                child.show()
                f = Gio.File.new_for_uri(uri)
                (status, content, tag) = f.load_contents()
                if status:
                    status = child.populate(content)
                if status:
                    self.__view.add(child)
            self.__search_for_artwork()
        except Exception as e:
            Logger.error("ArtworkWidget::populate(): %s", e)

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
                    App().art.save_album_artwork(data, self.__album)
                else:
                    App().art.uncache_artist_artwork(self.__artist)
                    App().art.add_artist_artwork(self.__artist, data)
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
            App().art.save_album_artwork(None, self.__album)
            App().art.clean_album_cache(self.__album)
            App().art.emit("album-artwork-changed", self.__album.id)
        else:
            App().art.uncache_artist_artwork(self.__artist)
            App().art.add_artist_artwork(self.__artist, None)
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

    def __search_from_downloader(self, search):
        """
            Load artwork from downloader
        """
        if self.__album is None:
            App().task_helper.run(
                App().art.search_artist_artwork,
                self.__artist,
                self.__cancellable)
        else:
            App().task_helper.run(
                App().art.search_album_artworks,
                self.__artist,
                self.__album.name,
                self.__cancellable)

    def __search_for_artwork(self):
        """
            Search artwork on the web
        """
        self.__uris = []
        self.__count = 0
        self.__cancellable = Gio.Cancellable()
        search = self.__get_current_search()
        self.__spinner.start()
        self.__search_from_downloader(search)
        App().task_helper.run(App().art.search_artwork_from_google,
                              search,
                              self.__cancellable)
        App().task_helper.run(App().art.search_artwork_from_startpage,
                              search,
                              self.__cancellable)

    def __add_pixbuf(self, content, api):
        """
            Add content to view
            @param content as bytes
            @param api as str
        """
        child = ArtworkSearchChild(api)
        child.show()
        status = child.populate(content)
        if status:
            child.set_name("web")
            self.__view.add(child)
        else:
            child.destroy()

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

    def __on_map(self, widget):
        """
            Cancel loading
            @param widget as Gtk.Widget
        """
        self.__uri_artwork_id = App().art.connect(
            "uri-artwork-found", self.__on_uri_artwork_found)

    def __on_unmap(self, widget):
        """
            Cancel loading and disconnect signals
            @param widget as Gtk.Widget
        """
        self.__cancellable.cancel()
        if self.__uri_artwork_id is not None:
            App().art.disconnect(self.__uri_artwork_id)
            self.__uri_artwork_id = None

    def __on_uri_artwork_found(self, art, uris):
        """
            Load content in view
            @param art as Art
            @param uris as (str, str)
        """
        if uris:
            self.__count += len(uris)
            (uri, api) = uris.pop(0)
            App().task_helper.load_uri_content(uri,
                                               self.__cancellable,
                                               self.__on_load_uri_content,
                                               api,
                                               uris)
        elif uris is not None and self.__count == 0:
            self.__spinner.stop()

    def __on_load_uri_content(self, uri, loaded, content, api, uris):
        """
            Add loaded pixbuf
            @param uri as str
            @param loaded as bool
            @param content as bytes
            @param uris as [str]
            @param api as str
            @param last as bool
        """
        try:
            if loaded:
                self.__add_pixbuf(content, api)
            if uris:
                (uri, api) = uris.pop(0)
                App().task_helper.load_uri_content(uri,
                                                   self.__cancellable,
                                                   self.__on_load_uri_content,
                                                   api,
                                                   uris)
        except Exception as e:
            Logger.warning("ArtworkWidget::__on_load_uri_content(): %s", e)
        self.__count -= 1
        if self.__count == 0:
            self.__spinner.stop()

    def __on_activate(self, flowbox, child):
        """
            Use pixbuf as cover
            Reset cache and use player object to announce cover change
        """
        try:
            if isinstance(child, ArtworkSearchChild):
                self.__close_popover()
                if self.__album is not None:
                    App().art.save_album_artwork(child.bytes, self.__album)
                else:
                    App().art.uncache_artist_artwork(self.__artist)
                    App().art.add_artist_artwork(self.__artist, child.bytes)
                    App().art.emit("artist-artwork-changed", self.__artist)
                self._streams = {}
            else:
                self.__infobar_label.set_text(_("Reset artwork?"))
                self.__infobar.show()
                # GTK 3.20 https://bugzilla.gnome.org/show_bug.cgi?id=710888
                self.__infobar.queue_resize()
        except Exception as e:
            Logger.error("ArtworkWidget::__on_activate(): %s", e)

    def __on_search_timeout(self, string):
        """
            Populate widget
            @param string as str
        """
        self.__timeout_id = None
        self.__cancellable.cancel()
        for child in self.__view.get_children():
            if child.get_name() == "web":
                child.destroy()
        GLib.timeout_add(250, self.__search_for_artwork)
