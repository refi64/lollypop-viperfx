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

from gi.repository import Gtk, Gio, GLib

from gettext import gettext as _
from urllib.parse import urlparse

from lollypop.define import Lp, Type
from lollypop.loader import Loader
from lollypop.selectionlist import SelectionList
from lollypop.view_container import ViewContainer
from lollypop.progressbar import ProgressBar


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
        self.__pulse_timeout = None
        # Index will start at -VOLUMES
        self.__devices = {}
        self.__devices_index = Type.DEVICES
        self.__show_genres = Lp().settings.get_value("show-genres")
        self.__stack = ViewContainer(500)
        self.__stack.show()

        self.__setup_view()
        self.__setup_scanner()

        (list_one_ids, list_two_ids) = self.__get_saved_view_state()
        if list_one_ids and list_one_ids[0] != Type.NONE:
            self.__list_one.select_ids(list_one_ids)
        if list_two_ids and list_two_ids[0] != Type.NONE:
            self.__list_two.select_ids(list_two_ids)

        # Volume manager
        self.__vm = Gio.VolumeMonitor.get()
        self.__vm.connect("mount-added", self.__on_mount_added)
        self.__vm.connect("mount-removed", self.__on_mount_removed)
        for mount in self.__vm.get_mounts():
            self.__add_device(mount, False)

        Lp().playlists.connect("playlists-changed",
                               self.__update_playlists)

    def update_db(self, *ignore):
        """
            Update db at startup only if needed
        """
        # Stop previous scan
        if Lp().scanner.is_locked():
            Lp().scanner.stop()
            GLib.timeout_add(250, self.update_db)
        else:
            # Allow user to disable network access before first load
            if Lp().tracks.count() == 0:
                self.__show_first_run()
            Lp().scanner.update()

    def get_genre_id(self):
        """
            Return current selected genre
            @return genre id as int
        """
        if self.__show_genres:
            return self.__list_one.get_selected_id()
        else:
            return None

    def init_list_one(self):
        """
            Init list one
        """
        self.__update_list_one(None)

    def save_view_state(self):
        """
            Save view state
        """
        Lp().settings.set_value(
                            "list-one-ids",
                            GLib.Variant("ai",
                                         self.__list_one.selected_ids))
        Lp().settings.set_value(
                            "list-two-ids",
                            GLib.Variant("ai",
                                         self.__list_two.selected_ids))

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
        from lollypop.view_playlists import PlaylistsManageView
        current = self.__stack.get_visible_child()
        view = PlaylistsManageView(object_id, genre_ids, artist_ids, is_album)
        view.populate()
        view.show()
        self.__stack.add(view)
        self.__stack.set_visible_child(view)
        current.disable_overlay()

    def show_playlist_editor(self, playlist_id):
        """
            Show playlist editor for playlist
            Current view stay present in ViewContainer
            @param playlist id as int
            @param playlist name as str
        """
        from lollypop.view_playlists import PlaylistEditView
        view = PlaylistEditView(playlist_id)
        view.show()
        self.__stack.add(view)
        self.__stack.set_visible_child(view)
        self.__stack.clean_old_views(view)
        view.populate()

    def get_view_width(self):
        """
            Return view width
            @return width as int
        """
        return self.__stack.get_allocation().width

    def stop_all(self):
        """
            Stop current view from processing
        """
        view = self.__stack.get_visible_child()
        if view is not None:
            self.__stack.clean_old_views(None)

    def show_genres(self, show):
        """
            Show/Hide genres
            @param bool
        """
        self.__show_genres = show
        self.__list_one.clear()
        self.__list_two.clear()
        self.__list_two.hide()
        self.__update_list_one(None)
        self.__list_one.select_ids([Type.POPULARS])

    def destroy_current_view(self):
        """
            Destroy current view
        """
        view = self.__stack.get_visible_child()
        for child in self.__stack.get_children():
            if child != view:
                self.__stack.set_visible_child(child)
                self.__stack.clean_old_views(child)
                break

    @property
    def view(self):
        """
            Disable overlays
        """
        return self.__stack.get_visible_child()

    @property
    def progress(self):
        """
            Progress bar
            @return ProgressBar
        """
        return self.__progress

    def add_remove_from(self, value, list_one, add):
        """
            Add or remove value to list
            @param value as (int, str)
            @param list one as bool
            @param add as bool
        """
        if list_one:
            l = self.__list_one
        else:
            l = self.__list_two
        if add:
            l.add_value(value)
        else:
            l.remove_value(value[0])

    def reload_view(self):
        """
            Reload current view
        """
        values_two = self.__list_two.selected_ids
        values_one = self.__list_one.selected_ids
        if not values_one:
            values_one = [Type.POPULARS]
        self.__list_one.select_ids([])
        self.__list_one.clear()
        self.__update_list_one(None)
        self.__list_one.select_ids(values_one)
        if self.__list_two.is_visible():
            self.__list_two.select_ids([])
            self.__list_two.clear()
            self.__update_list_two(None)
            self.__list_two.select_ids(values_two)

    def pulse(self, pulse):
        """
            Make progress bar visible/pulse if pulse is True
            @param pulse as bool
        """
        if pulse and not self.__progress.is_visible():
            self.__progress.show()
            if self.__pulse_timeout is None:
                self.__pulse_timeout = GLib.timeout_add(500, self.__pulse)
        else:
            if self.__pulse_timeout is not None:
                GLib.source_remove(self.__pulse_timeout)
                self.__pulse_timeout = None
                self.__progress.hide()

    def on_scan_finished(self, scanner):
        """
            Mark force scan as False, update lists
            @param scanner as CollectionScanner
        """
        self.__update_lists(scanner)

    def add_fake_phone(self):
        """
            Emulate an Android Phone
        """
        self.__devices_index -= 1
        dev = Device()
        dev.id = self.__devices_index
        dev.name = "Android phone"
        dev.uri = "file:///tmp/android/"
        d = Gio.File.new_for_uri(dev.uri+"Internal Memory")
        if not d.query_exists():
            d.make_directory_with_parents()
        d = Gio.File.new_for_uri(dev.uri+"SD Card")
        if not d.query_exists():
            d.make_directory_with_parents()
        self.__devices[self.__devices_index] = dev

    def show_artists_albums(self, artist_ids):
        """
            Show albums from artists
            @param artist id as int
        """
        GLib.idle_add(self.__list_one.select_ids, [])
        GLib.idle_add(self.__list_two.select_ids, [])
        if self.__show_genres:
            # Get artist genres
            genre_ids = []
            for artist_id in artist_ids:
                album_ids = Lp().artists.get_albums(artist_ids)
                for album_id in album_ids:
                    for genre_id in Lp().albums.get_genre_ids(album_id):
                        if genre_id not in genre_ids:
                            genre_ids.append(genre_id)
            # Select genres on list one
            GLib.idle_add(self.__list_one.select_ids, genre_ids)
            # Select artists on list two
            GLib.idle_add(self.__list_two.select_ids, artist_ids)
        else:
            # Select artists on list one
            GLib.idle_add(self.__list_one.select_ids, artist_ids)

