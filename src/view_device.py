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

from gi.repository import Gtk, GLib, Gio

from gettext import gettext as _
import re

from lollypop.view import View
from lollypop.widgets_device import DeviceManagerWidget


class DeviceLocked(View):
    """
        Show a message about locked device to users
    """
    def __init__(self):
        """
            Init view
        """
        View.__init__(self)
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/DeviceManagerView.ui')
        self.add(builder.get_object('message'))
        builder.get_object('label').set_text(_("Please unlock your device"))


# FIXME Remove this later
class DeviceMigration(View):
    """
        Show a message about old lollypop sync
    """
    def __init__(self):
        """
            Init view
        """
        View.__init__(self)
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/DeviceManagerView.ui')
        self.add(builder.get_object('message'))
        builder.get_object('label').set_text(
            _("Lollypop sync changed due to limitations in some devices.\n"
              "Please remove Music/lollypop folder on your device..."))


class DeviceView(View):
    """
        Playlist synchronisation to MTP
    """
    def exists_old_sync(uri):
        """
            True if exists an old sync on device
            @param uri as str
            @return bool
        """
        d = Gio.File.new_for_uri(uri+"/Music/lollypop/tracks")
        return d.query_exists(None)

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
                'standard::name,standard::type',
                Gio.FileQueryInfoFlags.NONE,
                None)
            for info in infos:
                if info.get_file_type() != Gio.FileType.DIRECTORY:
                    continue
                # We look to this folder to select an already synced path
                suburi = uri + "/" + info.get_name() + "/Music/unsync"
                sub = Gio.File.new_for_uri(suburi)
                if sub.query_exists(None):
                    files.insert(0, info.get_name())
                else:
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
        grid = builder.get_object('device')
        self.add(grid)
        self._device_widget = DeviceManagerWidget(progress, self)
        self._device_widget.connect('sync-finished', self._on_sync_finished)
        self._device_widget.show()
        self._viewport.add(self._device_widget)
        self.add(self._scrolled)
        self._sanitize_non_mtp()

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
    def _sanitize_non_mtp(self):
        """
            Sanitize non MTP device by changing uri and creating a default
            folder
        """
        uri = self._device.uri
        # Mtp device contain a virtual folder
        # For others, just go up in path
        if uri.find('mtp:') == -1:
            m = re.search('(.*)/[^/]*', uri)
            if m:
                uri = m.group(1)
        # Add / to uri if needed, some gvfs modules add one and some not
        if uri is not None and len(uri) > 1 and uri[-1:] != '/':
            uri += '/'
        self._device.uri = uri

    def stop(self):
        """
            Stop syncing
        """
        self._device_widget.cancel_sync()

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
        uri = "%s%s/Music" % (self._device.uri, text)
        self._device_widget.set_uri(uri)
        self._device_widget.populate()

    def _set_combo_text(self, text_list):
        """
            Set combobox text
            @param text list as [str]
        """
        if self._memory_combo.get_active_text() is not None:
            return
        for text in text_list:
            self._memory_combo.append_text(text)
        self._memory_combo.set_active(0)
