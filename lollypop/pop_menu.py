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

from gi.repository import Gio, GLib, Gtk

from gettext import gettext as _

from lollypop.widgets_rating import RatingWidget
from lollypop.widgets_loved import LovedWidget
from lollypop.define import App, Type
from lollypop.objects import Track, Album
from lollypop.logger import Logger
from lollypop.helper_task import TaskHelper


class BaseMenu(Gio.Menu):
    """
        Base menu for all menus
    """

    def __init__(self, object):
        """
            Init variable
            @param object as Album/Track
        """
        Gio.Menu.__init__(self)
        self._object = object


class ArtistMenu(BaseMenu):
    """
        Contextual menu for artist
    """

    def __init__(self, object):
        """
            Init playlists menu
            @param object as Album/Track
        """
        BaseMenu.__init__(self, object)
        if self.__filter_artist_ids():
            self.__set_artists_actions()

#######################
# PRIVATE             #
#######################
    def __filter_artist_ids(self):
        """
            Remove static entries
            @return [int]
        """
        artist_ids = []
        for artist_id in self._object.artist_ids:
            if artist_id > 0:
                artist_ids.append(artist_id)
        return artist_ids

    def __set_artists_actions(self):
        """
            Set queue actions
        """
        go_artist_action = Gio.SimpleAction(name="go_artist_action")
        App().add_action(go_artist_action)
        go_artist_action.connect("activate",
                                 self.__go_to_artists)
        self.append(_("Show albums from artist"), "app.go_artist_action")

    def __go_to_artists(self, action, variant):
        """
            Show albums from artists
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        App().window.container.show_artists_albums(self.__filter_artist_ids())


class QueueMenu(BaseMenu):
    """
        Contextual menu for queue
    """

    def __init__(self, track):
        """
            Init playlists menu
            @param track as Track
        """
        BaseMenu.__init__(self, track)
        self.__set_queue_actions()

#######################
# PRIVATE             #
#######################
    def __set_queue_actions(self):
        """
            Set queue actions
        """
        if self._object.id not in App().player.queue:
            append_queue_action = Gio.SimpleAction(name="append_queue_action")
            App().add_action(append_queue_action)
            append_queue_action.connect("activate",
                                        self.__append_to_queue)
            self.append(_("Add to queue"), "app.append_queue_action")
        else:
            del_queue_action = Gio.SimpleAction(name="del_queue_action")
            App().add_action(del_queue_action)
            del_queue_action.connect("activate",
                                     self.__del_from_queue)
            self.append(_("Remove from queue"), "app.del_queue_action")

    def __append_to_queue(self, action, variant):
        """
            Append track to queue
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        App().player.append_to_queue(self._object.id, False)
        App().player.emit("queue-changed")

    def __del_from_queue(self, action, variant):
        """
            Delete track id from queue
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        App().player.del_from_queue(self._object.id, False)
        App().player.emit("queue-changed")


class PlaylistsMenu(BaseMenu):
    """
        Contextual menu for playlists
    """

    def __init__(self, object):
        """
            Init playlist menu
            @param object as Album/Track
        """
        BaseMenu.__init__(self, object)
        self.__set_playlist_actions()

#######################
# PRIVATE             #
#######################
    def __set_playlist_actions(self):
        """
            Set playlist actions
        """
        playlist_action = Gio.SimpleAction(name="playlist_action")
        App().add_action(playlist_action)
        playlist_action.connect("activate",
                                self.__add_to_playlists)
        self.append(_("Add to others"), "app.playlist_action")

        playlist_action = Gio.SimpleAction(name="playlist_not_in_party")
        App().add_action(playlist_action)
        if isinstance(self._object, Album):
            exists = App().playlists.exists_album(Type.NOPARTY,
                                                  self._object)
        else:
            exists = App().playlists.exists_track(Type.NOPARTY,
                                                  self._object)
        if exists:
            self.append(_('Remove from "Not in party"'),
                        "app.playlist_not_in_party")
            playlist_action.connect("activate",
                                    self.__remove_from_playlist, Type.NOPARTY)
        else:
            self.append(_('Add to "Not in party"'),
                        "app.playlist_not_in_party")
            playlist_action.connect("activate",
                                    self.__add_to_playlist, Type.NOPARTY)

        i = 0
        for playlist in App().playlists.get_last():
            action = Gio.SimpleAction(name="playlist%s" % i)
            App().add_action(action)
            if isinstance(self._object, Album):
                exists = App().playlists.exists_album(playlist[0],
                                                      self._object)
            else:
                exists = App().playlists.exists_track(playlist[0],
                                                      self._object)
            if exists:
                action.connect("activate",
                               self.__remove_from_playlist,
                               playlist[0])
                self.append(_("Remove from \"%s\"") % playlist[1],
                            "app.playlist%s" % i)
            else:
                action.connect("activate",
                               self.__add_to_playlist,
                               playlist[0])
                self.append(_("Add to \"%s\"") % playlist[1],
                            "app.playlist%s" % i)
            i += 1

    def __add_to_playlists(self, action, variant):
        """
            Add to playlists
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        App().window.container.show_playlist_manager(self._object)

    def __add_to_playlist(self, action, variant, playlist_id):
        """
            Add to playlist
            @param Gio.SimpleAction
            @param GLib.Variant
            @param playlist id as int
        """
        def add(playlist_id):
            tracks = []
            if isinstance(self._object, Album):
                track_ids = App().albums.get_track_ids(self._object.id,
                                                       self._object.genre_ids,
                                                       self._object.artist_ids)
                for track_id in track_ids:
                    tracks.append(Track(track_id))
            else:
                tracks = [Track(self._object.id)]
            App().playlists.add_tracks(playlist_id, tracks)
            if playlist_id in App().player.get_playlist_ids():
                App().player.update_playlist(
                    App().playlists.get_track_ids(playlist_id))
        helper = TaskHelper()
        helper.run(add, playlist_id)

    def __remove_from_playlist(self, action, variant, playlist_id):
        """
            Del from playlist
            @param Gio.SimpleAction
            @param GLib.Variant
            @param object id as int
            @param is album as bool
            @param playlist id as int
        """
        def remove(playlist_id):
            tracks = []
            if isinstance(self._object, Album):
                track_ids = App().albums.get_track_ids(self._object.id,
                                                       self._object.genre_ids,
                                                       self._object.artist_ids)
                for track_id in track_ids:
                    tracks.append(Track(track_id))
            else:
                tracks = [Track(self._object.id)]
            App().playlists.remove_tracks(playlist_id, tracks)
            if playlist_id in App().player.get_playlist_ids():
                App().player.update_playlist(
                    App().playlists.get_track_ids(playlist_id))
        helper = TaskHelper()
        helper.run(remove, playlist_id)

    def __add_to_loved(self, action, variant):
        """
            Add to loved
            @param Gio.SimpleAction
            @param GLib.Variant
            @param playlist name as str
        """
        self._object.set_loved(True)

    def __del_from_loved(self, action, variant):
        """
            Remove from loved
            @param Gio.SimpleAction
            @param GLib.Variant
            @param playlist name as str
        """
        self._object.set_loved(False)


