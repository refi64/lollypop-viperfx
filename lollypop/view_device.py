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

from gi.repository import Gtk, GLib, Gio

from gettext import gettext as _
import re

from lollypop.loader import Loader
from lollypop.view import View
from lollypop.define import App, SelectionListMask, Type
from lollypop.logger import Logger
from lollypop.selectionlist import SelectionList
from lollypop.widgets_device import DeviceManagerWidget


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
        d = Gio.File.new_for_uri(uri + "/Music/lollypop/tracks")
        return d.query_exists()

    def get_files(uri):
        """
            Get files for uri
            @param uri as str
            @return [str]
        """
        files = []
        try:
            d = Gio.File.new_for_uri(uri)
            if not d.query_exists():
                d.make_directory_with_parents()
            infos = d.enumerate_children(
                "standard::name,standard::type",
                Gio.FileQueryInfoFlags.NONE,
                None)
            for info in infos:
                if info.get_file_type() != Gio.FileType.DIRECTORY:
                    continue
                f = infos.get_child(info)
                # We look to this folder to select an already synced uri
                suburi = f.get_uri() + "/Music/unsync"
                sub = Gio.File.new_for_uri(suburi)
                if sub.query_exists():
                    files.insert(0, info.get_name())
                else:
                    files.append(info.get_name())
            infos.close(None)
        except Exception as e:
            Logger.error("DeviceManagerView::_get_files: %s: %s" % (uri, e))
            files = []
        return files

    def __init__(self, device):
        """
            Init view
            @param device as Device
        """
        View.__init__(self)
        self._empty_message = _("Please unlock your device")
        self._empty_icon_name = "multimedia-player-symbolic"
        self.__timeout_id = None
        self.__device = device
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/DeviceManagerView.ui")
        self.__memory_combo = builder.get_object("memory_combo")
        self.__sync_button = builder.get_object("sync_btn")
        self.__sync_button.set_label(_("Synchronize"))
        builder.connect_signals(self)
        self.__device_widget = DeviceManagerWidget(self)
        self.__device_widget.mtp_sync.connect("sync-finished",
                                              self.__on_sync_finished)
        self.__device_widget.mtp_sync.connect("sync-errors",
                                              self.__on_sync_errors)
        self.__device_widget.show()
        self.__infobar = builder.get_object("infobar")
        self.__error_label = builder.get_object("error_label")
        self.__paned = builder.get_object("paned")
        self.__selection_list = SelectionList(SelectionListMask.LIST_ONE)
        self.__selection_list.set_vexpand(True)
        self.__selection_list.connect("item-selected", self.__on_item_selected)
        self.__selection_list.mark_as(SelectionListMask.ARTISTS)
        self.__paned.add1(self.__selection_list)
        self.__paned.add2(builder.get_object("device_view"))
        builder.get_object("device_view").attach(self._scrolled, 0, 3, 4, 1)
        self.add(self.__paned)
        self.__paned.set_position(
            App().settings.get_value("paned-device-width").get_int32())

        self.__update_list_device()
        self.__sanitize_non_mtp()

    def populate(self):
        """
            Populate combo box
            @thread safe
        """
        self._remove_placeholder()
        child = self._viewport.get_child()
        if child is None:
            label = Gtk.Label.new(
                _("This will remove some files on your device!"))
            label.get_style_context().add_class("lyrics-x-large")
            label.get_style_context().add_class("lyrics")
            label.set_vexpand(True)
            label.set_hexpand(True)
            label.show()
            self._viewport.add(label)
        files = DeviceView.get_files(self.__device.uri)
        if files:
            self.__selection_list.show()
            GLib.idle_add(self.__set_combo_text, files)
            self.__sync_button.set_sensitive(True)
        else:
            self.__selection_list.hide()
            View.populate(self)
            self.__sync_button.set_sensitive(False)

    def is_syncing(self):
        """
            Check if lollypop is syncing
            @return bool
        """
        return not self.__device_widget.mtp_sync.cancellable.is_cancelled()

    @property
    def device(self):
        """
            Get device for view
            @return Device
        """
        return self.__device

    @property
    def should_destroy(self):
        return False

