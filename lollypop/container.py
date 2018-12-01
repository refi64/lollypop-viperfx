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

from gi.repository import Gtk, GLib

from lollypop.define import App, Type, RowListType, SelectionListMask
from lollypop.objects import Album
from lollypop.loader import Loader
from lollypop.selectionlist import SelectionList
from lollypop.view import View
from lollypop.adaptive import AdaptiveStack
from lollypop.shown import ShownLists
from lollypop.logger import Logger
from lollypop.container_device import DeviceContainer
from lollypop.container_donation import DonationContainer
from lollypop.container_progress import ProgressContainer
from lollypop.container_scanner import ScannerContainer
from lollypop.container_playlists import PlaylistsContainer


class Container(Gtk.Overlay, DeviceContainer, DonationContainer,
                ProgressContainer, ScannerContainer, PlaylistsContainer):
    """
        Main view management
    """

    def __init__(self):
        """
            Init container
        """
        Gtk.Overlay.__init__(self)
        DeviceContainer.__init__(self)
        DonationContainer.__init__(self)
        ProgressContainer.__init__(self)
        ScannerContainer.__init__(self)
        PlaylistsContainer.__init__(self)
        self._stack = AdaptiveStack()
        self._stack.show()
        self.__setup_view()
        self.add(self.__paned_one)

    def update_list_one(self, update=False):
        """
            Update list one
            @param update as bool
        """
        if self._list_one.get_visible():
            if App().settings.get_value("show-genres"):
                self.__update_list_genres(self._list_one, update)
            else:
                self.__update_list_artists(self._list_one, [Type.ALL], update)

    def update_list_two(self, update=False):
        """
            Update list two
            @param update as bool
        """
        if self._list_one.get_visible():
            ids = self._list_one.selected_ids
            if ids and ids[0] in [Type.PLAYLISTS, Type.YEARS]:
                self._update_list_playlists(update, ids[0])
            elif App().settings.get_value("show-genres") and ids:
                self.__update_list_artists(self._list_two, ids, update)

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
            view.stop()

    def show_genres(self, show):
        """
            Show/Hide genres
            @param bool
        """
        def select_list_one(selection_list):
            self._list_one.select_first()
            self._list_one.disconnect_by_func(select_list_one)
        if App().settings.get_value("show-sidebar"):
            self._list_two.hide()
            self.update_list_one()
            self._list_one.connect("populated", select_list_one)

    def reload_view(self):
        """
            Reload current view
        """
        if App().settings.get_value("show-sidebar"):
            self.__reload_list_view()
        else:
            self.__reload_navigation_view()

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
        def select_list_one(selection_list):
            self.__reload_list_view()
            self._list_one.disconnect_by_func(select_list_one)

        adpative_window = App().window.is_adaptive
        self._stack.set_navigation_enabled(not show or adpative_window)
        self._stack.clear()
        # Destroy to force update (static vs non static)
        view = self.view_artists_rounded
        if view is not None:
            view.destroy()
        if show or adpative_window:
            if not adpative_window:
                App().window.emit("show-can-go-back", False)
            self._list_one.show()
            if self._list_one.count == 0:
                self._list_one.connect("populated", select_list_one)
                self.update_list_one()
            else:
                self.__reload_list_view()
        elif not adpative_window:
            if self._list_one.get_visible():
                self._list_two.hide()
                self._list_one.hide()
            self.__reload_navigation_view()

    def show_lyrics(self, track=None):
        """
            Show lyrics for track
            @pram track as Track
        """
        from lollypop.view_lyrics import LyricsView
        current = self._stack.get_visible_child()
        view = LyricsView()
        view.populate(track or App().player.current_track)
        view.show()
        self._stack.add(view)
        App().window.container.stack.set_navigation_enabled(True)
        self._stack.set_visible_child(view)
        App().window.container.stack.set_navigation_enabled(False)
        current.disable_overlay()

    def show_artists_albums(self, artist_ids):
        """
            Show albums from artists
            @param artist id as int
        """
        def select_list_two(selection_list, artist_ids):
            self._list_two.select_ids(artist_ids)
            self._list_two.disconnect_by_func(select_list_two)
        self._list_one.select_ids()
        self._list_two.select_ids()
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
            self._list_two.connect("populated", select_list_two, artist_ids)
            self._list_one.select_ids(genre_ids)
        else:
            # Select artists on list one
            self._list_one.select_ids(artist_ids)

    def show_view(self, item_id, data=None, switch=True):
        """
            Show view for item id
            @param item_ids as int
            @param data as object
            @param switch as bool
        """
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
            view = self._get_view_playlists([] if data is None else data)
        elif item_id == Type.COMPILATIONS:
            view = self.__get_view_albums([], [item_id])
        elif item_id == Type.RADIOS:
            view = self.__get_view_radios()
        elif Type.DEVICES - 999 < item_id < Type.DEVICES:
            from lollypop.view_device import DeviceView
            # Search for an existing view
            view = None
            for child in self._stack.get_children():
                if isinstance(child, DeviceView):
                    view = child
                    break
            if view is None:
                view = self._get_view_device(item_id)
        else:
            view = self.__get_view_artists([], [item_id])
        view.show()
        self._stack.add(view)
        if switch:
            self._stack.set_visible_child(view)
        else:
            self._stack.add_to_history(view)

    def show_artists_view(self):
        """
            Show artists view (rounded artwork)
        """
        App().window.emit("can-go-back-changed", False)
        view = self.__get_view_artists_rounded()
        App().window.emit("show-can-go-back", True)
        self._stack.set_visible_child(view)

    def stop_current_view(self):
        """
            Stop current view
        """
        child = self._stack.get_visible_child()
        if child is not None:
            if hasattr(child, "stop"):
                child.stop()

    @property
    def view(self):
        """
            Get current view
            @return View
        """
        view = self._stack.get_visible_child()
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
        self.stop_current_view()
        for view in self._stack.get_children():
            if isinstance(view, RoundedArtistsView):
                return view
        return None

    @property
    def stack(self):
        """
            Container stack
            @return stack as Gtk.Stack
        """
        return self._stack

    @property
    def list_one(self):
        """
            Get first SelectionList
            @return SelectionList
        """
        return self._list_one

    @property
    def list_two(self):
        """
            Get second SelectionList
            @return SelectionList
        """
        return self._list_two

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

        self._list_one = SelectionList(SelectionListMask.LIST_ONE)
        self._list_two = SelectionList(SelectionListMask.LIST_TWO)
        self._list_one.connect("item-selected", self.__on_list_one_selected)
        self._list_one.connect("populated", self.__on_list_populated)
        self._list_one.connect("pass-focus", self.__on_pass_focus)
        self._list_two.connect("item-selected", self.__on_list_two_selected)
        self._list_two.connect("pass-focus", self.__on_pass_focus)

        vgrid.add(self._stack)
        vgrid.add(self._progress)
        vgrid.show()

        self.__paned_two.add1(self._list_two)
        self.__paned_two.add2(vgrid)
        self.__paned_one.add1(self._list_one)
        self.__paned_one.add2(self.__paned_two)
        self.__paned_one.set_position(
            App().settings.get_value("paned-mainlist-width").get_int32())
        self.__paned_two.set_position(
            App().settings.get_value("paned-listview-width").get_int32())
        self.__paned_one.show()
        self.__paned_two.show()

    def __reload_list_view(self):
        """
            Reload list view
        """
        def select_list_two(selection_list, ids):
            # For some reasons, we need to delay this
            # If list two list is short, we may receive list two selected-item
            # signal before list one
            GLib.idle_add(self._list_two.select_ids, ids)
            self._list_two.disconnect_by_func(select_list_two)

        state_one_ids = App().settings.get_value("state-one-ids")
        state_two_ids = App().settings.get_value("state-two-ids")
        if state_two_ids and not state_one_ids:
            if App().settings.get_value("show-genres"):
                self.show_artists_albums(state_two_ids)
                return
            else:
                state_one_ids = state_two_ids
                state_two_ids = []
        if state_two_ids:
            self._list_two.connect("populated", select_list_two, state_two_ids)
        self._list_one.select_ids()
        if state_one_ids:
            self._list_one.select_ids(state_one_ids)
        else:
            self._list_one.select_first()

    def __reload_navigation_view(self):
        """
            Reload navigation view
        """
        state_two_ids = App().settings.get_value("state-two-ids")
        state_one_ids = App().settings.get_value("state-one-ids")
        # We do not support genres in navigation mode
        if App().settings.get_value("show-genres") and\
                state_one_ids and state_one_ids[0] >= 0 and not state_two_ids:
            state_one_ids = []
        # Artist id with genre off or genre and artist id
        elif (state_two_ids and not state_one_ids) or\
                (state_one_ids and state_one_ids[0] >= 0 and state_two_ids):
            state_one_ids = state_two_ids
            state_two_ids = []
        self.show_artists_view()
        if state_one_ids and state_two_ids:
            self.show_view(state_one_ids[0], None, False)
            self.show_view(state_one_ids[0], state_two_ids)
        elif state_one_ids:
            self.show_view(state_one_ids[0])
        elif state_two_ids:
            self.show_view(state_two_ids[0])

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
        if selection_list == self._list_one:
            if self._list_two.is_visible():
                self._list_two.hide()
            self._list_two_restore = Type.NONE
        loader = Loader(target=load, view=selection_list,
                        on_finished=lambda r: setup(*r))
        loader.start()

    def __get_view_artists_rounded(self, static=True):
        """
            Get rounded artists view
            @param static as bool, show static entries
            @return view
        """
        def load():
            ids = App().artists.get()
            compilations = App().albums.get_compilation_ids([])
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
                for dev in self.devices.values():
                    items.append((dev.id, dev.name, dev.name))
            items += artist_ids
            view.populate(items)

        from lollypop.view_artists_rounded import RoundedArtistsView
        self.stop_current_view()
        view = self.view_artists_rounded
        if view is None:
            view = RoundedArtistsView()
            self._stack.add(view)
            loader = Loader(target=load, view=view,
                            on_finished=lambda r: setup(*r))
            loader.start()
            view.show()
        return view

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
        self.stop_current_view()
        if App().window.is_adaptive:
            from lollypop.view_albums_list import AlbumsListView
            view = AlbumsListView(RowListType.DEFAULT, artist_ids, genre_ids)
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
        self.stop_current_view()
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
        self.stop_current_view()
        if App().window.is_adaptive:
            from lollypop.view_albums_list import AlbumsListView
            view = AlbumsListView(RowListType.DEFAULT, [Type.YEARS], years)
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
                    items = App().albums.get_compilation_ids([])
                if not is_compilation:
                    items += App().albums.get_ids([], [])
            elif genre_ids and genre_ids[0] == Type.POPULARS:
                items = App().albums.get_rated()
                count = 100 - len(items)
                for album in App().albums.get_populars(count):
                    if album not in items:
                        items.append(album)
            elif genre_ids and genre_ids[0] == Type.LOVED:
                items = App().albums.get_loved_albums()
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

        self.stop_current_view()
        if App().window.is_adaptive:
            from lollypop.view_albums_list import AlbumsListView
            view = AlbumsListView(RowListType.DEFAULT, genre_ids, artist_ids)
        else:
            from lollypop.view_albums_box import AlbumsBoxView
            view = AlbumsBoxView(genre_ids, artist_ids)
        loader = Loader(target=load, view=view)
        loader.start()
        view.show()
        return view

    def __get_view_radios(self):
        """
            Get radios view
        """
        def load():
            from lollypop.radios import Radios
            radios = Radios()
            return radios.get_ids()
        self.stop_current_view()
        from lollypop.view_radios import RadiosView
        view = RadiosView()
        loader = Loader(target=load, view=view)
        loader.start()
        view.show()
        return view

    def __on_list_one_selected(self, selection_list):
        """
            Update view based on selected object
            @param list as SelectionList
        """
        Logger.debug("Container::__on_list_one_selected()")
        self._stack.destroy_non_visible_children()
        if not App().window.is_adaptive:
            App().window.emit("show-can-go-back", False)
            App().window.emit("can-go-back-changed", False)
        view = None
        selected_ids = self._list_one.selected_ids
        if not selected_ids:
            return
        # Update lists
        if selected_ids[0] in [Type.PLAYLISTS, Type.YEARS]:
            self._update_list_playlists(False, selected_ids[0])
            self._list_two.show()
        elif (selected_ids[0] > 0 or selected_ids[0] == Type.ALL) and\
                self._list_one.mask & SelectionListMask.GENRE:
            self.__update_list_artists(self._list_two, selected_ids, False)
            self._list_two.show()
        else:
            self._list_two.hide()
        # Update view
        if selected_ids[0] == Type.PLAYLISTS:
            if not self._list_two.selected_ids:
                view = self._get_view_playlists()
        elif Type.DEVICES - 999 < selected_ids[0] < Type.DEVICES:
            view = self._get_view_device(selected_ids[0])
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
            if view not in self._stack.get_children():
                self._stack.add(view)
            # If we are in paned stack mode, show list two if wanted
            if App().window.is_adaptive\
                    and self._list_two.is_visible()\
                    and (
                        selected_ids[0] >= 0 or
                        Type.DEVICES - 999 < selected_ids[0] < Type.DEVICES or
                        selected_ids[0] in [Type.PLAYLISTS,
                                            Type.YEARS,
                                            Type.ALL]):
                self._stack.set_visible_child(self._list_two)
            else:
                self._stack.set_visible_child(view)

    def __on_list_populated(self, selection_list):
        """
            Add device to list one
            @param selection_list as SelectionList
        """
        for dev in self.devices.values():
            self._list_one.add_value((dev.id, dev.name, dev.name))

    def __on_list_two_selected(self, selection_list):
        """
            Update view based on selected object
            @param selection_list as SelectionList
        """
        Logger.debug("Container::__on_list_two_selected()")
        self._stack.destroy_non_visible_children()
        if not App().window.is_adaptive:
            App().window.emit("show-can-go-back", False)
            App().window.emit("can-go-back-changed", False)
        genre_ids = self._list_one.selected_ids
        selected_ids = self._list_two.selected_ids
        if not selected_ids or not genre_ids:
            return
        if genre_ids[0] == Type.PLAYLISTS:
            view = self._get_view_playlists(selected_ids)
        elif genre_ids[0] == Type.YEARS:
            view = self.__get_view_albums_years(selected_ids)
        elif selected_ids[0] == Type.COMPILATIONS:
            view = self.__get_view_albums(genre_ids, selected_ids)
        else:
            view = self.__get_view_artists(genre_ids, selected_ids)
        self._stack.add(view)
        self._stack.set_visible_child(view)

    def __on_pass_focus(self, selection_list):
        """
            Pass focus to other list
            @param selection_list as SelectionList
        """
        if selection_list == self._list_one:
            if self._list_two.is_visible():
                self._list_two.grab_focus()
        else:
            self._list_one.grab_focus()
