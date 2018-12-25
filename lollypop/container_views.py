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

from lollypop.shown import ShownLists
from lollypop.loader import Loader
from lollypop.objects import Track, Album
from lollypop.view import View
from lollypop.define import App, Type, RowListType, SelectionListMask


class ViewsContainer:
    """
        Views management for main view
    """

    def __init__(self):
        """
            Init container
        """
        pass

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
            view = self._get_view_albums([item_id], [])
        elif item_id == Type.SEARCH:
            view = self._get_view_search()
        elif item_id == Type.INFO:
            view = self._get_view_info()
        elif item_id == Type.YEARS:
            if data is None:
                view = self._get_view_albums_decades()
            else:
                view = self._get_view_albums_years(data)
        elif item_id == Type.PLAYLISTS:
            view = self._get_view_playlists([] if data is None else data)
        elif item_id == Type.COMPILATIONS:
            view = self._get_view_albums([], [item_id])
        elif item_id == Type.RADIOS:
            view = self._get_view_radios()
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
            view = self._get_view_artists([], [item_id])
        view.show()
        self._stack.add(view)
        if switch:
            self._stack.set_visible_child(view)

##############
# PROTECTED  #
##############
    def _get_view_playlists(self, playlist_ids=[]):
        """
            Get playlists view for playlists
            @param playlist ids as [int]
            @return View
        """
        def load():
            tracks = []
            all_ids = []
            for playlist_id in playlist_ids:
                if playlist_id == Type.LOVED:
                    ids = App().tracks.get_loved_track_ids()
                else:
                    ids = App().playlists.get_track_ids(playlist_id)
                for id in ids:
                    if id in all_ids:
                        continue
                    all_ids.append(id)
                    track = Track(id)
                    tracks.append(track)
            return tracks

        def load_smart():
            tracks = []
            request = App().playlists.get_smart_sql(playlist_ids[0])
            ids = App().db.execute(request)
            for id in ids:
                track = Track(id)
                # Smart playlist may report invalid tracks
                # An album always have an artist so check
                # object is valid. Others Lollypop widgets assume
                # objects are valid
                if not track.album.artist_ids:
                    continue
                tracks.append(track)
            return tracks

        if App().window.is_adaptive:
            list_type = RowListType.DND
        else:
            list_type = RowListType.TWO_COLUMNS |\
                        RowListType.DND |\
                        RowListType.PLAYLISTS
        if len(playlist_ids) == 1 and\
                App().playlists.get_smart(playlist_ids[0]):
            from lollypop.view_playlists import PlaylistsView
            view = PlaylistsView(playlist_ids, list_type)
            loader = Loader(target=load_smart, view=view)
            loader.start()
        elif playlist_ids:
            from lollypop.view_playlists import PlaylistsView
            if len(playlist_ids) > 1:
                list_type |= RowListType.READ_ONLY
            view = PlaylistsView(playlist_ids, list_type)
            loader = Loader(target=load, view=view)
            loader.start()
        else:
            from lollypop.view_playlists_manager import PlaylistsManagerView
            view = PlaylistsManagerView()
            view.populate(App().playlists.get_ids())
        view.show()
        return view

    def _get_view_artists_rounded(self, static):
        """
            Get rounded artists view
            @return view
        """
        def load():
            ids = App().artists.get()
            compilations = App().albums.get_compilation_ids([])
            return (ids, compilations)

        def get_items(artist_ids, compilation_ids):
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
            return items

        def setup(artist_ids, compilation_ids):
            view.populate(get_items(artist_ids, compilation_ids))

        from lollypop.view_artists_rounded import RoundedArtistsView
        view = RoundedArtistsView()
        self._stack.add(view)
        loader = Loader(target=load, view=view,
                        on_finished=lambda r: setup(*r))
        loader.start()
        view.show()
        return view

    def _get_view_artists(self, genre_ids, artist_ids):
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

    def _get_view_albums_decades(self):
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
        if App().window.is_adaptive:
            view = View()
        else:
            from lollypop.view_albums_decade_box import AlbumsDecadeBoxView
            view = AlbumsDecadeBoxView()
            loader = Loader(target=load, view=view)
            loader.start()
        view.show()
        return view

    def _get_view_albums_years(self, years):
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
        if App().window.is_adaptive:
            from lollypop.view_albums_list import AlbumsListView
            view = AlbumsListView(RowListType.DEFAULT, years, [Type.YEARS])
        else:
            from lollypop.view_albums_box import AlbumsBoxView
            view = AlbumsBoxView([Type.YEARS], years)
        loader = Loader(target=load, view=view)
        loader.start()
        view.show()
        return view

    def _get_view_albums(self, genre_ids, artist_ids):
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

    def _get_view_radios(self):
        """
            Get radios view
            @return RadiosView
        """
        def load():
            from lollypop.radios import Radios
            radios = Radios()
            return radios.get_ids()
        from lollypop.view_radios import RadiosView
        view = RadiosView()
        loader = Loader(target=load, view=view)
        loader.start()
        view.show()
        return view

    def _get_view_info(self):
        """
            Get view for information
            @return InformationView
        """
        from lollypop.view_information import InformationView
        view = InformationView(True)
        view.populate()
        view.set_margin_top(5)
        view.set_margin_start(5)
        view.set_margin_end(5)
        view.show()
        return view

    def _get_view_search(self):
        """
            Get view for search
            @return SearchView
        """
        from lollypop.view_search import SearchView
        view = SearchView()
        view.set_margin_top(5)
        view.set_margin_start(5)
        view.set_margin_end(5)
        view.show()
        return view

    def _get_view_current(self):
        """
            Get view for current playlist
            @return View
        """
        if App().player.playlist_ids:
            from lollypop.view_playlists import PlaylistsView
            view = PlaylistsView(App().player.playlist_ids,
                                 RowListType.DND | RowListType.POPOVER,
                                 False)
            view.populate(App().player.playlist_tracks)
        else:
            from lollypop.view_current_albums import CurrentAlbumsView
            view = CurrentAlbumsView()
            view.populate(App().player.albums)
        view.set_margin_top(5)
        view.set_margin_start(5)
        view.set_margin_end(5)
        view.show()
        return view

    def _reload_navigation_view(self):
        """
            Reload navigation view
        """
        App().window.emit("show-can-go-back", True)
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
        # Be sure to have an initial artist view
        if self._rounded_artists_view is None:
            self._rounded_artists_view = self._get_view_artists_rounded(True)
            self._stack.set_visible_child(self._rounded_artists_view)
        if state_one_ids and state_two_ids:
            self.show_view(state_one_ids[0], None, False)
            self.show_view(state_one_ids[0], state_two_ids)
        elif state_one_ids and state_one_ids[0] != Type.ARTISTS:
            self.show_view(state_one_ids[0])
        elif state_two_ids:
            self.show_view(state_two_ids[0])
        else:
            App().window.emit("can-go-back-changed", False)
            self._stack.set_visible_child(self._rounded_artists_view)

############
# PRIVATE  #
############
