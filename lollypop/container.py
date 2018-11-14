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

from lollypop.define import App, Type, ResponsiveType, SelectionListMask
from lollypop.objects import Album
from lollypop.loader import Loader
from lollypop.selectionlist import SelectionList
from lollypop.view import View, MessageView
from lollypop.progressbar import ProgressBar
from lollypop.adaptive import AdaptiveStack
from lollypop.shown import ShownLists
from lollypop.logger import Logger


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
        # Index will start at -VOLUMES
        self.__devices = {}
        self.__devices_index = Type.DEVICES
        self.__stack = AdaptiveStack()
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
        self.add(self.__paned_one)

        if App().settings.get_value("save-state"):
            self.__list_one_ids = App().settings.get_value("list-one-ids")
            self.__list_two_ids = App().settings.get_value("list-two-ids")
        else:
            self.__list_one_ids = []
            self.__list_two_ids = []

        # Show donation notification
        if App().settings.get_value("show-donation"):
            GLib.timeout_add_seconds(randint(3600, 7200),
                                     self.__show_donation)

    def update_list_one(self, update=False):
        """
            Update list one
            @param update as bool
        """
        if self.__list_one.get_visible():
            if App().settings.get_value("show-genres"):
                self.__update_list_genres(self.__list_one, update)
            else:
                self.__update_list_artists(self.__list_one, [Type.ALL], update)

    def update_list_two(self, update=False):
        """
            Update list two
            @param update as bool
        """
        if self.__list_one.get_visible():
            ids = self.__list_one.selected_ids
            if ids and ids[0] in [Type.PLAYLISTS, Type.YEARS]:
                self.__update_list_playlists(update, ids[0])
            elif App().settings.get_value("show-genres") and ids:
                self.__update_list_artists(self.__list_two, ids, update)

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
            view.stop()

    def show_genres(self, show):
        """
            Show/Hide genres
            @param bool
        """
        self.__list_two.hide()
        self.update_list_one()
        self.__list_one.select_ids([Type.POPULARS])

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

    def save_internals(self):
        """
            Save paned position
        """
        main_pos = self.__paned_one.get_position()
        listview_pos = self.__paned_two.get_position()
        listview_pos = listview_pos if listview_pos > 100 else 100
        App().settings.set_value("paned-mainlist-width",
                                 GLib.Variant("i",
                                              main_pos))
        App().settings.set_value("paned-listview-width",
                                 GLib.Variant("i",
                                              listview_pos))

    def show_sidebar(self, show):
        """
            Show/Hide navigation sidebar
            @param show as bool
        """
        view = self.view_artists_rounded
        if view is not None:
            view.destroy()
        if show or App().window.is_adaptive:
            # We are entering paned stack mode
            self.__list_one.select_ids()
            self.__list_two_ids = App().settings.get_value("list-two-ids")
            self.__list_one.select_ids(
                App().settings.get_value("list-one-ids"))
            self.__list_one.show()
            if not App().window.is_adaptive:
                App().window.emit("show-can-go-back", False)
            if self.__list_one.count == 0:
                self.update_list_one()
            if self.__list_two.count > 0 and\
                    App().settings.get_value("show-genres") and\
                    self.__list_two_ids:
                self.__list_two.show()
        elif not App().window.is_adaptive:
            if self.__list_one.get_visible():
                list_two_ids = App().settings.get_value("list-two-ids")
                list_one_ids = App().settings.get_value("list-one-ids")
                # We are leaving paned stack mode
                # Restore static entry
                if list_one_ids and list_one_ids[0] < 0:
                    self.__list_one_ids = list_one_ids
                    self.__list_two_ids = list_two_ids
                # Restore genre entry
                elif list_one_ids and list_one_ids[0] >= 0 and list_two_ids:
                    self.__list_one_ids = list_two_ids
                else:
                    self.__list_one_ids = []
                self.__list_two.hide()
                self.__list_one.hide()
            self.show_artists_view()
            if self.__list_one_ids and self.__list_two_ids:
                self.show_view(self.__list_one_ids[0], None, False)
                self.show_view(self.__list_one_ids[0], self.__list_two_ids)
            elif self.__list_one_ids:
                self.show_view(self.__list_one_ids[0])
            elif self.__list_two_ids:
                self.show_view(self.__list_two_ids[0])
            self.__list_one_ids = []
            self.__list_two_ids = []

    def show_lyrics(self, track=None):
        """
            Show lyrics for track
            @pram track as Track
        """
        App().window.emit("can-go-back-changed", True)
        from lollypop.view_lyrics import LyricsView
        current = self.__stack.get_visible_child()
        view = LyricsView()
        view.populate(track or App().player.current_track)
        view.show()
        self.__stack.add(view)
        self.__stack.set_visible_child(view)
        current.disable_overlay()

    def show_smart_playlist_editor(self, playlist_id):
        """
            Show a view allowing user to edit smart view
            @param playlist_id as int
        """
        App().window.emit("can-go-back-changed", True)
        from lollypop.view_playlist_smart import SmartPlaylistView
        current = self.__stack.get_visible_child()
        view = SmartPlaylistView(playlist_id)
        view.populate()
        view.show()
        self.__stack.add(view)
        self.__stack.set_visible_child(view)
        current.disable_overlay()

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

    def show_view(self, item_id, data=None, switch=True):
        """
            Show view for item id
            @param item_ids as int
            @param data as object
            @param switch as bool
        """
        self.__destroy_visible()
        App().window.emit("can-go-back-changed", True)
        if item_id in [Type.POPULARS,
                       Type.LOVED,
                       Type.RECENTS,
                       Type.NEVER,
                       Type.RANDOMS]:
            view = self.__get_view_albums([item_id], [])
        elif item_id == Type.YEARS:
            if data is None:
                view = self.__get_view_albums_decades()
            else:
                view = self.__get_view_albums_years(data)
        elif item_id == Type.PLAYLISTS:
            view = self.__get_view_playlists([] if data is None else data)
        elif item_id == Type.COMPILATIONS:
            view = self.__get_view_albums([], [item_id])
        elif item_id == Type.RADIOS:
            view = self.__get_view_radios()
        elif Type.DEVICES - 999 < item_id < Type.DEVICES:
            from lollypop.view_device import DeviceView
            # Search for an existing view
            view = None
            for child in self.__stack.get_children():
                if isinstance(child, DeviceView):
                    view = child
                    break
            if view is None:
                view = self.__get_view_device(item_id)
        else:
            view = self.__get_view_artists([], [item_id])
        view.show()
        self.__stack.add(view)
        self.__stack.set_visible_child(view)

    def show_artists_view(self):
        """
            Show artists view (rounded artwork)
        """
        self.__destroy_visible()
        App().window.emit("can-go-back-changed", False)
        view = self.__get_view_artists_rounded()
        App().window.emit("show-can-go-back", True)
        self.__stack.set_visible_child(view)

    @property
    def view(self):
        """
            Get current view
            @return View
        """
        view = self.__stack.get_visible_child()
        if view is not None and isinstance(view, View):
            return view
        return None

    @property
    def view_artists_rounded(self):
        """
            Get existing rounded artists view
            @return RoundedArtistsView
        """
        from lollypop.view_artists_rounded import RoundedArtistsView
        self.__stop_current_view()
        for view in self.__stack.get_children():
            if isinstance(view, RoundedArtistsView):
                return view
        return None

    @property
    def progress(self):
        """
            Progress bar
            @return ProgressBar
        """
        return self.__progress

    @property
    def stack(self):
        """
            Container stack
            @return stack as Gtk.Stack
        """
        return self.__stack

    @property
    def list_one(self):
        """
            Get first SelectionList
            @return SelectionList
        """
        return self.__list_one

    @property
    def list_two(self):
        """
            Get second SelectionList
            @return SelectionList
        """
        return self.__list_two

    @property
    def paned_one(self):
        """
            Get first paned (list_one)
        """
        return self.__paned_one

    @property
    def paned_two(self):
        """
            Get second paned (list_two)
        """
        return self.__paned_two

