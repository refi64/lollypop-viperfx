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

from gi.repository import Gtk, Gio, GLib, Gdk

from gettext import gettext as _

from urllib.parse import urlparse
from random import randint

from lollypop.define import App, Type, ResponsiveType
from lollypop.objects import Album
from lollypop.loader import Loader
from lollypop.selectionlist import SelectionList
from lollypop.view_container import ViewContainer
from lollypop.view import View
from lollypop.progressbar import ProgressBar


# This is a multimedia device
class Device:
    id = None
    name = None
    uri = None


class Container(Gtk.Overlay):
    """
        Container for main view
    """

    def __init__(self):
        """
            Init container
        """
        Gtk.Overlay.__init__(self)
        self.__pulse_timeout = None
        self.__list_one_state = App().settings.get_value("list-one-ids") or\
            [Type.POPULARS]
        self.__list_two_state = App().settings.get_value("list-two-ids")
        # Index will start at -VOLUMES
        self.__devices = {}
        self.__devices_index = Type.DEVICES
        self.__stack = ViewContainer(500)
        self.__stack.show()

        self.__setup_view()
        self.__setup_scanner()

        # Volume manager
        self.__vm = Gio.VolumeMonitor.get()
        self.__vm.connect("mount-added", self.__on_mount_added)
        self.__vm.connect("mount-removed", self.__on_mount_removed)
        for mount in self.__vm.get_mounts():
            self.__add_device(mount, False)

        App().playlists.connect("playlists-changed",
                                self.__update_playlists)
        self.add(self.__paned_main_list)

        # Show donation notification
        if App().settings.get_value("show-donation"):
            GLib.timeout_add_seconds(randint(3600, 7200),
                                     self.__show_donation)

    def update_list_one(self, updater=None):
        """
            Update list one
            @param updater as GObject
        """
        update = updater is not None
        if App().settings.get_value("show-genres"):
            self.__update_list_genres(self.__list_one, update)
        else:
            self.__update_list_artists(self.__list_one, [Type.ALL], update)

    def update_list_two(self, updater=None):
        """
            Update list two
            @param updater as GObject
        """
        update = updater is not None
        ids = self.__list_one.selected_ids
        if ids and ids[0] == Type.PLAYLISTS:
            self.__update_list_playlists(update)
        elif App().settings.get_value("show-genres") and ids:
            self.__update_list_artists(self.__list_two, ids, update)

    def save_view_state(self):
        """
            Save view state
        """
        App().settings.set_value(
            "list-one-ids",
            GLib.Variant("ai",
                         self.__list_one.selected_ids))
        App().settings.set_value(
            "list-two-ids",
            GLib.Variant("ai",
                         self.__list_two.selected_ids))

    def show_lyrics(self, track=None):
        """
            Show lyrics for track
            @pram track as Track
        """
        from lollypop.view_lyrics import LyricsView
        current = self.__stack.get_visible_child()
        view = LyricsView()
        view.populate(track or App().player.current_track)
        view.show()
        self.__stack.add(view)
        self.__stack.set_visible_child(view)
        if hasattr(current, "disable_overlay"):
            current.disable_overlay()

    def show_playlist_manager(self, object):
        """
            Show playlist manager for object_id
            Current view stay present in ViewContainer
            @param object as Track/Album/Disc
        """
        from lollypop.view_playlists import PlaylistsManageView
        current = self.__stack.get_visible_child()
        view = PlaylistsManageView(object)
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
        self.__list_two.hide()
        self.update_list_one()
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

    def reload_view(self):
        """
            Reload current view
        """
        if self.__list_two.selected_ids:
            self.__on_list_two_selected(self.__list_two)
        elif self.__list_one.selected_ids:
            self.__on_list_one_selected(self.__list_one)

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

    def add_fake_phone(self):
        """
            Emulate an Android Phone
        """
        self.__devices_index -= 1
        dev = Device()
        dev.id = self.__devices_index
        dev.name = "Android phone"
        dev.uri = "file:///tmp/android/"
        d = Gio.File.new_for_uri(dev.uri + "Internal Memory")
        if not d.query_exists():
            d.make_directory_with_parents()
        d = Gio.File.new_for_uri(dev.uri + "SD Card")
        if not d.query_exists():
            d.make_directory_with_parents()
        self.__devices[self.__devices_index] = dev

    def show_artists_albums(self, artist_ids):
        """
            Show albums from artists
            @param artist id as int
        """
        def select_list_two(selection_list, artist_ids):
            GLib.idle_add(self.__list_two.select_ids, artist_ids)
            self.__list_two.disconnect_by_func(select_list_two)
        GLib.idle_add(self.__list_one.select_ids, [])
        GLib.idle_add(self.__list_two.select_ids, [])
        if App().settings.get_value("show-genres"):
            # Get artist genres
            genre_ids = []
            for artist_id in artist_ids:
                album_ids = App().artists.get_albums(artist_ids)
                for album_id in album_ids:
                    for genre_id in App().albums.get_genre_ids(album_id):
                        if genre_id not in genre_ids:
                            genre_ids.append(genre_id)
            # Select genres on list one
            self.__list_two.connect("populated", select_list_two, artist_ids)
            GLib.idle_add(self.__list_one.select_ids, genre_ids)
        else:
            # Select artists on list one
            GLib.idle_add(self.__list_one.select_ids, artist_ids)

    def go_back(self):
        """
            Go back in stack
        """
        visible_child = self.__stack.get_visible_child()
        if isinstance(visible_child, View):
            visible_child.stop()
        if visible_child == self.__list_two:
            self.__stack.set_visible_child(self.__list_one)
            App().window.toolbar.playback.show_back(True)
        elif self.__list_two.is_visible():
            self.__stack.set_visible_child(self.__list_two)
        else:
            self.__stack.set_visible_child(self.__list_one)
            App().window.toolbar.playback.show_back(True)

    def save_internals(self):
        """
            Save paned position
        """
        main_pos = self.__paned_main_list.get_position()
        listview_pos = self.__paned_list_view.get_position()
        listview_pos = listview_pos if listview_pos > 100 else 100
        App().settings.set_value("paned-mainlist-width",
                                 GLib.Variant("i",
                                              main_pos))
        App().settings.set_value("paned-listview-width",
                                 GLib.Variant("i",
                                              listview_pos))

    def paned_stack(self, b):
        """
            Enable paned stack
            @param bool as b
        """
        if b and not self.is_paned_stack:
            self.__paned_list_view.remove(self.__list_two)
            self.__paned_main_list.remove(self.__list_one)
            self.__stack.add(self.__list_one)
            self.__stack.add(self.__list_two)
            App().window.toolbar.playback.show_back(True, True)
            self.show_sidebar(True, True)
            self.reload_view()
        elif not b and self.is_paned_stack:
            value = App().settings.get_value("show-sidebar")
            self.__stack.remove(self.__list_two)
            self.__stack.remove(self.__list_one)
            self.__paned_list_view.add1(self.__list_two)
            self.__paned_main_list.add1(self.__list_one)
            App().window.toolbar.playback.show_back(False)
            self.show_sidebar(value)
            self.reload_view()

    def show_sidebar(self, value, force=False):
        """
            Show/Hide navigation sidebar
            @param value as bool
            @param force as bool
            Internally hide list one and list two
        """
        if value:
            self.__list_one.show(force)
            if self.__list_two.was_visible:
                self.__list_two.show(force)
        elif not self.is_paned_stack:
            self.__list_two.hide()
            self.__list_one.hide()

    @property
    def view(self):
        """
            Disable overlays
        """
        view = self.__stack.get_visible_child()
        if view is not None and not isinstance(view, View):
            for child in self.__stack.get_children():
                if isinstance(child, View):
                    view = child
                    break
        return view

    @property
    def progress(self):
        """
            Progress bar
            @return ProgressBar
        """
        return self.__progress

    @property
    def is_paned_stack(self):
        """
            Return True if stack contains paned
            return True
        """
        return self.__list_one in self.__stack.get_children()