##############
# PROTECTED  #
##############
    def _hide_pane(self):
        """
            Hide navigation pane
            Internally hide list one and list two
        """
        if self.__list_one.is_visible():
            self.__list_two.hide()
            self.__list_one.hide()
        else:
            self.__list_one.show()
            if self.__list_two.was_visible:
                self.__list_two.show()
        Lp().settings.set_value("show-navigation-list",
                                GLib.Variant("b",
                                             self.__list_one.is_visible()))

############
# PRIVATE  #
############
    def __pulse(self):
        """
            Make progress bar pulse while visible
            @param pulse as bool
        """
        if self.__progress.is_visible() and not Lp().scanner.is_locked():
            self.__progress.pulse()
            return True
        else:
            self.__progress.set_fraction(0.0, self)
            return False

    def __show_first_run(self):
        """
            Show first run view
        """
        from lollypop.view_first_run import FirstRunView
        self.__stop_current_view()
        view = FirstRunView()
        view.show()
        self.__stack.add(view)
        self.__stack.set_visible_child(view)
        self.__stack.clean_old_views(view)

    def __setup_view(self):
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

        self.__list_one = SelectionList()
        if Lp().settings.get_value("show-navigation-list"):
            self.__list_one.show()
        self.__list_two = SelectionList()
        self.__list_one.connect("item-selected", self.__on_list_one_selected)
        self.__list_one.connect("populated", self.__on_list_populated)
        self.__list_one.connect("pass-focus", self.__on_pass_focus)
        self.__list_two.connect("item-selected", self.__on_list_two_selected)
        self.__list_two.connect("pass-focus", self.__on_pass_focus)

        self.__progress = ProgressBar()
        self.__progress.set_property("hexpand", True)

        vgrid.add(self.__stack)
        vgrid.add(self.__progress)
        vgrid.show()

        self._paned_list_view.add1(self.__list_two)
        self._paned_list_view.add2(vgrid)
        self._paned_main_list.add1(self.__list_one)
        self._paned_main_list.add2(self._paned_list_view)
        self._paned_main_list.set_position(
            Lp().settings.get_value("paned-mainlist-width").get_int32())
        self._paned_list_view.set_position(
            Lp().settings.get_value("paned-listview-width").get_int32())
        self._paned_main_list.show()
        self._paned_list_view.show()

    def __get_saved_view_state(self):
        """
            Get save view state
            @return (list one id, list two id)
        """
        # Get list one ids (always)
        list_one_ids = []
        ids = Lp().settings.get_value("list-one-ids")
        for i in ids:
            if isinstance(i, int):
                list_one_ids.append(i)
        if not list_one_ids:
            list_one_ids = [Type.POPULARS]
        list_two_ids = [Type.NONE]
        # Get list two ids (only on save state)
        if Lp().settings.get_value("save-state"):
            list_two_ids = []
            ids = Lp().settings.get_value("list-two-ids")
            for i in ids:
                if isinstance(i, int):
                    list_two_ids.append(i)
        return (list_one_ids, list_two_ids)

    def __setup_scanner(self):
        """
            Run collection update if needed
            @return True if hard scan is running
        """
        Lp().scanner.connect("scan-finished", self.on_scan_finished)
        Lp().scanner.connect("genre-updated", self.__on_genre_updated)
        Lp().scanner.connect("artist-updated", self.__on_artist_updated)

    def __update_playlists(self, playlists, playlist_id):
        """
            Update playlists in second list
            @param playlists as Playlists
            @param playlist_id as int
        """
        ids = self.__list_one.selected_ids
        if ids and ids[0] == Type.PLAYLISTS:
            if Lp().playlists.exists(playlist_id):
                self.__list_two.update_value(playlist_id,
                                             Lp().playlists.get_name(
                                                                  playlist_id))
            else:
                self.__list_two.remove_value(playlist_id)

    def __update_lists(self, updater=None):
        """
            Update lists
            @param updater as GObject
        """
        self.__update_list_one(updater)
        self.__update_list_two(updater)

    def __update_list_one(self, updater):
        """
            Update list one
            @param updater as GObject
        """
        update = updater is not None
        if self.__show_genres:
            self.__update_list_genres(self.__list_one, update)
        else:
            self.__update_list_artists(self.__list_one, [Type.ALL], update)

    def __update_list_two(self, updater):
        """
            Update list two
            @param updater as GObject
        """
        update = updater is not None
        ids = self.__list_one.selected_ids
        if ids and ids[0] == Type.PLAYLISTS:
            self.__update_list_playlists(update)
        elif self.__show_genres and ids:
            self.__update_list_artists(self.__list_two, ids, update)

    def __update_list_genres(self, selection_list, update):
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
            items = selection_list.get_headers()
            items.append((Type.SEPARATOR, ""))
            items += genres
            selection_list.mark_as_artists(False)
            if update:
                selection_list.update_values(items)
            else:
                selection_list.populate(items)

        loader = Loader(target=load, view=selection_list, on_finished=setup)
        loader.start()

    def __update_list_artists(self, selection_list, genre_ids, update):
        """
            Setup list for artists
            @param list as SelectionList
            @param genre ids as [int]
            @param update as bool, if True, just update entries
            @thread safe
        """
        def load():
            artists = Lp().artists.get(genre_ids)
            compilations = Lp().albums.get_compilation_ids(genre_ids)
            return (artists, compilations)

        def setup(artists, compilations):
            if selection_list == self.__list_one:
                items = selection_list.get_headers()
                if not compilations:
                    items.append((Type.SEPARATOR, ""))
            else:
                items = []
            if compilations:
                items.append((Type.COMPILATIONS, _("Compilations")))
                items.append((Type.SEPARATOR, ""))
            items += artists
            selection_list.mark_as_artists(True)
            if update:
                selection_list.update_values(items)
            else:
                selection_list.populate(items)

        if selection_list == self.__list_one:
            if self.__list_two.is_visible():
                self.__list_two.hide()
            self.__list_two_restore = Type.NONE
        loader = Loader(target=load, view=selection_list,
                        on_finished=lambda r: setup(*r))
        loader.start()

    def __update_list_playlists(self, update):
        """
            Setup list for playlists
            @param update as bool
            @thread safe
        """
        items = self.__list_two.get_pl_headers()
        items += Lp().playlists.get()
        if update:
            self.__list_two.update_values(items)
        else:
            self.__list_two.mark_as_artists(False)
            self.__list_two.populate(items)

    def __stop_current_view(self):
        """
            Stop current view
        """
        child = self.__stack.get_visible_child()
        if child is not None:
            if hasattr(child, "stop"):
                child.stop()

    def __update_view_device(self, device_id):
        """
            Update current view with device view,
            Use existing view if available
            @param device id as int
        """
        from lollypop.view_device import DeviceView, DeviceLocked
        self.__stop_current_view()
        device = self.__devices[device_id]
        child = self.__stack.get_child_by_name(device.uri)
        if child is None:
            files = DeviceView.get_files(device.uri)
            if files:
                if child is None:
                    child = DeviceView(device)
                    self.__stack.add_named(child, device.uri)
            else:
                child = DeviceLocked()
                self.__stack.add(child)
            child.show()
        child.populate()
        self.__stack.set_visible_child(child)
        self.__stack.clean_old_views(child)

    def __update_view_artists(self, genre_ids, artist_ids):
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
                    albums += Lp().albums.get_compilation_ids(genre_ids)
                albums += Lp().albums.get_ids(artist_ids, genre_ids)
            return albums
        from lollypop.view_artist import ArtistView
        self.__stop_current_view()
        view = ArtistView(artist_ids, genre_ids)
        loader = Loader(target=load, view=view)
        loader.start()
        view.show()
        self.__stack.add(view)
        self.__stack.set_visible_child(view)
        self.__stack.clean_old_views(view)

    def __update_view_albums(self, genre_ids, artist_ids):
        """
            Update current view with albums view
            @param genre ids as [int]
            @param is compilation as bool
        """
        def load():
            items = []
            is_compilation = artist_ids and artist_ids[0] == Type.COMPILATIONS
            if genre_ids and genre_ids[0] == Type.ALL:
                if is_compilation or\
                        Lp().settings.get_value("show-compilations"):
                    items = Lp().albums.get_compilation_ids()
                if not is_compilation:
                    items += Lp().albums.get_ids()
            elif genre_ids and genre_ids[0] == Type.POPULARS:
                items = Lp().albums.get_rated()
                count = 100 - len(items)
                for album in Lp().albums.get_populars(count):
                    if album not in items:
                        items.append(album)
            elif genre_ids and genre_ids[0] == Type.LOVED:
                items = Lp().albums.get_loves()
            elif genre_ids and genre_ids[0] == Type.RECENTS:
                items = Lp().albums.get_recents()
            elif genre_ids and genre_ids[0] == Type.NEVER:
                items = Lp().albums.get_never_listened_to()
            elif genre_ids and genre_ids[0] == Type.RANDOMS:
                items = Lp().albums.get_randoms()
            else:
                if is_compilation or\
                        Lp().settings.get_value("show-compilations"):
                    items = Lp().albums.get_compilation_ids(genre_ids)
                if not is_compilation:
                    items += Lp().albums.get_ids([], genre_ids)
            return items

        from lollypop.view_albums import AlbumsView
        self.__stop_current_view()
        view = AlbumsView(genre_ids, artist_ids)
        loader = Loader(target=load, view=view)
        loader.start()
        view.show()
        self.__stack.add(view)
        self.__stack.set_visible_child(view)
        self.__stack.clean_old_views(view)

    def __update_view_playlists(self, playlist_ids=[]):
        """
            Update current view with playlist view
            @param playlist ids as [int]
        """
        def load():
            track_ids = []
            for playlist_id in playlist_ids:
                if playlist_id == Type.POPULARS:
                    tracks = Lp().tracks.get_rated()
                    for track in Lp().tracks.get_populars():
                        tracks.append(track)
                elif playlist_id == Type.RECENTS:
                    tracks = Lp().tracks.get_recently_listened_to()
                elif playlist_id == Type.NEVER:
                    tracks = Lp().tracks.get_never_listened_to()
                elif playlist_id == Type.RANDOMS:
                    tracks = Lp().tracks.get_randoms()
                elif playlist_id == Type.LOVED:
                    tracks = Lp().playlists.get_track_ids_sorted(playlist_id)
                else:
                    tracks = Lp().playlists.get_track_ids(playlist_id)
                for track_id in tracks:
                    if track_id not in track_ids:
                        track_ids.append(track_id)
            return track_ids

        self.__stop_current_view()
        view = None
        if playlist_ids:
            from lollypop.view_playlists import PlaylistsView
            view = PlaylistsView(playlist_ids)
            loader = Loader(target=load, view=view)
            loader.start()
        else:
            from lollypop.view_playlists import PlaylistsManageView
            view = PlaylistsManageView(Type.NONE, [], [], False)
            view.populate()
        view.show()
        self.__stack.add(view)
        self.__stack.set_visible_child(view)
        self.__stack.clean_old_views(view)

    def __update_view_radios(self):
        """
            Update current view with radios view
        """
        from lollypop.view_radios import RadiosView
        self.__stop_current_view()
        view = RadiosView()
        view.populate()
        view.show()
        self.__stack.add(view)
        self.__stack.set_visible_child(view)
        self.__stack.clean_old_views(view)

    def __add_device(self, mount, show=False):
        """
            Add a device
            @param mount as Gio.Mount
            @param show as bool
        """
        if mount.get_volume() is None:
            return
        uri = mount.get_default_location().get_uri()
        if uri is None:
            return
        parsed = urlparse(uri)
        is_removable = parsed.scheme == "file" and mount.can_eject()
        if is_removable or parsed.scheme == "mtp":
            self.__devices_index -= 1
            dev = Device()
            dev.id = self.__devices_index
            dev.name = mount.get_name()
            dev.uri = uri
            self.__devices[self.__devices_index] = dev
            if show:
                self.__list_one.add_value((dev.id, dev.name))

    def __remove_device(self, mount):
        """
            Remove volume from device list
            @param mount as Gio.Mount
        """
        uri = mount.get_default_location().get_uri()
        for dev in self.__devices.values():
            if dev.uri == uri:
                self.__list_one.remove_value(dev.id)
                child = self.__stack.get_child_by_name(uri)
                if child is not None:
                    child.destroy()
                del self.__devices[dev.id]
            break

    def __on_list_one_selected(self, selection_list):
        """
            Update view based on selected object
            @param list as SelectionList
        """
        selected_ids = self.__list_one.selected_ids
        if not selected_ids:
            return
        self.__list_two.clear()
        if selected_ids[0] == Type.PLAYLISTS:
            if Lp().settings.get_value("show-navigation-list"):
                self.__list_two.show()
            if not self.__list_two.will_be_selected():
                self.__update_view_playlists()
            self.__update_list_playlists(False)
        elif Type.DEVICES - 999 < selected_ids[0] < Type.DEVICES:
            self.__list_two.hide()
            if not self.__list_two.will_be_selected():
                self.__update_view_device(selected_ids[0])
        elif selected_ids[0] in [Type.POPULARS,
                                 Type.LOVED,
                                 Type.RECENTS,
                                 Type.NEVER,
                                 Type.RANDOMS]:
            self.__list_two.hide()
            self.__update_view_albums(selected_ids, [])
        elif selected_ids[0] == Type.RADIOS:
            self.__list_two.hide()
            self.__update_view_radios()
        elif selection_list.is_marked_as_artists():
            self.__list_two.hide()
            if selected_ids[0] == Type.ALL:
                self.__update_view_albums(selected_ids, [])
            elif selected_ids[0] == Type.COMPILATIONS:
                self.__update_view_albums([], selected_ids)
            else:
                self.__update_view_artists([], selected_ids)
        else:
            self.__update_list_artists(self.__list_two, selected_ids, False)
            if Lp().settings.get_value("show-navigation-list"):
                self.__list_two.show()
            if not self.__list_two.will_be_selected():
                self.__update_view_albums(selected_ids, [])

    def __on_list_populated(self, selection_list):
        """
            Add device to list one and update db
            @param selection_list as SelectionList
        """
        for dev in self.__devices.values():
            self.__list_one.add_value((dev.id, dev.name))

    def __on_list_two_selected(self, selection_list):
        """
            Update view based on selected object
            @param selection_list as SelectionList
        """
        genre_ids = self.__list_one.selected_ids
        selected_ids = self.__list_two.selected_ids
        if not selected_ids or not genre_ids:
            return
        if genre_ids[0] == Type.PLAYLISTS:
            self.__update_view_playlists(selected_ids)
        elif selected_ids[0] == Type.COMPILATIONS:
            self.__update_view_albums(genre_ids, selected_ids)
        else:
            self.__update_view_artists(genre_ids, selected_ids)

    def __on_pass_focus(self, selection_list):
        """
            Pass focus to other list
            @param selection_list as SelectionList
        """
        if selection_list == self.__list_one:
            if self.__list_two.is_visible():
                self.__list_two.grab_focus()
        else:
            self.__list_one.grab_focus()

    def __on_genre_updated(self, scanner, genre_id, add):
        """
            Add genre to genre list
            @param scanner as CollectionScanner
            @param genre id as int
            @param add as bool
        """
        if self.__show_genres:
            if add:
                genre_name = Lp().genres.get_name(genre_id)
                self.__list_one.add_value((genre_id, genre_name))
            else:
                genre_ids = Lp().genres.get_ids()
                if genre_id not in genre_ids:
                    self.__list_one.remove_value(genre_id)

    def __on_artist_updated(self, scanner, artist_id, add):
        """
            Add artist to artist list
            @param scanner as CollectionScanner
            @param artist id as int
            @param add as bool
        """
        artist_name = Lp().artists.get_name(artist_id)
        sortname = Lp().artists.get_sortname(artist_id)
        if self.__show_genres:
            l = self.__list_two
            artist_ids = Lp().artists.get_ids(self.__list_one.selected_ids)
        else:
            l = self.__list_one
            artist_ids = Lp().artists.get_ids()
        if add:
            if artist_id in artist_ids:
                l.add_value((artist_id, artist_name, sortname))
        else:
            if artist_id not in artist_ids:
                l.remove_value(artist_id)

    def __on_mount_added(self, vm, mount):
        """
            On volume mounter
            @param vm as Gio.VolumeMonitor
            @param mount as Gio.Mount
        """
        self.__add_device(mount, True)

    def __on_mount_removed(self, vm, mount):
        """
            On volume removed, clean selection list
            @param vm as Gio.VolumeMonitor
            @param mount as Gio.Mount
        """
        self.__remove_device(mount)
