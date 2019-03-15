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
from lollypop.define import App, ViewType
from lollypop.objects import Track, Album
from lollypop.widgets_utils import Popover
from lollypop.logger import Logger


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

    def __init__(self, object, view_type):
        """
            Init playlists menu
            @param object as Album/Track
            @param view_type as ViewType
        """
        BaseMenu.__init__(self, object)
        self.__set_artists_actions(view_type)

#######################
# PRIVATE             #
#######################
    def __set_artists_actions(self, view_type):
        """
            Set artist actions
            @param view_type as ViewType
        """
        if view_type & ViewType.ALBUM:
            go_artist_action = Gio.SimpleAction(name="go_artist_action")
            App().add_action(go_artist_action)
            go_artist_action.connect("activate",
                                     self.__go_to_artists)
            self.append(_("Available albums"), "app.go_artist_action")
        search_artist_action = Gio.SimpleAction(name="search_artist_action")
        App().add_action(search_artist_action)
        search_artist_action.connect("activate",
                                     self.__search_artist)
        self.append(_("Other albums"), "app.search_artist_action")

    def __search_artist(self, action, variant):
        """
            Search albums from artist
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        artist_name = App().artists.get_name(self._object.artist_ids[0])
        target = "web://%s" % artist_name
        App().lookup_action("search").activate(GLib.Variant("s", target))

    def __go_to_artists(self, action, variant):
        """
            Show albums from artists
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        App().window.container.show_artist_view(self._object.artist_ids)


class PlaybackMenu(BaseMenu):
    """
        Contextual menu for queue
    """

    def __init__(self, track):
        """
            Init playlists menu
            @param track as Track
        """
        BaseMenu.__init__(self, track)
        self.__set_playback_actions()
        self.__set_queue_actions()

#######################
# PRIVATE             #
#######################
    def __is_in_current_playlist(self):
        """
            Check if track in Player current playlist
            @return bool
        """
        if App().player.albums:
            for album in App().player.albums:
                if self._object.album.id == album.id:
                    if self._object.id in album.track_ids:
                        return True
        elif App().player.playlist_ids:
            if self._object.id in App().player.playlist_track_ids:
                return True
        return False

    def __set_playback_actions(self):
        """
            Set playback actions
        """
        if not self.__is_in_current_playlist():
            append_playback_action = Gio.SimpleAction(
                name="append_playback_action")
            App().add_action(append_playback_action)
            append_playback_action.connect("activate",
                                           self.__append_to_playback)
            self.append(_("Add to playback"), "app.append_playback_action")
        else:
            del_playback_action = Gio.SimpleAction(name="del_playback_action")
            App().add_action(del_playback_action)
            del_playback_action.connect("activate",
                                        self.__remove_from_playback)
            self.append(_("Remove from playback"), "app.del_playback_action")

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
                                     self.__remove_from_queue)
            self.append(_("Remove from queue"), "app.del_queue_action")

    def __append_to_playback(self, action, variant):
        """
            Append track to playback
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        albums = App().player.albums
        # If album last in list, merge
        if albums and albums[-1].id == self._object.album.id:
            albums[-1].insert_track(self._object)
            App().player.set_next()
        # Add album with only one track
        else:
            # We do not want to share same album with multiple user add
            # If needed, previous merge will do the job
            album = self._object.album.clone(True)
            album.set_tracks([self._object])
            if App().player.is_playing:
                App().player.add_album(album)
            else:
                App().player.play_album(album)

    def __remove_from_playback(self, action, variant):
        """
            Delete track id from playback
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        for album in App().player.albums:
            if album.id == self._object.album.id:
                if self._object.id in album.track_ids:
                    index = album.track_ids.index(self._object.id)
                    track = album.tracks[index]
                    album.remove_track(track)
                    break
        App().player.set_next()
        App().player.set_prev()

    def __append_to_queue(self, action, variant):
        """
            Append track to queue
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        App().player.append_to_queue(self._object.id, False)
        App().player.emit("queue-changed")

    def __remove_from_queue(self, action, variant):
        """
            Delete track id from queue
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        App().player.remove_from_queue(self._object.id, False)
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
        i = 0
        for playlist in App().playlists.get_last():
            action = Gio.SimpleAction(name="playlist%s" % i)
            App().add_action(action)
            if isinstance(self._object, Album):
                exists = App().playlists.exists_album(playlist[0],
                                                      self._object)
            else:
                exists = App().playlists.exists_track(playlist[0],
                                                      self._object.uri)
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
                for track_id in self._object.track_ids:
                    tracks.append(Track(track_id))
            else:
                tracks = [Track(self._object.id)]
            App().playlists.add_tracks(playlist_id, tracks, True)
            if playlist_id in App().player.playlist_ids:
                App().player.update_playlist(
                    App().playlists.get_track_ids(playlist_id))
        App().task_helper.run(add, playlist_id)

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
                for track_id in self._object.track_ids:
                    tracks.append(Track(track_id))
            else:
                tracks = [Track(self._object.id)]
            App().playlists.remove_tracks(playlist_id, tracks, True)
            if playlist_id in App().player.playlist_ids:
                App().player.update_playlist(
                    App().playlists.get_track_ids(playlist_id))
        App().task_helper.run(remove, playlist_id)

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
        self.insert_section(2, _("Artist"),
                            ArtistMenu(track, ViewType.ALBUM))

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
        if isinstance(object, Album):
            self.__set_save_action()
        if object.is_in_user_collection and App().art.tag_editor:
            self.__set_edit_action()