############
# PRIVATE  #
############
    def __destroy_visible(self):
        """
            Destroy visible child
        """
        visible = self.__stack.get_visible_child()
        if visible is not None:
            visible.destroy()

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
        self.__paned_one = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        self.__paned_two = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)

        vgrid = Gtk.Grid()
        vgrid.set_orientation(Gtk.Orientation.VERTICAL)

        self.__list_one = SelectionList(SelectionListMask.LIST_ONE)
        self.__list_two = SelectionList(SelectionListMask.LIST_TWO)
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

        self.__paned_two.add1(self.__list_two)
        self.__paned_two.add2(vgrid)
        self.__paned_one.add1(self.__list_one)
        self.__paned_one.add2(self.__paned_two)
        self.__paned_one.set_position(
            App().settings.get_value("paned-mainlist-width").get_int32())
        self.__paned_two.set_position(
            App().settings.get_value("paned-listview-width").get_int32())
        self.__paned_one.show()
        self.__paned_two.show()

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
        if self.__list_one_ids:
            self.__list_one.select_ids(self.__list_one_ids)
            self.__list_one_ids = []
        else:
            self.__list_one.select_first()

    def __restore_list_two_state(self):
        """
            Restore saved state for list
        """
        if self.__list_two_ids:
            self.__list_two.select_ids(self.__list_two_ids)
            self.__list_two_ids = []

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

    def __update_lists(self, update=False):
        """
            Update lists
            @param update as bool
        """
        self.update_list_one(update)
        self.update_list_two(update)

    def __update_list_genres(self, selection_list, update):
        """
            Setup list for genres
            @param list as SelectionList
            @param update as bool, if True, just update entries
        """
        def load():
            genres = App().genres.get()
            return genres

        def setup(genres):
            selection_list.mark_as(SelectionListMask.GENRE)
            items = selection_list.get_headers(selection_list.mask)
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
        """
        def load():
            artists = App().artists.get(genre_ids)
            compilations = App().albums.get_compilation_ids(genre_ids)
            return (artists, compilations)

        def setup(artists, compilations):
            mask = SelectionListMask.ARTISTS
            if compilations:
                mask |= SelectionListMask.COMPILATIONS
            selection_list.mark_as(mask)
            items = selection_list.get_headers(selection_list.mask)
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

    def __update_list_playlists(self, update, type):
        """
            Setup list for playlists
            @param update as bool
            @param type as int
        """
        self.__list_two.mark_as(SelectionListMask.PLAYLISTS)
        if type == Type.PLAYLISTS:
            items = self.__list_two.get_playlist_headers()
            items += App().playlists.get()
        else:
            (years, unknown) = App().albums.get_years()
            items = [(year, str(year), str(year)) for year in sorted(years)]
            if unknown:
                items.insert(0, (Type.NONE, _("Unknown"), ""))
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

    def __get_view_artists_rounded(self, static=True):
        """
            Get rounded artists view
            @param static as bool, show static entries
            @return view
        """
        def load():
            ids = App().artists.get()
            compilations = App().albums.get_compilation_ids()
            return (ids, compilations)

        def setup(artist_ids, compilation_ids):
            items = []
            if static:
                mask = SelectionListMask.LIST_ONE |\
                       SelectionListMask.ARTISTS |\
                       SelectionListMask.ALL_ARTISTS
                if compilation_ids:
                    mask |= SelectionListMask.COMPILATIONS
                items = ShownLists.get(mask)
                for dev in self.__devices.values():
                    items.append((dev.id, dev.name, dev.name))
            items += artist_ids
            view.populate(items)

        from lollypop.view_artists_rounded import RoundedArtistsView
        self.__stop_current_view()
        view = self.view_artists_rounded
        if view is None:
            view = RoundedArtistsView()
            self.__stack.add(view)
            loader = Loader(target=load, view=view,
                            on_finished=lambda r: setup(*r))
            loader.start()
            view.show()
        return view

    def __get_view_device(self, device_id):
        """
            Get device view for id
            Use existing view if available
            @param device id as int
            @return View
        """
        from lollypop.view_device import DeviceView
        self.__stop_current_view()
        device = self.__devices[device_id]
        device_view = None

        # Search a device child with uri
        for child in self.__stack.get_children():
            if isinstance(child, DeviceView):
                if child.device.uri == device.uri:
                    device_view = child
                    break

        # If no view available, get a new one
        if device_view is None:
            files = DeviceView.get_files(device.uri)
            if files:
                device_view = DeviceView(device)
                self.__stack.add_named(device_view, device.uri)
            else:
                device_view = MessageView(_("Please unlock your device"))
                self.__stack.add(device_view)
            device_view.populate()
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
        if App().window.is_adaptive:
            from lollypop.view_albums_list import AlbumsListView
            view = AlbumsListView(ResponsiveType.LIST, artist_ids, genre_ids)
        else:
            from lollypop.view_artist import ArtistView
            view = ArtistView(artist_ids, genre_ids)
        loader = Loader(target=load, view=view)
        loader.start()
        view.show()
        return view

    def __get_view_albums_decades(self):
        """
            Get album view for decades
        """
        def load():
            (years, unknown) = App().albums.get_years()
            decades = []
            decade = []
            current_d = None
            for year in sorted(years):
                d = year // 10
                if current_d is not None and current_d != d:
                    current_d = d
                    decades.append(decade)
                    decade = []
                current_d = d
                decade.append(year)
            if decade:
                decades.append(decade)
            return decades
        self.__stop_current_view()
        if App().window.is_adaptive:
            view = Gtk.Grid()
        else:
            from lollypop.view_albums_decade_box import AlbumsDecadeBoxView
            view = AlbumsDecadeBoxView()
            loader = Loader(target=load, view=view)
            loader.start()
        view.show()
        return view

    def __get_view_albums_years(self, years):
        """
            Get album view for years
            @param years as [int]
        """
        def load():
            items = []
            for year in years:
                items += App().albums.get_compilations_for_year(year)
                items += App().albums.get_albums_for_year(year)
            return [Album(album_id, [Type.YEARS], [])
                    for album_id in items]
        self.__stop_current_view()
        if App().window.is_adaptive:
            from lollypop.view_albums_list import AlbumsListView
            view = AlbumsListView(ResponsiveType.LIST, [Type.YEARS], years)
        else:
            from lollypop.view_albums_box import AlbumsBoxView
            view = AlbumsBoxView([Type.YEARS], years)
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
        if App().window.is_adaptive:
            from lollypop.view_albums_list import AlbumsListView
            view = AlbumsListView(ResponsiveType.LIST, genre_ids, artist_ids)
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
                for track_id in App().playlists.get_track_ids(playlist_id):
                    if track_id not in track_ids:
                        track_ids.append(track_id)
            return track_ids

        def load_smart():
            request = App().playlists.get_smart_sql(playlist_ids[0])
            return App().db.execute(request)

        self.__stop_current_view()
        if len(playlist_ids) == 1 and\
                App().playlists.get_smart(playlist_ids[0]):
            from lollypop.view_playlists import PlaylistsView
            view = PlaylistsView(playlist_ids)
            loader = Loader(target=load_smart, view=view)
            loader.start()
        elif playlist_ids:
            from lollypop.view_playlists import PlaylistsView
            view = PlaylistsView(playlist_ids)
            loader = Loader(target=load, view=view)
            loader.start()
        else:
            from lollypop.view_playlists_manager import PlaylistsManagerView
            view = PlaylistsManagerView()
            view.populate(App().playlists.get_ids())
        view.show()
        return view

    def __get_view_radios(self):
        """
            Get radios view
        """
        from lollypop.view_radios import RadiosView
        from lollypop.radios import Radios
        self.__stop_current_view()
        radios = Radios()
        radio_ids = radios.get_ids()
        view = RadiosView(radios)
        if radio_ids:
            view.populate(radio_ids)
        else:
            view.show_warning()
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
        drive = mount.get_drive()
        if uri is None:
            return
        parsed = urlparse(uri)
        is_removable = drive is not None and drive.is_removable() and\
            Type.USB_DISKS in App().settings.get_value("shown-album-lists")
        if is_removable or parsed.scheme == "mtp":
            self.__devices_index -= 1
            dev = Device()
            dev.id = self.__devices_index
            dev.name = mount.get_name()
            dev.uri = uri
            self.__devices[self.__devices_index] = dev
            if show:
                if App().settings.get_value("show-sidebar"):
                    self.__list_one.add_value((dev.id, dev.name, dev.name))
                else:
                    self.view_artists_rounded.insert_item((dev.id,
                                                           dev.name,
                                                           dev.name))

    def __remove_device(self, mount):
        """
            Remove volume from device list
            @param mount as Gio.Mount
        """
        uri = mount.get_default_location().get_uri()
        for dev in self.__devices.values():
            if dev.uri == uri:
                if App().settings.get_value("show-sidebar"):
                    self.__list_one.remove_value(dev.id)
                else:
                    self.view_artists_rounded.remove_item(dev.id)
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
        self.__destroy_visible()
        if not App().window.is_adaptive:
            App().window.emit("show-can-go-back", False)
            App().window.emit("can-go-back-changed", False)
        Logger.debug("Container::__on_list_one_selected()")
        view = None
        selected_ids = self.__list_one.selected_ids
        if not selected_ids:
            return
        # Update lists
        if selected_ids[0] in [Type.PLAYLISTS, Type.YEARS]:
            self.__update_list_playlists(False, selected_ids[0])
            self.__list_two.show()
        elif (selected_ids[0] > 0 or selected_ids[0] == Type.ALL) and\
                self.__list_one.mask & SelectionListMask.GENRE:
            self.__update_list_artists(self.__list_two, selected_ids, False)
            self.__list_two.show()
        else:
            self.__list_two.hide()
        # Update view
        if selected_ids[0] == Type.PLAYLISTS:
            if not self.__list_two.selected_ids:
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
        elif selected_ids[0] == Type.YEARS:
            view = self.__get_view_albums_decades()
        elif selected_ids[0] == Type.ARTISTS:
            view = self.__get_view_artists_rounded(False)
            App().window.emit("show-can-go-back", True)
        elif selection_list.mask & SelectionListMask.ARTISTS:
            if selected_ids[0] == Type.ALL:
                view = self.__get_view_albums(selected_ids, [])
            elif selected_ids[0] == Type.COMPILATIONS:
                view = self.__get_view_albums([], selected_ids)
            else:
                view = self.__get_view_artists([], selected_ids)
        else:
            view = self.__get_view_albums(selected_ids, [])
        if view is not None:
            if App().window.is_adaptive:
                App().window.emit("can-go-back-changed", True)
            if view not in self.__stack.get_children():
                self.__stack.add(view)
            # If we are in paned stack mode, show list two if wanted
            if App().window.is_adaptive\
                    and self.__list_two.is_visible()\
                    and (
                        selected_ids[0] >= 0 or
                        Type.DEVICES - 999 < selected_ids[0] < Type.DEVICES or
                        selected_ids[0] in [Type.PLAYLISTS,
                                            Type.YEARS,
                                            Type.ALL]):
                self.__stack.set_visible_child(self.__list_two)
            else:
                self.__stack.set_visible_child(view)

    def __on_list_populated(self, selection_list):
        """
            Add device to list one
            @param selection_list as SelectionList
        """
        for dev in self.__devices.values():
            self.__list_one.add_value((dev.id, dev.name, dev.name))

    def __on_list_two_selected(self, selection_list):
        """
            Update view based on selected object
            @param selection_list as SelectionList
        """
        self.__destroy_visible()
        Logger.debug("Container::__on_list_two_selected()")
        genre_ids = self.__list_one.selected_ids
        selected_ids = self.__list_two.selected_ids
        if not selected_ids or not genre_ids:
            return
        if genre_ids[0] == Type.PLAYLISTS:
            view = self.__get_view_playlists(selected_ids)
        elif genre_ids[0] == Type.YEARS:
            view = self.__get_view_albums_years(selected_ids)
        elif selected_ids[0] == Type.COMPILATIONS:
            view = self.__get_view_albums(genre_ids, selected_ids)
        else:
            view = self.__get_view_artists(genre_ids, selected_ids)
        self.__stack.add(view)
        self.__stack.set_visible_child(view)

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
            self.__update_lists(True)
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
                self.__list_one.add_value((genre_id, genre_name, genre_name))
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
        if App().settings.get_value("show-sidebar"):
            if App().settings.get_value("show-genres"):
                l = self.__list_two
                artist_ids = App().artists.get_ids(
                    self.__list_one.selected_ids)
                if artist_id not in artist_ids:
                    return
            else:
                l = self.__list_one
            if add:
                l.add_value((artist_id, artist_name, sortname))
            else:
                l.remove_value(artist_id)
        else:
            if add:
                self.view_artists_rounded.insert_item((artist_id,
                                                       artist_name,
                                                       sortname))
            else:
                self.view_artists_rounded.remove_item(artist_id)

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
