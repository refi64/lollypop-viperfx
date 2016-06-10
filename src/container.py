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

from gi.repository import Gtk, Gio, GLib

from gettext import gettext as _

from lollypop.define import Lp, Type, SelectionMode
from lollypop.loader import Loader
from lollypop.selectionlist import SelectionList
from lollypop.view_container import ViewContainer
from lollypop.view_albums import AlbumsView
from lollypop.view_artist import ArtistView
from lollypop.view_radios import RadiosView
from lollypop.view_playlists import PlaylistsView
from lollypop.view_playlists import PlaylistsManageView, PlaylistEditView
from lollypop.view_device import DeviceView, DeviceLocked, DeviceMigration


# This is a multimedia device
class Device:
    id = None
    name = None
    uri = None


class Container:
    """
        Container for main view
    """
    def __init__(self):
        """
            Init container
        """
        self._pulse_timeout = None
        # Index will start at -VOLUMES
        self._devices = {}
        self._devices_index = Type.DEVICES
        self._show_genres = Lp().settings.get_value('show-genres')
        self._stack = ViewContainer(500)
        self._stack.show()

        self._setup_view()
        self._setup_scanner()

        (list_one_ids, list_two_ids) = self._get_saved_view_state()
        if list_one_ids and list_one_ids[0] != Type.NONE:
            self._list_one.select_ids(list_one_ids)
        if list_two_ids and list_two_ids[0] != Type.NONE:
            self._list_two.select_ids(list_two_ids)

        # Volume manager
        self._vm = Gio.VolumeMonitor.get()
        self._vm.connect('mount-added', self._on_mount_added)
        self._vm.connect('mount-removed', self._on_mount_removed)
        for mount in self._vm.get_mounts():
            self._add_device(mount, False)

        Lp().playlists.connect('playlists-changed',
                               self._update_playlists)

    def update_db(self):
        """
            Update db at startup only if needed
        """
        # Stop previous scan
        if Lp().scanner.is_locked():
            Lp().scanner.stop()
            GLib.timeout_add(250, self.update_db)
        else:
            # Something (device manager) is using progress bar
            if not self._progress.is_visible():
                Lp().scanner.update(self._progress)

    def get_genre_id(self):
        """
            Return current selected genre
            @return genre id as int
        """
        if self._show_genres:
            return self._list_one.get_selected_id()
        else:
            return None

    def init_list_one(self):
        """
            Init list one
        """
        self._update_list_one(None)

    def save_view_state(self):
        """
            Save view state
        """
        Lp().settings.set_value(
                            "list-one-ids",
                            GLib.Variant('ai',
                                         self._list_one.get_selected_ids()))
        Lp().settings.set_value(
                            "list-two-ids",
                            GLib.Variant('ai',
                                         self._list_two.get_selected_ids()))

    def show_playlist_manager(self, object_id, genre_ids,
                              artist_ids, is_album):
        """
            Show playlist manager for object_id
            Current view stay present in ViewContainer
            @param object id as int
            @param genre ids as [int]
            @param artist ids as [int]
            @param is_album as bool
        """
        current = self._stack.get_visible_child()
        view = PlaylistsManageView(object_id, genre_ids, artist_ids, is_album)
        view.populate()
        view.show()
        self._stack.add(view)
        self._stack.set_visible_child(view)
        current.disable_overlays()

    def show_playlist_editor(self, playlist_id):
        """
            Show playlist editor for playlist
            Current view stay present in ViewContainer
            @param playlist id as int
            @param playlist name as str
        """
        view = PlaylistEditView(playlist_id)
        view.show()
        self._stack.add(view)
        self._stack.set_visible_child(view)
        self._stack.clean_old_views(view)
        view.populate()

    def main_widget(self):
        """
            Get main widget
            @return Gtk.HPaned
        """
        return self._paned_main_list

    def get_view_width(self):
        """
            Return view width
            @return width as int
        """
        return self._stack.get_allocation().width

    def stop_all(self):
        """
            Stop current view from processing
        """
        view = self._stack.get_visible_child()
        if view is not None:
            self._stack.clean_old_views(None)

    def show_genres(self, show):
        """
            Show/Hide genres
            @param bool
        """
        self._show_genres = show
        self._list_one.clear()
        self._list_two.clear()
        self._list_two.hide()
        self._update_list_one(None)
        self._list_one.select_ids([Type.POPULARS])

    def destroy_current_view(self):
        """
            Destroy current view
        """
        view = self._stack.get_visible_child()
        for child in self._stack.get_children():
            if child != view:
                self._stack.set_visible_child(child)
                self._stack.clean_old_views(child)
                break

    def disable_overlays(self):
        """
            Disable overlays
        """
        view = self._stack.get_visible_child()
        if view:
            view.disable_overlays()

    def update_view(self):
        """
            Update current view
        """
        view = self._stack.get_visible_child()
        if view:
            view.update_children()

    def reload_view(self):
        """
            Reload current view
        """
        values_two = self._list_two.get_selected_ids()
        values_one = self._list_one.get_selected_ids()
        if not values_one:
            values_one = [Type.POPULARS]
        self._list_one.select_ids([])
        self._list_one.clear()
        self._update_list_one(None)
        self._list_one.select_ids(values_one)
        if self._list_two.is_visible():
            self._list_two.select_ids([])
            self._list_two.clear()
            self._update_list_two(None)
            self._list_two.select_ids(values_two)

    def pulse(self, pulse):
        """
            Make progress bar visible/pulse if pulse is True
            @param pulse as bool
        """
        if pulse and not self._progress.is_visible():
            self._progress.show()
            if self._pulse_timeout is None:
                self._pulse_timeout = GLib.timeout_add(500, self._pulse)
        else:
            if self._pulse_timeout is not None:
                GLib.source_remove(self._pulse_timeout)
                self._pulse_timeout = None
                self._progress.hide()

    def on_scan_finished(self, scanner):
        """
            Mark force scan as False, update lists
            @param scanner as CollectionScanner
        """
        self._update_lists(scanner)

    def add_fake_phone(self):
        """
            Emulate an Android Phone
        """
        self._devices_index -= 1
        dev = Device()
        dev.id = self._devices_index
        dev.name = "Android phone"
        dev.uri = "file:///tmp/android/"
        d = Gio.File.new_for_uri(dev.uri+"Internal Memory")
        if not d.query_exists(None):
            d.make_directory_with_parents(None)
        d = Gio.File.new_for_uri(dev.uri+"SD Card")
        if not d.query_exists(None):
            d.make_directory_with_parents(None)
        self._devices[self._devices_index] = dev

