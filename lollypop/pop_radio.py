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

from lollypop.objects import Track
from lollypop.widgets_rating import RatingWidget
from lollypop.define import Lp, ArtSize
from lollypop.helper_task import TaskHelper
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
        self.connect("map", self.__on_map)
        self.connect("unmap", self.__on_unmap)
        self.__name = name
        self.__radios_manager = radios_manager
        self.__start = 0
        self.__orig_pixbufs = {}
        self.__cancellable = Gio.Cancellable()

        self.__stack = Gtk.Stack()
        self.__stack.set_transition_duration(1000)
        self.__stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.__stack.show()

        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/RadioPopover.ui")
        builder.connect_signals(self)

        self.__view = Gtk.FlowBox()
        self.__view.set_selection_mode(Gtk.SelectionMode.NONE)
        self.__view.connect("child-activated", self.__on_activate)
        self.__view.set_max_children_per_line(100)
        self.__view.set_property("row-spacing", 10)
        self.__view.show()

        builder.get_object("viewport").add(self.__view)

        self.__name_entry = builder.get_object("name")
        self.__uri_entry = builder.get_object("uri")
        self.__btn_add_modify = builder.get_object("btn_add_modify")
        self.__spinner = builder.get_object("spinner")
        self.__stack.add_named(builder.get_object("spinner-grid"), "spinner")
        self.__stack.add_named(builder.get_object("notfound"), "notfound")
        self.__stack.add_named(builder.get_object("logo"), "logo")
        self.__stack.add_named(builder.get_object("widget"), "widget")
        self.__stack.set_visible_child_name("widget")
        self.add(self.__stack)

        track = Track()
        track.set_radio(name, "")
        rating = RatingWidget(track)
        rating.show()
        builder.get_object("widget").attach(rating, 0, 2, 2, 1)

        if self.__name == "":
            # Translators: radio context
            builder.get_object("btn_add_modify").set_label(_("Add"))
        else:
            # Translators: radio context
            builder.get_object("btn_add_modify").set_label(_("Modify"))
            builder.get_object("btn_delete").show()
            self.__name_entry.set_text(self.__name)
            url = self.__radios_manager.get_url(self.__name)
            if url:
                self.__uri_entry.set_text(url)

#######################
# PROTECTED           #
#######################
    def _on_btn_add_modify_clicked(self, widget):
        """
            Add/Modify a radio
            @param widget as Gtk.Widget
        """
        uri = self.__uri_entry.get_text()
        new_name = self.__name_entry.get_text()
        rename = self.__name != "" and self.__name != new_name

        if uri != "" and new_name != "":
            self.__stack.get_visible_child().hide()
            if rename:
                self.__radios_manager.rename(self.__name, new_name)
                Lp().art.rename_radio(self.__name, new_name)
            else:
                self.__radios_manager.add(new_name, uri.lstrip().rstrip())
            self.__stack.set_visible_child_name("spinner")
            self.__name = new_name
            uri = Lp().art.get_google_search_uri(self.__name + "+logo+radio")
            helper = TaskHelper()
            helper.load_uri_content(uri,
                                    self.__cancellable,
                                    self.__on_google_content_loaded)
            self.set_size_request(700, 400)

    def _on_btn_delete_clicked(self, widget):
        """
            Delete a radio
            @param widget as Gtk.Widget
        """
        self.hide()
        if self.__name != "":
            store = Art._RADIOS_PATH
            self.__radios_manager.delete(self.__name)
            Lp().art.clean_radio_cache(self.__name)
            f = Gio.File.new_for_path(store + "/%s.png" % self.__name)
            if f.query_exists():
                f.delete()

    def _on_entry_changed(self, entry):
        """
            Update modify/add button
            @param entry as Gtk.Entry
        """
        uri = self.__uri_entry.get_text()
        name = self.__name_entry.get_text()
        if name != "" and uri.find("://") != -1:
            self.__btn_add_modify.set_sensitive(True)
        else:
            self.__btn_add_modify.set_sensitive(False)

    def _on_button_clicked(self, button):
        """
            Show file chooser
            @param button as Gtk.button
        """
        dialog = Gtk.FileChooserDialog()
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        dialog.add_buttons(Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        dialog.set_transient_for(Lp().window)
        self.hide()
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(dialog.get_filename())
                Lp().art.save_radio_artwork(pixbuf, self.__name)
                Lp().art.clean_radio_cache(self.__name)
                Lp().art.radio_artwork_update(self.__name)
                self._streams = {}
            except Exception as e:
                print("RadioPopover::_on_button_clicked():", e)
        dialog.destroy()

#######################
# PRIVATE             #
#######################
    def __populate(self, uris):
        """
            Add uris to view
            @param uris as [str]
        """
        if uris:
            uri = uris.pop(0)
            helper = TaskHelper()
            helper.load_uri_content(uri,
                                    self.__cancellable,
                                    self.__add_pixbuf,
                                    self.__populate,
                                    uris)
        elif len(self.__view.get_children()) == 0:
            self.__stack.set_visible_child_name("notfound")

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
        if loaded:
            bytes = GLib.Bytes(content)
            stream = Gio.MemoryInputStream.new_from_bytes(bytes)
            bytes.unref()
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(
                stream, ArtSize.MONSTER,
                ArtSize.MONSTER,
                True,
                None)
            stream.close()
            image = Gtk.Image()
            image.get_style_context().add_class("cover-frame")
            image.set_property("halign", Gtk.Align.CENTER)
            image.set_property("valign", Gtk.Align.CENTER)
            self.__orig_pixbufs[image] = pixbuf
            # Scale preserving aspect ratio
            width = pixbuf.get_width()
            height = pixbuf.get_height()
            if width > height:
                height = height*ArtSize.BIG*self.get_scale_factor()/width
                width = ArtSize.BIG*self.get_scale_factor()
            else:
                width = width*ArtSize.BIG*self.get_scale_factor()/height
                height = ArtSize.BIG*self.get_scale_factor()
            scaled_pixbuf = pixbuf.scale_simple(width,
                                                height,
                                                GdkPixbuf.InterpType.BILINEAR)
            surface = Gdk.cairo_surface_create_from_pixbuf(
                                                       scaled_pixbuf,
                                                       self.get_scale_factor(),
                                                       None)
            image.set_from_surface(surface)
            image.show()
            self.__view.add(image)
        # Switch on first image
        if self.__stack.get_visible_child_name() == "spinner":
            self.__spinner.stop()
            self.__stack.set_visible_child_name("logo")
        callback(*args)

    def __on_map(self, widget):
        """
            Grab focus/Disable global shortcuts
            @param widget as Gtk.Widget
        """
        GLib.idle_add(self.__name_entry.grab_focus)
        # FIXME Not needed with GTK >= 3.18
        Lp().window.enable_global_shortcuts(False)

    def __on_unmap(self, widget):
        """
            Enable global shortcuts, destroy
            @param widget as Gtk.Widget
        """
        self._thread = False
        # FIXME Not needed with GTK >= 3.18
        Lp().window.enable_global_shortcuts(True)
        GLib.idle_add(self.destroy)

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
        self.__cancellable.cancel()
        pixbuf = self.__orig_pixbufs[child.get_child()]
        Lp().art.save_radio_artwork(pixbuf, self.__name)
        Lp().art.clean_radio_cache(self.__name)
        Lp().art.radio_artwork_update(self.__name)
        self.hide()
        self._streams = {}
