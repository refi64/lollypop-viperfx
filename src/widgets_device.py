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
        self._uri = None

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/DeviceManagerWidget.ui')
        self._error_label = builder.get_object('error-label')
        self._switch_albums = builder.get_object('switch_albums')
        self._switch_albums.set_state(Lp().settings.get_value('sync-albums'))
        self._switch_mp3 = builder.get_object('switch_mp3')
        self._switch_normalize = builder.get_object('switch_normalize')
        if not self._check_encoder_status():
            self._switch_mp3.set_sensitive(False)
            self._switch_normalize.set_sensitive(False)
            self._switch_mp3.set_tooltip_text(_("You need to install " +
                                              "gstreamer-plugins-ugly"))
        else:
            self._switch_mp3.set_state(Lp().settings.get_value('convert-mp3'))
        self._menu_items = builder.get_object('menu-items')
        self._menu = builder.get_object('menu')

        self._model = Gtk.ListStore(bool, str, int)
        self._model.set_sort_column_id(1, Gtk.SortType.ASCENDING)
        self._model.set_sort_func(1, self._sort_items)

        self._view = builder.get_object('view')
        self._view.set_model(self._model)
        self._view.set_sensitive(not Lp().settings.get_value('sync-albums'))

        builder.connect_signals(self)

        self.add(builder.get_object('widget'))

        self._infobar = builder.get_object('infobar')
        self._infobar_label = builder.get_object('infobarlabel')

        renderer0 = Gtk.CellRendererToggle()
        renderer0.set_property('activatable', True)
        renderer0.connect('toggled', self._on_playlist_toggled)
        column0 = Gtk.TreeViewColumn(" ✓", renderer0, active=0)
        column0.set_clickable(True)
        column0.connect('clicked', self._on_column0_clicked)

        renderer1 = Gtk.CellRendererText()
        renderer1.set_property('ellipsize-set', True)
        renderer1.set_property('ellipsize', Pango.EllipsizeMode.END)
        renderer1.set_property('editable', True)
        column1 = Gtk.TreeViewColumn(_("Playlists"), renderer1, text=1)
        column1.set_expand(True)

        self._view.append_column(column0)
        self._view.append_column(column1)

    def populate(self):
        """
            Populate playlists
            @thread safe
        """
        self._model.clear()
        playlists = [(Type.LOVED, Lp().playlists._LOVED)]
        playlists += Lp().playlists.get()
        self._append_playlists(playlists)

    def set_uri(self, uri):
        """
            Set uri
            @param uri as str
        """
        self._uri = uri
        d = Gio.File.new_for_uri(uri)
        try:
            if not d.query_exists(None):
                d.make_directory_with_parents(None)
        except:
            pass

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
        self._menu.set_sensitive(False)
        playlists = []
        if not self._switch_albums.get_active():
            self._view.set_sensitive(False)
            for item in self._model:
                if item[0]:
                    playlists.append(item[2])
        else:
            playlists.append(Type.ALL)

        t = Thread(target=self._sync,
                   args=(playlists,
                         self._switch_mp3.get_active(),
                         self._switch_normalize.get_active()))
        t.daemon = True
        t.start()

    def cancel_sync(self):
        """
            Cancel synchronisation
        """
        self._syncing = False

    def show_overlay(self, bool):
        """
            No overlay here now
        """
        pass

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
        for playlist in playlists:
            playlist_name = GLib.uri_escape_string(playlist[1], "", False)
            playlist_obj = Gio.File.new_for_uri(self._uri + "/" +
                                                playlist_name + '.m3u')
            selected = playlist_obj.query_exists(None)
            self._model.append([selected, playlist[1], playlist[0]])

    def _update_progress(self):
        """
            Update progress bar smoothly
        """
        if not self._progress.is_visible():
            return
        current = self._progress.get_fraction()
        if self._syncing:
            progress = (self._fraction-current)/10
        else:
            progress = 0.01
        if current < self._fraction:
            self._progress.set_fraction(current+progress)
        if current < 1.0:
            if progress < 0.0002:
                GLib.timeout_add(500, self._update_progress)
            else:
                GLib.timeout_add(25, self._update_progress)
        else:
            GLib.timeout_add(1000, self._on_finished)

    def _pop_menu(self, button):
        """
            Popup menu for album
            @param button as Gtk.Button
            @param album id as int
        """
        parent = self._menu_items.get_parent()
        if parent is not None:
            parent.remove(self._menu_items)
        popover = Gtk.Popover.new(button)
        popover.set_position(Gtk.PositionType.BOTTOM)
        popover.add(self._menu_items)
        popover.show()

    def _on_finished(self):
        """
            Emit finished signal
        """
        MtpSync._on_finished(self)
        if not self._switch_albums.get_state():
            self._view.set_sensitive(True)
        self._menu.set_sensitive(True)
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

    def _on_albums_state_set(self, widget, state):
        """
            Enable or disable playlist selection
            Save option
            @param widget as Gtk.Switch
            @param state as bool
        """
        Lp().settings.set_value('sync-albums', GLib.Variant('b', state))
        self._view.set_sensitive(not state)

    def _on_mp3_state_set(self, widget, state):
        """
            Save option
            @param widget as Gtk.Switch
            @param state as bool
        """
        Lp().settings.set_value('convert-mp3', GLib.Variant('b', state))
        if not state:
            self._switch_normalize.set_active(False)
            Lp().settings.set_value('normalize-mp3',
                                    GLib.Variant('b', False))

    def _on_normalize_state_set(self, widget, state):
        """
            Save option
            @param widget as Gtk.Switch
            @param state as bool
        """
        Lp().settings.set_value('normalize-mp3', GLib.Variant('b', state))
        if state:
            self._switch_mp3.set_active(True)
            Lp().settings.set_value('convert-mp3', GLib.Variant('b', True))

    def _on_response(self, infobar, response_id):
        """
            Hide infobar
            @param widget as Gtk.Infobar
            @param reponse id as int
        """
        if response_id == Gtk.ResponseType.CLOSE:
            self._infobar.hide()

    def _on_column0_clicked(self, column):
        """
            Select/Unselect all playlists
            @param column as Gtk.TreeViewColumn
        """
        selected = False
        for item in self._model:
            if item[0]:
                selected = True
        for item in self._model:
            item[0] = not selected

    def _on_playlist_toggled(self, view, path):
        """
            When playlist is activated, add object to playlist
            @param widget as cell renderer
            @param path as str representation of Gtk.TreePath
        """
        iterator = self._model.get_iter(path)
        toggle = not self._model.get_value(iterator, 0)
        self._model.set_value(iterator, 0, toggle)