class ToolbarMenu(BaseMenu):
    """
        Contextual menu for toolbar
    """

    def __init__(self, track):
        """
            Init menu
            @param track as Track
        """
        BaseMenu.__init__(self, track)
        lyrics_menu = Gio.Menu()
        action = Gio.SimpleAction(name="lyrics_action")
        App().add_action(action)
        action.connect("activate", self.__show_lyrics)
        lyrics_menu.append(_("Show lyrics"), "app.lyrics_action")
        self.insert_section(0, _("Lyrics"), lyrics_menu)
        if track.id >= 0:
            playlist_menu = PlaylistsMenu(track)
            self.insert_section(1, _("Playlists"), playlist_menu)

#######################
# PRIVATE             #
#######################
    def __show_lyrics(self, action, variant):
        """
            Show lyrics on main window
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        App().window.container.show_lyrics()


class EditMenu(BaseMenu):
    """
        Edition menu for album
    """

    def __init__(self, object):
        """
            Init edit menu
            @param object as Album/Track
        """
        # Ignore genre_ids/artist_ids
        if isinstance(object, Album):
            obj = Album(object.id)
        else:
            obj = Track(object.id)
        BaseMenu.__init__(self, obj)
        if App().art.tag_editor:
            self.__set_edit_actions()

#######################
# PRIVATE             #
#######################
    def __set_edit_actions(self):
        """
            Set edit actions
        """
        edit_tag_action = Gio.SimpleAction(name="edit_tag_action")
        App().add_action(edit_tag_action)
        edit_tag_action.connect("activate", self.__edit_tag)
        self.append(_("Modify information"), "app.edit_tag_action")

    def __edit_tag(self, action, variant):
        """
            Run tag editor
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        path = GLib.filename_from_uri(self._object.uri)[0]
        if GLib.find_program_in_path("flatpak-spawn") is not None:
            argv = ["flatpak-spawn", "--host", App().art.tag_editor, path]
        else:
            argv = [App().art.tag_editor, path]
        try:
            (pid, stdin, stdout, stderr) = GLib.spawn_async(
                argv, flags=GLib.SpawnFlags.SEARCH_PATH |
                GLib.SpawnFlags.STDOUT_TO_DEV_NULL,
                standard_input=False,
                standard_output=False,
                standard_error=False
            )
        except Exception as e:
            Logger.error("MenuPopover::__edit_tag(): %s" % e)


