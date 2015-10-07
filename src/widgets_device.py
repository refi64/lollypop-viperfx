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

from gi.repository import Gtk, GLib, Gio, GObject, Pango

from gettext import gettext as _
from threading import Thread

from lollypop.sync_mtp import MtpSync
from lollypop.define import Lp, Type


class DeviceManagerWidget(Gtk.Bin, MtpSync):
    """
        Widget for synchronize mtp devices
    """
    __gsignals__ = {
        'sync-finished': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self, progress, parent):
        """
            Init widget
            @param device as Device
            @param progress bar as Gtk.ProgressBar
            @param parent as Gtk.Widget
        """
        Gtk.Bin.__init__(self)
        MtpSync.__init__(self)
        self._parent = parent
        self._progress = progress
        self._on_disk_playlists = None
        self._uri = None

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/DeviceManagerWidget.ui')
        self._error_label = builder.get_object('error-label')
        self._switch = builder.get_object('switch')

        self._model = Gtk.ListStore(bool, str, int)
        self._model.set_sort_column_id(1, Gtk.SortType.ASCENDING)
        self._model.set_sort_func(1, self._sort_items)

        self._view = builder.get_object('view')
        self._view.set_model(self._model)

        builder.connect_signals(self)

        self.add(builder.get_object('widget'))

        self._infobar = builder.get_object('infobar')
        self._infobar_label = builder.get_object('infobarlabel')

        renderer0 = Gtk.CellRendererToggle()
        renderer0.set_property('activatable', True)
        renderer0.connect('toggled', self._on_playlist_toggled)
        column0 = Gtk.TreeViewColumn("toggle", renderer0, active=0)

        renderer1 = Gtk.CellRendererText()
        renderer1.set_property('ellipsize-set', True)
        renderer1.set_property('ellipsize', Pango.EllipsizeMode.END)
        renderer1.set_property('editable', True)
        column1 = Gtk.TreeViewColumn('text', renderer1, text=1)
        column1.set_expand(True)

        self._view.append_column(column0)
        self._view.append_column(column1)

    def populate(self):
        """
            Populate playlists, thread safe
        """
        self._model.clear()
        playlists = [(Type.LOVED, Lp.playlists._LOVED)]
        playlists += Lp.playlists.get()
        self._append_playlists(playlists)

    def set_playlists(self, playlists, uri):
        """
            Set available playlists
            @param uri as str
        """
        self._on_disk_playlists = playlists
        self._uri = uri

    def is_syncing(self):
        """
            @return True if syncing
        """
        return self._syncing

    def sync(self):
        """
            Start synchronisation
        """
        self._syncing = True
        self._progress.show()
        self._progress.set_fraction(0.0)
        self._switch.set_sensitive(False)
        playlists = []
        if not self._switch.get_active():
            self._view.set_sensitive(False)
            for item in self._model:
                if item[0]:
                    playlists.append(item[2])
        else:
            playlists.append(Type.ALL)

        t = Thread(target=self._sync, args=(playlists,))
        t.daemon = True
        t.start()

    def cancel_sync(self):
        """
            Cancel synchronisation
        """
        self._syncing = False

#######################
# PRIVATE             #
#######################
    def _sort_items(self, model, itera, iterb, data):
        """
            Sort model
        """
        a = model.get_value(itera, 1)
        b = model.get_value(iterb, 1)
        return a.lower() > b.lower()

    def _append_playlists(self, playlists):
        """
            Append a playlist
            @param playlists as [(int, str)]
            @param playlist selected as bool
        """
        if playlists:
            playlist = playlists.pop(0)
            selected = playlist[1]+'.m3u' in self._on_disk_playlists
            self._model.append([selected, playlist[1], playlist[0]])
            GLib.idle_add(self._append_playlists, playlists)
        else:
            self._view.get_selection().unselect_all()

    def _update_progress(self):
        """
            Update progress bar smoothly
        """
        current = self._progress.get_fraction()
        if self._syncing:
            progress = (self._fraction-current)/10000
        else:
            progress = 0.001

        if current < self._fraction:
            self._progress.set_fraction(current+progress)
            if not self._progress.is_visible():
                self._progress.show()
        if self._syncing or current < 1.0:
            GLib.idle_add(self._update_progress)
        else:
            GLib.timeout_add(1000, self._progress.hide)

    def _on_finished(self):
        """
            Emit finished signal
        """
        MtpSync._on_finished(self)
        if not self._switch.get_state():
            self._view.set_sensitive(True)
        self._switch.set_sensitive(True)
        self.emit('sync-finished')

    def _on_errors(self):
        """
            Show information bar with error message
        """
        MtpSync._on_errors(self)
        error_text = _("Unknown error while syncing,"
                       " try to reboot your device")
        try:
            d = Gio.File.new_for_uri(self._uri)
            info = d.query_filesystem_info('filesystem::free')
            free = info.get_attribute_as_string('filesystem::free')

            if free is None or int(free) < 1024:
                error_text = _("No free space available on device")
        except Exception as e:
            print("DeviceWidget::_on_errors(): %s" % e)
        self._error_label.set_text(error_text)
        self._infobar.show()

    def _on_switch_state_set(self, widget, state):
        """
            Enable or disable playlist selection
            @param widget as Gtk.Switch
            @param state as bool
        """
        if state:
            self._view.set_sensitive(False)
        else:
            self._view.set_sensitive(True)

    def _on_response(self, infobar, response_id):
        """
            Hide infobar
            @param widget as Gtk.Infobar
            @param reponse id as int
        """
        if response_id == Gtk.ResponseType.CLOSE:
            self._infobar.hide()

    def _on_playlist_toggled(self, view, path):
        """
            When playlist is activated, add object to playlist
            @param widget as cell renderer
            @param path as str representation of Gtk.TreePath
        """
        iterator = self._model.get_iter(path)
        toggle = not self._model.get_value(iterator, 0)
        self._model.set_value(iterator, 0, toggle)
