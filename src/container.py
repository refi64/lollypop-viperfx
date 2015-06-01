#!/usr/bin/python
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

from gi.repository import Gtk, Gio, GLib

from _thread import start_new_thread
from gettext import gettext as _

from lollypop.define import Lp, Type
from lollypop.selectionlist import SelectionList
from lollypop.playlists import PlaylistsManager
from lollypop.view_container import ViewContainer
from lollypop.view_albums import AlbumsView, ArtistView
from lollypop.view_radios import RadiosView
from lollypop.view_playlists import PlaylistsView
from lollypop.view_playlists import PlaylistsManageView, PlaylistEditView
from lollypop.view_device import DeviceView


# This is a multimedia device
class Device:
    id = None
    name = None
    uri = None
    view = None


# Container for main window child
class Container:
    def __init__(self):

        # Try to update db on start, will be done after list one populating
        # finished
        self._need_to_update_db = Lp.settings.get_value('auto-update') or\
            Lp.tracks.is_empty()
        # Index will start at -VOLUMES
        self._devices = {}
        self._devices_index = Type.DEVICES
        self._show_genres = Lp.settings.get_value('show-genres')
        self._stack = ViewContainer(500)
        self._stack.show()

        self._setup_view()
        self._setup_scanner()

        (list_one_id, list_two_id) = self._get_saved_view_state()
        self._list_one.select_id(list_one_id)
        self._list_two.select_id(list_two_id)

        # Volume manager
        self._vm = Gio.VolumeMonitor.get()
        self._vm.connect('mount-added', self._on_mount_added)
        self._vm.connect('mount-removed', self._on_mount_removed)

        Lp.playlists.connect('playlists-changed',
                             self._update_lists)

    """
        Update db at startup only if needed
    """
    def update_db(self):
        # Stop previous scan
        if Lp.scanner.is_locked():
            Lp.scanner.stop()
            GLib.timeout_add(250, self.update_db)
        else:
            # Something (device manager) is using progress bar
            progress = None
            if not self._progress.is_visible():
                progress = self._progress
            Lp.scanner.update(progress)

    """
        Return current selected genre
        @return genre id as int
    """
    def get_genre_id(self):
        if self._show_genres:
            return self._list_one.get_selected_id()
        else:
            return None
    """
        Init list one
    """
    def init_list_one(self):
        self._update_list_one(None)

    """
        Save view state
    """
    def save_view_state(self):
        Lp.settings.set_value("list-one",
                              GLib.Variant('i',
                                           self._list_one.get_selected_id()))
        Lp.settings.set_value("list-two",
                              GLib.Variant('i',
                                           self._list_two.get_selected_id()))

    """
        Show playlist manager for object_id
        Current view stay present in ViewContainer
        @param object id as int
        @param genre id as int
        @param is_album as bool
    """
    def show_playlist_manager(self, object_id, genre_id, is_album):
        view = PlaylistsManageView(object_id, genre_id, is_album,
                                   self._stack.get_allocated_width()/2)
        view.show()
        self._stack.add(view)
        self._stack.set_visible_child(view)
        start_new_thread(view.populate, ())

    """
        Show playlist editor for playlist
        Current view stay present in ViewContainer
        @param playlist name as str
    """
    def show_playlist_editor(self, playlist_name):
        view = PlaylistEditView(playlist_name,
                                self._stack.get_allocated_width()/2)
        view.show()
        self._stack.add(view)
        self._stack.set_visible_child(view)
        start_new_thread(view.populate, ())

    """
        Get main widget
        @return Gtk.HPaned
    """
    def main_widget(self):
        return self._paned_main_list

    """
        Stop current view from processing
    """
    def stop_all(self):
        view = self._stack.get_visible_child()
        if view is not None:
            self._stack.clean_old_views(None)

    """
        Show/Hide genres
        @param bool
    """
    def show_genres(self, show):
        self._show_genres = show
        self._list_one.clear()
        self._update_list_one(None)

    """
        Destroy current view
    """
    def destroy_current_view(self):
        view = self._stack.get_visible_child()
        for child in self._stack.get_children():
            if child != view:
                self._stack.set_visible_child(child)
                self._stack.clean_old_views(child)
                break

    """
        Update current view
    """
    def update_view(self):
        view = self._stack.get_visible_child()
        if view:
            start_new_thread(view.update_covers, ())

    """
        Mark force scan as False, update lists
        @param scanner as CollectionScanner
    """
    def on_scan_finished(self, scanner):
        if self._list_one.is_populating() or self._list_two.is_populating():
            GLib.timeout_add(500, self.on_scan_finished, scanner)
        else:
            self._update_lists(scanner)