#######################
# PRIVATE             #
#######################
    def __set_save_action(self):
        """
            Set save action
        """
        if self._object.mtime == 0:
            save_action = Gio.SimpleAction(name="save_album_action")
            App().add_action(save_action)
            save_action.connect("activate", self.__save_to_collection, True)
            self.append(_("Save in collection"), "app.save_album_action")
        elif self._object.mtime == -1:
            save_action = Gio.SimpleAction(name="remove_album_action")
            App().add_action(save_action)
            save_action.connect("activate", self.__save_to_collection, False)
            self.append(_("Remove from collection"), "app.remove_album_action")

    def __set_edit_action(self):
        """
            Set edit action
        """
        edit_tag_action = Gio.SimpleAction(name="edit_tag_action")
        App().add_action(edit_tag_action)
        edit_tag_action.connect("activate", self.__edit_tag)
        self.append(_("Modify information"), "app.edit_tag_action")

    def __save_to_collection(self, action, variant, save):
        """
            Save album to collection
            @param Gio.SimpleAction
            @param GLib.Variant
            @param save as bool
        """
        self._object.save(save)

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

    def __init__(self, album, view_type):
        """
            Init menu model
            @param album as Album
            @param view_type as ViewType
        """
        Gio.Menu.__init__(self)
        self.insert_section(0, _("Artist"),
                            ArtistMenu(album, view_type))
        if album.mtime != 0:
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
        if show_artist and track.mtime != 0:
            self.insert_section(0, _("Artist"),
                                ArtistMenu(track))
        self.insert_section(1, _("Playback"),
                            PlaybackMenu(track))
        if track.mtime != 0:
            self.insert_section(2, _("Playlists"),
                                PlaylistsMenu(track))
        self.insert_section(3, _("Edit"),
                            EditMenu(track))


class RemoveMenuPopover(Gtk.PopoverMenu):
    """
        Contextual menu for removing Rows
    """

    def __init__(self, rows):
        """
            Init menu
            @param rows as [Row]
        """
        Gtk.PopoverMenu.__init__(self)
        self.__rows = rows
        button = Gtk.ModelButton.new()
        if len(rows) == 1:
            button.set_label(_("Remove track"))
        else:
            button.set_label(_("Remove tracks"))
        button.show()
        button.connect("clicked", self.__on_button_clicked)
        self.add(button)

#######################
# PRIVATE             #
#######################
    def __on_button_clicked(self, button):
        """
            Remove rows
            @param button as Gtk.ModelButton
        """
        from lollypop.widgets_row_dnd import DNDRow
        for r in self.__rows:
            DNDRow.destroy_track_row(r)


class TrackMenuPopover(Popover):
    """
        Contextual menu widget for a track
    """

    def __init__(self, track, menu):
        """
            Init widget
            @param track as Track
            @param menu as Gio.Menu
        """
        Popover.__init__(self)
        if menu is not None:
            self.bind_model(menu, None)

        if track.mtime == 0:
            return

        if track.year is not None:
            year_label = Gtk.Label.new()
            year_label.set_text(str(track.year))
            dt = GLib.DateTime.new_from_unix_local(track.timestamp)
            year_label.set_tooltip_text(dt.format(_("%Y-%m-%d")))
            year_label.set_margin_end(5)
            year_label.get_style_context().add_class("dim-label")
            year_label.set_property("halign", Gtk.Align.END)
            year_label.set_property("hexpand", True)
            year_label.show()

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

        if track.year is not None:
            hgrid.add(year_label)
        hgrid.show()

        if track.mtime in [-1, 0]:
            edit = Gtk.Entry()
            edit.set_margin_top(5)
            edit.set_margin_start(5)
            edit.set_margin_end(5)
            edit.set_margin_bottom(5)
            edit.set_property("hexpand", True)
            edit.set_text(track.uri)
            edit.connect("changed", self.__on_edit_changed, track)
            edit.show()
            grid.add(edit)

        grid.add(hgrid)
        self.add(stack)

#######################
# PRIVATE             #
#######################
    def __on_edit_changed(self, edit, track):
        """
            Update track uri
            @param edit as Gtk.Edit
            @param track as Track
        """
        from urllib.parse import urlparse
        text = edit.get_text()
        parsed = urlparse(text)
        if parsed.scheme not in ["http", "https", "web"]:
            text = "web://null"
        App().tracks.set_uri(track.id, text)
        track.reset("uri")