############
# PRIVATE  #
############
    def __pulse(self):
        """
            Make progress bar pulse while visible
            @param pulse as bool
        """
        if self.__progress.is_visible() and not App().scanner.is_locked():
            self.__progress.pulse()
            return True
        else:
            self.__progress.set_fraction(0.0, self)
            self.__pulse_timeout = None
            return False

    def __setup_view(self):
        """
            Setup window main view:
                - genre list
                - artist list
                - main view as artist view or album view
        """
        self.__paned_main_list = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        self.__paned_list_view = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        vgrid = Gtk.Grid()
        vgrid.set_orientation(Gtk.Orientation.VERTICAL)

        self.__list_one = SelectionList(SelectionList.Type.LIST_ONE)
        self.__list_one.show()
        self.__list_two = SelectionList(SelectionList.Type.LIST_TWO)
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

        self.__paned_list_view.add1(self.__list_two)
        self.__paned_list_view.add2(vgrid)
        self.__paned_main_list.add1(self.__list_one)
        self.__paned_main_list.add2(self.__paned_list_view)
        self.__paned_main_list.set_position(
            App().settings.get_value("paned-mainlist-width").get_int32())
        self.__paned_list_view.set_position(
            App().settings.get_value("paned-listview-width").get_int32())
        self.__paned_main_list.show()
        self.__paned_list_view.show()

    def __setup_scanner(self):
        """
            Run collection update if needed
            @return True if hard scan is running
        """
        App().scanner.connect("scan-finished", self.__on_scan_finished)
        App().scanner.connect("genre-updated", self.__on_genre_updated)
        App().scanner.connect("artist-updated", self.__on_artist_updated)

    def __restore_list_one_state(self):
        """
            Restore saved state for list
        """
        if not self.__list_one_state:
            return
        # Get list one ids (always)
        list_one_ids = []
        for i in self.__list_one_state:
            if isinstance(i, int):
                list_one_ids.append(i)
        if not list_one_ids:
            list_one_ids = [Type.POPULARS]
        if list_one_ids[0] != Type.NONE:
            self.__list_one.select_ids(list_one_ids)
        self.__list_one_state = []

    def __restore_list_two_state(self):
        """
            Restore saved state for list
        """
        if not self.__list_two_state:
            return
        # Get list two ids (only on save state)
        list_two_ids = [Type.NONE]
        if App().settings.get_value("save-state"):
            list_two_ids = []
            for i in self.__list_two_state:
                if isinstance(i, int):
                    list_two_ids.append(i)
        if list_two_ids and list_two_ids[0] != Type.NONE:
            self.__list_two.select_ids(list_two_ids)
        self.__list_two_state = []

    def __update_playlists(self, playlists, playlist_id):
        """
            Update playlists in second list
            @param playlists as Playlists
            @param playlist_id as int
        """
        ids = self.__list_one.selected_ids
        if ids and ids[0] == Type.PLAYLISTS:
            if App().playlists.exists(playlist_id):
                self.__list_two.update_value(playlist_id,
                                             App().playlists.get_name(
                                                 playlist_id))
            else:
                self.__list_two.remove_value(playlist_id)

    def __update_lists(self, updater=None):
        """
            Update lists
            @param updater as GObject
        """
        self.update_list_one(updater)
        self.update_list_two(updater)

    def __update_list_genres(self, selection_list, update):
        """
            Setup list for genres
            @param list as SelectionList
            @param update as bool, if True, just update entries
            @thread safe
        """
        def load():
            genres = App().genres.get()
            return genres

        def setup(genres):
            selection_list.mark_as(SelectionList.Type.GENRE)
            items = selection_list.get_headers()
            items += genres
            if update:
                selection_list.update_values(items)
            else:
                selection_list.populate(items)
                self.__restore_list_one_state()

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
            artists = App().artists.get(genre_ids)
            compilations = App().albums.get_compilation_ids(genre_ids)
            return (artists, compilations)

        def setup(artists, compilations):
            mask = SelectionList.Type.ARTISTS
            if compilations:
                mask |= SelectionList.Type.COMPILATIONS
            selection_list.mark_as(mask)
            items = selection_list.get_headers()
            items += artists
            if update:
                selection_list.update_values(items)
            else:
                selection_list.populate(items)
                if selection_list == self.__list_one:
                    self.__restore_list_one_state()
                else:
                    self.__restore_list_two_state()
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
        self.__list_two.mark_as(SelectionList.Type.PLAYLISTS)
        items = self.__list_two.get_playlist_headers()
        items += App().playlists.get()
        if update:
            self.__list_two.update_values(items)
        else:
            self.__list_two.populate(items)
            self.__restore_list_two_state()

    def __stop_current_view(self):
        """
            Stop current view
        """
        child = self.__stack.get_visible_child()
        if child is not None:
            if hasattr(child, "stop"):
                child.stop()

    def __get_view_device(self, device_id):
        """
            Get device view for id
            Use existing view if available
            @param device id as int
            @return View
        """
        from lollypop.view_device import DeviceView, DeviceLocked
        self.__stop_current_view()
        device = self.__devices[device_id]
        device_view = None

        # Search a device child with uri
        for child in self.__stack.get_children():
            if isinstance(child, DeviceView):
                if child.device.uri == device.uri:
                    device_view = child
                    break
            elif isinstance(child, DeviceLocked):
                device_view = child
                break

        # If no view available, get a new one
        if device_view is None:
            files = DeviceView.get_files(device.uri)
            if files:
                device_view = DeviceView(device)
                device_view.populate()
                self.__stack.add_named(device_view, device.uri)
            else:
                device_view = DeviceLocked()
                self.__stack.add(device_view)
            device_view.show()
        return device_view

    def __get_view_artists(self, genre_ids, artist_ids):
        """
            Get artists view for genres/artists
            @param genre ids as [int]
            @param artist ids as [int]
        """
        def load():
            if genre_ids and genre_ids[0] == Type.ALL:
                items = App().albums.get_ids(artist_ids, [])
            else:
                items = []
                if artist_ids and artist_ids[0] == Type.COMPILATIONS:
                    items += App().albums.get_compilation_ids(genre_ids)
                items += App().albums.get_ids(artist_ids, genre_ids)
            return [Album(album_id, genre_ids, artist_ids)
                    for album_id in items]
        self.__stop_current_view()
        if self.is_paned_stack:
            from lollypop.view_albums_list import AlbumsListView
            view = AlbumsListView(ResponsiveType.LIST)
        else:
            from lollypop.view_artist import ArtistView
            view = ArtistView(artist_ids, genre_ids)
        loader = Loader(target=load, view=view)
        loader.start()
        view.show()
        return view

    def __get_view_albums(self, genre_ids, artist_ids):
        """
            Get albums view for genres/artists
            @param genre ids as [int]
            @param is compilation as bool
        """
        def load():
            items = []
            is_compilation = artist_ids and artist_ids[0] == Type.COMPILATIONS
            if genre_ids and genre_ids[0] == Type.ALL:
                if is_compilation or\
                        App().settings.get_value(
                            "show-compilations-in-album-view"):
                    items = App().albums.get_compilation_ids()
                if not is_compilation:
                    items += App().albums.get_ids()
            elif genre_ids and genre_ids[0] == Type.POPULARS:
                items = App().albums.get_rated()
                count = 100 - len(items)
                for album in App().albums.get_populars(count):
                    if album not in items:
                        items.append(album)
            elif genre_ids and genre_ids[0] == Type.LOVED:
                items = App().albums.get_loves()
            elif genre_ids and genre_ids[0] == Type.RECENTS:
                items = App().albums.get_recents()
            elif genre_ids and genre_ids[0] == Type.NEVER:
                items = App().albums.get_never_listened_to()
            elif genre_ids and genre_ids[0] == Type.RANDOMS:
                items = App().albums.get_randoms()
            else:
                if is_compilation or\
                        App().settings.get_value(
                            "show-compilations-in-album-view"):
                    items = App().albums.get_compilation_ids(genre_ids)
                if not is_compilation:
                    items += App().albums.get_ids([], genre_ids)
            return [Album(album_id, genre_ids, artist_ids)
                    for album_id in items]

        self.__stop_current_view()
        if self.is_paned_stack:
            from lollypop.view_albums_list import AlbumsListView
            view = AlbumsListView(ResponsiveType.LIST)
        else:
            from lollypop.view_albums_box import AlbumsBoxView
            view = AlbumsBoxView(genre_ids, artist_ids)
        loader = Loader(target=load, view=view)
        loader.start()
        view.show()
        return view

    def __get_view_playlists(self, playlist_ids=[]):
        """
            Get playlits view for playlists
            @param playlist ids as [int]
            @return View
        """
        def load():
            track_ids = []
            for playlist_id in playlist_ids:
                if playlist_id == Type.POPULARS:
                    tracks = App().tracks.get_rated()
                    for track in App().tracks.get_populars():
                        tracks.append(track)
                elif playlist_id == Type.RECENTS:
                    tracks = App().tracks.get_recently_listened_to()
                elif playlist_id == Type.NEVER:
                    tracks = App().tracks.get_never_listened_to()
                elif playlist_id == Type.RANDOMS:
                    tracks = App().tracks.get_randoms()
                elif playlist_id == Type.LOVED:
                    tracks = App().playlists.get_track_ids_sorted(playlist_id)
                else:
                    tracks = App().playlists.get_track_ids(playlist_id)
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
            view = PlaylistsManageView(None)
            view.populate()
        view.show()
        return view

    def __get_view_radios(self):
        """
            Get radios view
        """
        from lollypop.view_radios import RadiosView
        self.__stop_current_view()
        view = RadiosView()
        view.populate()
        view.show()
        return view

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
        is_removable = parsed.scheme == "file" and\
            Type.USB_DISKS in App().settings.get_value("shown-album-lists")
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

    def __show_donation(self):
        """
            Show a notification telling user to donate a little
        """
        from lollypop.app_notification import AppNotification
        notification = AppNotification(
            _("Please consider a donation to the project"),
            [_("PayPal"), _("Liberapay")],
            [lambda: Gtk.show_uri_on_window(
                App().window,
                "https://www.paypal.me/lollypopgnome",
                Gdk.CURRENT_TIME),
             lambda: Gtk.show_uri_on_window(
                App().window,
                "https://liberapay.com/gnumdk",
                Gdk.CURRENT_TIME)])
        self.add_overlay(notification)
        notification.show()
        notification.set_reveal_child(True)
        App().settings.set_value("show-donation",
                                 GLib.Variant("b", False))

    def __on_list_one_selected(self, selection_list):
        """
            Update view based on selected object
            @param list as SelectionList
        """
        view = None
        list_two_about_to_do_selection = list(self.__list_two_state)
        selected_ids = self.__list_one.selected_ids
        if not selected_ids:
            return
        # Update lists
        if selected_ids[0] == Type.PLAYLISTS:
            self.__update_list_playlists(False)
            self.__list_two.show()
        elif (selected_ids[0] > 0 or selected_ids[0] == Type.ALL) and\
                self.__list_one.type & SelectionList.Type.GENRE:
            self.__update_list_artists(self.__list_two, selected_ids, False)
            self.__list_two.show()
        else:
            self.__list_two.hide()
        # Update view
        if selected_ids[0] == Type.PLAYLISTS:
            if not list_two_about_to_do_selection:
                view = self.__get_view_playlists()
        elif Type.DEVICES - 999 < selected_ids[0] < Type.DEVICES:
            view = self.__get_view_device(selected_ids[0])
        elif selected_ids[0] in [Type.POPULARS,
                                 Type.LOVED,
                                 Type.RECENTS,
                                 Type.NEVER,
                                 Type.RANDOMS]:
            view = self.__get_view_albums(selected_ids, [])
        elif selected_ids[0] == Type.RADIOS:
            view = self.__get_view_radios()
        elif selection_list.type & SelectionList.Type.ARTISTS:
            if selected_ids[0] == Type.ALL:
                view = self.__get_view_albums(selected_ids, [])
            elif selected_ids[0] == Type.COMPILATIONS:
                view = self.__get_view_albums([], selected_ids)
            else:
                view = self.__get_view_artists([], selected_ids)
        else:
            view = self.__get_view_albums(selected_ids, [])
        if view is not None:
            if self.is_paned_stack:
                # Just to make it sensitive
                App().window.toolbar.playback.show_back(True, True)
            if view not in self.__stack.get_children():
                self.__stack.add(view)
            # If we are in paned stack mode, show list two if wanted
            if self.is_paned_stack\
                    and self.__list_two.is_visible()\
                    and (
                        selected_ids[0] >= 0 or
                        selected_ids[0] in [Type.PLAYLISTS, Type.ALL]):
                self.__stack.set_visible_child(self.__list_two)
            else:
                self.__stack.set_visible_child(view)
            self.__stack.clean_old_views(view)

    def __on_list_populated(self, selection_list):
        """
            Add device to list one
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
            view = self.__get_view_playlists(selected_ids)
        elif selected_ids[0] == Type.COMPILATIONS:
            view = self.__get_view_albums(genre_ids, selected_ids)
        else:
            view = self.__get_view_artists(genre_ids, selected_ids)
        self.__stack.add(view)
        self.__stack.set_visible_child(view)
        self.__stack.clean_old_views(view)

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

    def __on_scan_finished(self, scanner, modifications):
        """
            Update lists
            @param scanner as CollectionScanner
            @param modifications as bool
        """
        if modifications:
            self.__update_lists(App().scanner)
            from lollypop.app_notification import AppNotification
            notification = AppNotification(_("New tracks available"),
                                           [_("Refresh")],
                                           [lambda: self.reload_view()])
            self.add_overlay(notification)
            notification.show()
            notification.set_reveal_child(True)
            GLib.timeout_add(5000, notification.set_reveal_child, False)
            GLib.timeout_add(10000, notification.destroy)

    def __on_genre_updated(self, scanner, genre_id, add):
        """
            Add genre to genre list
            @param scanner as CollectionScanner
            @param genre id as int
            @param add as bool
        """
        if App().settings.get_value("show-genres"):
            if add:
                genre_name = App().genres.get_name(genre_id)
                self.__list_one.add_value((genre_id, genre_name))
            else:
                self.__list_one.remove_value(genre_id)

    def __on_artist_updated(self, scanner, artist_id, add):
        """
            Add/remove artist to/from list
            @param scanner as CollectionScanner
            @param artist id as int
            @param add as bool
        """
        artist_name = App().artists.get_name(artist_id)
        sortname = App().artists.get_sortname(artist_id)
        if App().settings.get_value("show-genres"):
            l = self.__list_two
            artist_ids = App().artists.get_ids(self.__list_one.selected_ids)
            if artist_id not in artist_ids:
                return
        else:
            l = self.__list_one
        if add:
            l.add_value((artist_id, artist_name, sortname))
        else:
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