############
# Private  #
############
    """
        Setup window main view:
            - genre list
            - artist list
            - main view as artist view or album view
    """
    def _setup_view(self):
        self._paned_main_list = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        self._paned_list_view = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        vgrid = Gtk.Grid()
        vgrid.set_orientation(Gtk.Orientation.VERTICAL)

        self._list_one = SelectionList()
        self._list_one.show()
        self._list_two = SelectionList()
        self._list_one.connect('item-selected', self._on_list_one_selected)
        self._list_one.connect('populated', self._on_list_populated)
        self._list_two.connect('item-selected', self._on_list_two_selected)

        self._progress = Gtk.ProgressBar()
        self._progress.set_property('hexpand', True)

        vgrid.add(self._stack)
        vgrid.add(self._progress)
        vgrid.show()

        separator = Gtk.Separator()
        separator.show()
        self._paned_list_view.add1(self._list_two)
        self._paned_list_view.add2(vgrid)
        self._paned_main_list.add1(self._list_one)
        self._paned_main_list.add2(self._paned_list_view)
        self._paned_main_list.set_position(
            Lp.settings.get_value('paned-mainlist-width').get_int32())
        self._paned_list_view.set_position(
            Lp.settings.get_value('paned-listview-width').get_int32())
        self._paned_main_list.show()
        self._paned_list_view.show()

    """
        Get save view state
        @return (list one id, list two id)
    """
    def _get_saved_view_state(self):
        list_one_id = Type.POPULARS
        list_two_id = Type.NONE
        if Lp.settings.get_value('save-state'):
            position = Lp.settings.get_value('list-one').get_int32()
            if position != -1:
                list_one_id = position
            position = Lp.settings.get_value('list-two').get_int32()
            if position != -1:
                list_two_id = position

        return (list_one_id, list_two_id)

    """
        Add genre to genre list
        @param scanner as CollectionScanner
        @param genre id as int
    """
    def _add_genre(self, scanner, genre_id):
        if self._show_genres:
            genre_name = Lp.genres.get_name(genre_id)
            self._list_one.add_value((genre_id, genre_name))

    """
        Add artist to artist list
        @param scanner as CollectionScanner
        @param artist id as int
        @param album id as int
    """
    def _add_artist(self, scanner, artist_id, album_id):
        artist_name = Lp.artists.get_name(artist_id)
        if self._show_genres:
            genre_ids = Lp.albums.get_genre_ids(album_id)
            genre_ids.append(Type.ALL)
            if self._list_one.get_selected_id() in genre_ids:
                self._list_two.add_value((artist_id, artist_name))
        else:
            self._list_one.add_value((artist_id, artist_name))

    """
        Run collection update if needed
        @return True if hard scan is running
    """
    def _setup_scanner(self):
        Lp.scanner.connect('scan-finished', self.on_scan_finished)
        Lp.scanner.connect('genre-update', self._add_genre)
        Lp.scanner.connect('artist-update', self._add_artist)

    """
        Update lists
        @param updater as GObject
    """
    def _update_lists(self, updater=None):
        self._update_list_one(updater)
        self._update_list_two(updater)

    """
        Update list one
        @param updater as GObject
    """
    def _update_list_one(self, updater):
        update = updater is not None
        # Do not update if updater is PlaylistsManager
        if not isinstance(updater, PlaylistsManager):
            if self._show_genres:
                self._setup_list_genres(self._list_one, update)
            else:
                self._setup_list_artists(self._list_one,
                                         Type.ALL,
                                         update)

    """
        Update list two
        @param updater as GObject
    """
    def _update_list_two(self, updater):
        update = updater is not None
        object_id = self._list_one.get_selected_id()
        if object_id == Type.PLAYLISTS:
            start_new_thread(self._setup_list_playlists, (update,))
        elif self._show_genres and object_id != Type.NONE:
            self._setup_list_artists(self._list_two, object_id, update)

    """
        Return list one headers
    """
    def _get_headers(self):
        items = []
        items.append((Type.POPULARS, _("Popular albums")))
        items.append((Type.RECENTS, _("Recent albums")))
        items.append((Type.RANDOMS, _("Random albums")))
        items.append((Type.PLAYLISTS, _("Playlists")))
        items.append((Type.RADIOS, _("Radios")))
        if self._show_genres:
            items.append((Type.ALL, _("All artists")))
        else:
            items.append((Type.ALL, _("All albums")))
        return items

    """
        Setup list for genres
        @param list as SelectionList
        @param update as bool, if True, just update entries
        @thread safe
    """
    def _setup_list_genres(self, selection_list, update):
        sql = Lp.db.get_cursor()
        selection_list.mark_as_artists(False)
        items = self._get_headers()
        items.append((Type.SEPARATOR, ''))
        items += Lp.genres.get(sql)
        if update:
            selection_list.update_values(items)
        else:
            selection_list.populate(items)
        sql.close()

    """
        Hide list two base on current artist list
    """
    def _pre_setup_list_artists(self, selection_list):
        if selection_list == self._list_one:
            if self._list_two.is_visible():
                self._list_two.hide()
            self._list_two_restore = Type.NONE

    """
        Setup list for artists
        @param list as SelectionList
        @param update as bool, if True, just update entries
        @thread safe
    """
    def _setup_list_artists(self, selection_list, genre_id, update):
        GLib.idle_add(self._pre_setup_list_artists, selection_list)
        sql = Lp.db.get_cursor()
        items = []
        selection_list.mark_as_artists(True)
        if selection_list == self._list_one:
            items = self._get_headers()
        if Lp.albums.get_compilations(genre_id, sql):
            items.append((Type.COMPILATIONS, _("Compilations")))
        items.append((Type.SEPARATOR, ''))
        items += Lp.artists.get(genre_id, sql)

        if update:
            selection_list.update_values(items)
        else:
            selection_list.populate(items)
        sql.close()

    """
        Setup list for playlists
        @param update as bool
        @thread safe
    """
    def _setup_list_playlists(self, update):
        playlists = Lp.playlists.get()
        if update:
            self._list_two.update_values(playlists)
        else:
            self._list_two.mark_as_artists(False)
            self._list_two.populate(playlists)

    """
        Update current view with device view,
        Use existing view if available
        @param device id as int
    """
    def _update_view_device(self, device_id):
        device = self._devices[device_id]

        if device and device.view:
            view = device.view
        else:
            view = DeviceView(device, self._progress,
                              self._stack.get_allocated_width()/2)
            device.view = view
            view.show()
            start_new_thread(view.populate, ())
        self._stack.add(view)
        self._stack.set_visible_child(view)
        self._stack.clean_old_views(view)

    """
        Update current view with artists view
        @param artist id as int
        @param genre id as int
    """
    def _update_view_artists(self, artist_id, genre_id):
        view = ArtistView(artist_id, genre_id)
        self._stack.add(view)
        view.show()
        start_new_thread(view.populate, ())
        self._stack.set_visible_child(view)
        self._stack.clean_old_views(view)

    """
        Update current view with albums view
        @param genre id as int
        @param is compilation as bool
    """
    def _update_view_albums(self, genre_id, is_compilation=False):
        view = AlbumsView(genre_id, is_compilation)
        self._stack.add(view)
        view.show()
        start_new_thread(view.populate, ())
        self._stack.set_visible_child(view)
        self._stack.clean_old_views(view)

    """
        Update current view with playlist view
        @param playlist id as int
    """
    def _update_view_playlists(self, playlist_id):
        view = None
        if playlist_id is not None:
            for (p_id, p_str) in Lp.playlists.get():
                if p_id == playlist_id:
                    view = PlaylistsView(p_str, self._stack)
                    break
        else:
            view = PlaylistsManageView(-1, None, False,
                                       self._stack.get_allocated_width()/2)
        if view:
            view.show()
            self._stack.add(view)
            self._stack.set_visible_child(view)
            start_new_thread(view.populate, ())
            self._stack.clean_old_views(view)

    """
        Update current view with radios view
    """
    def _update_view_radios(self):
        view = RadiosView()
        self._stack.add(view)
        view.show()
        start_new_thread(view.populate, ())
        self._stack.set_visible_child(view)
        self._stack.clean_old_views(view)

    """
        Add volume to device list
        @param volume as Gio.Volume
    """
    def _add_device(self, volume):
        if volume is None:
            return
        root = volume.get_activation_root()
        if root is None:
            return

        uri = root.get_uri()
        # Just to be sure
        if uri is not None and len(uri) > 1 and uri[-1:] != '/':
            uri += '/'
        if uri is not None and uri.find('mtp:') != -1:
            self._devices_index -= 1
            dev = Device()
            dev.id = self._devices_index
            dev.name = volume.get_name()
            dev.uri = uri
            self._devices[self._devices_index] = dev
            if not self._list_one.is_populating():
                self._list_one.add_value((dev.id, dev.name))

    """
        Remove volume from device list
        @param volume as Gio.Volume
    """
    def _remove_device(self, volume):
        if volume is None:
            return
        root = volume.get_activation_root()
        if root is None:
            return

        uri = root.get_uri()
        for dev in self._devices.values():
            if dev.uri == uri:
                self._list_one.remove(dev.id)
                device = self._devices[dev.id]
                if device.view:
                    device.view.destroy()
                del self._devices[dev.id]
            break

    """
        Update view based on selected object
        @param list as SelectionList
        @param selected id as int
    """
    def _on_list_one_selected(self, selection_list, selected_id):
        if selected_id == Type.PLAYLISTS:
            start_new_thread(self._setup_list_playlists, (False,))
            self._list_two.clear()
            self._list_two.show()
            if not self._list_two.will_be_selected():
                self._update_view_playlists(None)
        elif selected_id < Type.DEVICES:
            self._list_two.hide()
            if not self._list_two.will_be_selected():
                self._update_view_device(selected_id)
        elif selected_id in [Type.POPULARS,
                             Type.RECENTS,
                             Type.RANDOMS]:
            self._list_two.hide()
            self._update_view_albums(selected_id)
        elif selected_id == Type.RADIOS:
            self._list_two.hide()
            self._update_view_radios()
        elif selection_list.is_marked_as_artists():
            self._list_two.hide()
            if selected_id == Type.ALL:
                self._update_view_albums(selected_id)
            elif selected_id == Type.COMPILATIONS:
                self._update_view_albums(None, True)
            else:
                self._update_view_artists(selected_id, None)
        else:
            self._list_two.clear()
            start_new_thread(self._setup_list_artists,
                             (self._list_two, selected_id, False))
            self._list_two.show()
            if not self._list_two.will_be_selected():
                self._update_view_albums(selected_id, False)

    """
        Add device to list one and update db
        @param selection list as SelectionList
    """
    def _on_list_populated(self, selection_list):
        if self._list_one.is_populating() or\
           self._list_two.is_populating():
            GLib.timeout_add(500, self._on_list_populated, selection_list)
            return

        for dev in self._devices.values():
            self._list_one.add_value((dev.id, dev.name))
        if self._need_to_update_db:
            self._need_to_update_db = False
            self.update_db()

    """
        Update view based on selected object
        @param list as SelectionList
        @param selected id as int
    """
    def _on_list_two_selected(self, selection_list, selected_id):
        genre_id = self._list_one.get_selected_id()
        if genre_id == Type.PLAYLISTS:
            self._update_view_playlists(selected_id)
        elif selected_id == Type.COMPILATIONS:
            self._update_view_albums(genre_id, True)
        else:
            self._update_view_artists(selected_id, genre_id)

    """
        On volume mounter
        @param vm as Gio.VolumeMonitor
        @param mnt as Gio.Mount
    """
    def _on_mount_added(self, vm, mnt):
        self._add_device(mnt.get_volume())

    """
        On volume removed, clean selection list
        @param vm as Gio.VolumeMonitor
        @param mnt as Gio.Mount
    """
    def _on_mount_removed(self, vm, mnt):
        self._remove_device(mnt.get_volume())