#######################
# PROTECTED           #
#######################
    def _on_infobar_response(self, infobar, response_id):
        """
            Hide infobar
            @param widget as Gtk.Infobar
            @param reponse id as int
        """
        if response_id == Gtk.ResponseType.CLOSE:
            self.__infobar.set_revealed(False)
            # WTF?
            GLib.timeout_add(300, self.__infobar.hide)

    def _on_destroy(self, widget):
        """
            Remove running timeout
            @param widget as Gtk.Widget
        """
        if self.__timeout_id is not None:
            GLib.source_remove(self.__timeout_id)
            self.__timeout_id = None
        View._on_destroy(self, widget)

    def _on_sync_clicked(self, widget):
        """
            Start synchronisation
            @param widget as Gtk.Button
        """
        if not self.__device_widget.mtp_sync.cancellable.is_cancelled():
            self.__device_widget.mtp_sync.cancellable.cancel()
        elif not App().window.container.progress.is_visible():
            self.__memory_combo.hide()
            self.__sync_button.set_label(_("Cancel synchronization"))
            self.__device_widget.sync()

    def _on_memory_combo_changed(self, combo):
        """
            Update path
            @param combo as Gtk.ComboxText
        """
        self.__timeout_id = None
        text = combo.get_active_text()
        uri = "%s%s/Music" % (self.__device.uri, text)
        self.__device_widget.set_uri(uri)

    def _on_map(self, widget):
        """
            Set active ids
            @param widget as Gtk.Widget
        """
        App().settings.set_value("state-one-ids",
                                 GLib.Variant("ai", []))

    def _on_unmap(self, widget):
        """
            Save paned position
            @param widget as Gtk.Widget
        """
        App().settings.set_value("paned-device-width",
                                 GLib.Variant("i",
                                              self.__paned.get_position()))

#######################
# PRIVATE             #
#######################
    def __update_list_device(self):
        """
            Setup list for device
            @param list as SelectionList
            @thread safe
        """
        def load():
            artists = App().artists.get()
            compilations = App().albums.get_compilation_ids([])
            return (artists, compilations)

        def setup(artists, compilations):
            items = [(Type.ALL, _("Synced albums"), "")]
            items.append((Type.PLAYLISTS, _("Playlists"), ""))
            if compilations:
                items.append((Type.COMPILATIONS, _("Compilations"), ""))
                items.append((Type.SEPARATOR, "", ""))
            items += artists
            self.__selection_list.populate(items)
        loader = Loader(target=load, view=self.__selection_list,
                        on_finished=lambda r: setup(*r))
        loader.start()

    def __sanitize_non_mtp(self):
        """
            Sanitize non MTP device by changing uri and creating a default
            folder
        """
        uri = self.__device.uri
        # Mtp device contain a virtual folder
        # For others, just go up in path
        if uri.find("mtp:") == -1:
            m = re.search("(.*)/[^/]*", uri)
            if m:
                uri = m.group(1)
        # Add / to uri if needed, some gvfs modules add one and some not
        if uri is not None and len(uri) > 1 and uri[-1:] != "/":
            uri += "/"
        self.__device.uri = uri

    def stop(self):
        pass

    def __on_sync_errors(self, mtp_sync, error):
        """
            Show information bar with error message
            @param mtp_sync as MtpSync
            @param error as str
        """
        error_text = error or _("Unknown error while syncing,"
                                " try to reboot your device")
        self.__error_label.set_text(error_text)
        self.__infobar.show()
        self.__infobar.set_revealed(True)

    def __on_sync_finished(self, device_widget):
        """
            Restore widgets state
            @param device widget as DeviceManager
        """
        self.__memory_combo.show()
        self.__sync_button.set_label(_("Synchronize"))

    def __set_combo_text(self, text_list):
        """
            Set combobox text
            @param text list as [str]
        """
        for text in text_list:
            self.__memory_combo.append_text(text)
        self.__memory_combo.set_active(0)

    def __on_item_selected(self, selectionlist):
        """
            Update view
            @param selection_list as SelectionList
        """
        child = self._viewport.get_child()
        if child is not None and isinstance(child, Gtk.Label):
            child.destroy()
            self._viewport.add(self.__device_widget)
        self.__device_widget.populate(selectionlist.selected_ids)
