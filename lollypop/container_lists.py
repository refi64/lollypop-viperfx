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

from gi.repository import GLib

from gettext import gettext as _

from lollypop.loader import Loader
from lollypop.logger import Logger
from lollypop.selectionlist import SelectionList
from lollypop.define import App, Type, SelectionListMask


class ListsContainer:
    """
        Selections lists management for main view
    """

    def __init__(self):
        """
            Init container
        """
        self._list_one = SelectionList(SelectionListMask.LIST_ONE)
        self._list_two = SelectionList(SelectionListMask.LIST_TWO)
        self._list_one.connect("item-selected", self.__on_list_one_selected)
        self._list_one.connect("populated", self.__on_list_one_populated)
        self._list_one.connect("pass-focus", self.__on_pass_focus)
        self._list_two.connect("item-selected", self.__on_list_two_selected)
        self._list_two.connect("pass-focus", self.__on_pass_focus)

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
                self.__update_list_playlists(update, ids[0])
            elif App().settings.get_value("show-genres") and ids:
                self.__update_list_artists(self._list_two, ids, update)

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

##############
# PROTECTED  #
##############
    def _reload_list_view(self):
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

############
# PRIVATE  #
############
    def __update_list_playlists(self, update, type):
        """
            Setup list for playlists
            @param update as bool
            @param type as int
        """
        self._list_two.mark_as(SelectionListMask.PLAYLISTS)
        if type == Type.PLAYLISTS:
            items = self._list_two.get_playlist_headers()
            items += App().playlists.get()
        else:
            (years, unknown) = App().albums.get_years()
            items = [(year, str(year), str(year)) for year in sorted(years)]
            if unknown:
                items.insert(0, (Type.NONE, _("Unknown"), ""))
        if update:
            self._list_two.update_values(items)
        else:
            self._list_two.populate(items)

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
            self.__update_list_playlists(False, selected_ids[0])
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
        elif selected_ids[0] == Type.CURRENT:
            view = self._get_view_current()
        elif selected_ids[0] == Type.SEARCH:
            view = self._get_view_search()
        elif Type.DEVICES - 999 < selected_ids[0] < Type.DEVICES:
            view = self._get_view_device(selected_ids[0])
        elif selected_ids[0] in [Type.POPULARS,
                                 Type.LOVED,
                                 Type.RECENTS,
                                 Type.NEVER,
                                 Type.RANDOMS]:
            view = self._get_view_albums(selected_ids, [])
        elif selected_ids[0] == Type.RADIOS:
            view = self._get_view_radios()
        elif selected_ids[0] == Type.YEARS:
            view = self._get_view_albums_decades()
        elif selected_ids[0] == Type.ARTISTS:
            view = self._get_view_artists_rounded(False)
            App().window.emit("show-can-go-back", True)
        elif selection_list.mask & SelectionListMask.ARTISTS:
            if selected_ids[0] == Type.ALL:
                view = self._get_view_albums(selected_ids, [])
            elif selected_ids[0] == Type.COMPILATIONS:
                view = self._get_view_albums([], selected_ids)
            else:
                view = self._get_view_artists([], selected_ids)
        else:
            view = self._get_view_albums(selected_ids, [])
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

    def __on_list_one_populated(self, selection_list):
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
            view = self._get_view_albums_years(selected_ids)
        elif selected_ids[0] == Type.COMPILATIONS:
            view = self._get_view_albums(genre_ids, selected_ids)
        else:
            view = self._get_view_artists(genre_ids, selected_ids)
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
