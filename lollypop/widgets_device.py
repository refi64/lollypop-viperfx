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

from gi.repository import Gtk, GLib, Gio, GObject, Pango

from gettext import gettext as _

from lollypop.sync_mtp import MtpSync
from lollypop.sqlcursor import SqlCursor
from lollypop.cellrenderer import CellRendererAlbum
from lollypop.selectionlist import SelectionList
from lollypop.define import Lp, Type
from lollypop.objects import Album
from lollypop.loader import Loader
from lollypop.helper_task import TaskHelper


# FIXME This class should not inherit MtpSync
# TODO Rework MtpSync code
class DeviceManagerWidget(Gtk.Bin, MtpSync):
    """
        Widget for synchronize mtp devices
    """
    __gsignals__ = {
        "sync-finished": (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self, parent):
        """
            Init widget
            @param device as Device
            @param parent as Gtk.Widget
        """
        Gtk.Bin.__init__(self)
        MtpSync.__init__(self)
        self.__parent = parent
        self.__stop = False
        self._uri = None

        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/DeviceManagerWidget.ui")
        widget = builder.get_object("widget")
        self.__error_label = builder.get_object("error-label")
        self.__switch_albums = builder.get_object("switch_albums")
        self.__switch_albums.set_state(Lp().settings.get_value("sync-albums"))
        self.__switch_mp3 = builder.get_object("switch_mp3")
        self.__switch_normalize = builder.get_object("switch_normalize")
        if not self._check_encoder_status():
            self.__switch_mp3.set_sensitive(False)
            self.__switch_normalize.set_sensitive(False)
            self.__switch_mp3.set_tooltip_text(_("You need to install " +
                                               "gstreamer-plugins-ugly"))
        else:
            self.__switch_mp3.set_state(Lp().settings.get_value("convert-mp3"))
        self.__menu_items = builder.get_object("menu-items")
        self.__menu = builder.get_object("menu")

        self.__model = Gtk.ListStore(bool, str, int)

        self.__selection_list = SelectionList(False)
        self.__selection_list.connect("item-selected",
                                      self.__on_item_selected)
        widget.attach(self.__selection_list, 1, 1, 1, 1)
        self.__selection_list.set_hexpand(True)

        self.__view = builder.get_object("view")
        self.__view.set_model(self.__model)

        builder.connect_signals(self)

        self.add(widget)

        self.__infobar = builder.get_object("infobar")
        self.__infobar_label = builder.get_object("infobarlabel")

        renderer0 = Gtk.CellRendererToggle()
        renderer0.set_property("activatable", True)
        renderer0.connect("toggled", self.__on_item_toggled)
        column0 = Gtk.TreeViewColumn(" ✓", renderer0, active=0)
        column0.set_clickable(True)
        column0.connect("clicked", self.__on_column0_clicked)

        renderer1 = CellRendererAlbum()
        self.__column1 = Gtk.TreeViewColumn("", renderer1, album=2)

        renderer2 = Gtk.CellRendererText()
        renderer2.set_property("ellipsize-set", True)
        renderer2.set_property("ellipsize", Pango.EllipsizeMode.END)
        self.__column2 = Gtk.TreeViewColumn("", renderer2, markup=1)
        self.__column2.set_expand(True)

        self.__view.append_column(column0)
        self.__view.append_column(self.__column1)
        self.__view.append_column(self.__column2)

    def populate(self):
        """
            Populate playlists
            @thread safe
        """
        self.__model.clear()
        self.__stop = False
        if Lp().settings.get_value("sync-albums"):
            self.__selection_list.clear()
            self.__setup_list_artists(self.__selection_list)
            self.__column1.set_visible(True)
            self.__column2.set_title(_("Albums"))
            self.__selection_list.show()
            self.__selection_list.select_ids([Type.ALL])
        else:
            playlists = [(Type.LOVED, Lp().playlists.LOVED)]
            playlists += Lp().playlists.get()
            self.__append_playlists(playlists)
            self.__column1.set_visible(False)
            self.__column2.set_title(_("Playlists"))
            self.__selection_list.hide()

    def set_uri(self, uri):
        """
            Set uri
            @param uri as str
        """
        self._uri = uri
        d = Gio.File.new_for_uri(uri)
        try:
            if not d.query_exists():
                d.make_directory_with_parents()
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
        Lp().window.progress.add(self)
        self.__menu.set_sensitive(False)
        playlists = []
        if not Lp().settings.get_value("sync-albums"):
            self.__view.set_sensitive(False)
            for item in self.__model:
                if item[0]:
                    playlists.append(item[2])
        else:
            playlists.append(Type.NONE)

        helper = TaskHelper()
        helper.run(self._sync, playlists,
                   self.__switch_mp3.get_active(),
                   self.__switch_normalize.get_active())

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
# PROTECTED           #
#######################
    def _update_progress(self):
        """
            Update progress bar smoothly
        """
        current = Lp().window.progress.get_fraction()
        if self._syncing:
            progress = (self._fraction-current)/10
        else:
            progress = 0.01
        if current < self._fraction:
            Lp().window.progress.set_fraction(current+progress, self)
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
        parent = self.__menu_items.get_parent()
        if parent is not None:
            parent.remove(self.__menu_items)
        popover = Gtk.Popover.new(button)
        popover.set_position(Gtk.PositionType.BOTTOM)
        popover.add(self.__menu_items)
        popover.show()

    def _on_finished(self):
        """
            Emit finished signal
        """
        MtpSync._on_finished(self)
        Lp().window.progress.set_fraction(1.0, self)
        if not self.__switch_albums.get_state():
            self.__view.set_sensitive(True)
        self.__menu.set_sensitive(True)
        self.emit("sync-finished")

    def _on_errors(self):
        """
            Show information bar with error message
        """
        MtpSync._on_errors(self)
        error_text = _("Unknown error while syncing,"
                       " try to reboot your device")
        try:
            d = Gio.File.new_for_uri(self._uri)
            info = d.query_filesystem_info("filesystem::free")
            free = info.get_attribute_as_string("filesystem::free")

            if free is None or int(free) < 1024:
                error_text = _("No free space available on device")
        except Exception as e:
            print("DeviceWidget::_on_errors(): %s" % e)
        self.__error_label.set_text(error_text)
        self.__infobar.show()

    def _on_albums_state_set(self, widget, state):
        """
            Enable or disable playlist selection
            Save option
            @param widget as Gtk.Switch
            @param state as bool
        """
        self.__stop = True
        Lp().settings.set_value("sync-albums", GLib.Variant("b", state))
        GLib.idle_add(self.populate)

    def _on_mp3_state_set(self, widget, state):
        """
            Save option
            @param widget as Gtk.Switch
            @param state as bool
        """
        Lp().settings.set_value("convert-mp3", GLib.Variant("b", state))
        if not state:
            self.__switch_normalize.set_active(False)
            Lp().settings.set_value("normalize-mp3",
                                    GLib.Variant("b", False))

    def _on_normalize_state_set(self, widget, state):
        """
            Save option
            @param widget as Gtk.Switch
            @param state as bool
        """
        Lp().settings.set_value("normalize-mp3", GLib.Variant("b", state))
        if state:
            self.__switch_mp3.set_active(True)
            Lp().settings.set_value("convert-mp3", GLib.Variant("b", True))

    def _on_response(self, infobar, response_id):
        """
            Hide infobar
            @param widget as Gtk.Infobar
            @param reponse id as int
        """
        if response_id == Gtk.ResponseType.CLOSE:
            self.__infobar.hide()

#######################
# PRIVATE             #
#######################
    def __setup_list_artists(self, selection_list):
        """
            Setup list for artists
            @param list as SelectionList
            @thread safe
        """
        def load():
            artists = Lp().artists.get_local()
            compilations = Lp().albums.get_compilation_ids()
            return (artists, compilations)

        def setup(artists, compilations):
            items = []
            items.append((Type.ALL, _("Synced albums")))
            if compilations:
                items.append((Type.COMPILATIONS, _("Compilations")))
                items.append((Type.SEPARATOR, ""))
            items += artists
            selection_list.mark_as_artists(True)
            selection_list.populate(items)
        loader = Loader(target=load, view=selection_list,
                        on_finished=lambda r: setup(*r))
        loader.start()

    def __append_playlists(self, playlists, files_list=[]):
        """
            Append a playlist
            @param playlists as [(int, str)]
            @internal files_list
        """
        if playlists and not self.__stop:
            # Cache directory playlists
            if not files_list:
                try:
                    d = Gio.File.new_for_uri(self._uri)
                    infos = d.enumerate_children(
                                            "standard::name,standard::type",
                                            Gio.FileQueryInfoFlags.NONE,
                                            None)
                    for info in infos:
                        if info.get_file_type() != Gio.FileType.DIRECTORY:
                            f = infos.get_child(info)
                            if f.get_uri().endswith(".m3u"):
                                files_list.append(
                                          GLib.path_get_basename(f.get_path()))
                except:
                    pass
            playlist = playlists.pop(0)
            selected = playlist[1] + ".m3u" in files_list
            self.__model.append([selected, playlist[1], playlist[0]])
            GLib.idle_add(self.__append_playlists, playlists, files_list)

    def __append_albums(self, albums):
        """
            Append albums
            @param albums as [int]
        """
        if albums and not self.__stop:
            album = Album(albums.pop(0))
            synced = Lp().albums.get_synced(album.id)
            # Do not sync youtube albums
            if synced != Type.NONE:
                if album.artist_ids[0] == Type.COMPILATIONS:
                    name = GLib.markup_escape_text(album.name)
                else:
                    artists = ", ".join(album.artists)
                    name = "<b>%s</b> - %s" % (
                            GLib.markup_escape_text(artists),
                            GLib.markup_escape_text(album.name))
                self.__model.append([synced, name, album.id])
            GLib.idle_add(self.__append_albums, albums)

    def __populate_albums_playlist(self, album_id, toggle):
        """
            Populate hidden albums playlist
            @param album_id as int
            @param toggle as bool
            @warning commit on default sql cursor needed
        """
        if Lp().settings.get_value("sync-albums"):
            Lp().albums.set_synced(album_id, toggle)

    def __on_item_selected(self, selection_list):
        """
            Show album from artist
            @param selection list as SelectionList
        """
        if not selection_list.selected_ids:
            return
        if selection_list.selected_ids[0] == Type.COMPILATIONS:
            albums = Lp().albums.get_compilation_ids()
        elif selection_list.selected_ids[0] == Type.ALL:
            albums = Lp().albums.get_synced_ids()
        else:
            albums = Lp().albums.get_ids(selection_list.selected_ids)
        self.__model.clear()
        self.__append_albums(albums)

    def __on_column0_clicked(self, column):
        """
            Select/Unselect all playlists
            @param column as Gtk.TreeViewColumn
        """
        selected = False
        for item in self.__model:
            if item[0]:
                selected = True
        for item in self.__model:
            item[0] = not selected
            self.__populate_albums_playlist(item[2], item[0])
        with SqlCursor(Lp().db) as sql:
            sql.commit()

    def __on_item_toggled(self, view, path):
        """
            When item is toggled, set model
            @param widget as cell renderer
            @param path as str representation of Gtk.TreePath
        """
        iterator = self.__model.get_iter(path)
        toggle = not self.__model.get_value(iterator, 0)
        self.__model.set_value(iterator, 0, toggle)
        album_id = self.__model.get_value(iterator, 2)
        self.__populate_albums_playlist(album_id, toggle)
        with SqlCursor(Lp().db) as sql:
            sql.commit()