class AlbumMenu(Gio.Menu):
    """
        Contextual menu for album
    """

    def __init__(self, album, show_artist=False):
        """
            Init menu model
            @param album as Album
            @param show artist menu as bool
        """
        Gio.Menu.__init__(self)
        if show_artist:
            self.insert_section(0, _("Artist"),
                                ArtistMenu(album))
        self.insert_section(2, _("Playlists"),
                            PlaylistsMenu(album))
        self.insert_section(3, _("Edit"),
                            EditMenu(album))


class TrackMenu(Gio.Menu):
    """
        Contextual menu for a track
    """

    def __init__(self, track, show_artist=False):
        """
            Init menu model
            @param track as Track
            @param show artist menu as bool
        """
        Gio.Menu.__init__(self)
        if show_artist:
            self.insert_section(0, _("Artist"),
                                ArtistMenu(track))
        self.insert_section(1, _("Queue"),
                            QueueMenu(track))
        self.insert_section(2, _("Playlists"),
                            PlaylistsMenu(track))
        self.insert_section(3, _("Edit"),
                            EditMenu(track))


class TrackMenuPopover(Gtk.Popover):
    """
        Contextual menu widget for a track
    """

    def __init__(self, track, menu):
        """
            Init widget
            @param track as Track
            @param menu as Gio.Menu
        """
        Gtk.Popover.__init__(self)
        if menu is not None:
            self.bind_model(menu, None)
        # FIXME Does it works? => year in popover
        if track.year != track.album.year:
            track_year = str(track.year)
        else:
            track_year = ""

        if track_year != "":
            year = Gtk.Label()
            year.set_text(track_year)
            year.set_margin_end(5)
            year.get_style_context().add_class("dim-label")
            year.set_property("halign", Gtk.Align.END)
            year.set_property("hexpand", True)
            year.show()

        # Hack to add two widgets in popover
        grid = Gtk.Grid()
        grid.set_orientation(Gtk.Orientation.VERTICAL)

        stack = Gtk.Stack()
        stack.add_named(grid, "main")
        stack.show_all()

        menu_widget = self.get_child()
        if menu_widget is not None:
            self.remove(menu_widget)
            grid.add(menu_widget)

        hgrid = Gtk.Grid()
        hgrid.get_style_context().add_class("popover-rating-loved-grid")
        rating = RatingWidget(track)
        rating.set_property("halign", Gtk.Align.START)
        rating.set_margin_end(10)
        rating.show()

        loved = LovedWidget(track)
        loved.set_property("halign", Gtk.Align.START)
        loved.set_property("hexpand", True)
        loved.show()

        hgrid.add(rating)
        hgrid.add(loved)

        if track_year != "":
            hgrid.add(year)
        hgrid.show()

        grid.add(hgrid)
        self.add(stack)

#######################
# PRIVATE             #
#######################
    def __on_edit_changed(self, edit, track_id):
        """
            Update track uri
            @param edit as Gtk.Edit
            @param track id as int
        """
        App().tracks.set_uri(track_id, edit.get_text())
