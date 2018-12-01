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

from lollypop.loader import Loader
from lollypop.objects import Track
from lollypop.define import App, Type, RowListType


class PlaylistsContainer:
    """
        Playlists management for main view
    """

    def __init__(self):
        """
            Init container
        """
        App().playlists.connect("playlists-changed", self.__update_playlists)

    def show_playlist_manager(self, obj):
        """
            Show playlist manager for object_id
            Current view stay present in ViewContainer
            @param obj as Track/Album
        """
        from lollypop.view_playlists_manager import PlaylistsManagerView
        current = self._stack.get_visible_child()
        view = PlaylistsManagerView(obj)
        view.populate(App().playlists.get_ids())
        view.show()
        self._stack.add(view)
        App().window.container.stack.set_navigation_enabled(True)
        self._stack.set_visible_child(view)
        App().window.container.stack.set_navigation_enabled(False)
        current.disable_overlay()

    def show_smart_playlist_editor(self, playlist_id):
        """
            Show a view allowing user to edit smart view
            @param playlist_id as int
        """
        App().window.emit("can-go-back-changed", True)
        from lollypop.view_playlist_smart import SmartPlaylistView
        current = self._stack.get_visible_child()
        view = SmartPlaylistView(playlist_id)
        view.populate()
        view.show()
        self._stack.add(view)
        App().window.container.stack.set_navigation_enabled(True)
        self._stack.set_visible_child(view)
        App().window.container.stack.set_navigation_enabled(False)
        current.disable_overlay()

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

        self.stop_current_view()
        if len(playlist_ids) == 1 and\
                App().playlists.get_smart(playlist_ids[0]):
            from lollypop.view_playlists import PlaylistsView
            view = PlaylistsView(playlist_ids,
                                 RowListType.TWO_COLUMNS | RowListType.DND)
            loader = Loader(target=load_smart, view=view)
            loader.start()
        elif playlist_ids:
            from lollypop.view_playlists import PlaylistsView
            if len(playlist_ids) == 1:
                list_type = RowListType.TWO_COLUMNS | RowListType.DND
            else:
                list_type = RowListType.TWO_COLUMNS | RowListType.READ_ONLY
            view = PlaylistsView(playlist_ids, list_type)
            loader = Loader(target=load, view=view)
            loader.start()
        else:
            from lollypop.view_playlists_manager import PlaylistsManagerView
            view = PlaylistsManagerView()
            view.populate(App().playlists.get_ids())
        view.show()
        return view

############
# PRIVATE  #
############
    def __update_playlists(self, playlists, playlist_id):
        """
            Update playlists in second list
            @param playlists as Playlists
            @param playlist_id as int
        """
        ids = self._list_one.selected_ids
        if ids and ids[0] == Type.PLAYLISTS:
            if App().playlists.exists(playlist_id):
                self._list_two.update_value(playlist_id,
                                            App().playlists.get_name(
                                                 playlist_id))
            else:
                self._list_two.remove_value(playlist_id)
