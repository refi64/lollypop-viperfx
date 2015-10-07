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

from gi.repository import Gtk, GLib, Gio

from gettext import gettext as _

from lollypop.view import View
from lollypop.widgets_device import DeviceManagerWidget


class DeviceView(View):
    """
        Playlist synchronisation to MTP
    """

    def get_files(uri):
        """
            Get files for uri
            @param uri as str
            @return [str]
        """
        files = []
        try:
            d = Gio.File.new_for_uri(uri)
            if not d.query_exists(None):
                d.make_directory_with_parents(None)
            infos = d.enumerate_children(
                'standard::name',
                Gio.FileQueryInfoFlags.NONE,
                None)
            for info in infos:
                files.append(info.get_name())
            infos.close(None)
        except Exception as e:
            print("DeviceManagerView::_get_files: %s: %s" % (uri, e))
            files = []
        return files

    def __init__(self, device, progress):
        """
            Init view
            @param device as Device
            @param progress as Gtk.ProgressBar
        """
        View.__init__(self)
        self._timeout_id = None
        self._device = device
        self._progress = progress
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/DeviceManagerView.ui')
        self._memory_combo = builder.get_object('memory_combo')
        self._syncing_btn = builder.get_object('sync_btn')
        self._syncing_btn.set_label(_("Synchronize %s") % device.name)
        builder.connect_signals(self)
        grid = builder.get_object('widget')
        self.add(grid)
        self._device_widget = DeviceManagerWidget(progress, self)
        self._device_widget.connect('sync-finished', self._on_sync_finished)
        self._device_widget.show()
        self._viewport.add(self._device_widget)
        self.add(self._scrolledWindow)

    def populate(self):
        """
            Populate combo box
            @thread safe
        """
        files = DeviceView.get_files(self._device.uri)
        if files:
            GLib.idle_add(self._set_combo_text, files)
        else:
            GLib.idle_add(self.destroy)

    def is_syncing(self):
        """
            Check if lollypop is syncing
            @return bool
        """
        return self._device_widget.is_syncing()

#######################
# PRIVATE             #
#######################
    def _on_destroy(self, widget):
        """
            Remove running timeout
            @param widget as Gtk.Widget
        """
        if self._timeout_id is not None:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = None

    def _on_sync_clicked(self, widget):
        """
            Start synchronisation
            @param widget as Gtk.Button
        """
        if self._device_widget.is_syncing():
            self._device_widget.cancel_sync()
            self._on_sync_finished(None)
        elif not self._progress.is_visible():
            self._memory_combo.hide()
            self._syncing_btn.set_label(_("Cancel synchronization"))
            self._device_widget.sync()

    def _on_sync_finished(self, device_widget):
        """
            Restore widgets state
            @param device widget as DeviceManager
        """
        self._progress.hide()
        self._progress.set_fraction(0)
        self._memory_combo.show()
        self._syncing_btn.set_label(_("Synchronize %s") %
                                    self._device.name)

    def _on_memory_combo_changed(self, combo):
        """
            Update path
            @param combo as Gtk.ComboxText
        """
        self._timeout_id = None
        text = combo.get_active_text()
        uri = "%s%s/Music/%s" % (self._device.uri, text, "lollypop")
        on_disk_playlists = DeviceView.get_files(uri)
        if on_disk_playlists:
            self._device_widget.set_playlists(on_disk_playlists, uri)
            self._device_widget.populate()

    def _set_combo_text(self, text_list):
        """
            Set combobox text
            @param text list as [str]
        """
        for text in text_list:
            self._memory_combo.append_text(text)
        self._memory_combo.set_active(0)
