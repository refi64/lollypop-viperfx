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

import os
from threading import Thread

from gettext import gettext as _

from lollypop.objects import Track
from lollypop.widgets_rating import RatingWidget
from lollypop.define import Lp, ArtSize
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
        self.connect('map', self._on_map)
        self.connect('unmap', self._on_unmap)
        self._name = name
        self._radios_manager = radios_manager
        self._start = 0
        self._orig_pixbufs = {}

        self._stack = Gtk.Stack()
        self._stack.set_transition_duration(1000)
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._stack.show()

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/RadioPopover.ui')
        builder.connect_signals(self)

        self._view = Gtk.FlowBox()
        self._view.set_selection_mode(Gtk.SelectionMode.NONE)
        self._view.connect('child-activated', self._on_activate)
        self._view.set_max_children_per_line(100)
        self._view.set_property('row-spacing', 10)
        self._view.show()

        builder.get_object('viewport').add(self._view)

        self._name_entry = builder.get_object('name')
        self._uri_entry = builder.get_object('uri')
        self._btn_add_modify = builder.get_object('btn_add_modify')
        self._spinner = builder.get_object('spinner')
        self._stack.add_named(builder.get_object('spinner-grid'), 'spinner')
        self._stack.add_named(builder.get_object('notfound'), 'notfound')
        self._stack.add_named(builder.get_object('logo'), 'logo')
        self._stack.add_named(builder.get_object('widget'), 'widget')
        self._stack.set_visible_child_name('widget')
        self.add(self._stack)

        track = Track()
        track.set_radio(name, '')
        rating = RatingWidget(track)
        rating.show()
        builder.get_object('widget').attach(rating, 0, 2, 2, 1)

        if self._name == '':
            builder.get_object('btn_add_modify').set_label(_("Add"))
        else:
            builder.get_object('btn_add_modify').set_label(_("Modify"))
            builder.get_object('btn_delete').show()
            self._name_entry.set_text(self._name)
            url = self._radios_manager.get_url(self._name)
            if url:
                self._uri_entry.set_text(url)

#######################
# PRIVATE             #
#######################
    def _populate_threaded(self):
        """
            Populate view
        """
        self._thread = True
        t = Thread(target=self._populate)
        t.daemon = True
        t.start()

    def _populate(self):
        """
            Same as _populate_threaded()
            @thread safe
        """
        self._urls = Lp().art.get_duck_arts(self._name+"+logo+radio")
        if self._urls:
            self._add_pixbufs()
        else:
            GLib.idle_add(self._show_not_found)

    def _add_pixbufs(self):
        """
            Add urls to the view
        """
        if self._urls:
            url = self._urls.pop()
            stream = None
            try:
                f = Gio.File.new_for_uri(url)
                (status, data, tag) = f.load_contents()
                if status:
                    stream = Gio.MemoryInputStream.new_from_data(data, None)
            except:
                if self._thread:
                    self._add_pixbufs()
            if stream:
                GLib.idle_add(self._add_pixbuf, stream)
            if self._thread:
                self._add_pixbufs()

    def _show_not_found(self):
        """
            Show not found message if view empty
        """
        if len(self._view.get_children()) == 0:
            self._stack.set_visible_child_name('notfound')

    def _add_pixbuf(self, stream):
        """
            Add stream to the view
        """
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(
                stream, ArtSize.MONSTER,
                ArtSize.MONSTER,
                True,
                None)
            image = Gtk.Image()
            image.get_style_context().add_class('cover-frame')
            image.set_property('halign', Gtk.Align.CENTER)
            image.set_property('valign', Gtk.Align.CENTER)
            self._orig_pixbufs[image] = pixbuf
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
            del pixbuf
            surface = Gdk.cairo_surface_create_from_pixbuf(
                                                       scaled_pixbuf,
                                                       self.get_scale_factor(),
                                                       None)
            del scaled_pixbuf
            image.set_from_surface(surface)
            del surface
            image.show()
            self._view.add(image)
        except Exception as e:
            print(e)
            pass
        if self._stack.get_visible_child_name() == 'spinner':
            self._spinner.stop()
            self._stack.set_visible_child_name('logo')

    def _on_map(self, widget):
        """
            Grab focus/Disable global shortcuts
            @param widget as Gtk.Widget
        """
        GLib.idle_add(self._name_entry.grab_focus)
        # FIXME Not needed with GTK >= 3.18
        Lp().window.enable_global_shorcuts(False)

    def _on_unmap(self, widget):
        """
            Enable global shortcuts, destroy
            @param widget as Gtk.Widget
        """
        self._thread = False
        # FIXME Not needed with GTK >= 3.18
        Lp().window.enable_global_shorcuts(True)
        GLib.idle_add(self.destroy)

    def _on_btn_add_modify_clicked(self, widget):
        """
            Add/Modify a radio
            @param widget as Gtk.Widget
        """
        uri = self._uri_entry.get_text()
        new_name = self._name_entry.get_text()
        rename = self._name != '' and self._name != new_name

        if uri != '' and new_name != '':
            self._stack.get_visible_child().hide()
            if rename:
                self._radios_manager.rename(self._name, new_name)
                Lp().art.rename_radio(self._name, new_name)
            else:
                self._radios_manager.add(new_name, uri.lstrip().rstrip())
            self._stack.set_visible_child_name('spinner')
            self._name = new_name
            self._populate_threaded()
            self.set_size_request(700, 400)

    def _on_btn_delete_clicked(self, widget):
        """
            Delete a radio
            @param widget as Gtk.Widget
        """
        self.hide()
        if self._name != '':
            cache = Art._RADIOS_PATH
            self._radios_manager.delete(self._name)
            Lp().art.clean_radio_cache(self._name)
            if os.path.exists(cache+"/%s.png" % self._name):
                os.remove(cache+"/%s.png" % self._name)

    def _on_activate(self, flowbox, child):
        """
            Use pixbuf as cover
            Reset cache and use player object to announce cover change
        """
        pixbuf = self._orig_pixbufs[child.get_child()]
        Lp().art.save_radio_artwork(pixbuf, self._name)
        Lp().art.clean_radio_cache(self._name)
        Lp().art.radio_artwork_update(self._name)
        self.hide()
        self._streams = {}

    def _on_entry_changed(self, entry):
        """
            Update modify/add button
            @param entry as Gtk.Entry
        """
        uri = self._uri_entry.get_text()
        name = self._name_entry.get_text()
        if name != '' and uri.find('://') != -1:
            self._btn_add_modify.set_sensitive(True)
        else:
            self._btn_add_modify.set_sensitive(False)

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
                Lp().art.save_radio_artwork(pixbuf, self._name)
                Lp().art.clean_radio_cache(self._name)
                Lp().art.radio_artwork_update(self._name)
                self._streams = {}
            except Exception as e:
                print("RadioPopover::_on_button_clicked():", e)
        dialog.destroy()