############
# Private  #
############
    def _pulse(self):
        """
            Make progress bar pulse while visible
            @param pulse as bool
        """
        if self._progress.is_visible() and not Lp().scanner.is_locked():
            self._progress.pulse()
            return True
        else:
            self._progress.set_fraction(0.0)
            return False

    def _setup_view(self):
        """
            Setup window main view:
                - genre list
                - artist list
                - main view as artist view or album view
        """
        self._paned_main_list = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        self._paned_list_view = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        vgrid = Gtk.Grid()
        vgrid.set_orientation(Gtk.Orientation.VERTICAL)

        self._list_one = SelectionList(SelectionMode.LIMITED)
        self._list_one.show()
        self._list_two = SelectionList(SelectionMode.NORMAL)
        self._list_one.connect('item-selected', self._on_list_one_selected)
        self._list_one.connect('populated', self._on_list_populated)
        self._list_two.connect('item-selected', self._on_list_two_selected)

        self._progress = Gtk.ProgressBar()
        self._progress.set_property('hexpand', True)

        vgrid.add(self._stack)
        vgrid.add(self._progress)
        vgrid.show()

        self._paned_list_view.add1(self._list_two)
        self._paned_list_view.add2(vgrid)
        self._paned_main_list.add1(self._list_one)
        self._paned_main_list.add2(self._paned_list_view)
        self._paned_main_list.set_position(
            Lp().settings.get_value('paned-mainlist-width').get_int32())
        self._paned_list_view.set_position(
            Lp().settings.get_value('paned-listview-width').get_int32())
        self._paned_main_list.show()
        self._paned_list_view.show()

    def _get_saved_view_state(self):
        """
            Get save view state
            @return (list one id, list two id)
        """
        list_one_ids = [Type.POPULARS]
        list_two_ids = [Type.NONE]
        if Lp().settings.get_value('save-state'):
            list_one_ids = []
            list_two_ids = []
            ids = Lp().settings.get_value('list-one-ids')
            for i in ids:
                if isinstance(i, int):
                    list_one_ids.append(i)
            ids = Lp().settings.get_value('list-two-ids')
            for i in ids:
                if isinstance(i, int):
                    list_two_ids.append(i)
        return (list_one_ids, list_two_ids)

    def _add_genre(self, scanner, genre_id):
        """
            Add genre to genre list
            @param scanner as CollectionScanner
            @param genre id as int
        """
        if self._show_genres:
            genre_name = Lp().genres.get_name(genre_id)
            self._list_one.add_value((genre_id, genre_name))

    def _add_artist(self, scanner, artist_id, album_id):
        """
            Add artist to artist list
            @param scanner as CollectionScanner
            @param artist id as int
            @param album id as int
        """
        artist_name = Lp().artists.get_name(artist_id)
        if self._show_genres:
            genre_ids = Lp().albums.get_genre_ids(album_id)
            genre_ids.append(Type.ALL)
            for i in self._list_one.get_selected_ids():
                if i in genre_ids:
                    self._list_two.add_value((artist_id, artist_name))
        else:
            self._list_one.add_value((artist_id, artist_name))

    def _setup_scanner(self):
        """
            Run collection update if needed
            @return True if hard scan is running
        """
        Lp().scanner.connect('scan-finished', self.on_scan_finished)
        Lp().scanner.connect('genre-added', self._add_genre)
        Lp().scanner.connect('artist-added', self._add_artist)

    def _update_playlists(self, playlists, playlist_id):
        """
            Update playlists in second list
            @param playlists as Playlists
            @param playlist_id as int
        """
        ids = self._list_one.get_selected_ids()
        if ids and ids[0] == Type.PLAYLISTS:
            if Lp().playlists.exists(playlist_id):
                self._list_two.update_value(playlist_id,
                                            Lp().playlists.get_name(
                                                                  playlist_id))
            else:
                self._list_two.remove(playlist_id)

    def _update_lists(self, updater=None):
        """
            Update lists
            @param updater as GObject
        """
        self._update_list_one(updater)
        self._update_list_two(updater)

    def _update_list_one(self, updater):
        """
            Update list one
            @param updater as GObject
        """
        update = updater is not None
        if self._show_genres:
            self._setup_list_genres(self._list_one, update)
        else:
            self._setup_list_artists(self._list_one, [Type.ALL], update)

    def _update_list_two(self, updater):
        """
            Update list two
            @param updater as GObject
        """
        update = updater is not None
        ids = self._list_one.get_selected_ids()
        if ids and ids[0] == Type.PLAYLISTS:
            self._setup_list_playlists(update)
        elif self._show_genres and ids:
            self._setup_list_artists(self._list_two, ids, update)

    def _get_headers(self):
        """
            Return list one headers
        """
        items = []
        items.append((Type.POPULARS, _("Popular albums")))
        items.append((Type.RECENTS, _("Recently added albums")))
        items.append((Type.RANDOMS, _("Random albums")))
        items.append((Type.PLAYLISTS, _("Playlists")))
        items.append((Type.RADIOS, _("Radios")))
        if self._show_genres:
            items.append((Type.ALL, _("All artists")))
        else:
            items.append((Type.ALL, _("All albums")))
        return items

    def _setup_list_genres(self, selection_list, update):
        """
            Setup list for genres
            @param list as SelectionList
            @param update as bool, if True, just update entries
            @thread safe
        """
        def load():
            genres = Lp().genres.get()
            return genres

        def setup(genres):
            items = self._get_headers()
            items.append((Type.SEPARATOR, ''))
            items += genres
            selection_list.mark_as_artists(False)
            if update:
                selection_list.update_values(items)
            else:
                selection_list.populate(items)

        loader = Loader(target=load, view=selection_list, on_finished=setup)
        loader.start()

    def _setup_list_artists(self, selection_list, genre_ids, update):
        """
            Setup list for artists
            @param list as SelectionList
            @param genre ids as [int]
            @param update as bool, if True, just update entries
            @thread safe
        """
        def load():
            artists = Lp().artists.get(genre_ids)
            compilations = Lp().albums.get_compilations(genre_ids)
            return (artists, compilations)

        def setup(artists, compilations):
            if selection_list == self._list_one:
                items = self._get_headers()
                if not compilations:
                    items.append((Type.SEPARATOR, ''))
            else:
                items = []
            if compilations:
                items.append((Type.COMPILATIONS, _("Compilations")))
                items.append((Type.SEPARATOR, ''))
            items += artists
            selection_list.mark_as_artists(True)
            if update:
                selection_list.update_values(items)
            else:
                selection_list.populate(items)

        if selection_list == self._list_one:
            if self._list_two.is_visible():
                self._list_two.hide()
            self._list_two_restore = Type.NONE
        loader = Loader(target=load, view=selection_list,
                        on_finished=lambda r: setup(*r))
        loader.start()

    def _setup_list_playlists(self, update):
        """
            Setup list for playlists
            @param update as bool
            @thread safe
        """
        playlists = [(Type.LOVED, Lp().playlists._LOVED)]
        playlists.append((Type.POPULARS, _("Popular tracks")))
        playlists.append((Type.RECENTS, _("Recently played")))
        playlists.append((Type.NEVER, _("Never played")))
        playlists.append((Type.RANDOMS, _("Random tracks")))
        playlists.append((Type.SEPARATOR, ''))
        playlists += Lp().playlists.get()
        if update:
            self._list_two.update_values(playlists)
        else:
            self._list_two.mark_as_artists(False)
            self._list_two.populate(playlists)

    def _update_view_device(self, device_id):
        """
            Update current view with device view,
            Use existing view if available
            @param device id as int
        """
        device = self._devices[device_id]
        child = self._stack.get_child_by_name(device.uri)
        if child is None:
            files = DeviceView.get_files(device.uri)
            if files or device.uri.startswith("file:"):
                for f in files:
                    if DeviceView.exists_old_sync(device.uri+f):
                        child = DeviceMigration()
                        self._stack.add(child)
                if child is None:
                    child = DeviceView(device, self._progress)
                    self._stack.add_named(child, device.uri)
            else:
                child = DeviceLocked()
                self._stack.add(child)
            child.show()
        child.populate()
        self._stack.set_visible_child(child)
        self._stack.clean_old_views(child)

    def _update_view_artists(self, genre_ids, artist_ids):
        """
            Update current view with artists view
            @param genre ids as [int]
            @param artist ids as [int]
        """
        def load():
            if genre_ids and genre_ids[0] == Type.ALL:
                albums = Lp().albums.get_ids(artist_ids, [])
            else:
                albums = []
                if artist_ids and artist_ids[0] == Type.COMPILATIONS:
                    albums += Lp().albums.get_compilations(genre_ids)
                albums += Lp().albums.get_ids(artist_ids, genre_ids)
            return albums

        view = ArtistView(artist_ids, genre_ids)
        loader = Loader(target=load, view=view)
        loader.start()
        view.show()
        self._stack.add(view)
        self._stack.set_visible_child(view)
        self._stack.clean_old_views(view)

    def _update_view_albums(self, genre_ids, artist_ids):
        """
            Update current view with albums view
            @param genre ids as [int]
            @param is compilation as bool
        """
        def load():
            albums = []
            is_compilation = artist_ids and artist_ids[0] == Type.COMPILATIONS
            if genre_ids and genre_ids[0] == Type.ALL:
                if is_compilation or\
                        Lp().settings.get_value('show-compilations'):
                    albums = Lp().albums.get_compilations()
                if not is_compilation:
                    albums += Lp().albums.get_ids()
            elif genre_ids and genre_ids[0] == Type.POPULARS:
                albums = Lp().albums.get_populars()
            elif genre_ids and genre_ids[0] == Type.RECENTS:
                albums = Lp().albums.get_recents()
            elif genre_ids and genre_ids[0] == Type.RANDOMS:
                albums = Lp().albums.get_randoms()
            else:
                if is_compilation or\
                        Lp().settings.get_value('show-compilations'):
                    albums = Lp().albums.get_compilations(genre_ids)
                if not is_compilation:
                    albums += Lp().albums.get_ids([], genre_ids)
            return albums

        view = AlbumsView(genre_ids, artist_ids)
        loader = Loader(target=load, view=view)
        loader.start()
        view.show()
        self._stack.add(view)
        self._stack.set_visible_child(view)
        self._stack.clean_old_views(view)

    def _update_view_playlists(self, playlist_ids=[]):
        """
            Update current view with playlist view
            @param playlist ids as [int]
        """
        def load():
            track_ids = []
            for playlist_id in playlist_ids:
                if playlist_id == Type.POPULARS:
                    tracks = Lp().tracks.get_populars()
                elif playlist_id == Type.RECENTS:
                    tracks = Lp().tracks.get_recently_listened_to()
                elif playlist_id == Type.NEVER:
                    tracks = Lp().tracks.get_never_listened_to()
                elif playlist_id == Type.RANDOMS:
                    tracks = Lp().tracks.get_randoms()
                else:
                    tracks = Lp().playlists.get_track_ids(playlist_id)
                for track_id in tracks:
                    if track_id not in track_ids:
                        track_ids.append(track_id)
            return track_ids

        view = None
        if playlist_ids:
            view = PlaylistsView(playlist_ids)
            loader = Loader(target=load, view=view)
            loader.start()
        else:
            view = PlaylistsManageView(Type.NONE, [], [], False)
            view.populate()
        view.show()
        self._stack.add(view)
        self._stack.set_visible_child(view)
        self._stack.clean_old_views(view)

    def _update_view_radios(self):
        """
            Update current view with radios view
        """
        view = RadiosView()
        view.populate()
        view.show()
        self._stack.add(view)
        self._stack.set_visible_child(view)
        self._stack.clean_old_views(view)

    def _add_device(self, mount, show=False):
        """
            Add a device
            @param mount as Gio.Mount
            @param show as bool
        """
        if mount.get_volume() is None:
            return
        name = mount.get_name()
        uri = mount.get_default_location().get_uri()
        if uri is not None and (
                mount.can_eject() or uri.startswith('mtp')):
            self._devices_index -= 1
            dev = Device()
            dev.id = self._devices_index
            dev.name = name
            dev.uri = uri
            self._devices[self._devices_index] = dev
            if show:
                self._list_one.add_value((dev.id, dev.name))

    def _remove_device(self, mount):
        """
            Remove volume from device list
            @param mount as Gio.Mount
        """
        uri = mount.get_default_location().get_uri()
        for dev in self._devices.values():
            if dev.uri == uri:
                self._list_one.remove(dev.id)
                child = self._stack.get_child_by_name(uri)
                if child is not None:
                    child.destroy()
                del self._devices[dev.id]
            break

    def _on_list_one_selected(self, selection_list):
        """
            Update view based on selected object
            @param list as SelectionList
        """
        selected_ids = self._list_one.get_selected_ids()
        if not selected_ids:
            return
        self._list_two.clear()
        if selected_ids[0] == Type.PLAYLISTS:
            self._list_two.show()
            if not self._list_two.will_be_selected():
                self._update_view_playlists()
            self._setup_list_playlists(False)
        elif Type.DEVICES - 999 < selected_ids[0] < Type.DEVICES:
            self._list_two.hide()
            if not self._list_two.will_be_selected():
                self._update_view_device(selected_ids[0])
        elif selected_ids[0] in [Type.POPULARS,
                                 Type.RECENTS,
                                 Type.RANDOMS]:
            self._list_two.hide()
            self._update_view_albums(selected_ids, [])
        elif selected_ids[0] == Type.RADIOS:
            self._list_two.hide()
            self._update_view_radios()
        elif selection_list.is_marked_as_artists():
            self._list_two.hide()
            if selected_ids[0] == Type.ALL:
                self._update_view_albums(selected_ids, [])
            elif selected_ids[0] == Type.COMPILATIONS:
                self._update_view_albums([], selected_ids)
            else:
                self._update_view_artists([], selected_ids)
        else:
            self._setup_list_artists(self._list_two, selected_ids, False)
            self._list_two.show()
            if not self._list_two.will_be_selected():
                self._update_view_albums(selected_ids, [])

    def _on_list_populated(self, selection_list):
        """
            Add device to list one and update db
            @param selection list as SelectionList
        """
        for dev in self._devices.values():
            self._list_one.add_value((dev.id, dev.name))

    def _on_list_two_selected(self, selection_list):
        """
            Update view based on selected object
            @param list as SelectionList
        """
        genre_ids = self._list_one.get_selected_ids()
        selected_ids = self._list_two.get_selected_ids()
        if not selected_ids or not genre_ids:
            return
        if genre_ids[0] == Type.PLAYLISTS:
            self._update_view_playlists(selected_ids)
        elif selected_ids[0] == Type.COMPILATIONS:
            self._update_view_albums(genre_ids, selected_ids)
        else:
            self._update_view_artists(genre_ids, selected_ids)

    def _on_mount_added(self, vm, mount):
        """
            On volume mounter
            @param vm as Gio.VolumeMonitor
            @param mount as Gio.Mount
        """
        self._add_device(mount, True)

    def _on_mount_removed(self, vm, mount):
        """
            On volume removed, clean selection list
            @param vm as Gio.VolumeMonitor
            @param mount as Gio.Mount
        """
        self._remove_device(mount)
