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

from gi.repository import Gio, GLib, Gtk

from gettext import gettext as _
from threading import Thread
from time import time

from lollypop.widgets_rating import RatingWidget
from lollypop.widgets_loved import LovedWidget
from lollypop.define import Lp, Type
from lollypop.sqlcursor import SqlCursor
from lollypop.objects import Track, Album
from lollypop.utils import set_loved
from lollypop.helper_dbus import DBusHelper


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
        Contextual menu for queue
    """

    def __init__(self, object):
        """
            Init playlists menu
            @param object as Album/Track
        """
        BaseMenu.__init__(self, object)
        self.__set_artists_actions()

#######################
# PRIVATE             #
#######################
    def __set_artists_actions(self):
        """
            Set queue actions
        """
        go_artist_action = Gio.SimpleAction(name="go_artist_action")
        Lp().add_action(go_artist_action)
        go_artist_action.connect("activate",
                                 self.__go_to_artists)
        self.append(_("Show albums from artist"), "app.go_artist_action")

    def __go_to_artists(self, action, variant):
        """
            Show albums from artists
            @param SimpleAction
            @param GVariant
        """
        Lp().window.show_artists_albums(self._object.artist_ids)


class QueueMenu(BaseMenu):
    """
        Contextual menu for queue
    """

    def __init__(self, object):
        """
            Init playlists menu
            @param object as Album/Track
        """
        BaseMenu.__init__(self, object)
        self.__set_queue_actions()

#######################
# PRIVATE             #
#######################
    def __set_queue_actions(self):
        """
            Set queue actions
        """
        queue = Lp().player.queue
        append = True
        prepend = True
        delete = True
        if not queue:
            append = False
        if not isinstance(self._object, Album):
            if self._object.id in queue:
                if queue and queue[0] == self._object.id:
                    prepend = False
                append = False
            else:
                delete = False
        else:
            tracks = Lp().albums.get_track_ids(self._object.id,
                                               self._object.genre_ids,
                                               self._object.artist_ids)
            union = set(queue) & set(tracks)
            if len(union) == len(tracks):
                append = False
                prepend = False
            elif not bool(union):
                delete = False

        append_queue_action = Gio.SimpleAction(name="append_queue_action")
        Lp().add_action(append_queue_action)
        prepend_queue_action = Gio.SimpleAction(name="prepend_queue_action")
        Lp().add_action(prepend_queue_action)
        del_queue_action = Gio.SimpleAction(name="del_queue_action")
        Lp().add_action(del_queue_action)
        if append:
            append_queue_action.connect("activate",
                                        self.__append_to_queue)
            self.append(_("Add to queue"), "app.append_queue_action")
        if prepend:
            prepend_queue_action.connect("activate",
                                         self.__insert_in_queue)
            if isinstance(self._object, Album):
                self.append(_("Next tracks"), "app.prepend_queue_action")
            else:
                self.append(_("Next track"), "app.prepend_queue_action")
        if delete:
            del_queue_action.connect("activate",
                                     self.__del_from_queue)
            self.append(_("Remove from queue"), "app.del_queue_action")

    def __append_to_queue(self, action, variant):
        """
            Append track to queue
            @param SimpleAction
            @param GVariant
        """
        if isinstance(self._object, Album):
            for track_id in Lp().albums.get_track_ids(self._object.id,
                                                      self._object.genre_ids,
                                                      self._object.artist_ids):
                Lp().player.append_to_queue(track_id, False)
        else:
            Lp().player.append_to_queue(self._object.id, False)
        Lp().player.emit("queue-changed")

    def __insert_in_queue(self, action, variant):
        """
            Prepend track id to queue
            @param SimpleAction
            @param GVariant
        """
        if isinstance(self._object, Album):
            for track_id in reversed(Lp().albums.get_track_ids(
                                                     self._object.id,
                                                     self._object.genre_ids,
                                                     self._object.artist_ids)):
                Lp().player.insert_in_queue(track_id, 0, False)
        else:
            Lp().player.insert_in_queue(self._object.id, 0, False)
        Lp().player.emit("queue-changed")

    def __del_from_queue(self, action, variant):
        """
            Delete track id from queue
            @param SimpleAction
            @param GVariant
        """
        if isinstance(self._object, Album):
            for track_id in Lp().albums.get_track_ids(self._object.id,
                                                      self._object.genre_ids,
                                                      self._object.artist_ids):
                Lp().player.del_from_queue(track_id, False)
        else:
            Lp().player.del_from_queue(self._object.id, False)
        Lp().player.emit("queue-changed")


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
        Lp().add_action(playlist_action)
        playlist_action.connect("activate",
                                self.__add_to_playlists)
        self.append(_("Add to others"), "app.playlist_action")

        playlist_action = Gio.SimpleAction(name="playlist_not_in_party")
        Lp().add_action(playlist_action)
        if isinstance(self._object, Album):
            exists = Lp().playlists.exists_album(Type.NOPARTY,
                                                 self._object.id,
                                                 self._object.genre_ids,
                                                 self._object.artist_ids)
        else:
            exists = Lp().playlists.exists_track(Type.NOPARTY,
                                                 self._object.id)
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
        for playlist in Lp().playlists.get_last():
            action = Gio.SimpleAction(name="playlist%s" % i)
            Lp().add_action(action)
            if isinstance(self._object, Album):
                exists = Lp().playlists.exists_album(playlist[0],
                                                     self._object.id,
                                                     self._object.genre_ids,
                                                     self._object.artist_ids)
            else:
                exists = Lp().playlists.exists_track(playlist[0],
                                                     self._object.id)
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
            @param SimpleAction
            @param GVariant
        """
        Lp().window.show_playlist_manager(self._object.id,
                                          self._object.genre_ids,
                                          self._object.artist_ids,
                                          isinstance(self._object, Album))

    def __add_to_playlist(self, action, variant, playlist_id):
        """
            Add to playlist
            @param SimpleAction
            @param GVariant
            @param playlist id as int
        """
        def add(playlist_id):
            tracks = []
            if isinstance(self._object, Album):
                track_ids = Lp().albums.get_track_ids(self._object.id,
                                                      self._object.genre_ids,
                                                      self._object.artist_ids)
                for track_id in track_ids:
                    tracks.append(Track(track_id))
            else:
                tracks = [Track(self._object.id)]
            Lp().playlists.add_tracks(playlist_id, tracks)
            if playlist_id in Lp().player.get_user_playlist_ids():
                Lp().player.update_user_playlist(
                                     Lp().playlists.get_track_ids(playlist_id))
        t = Thread(target=add, args=(playlist_id,))
        t.daemon = True
        t.start()

    def __remove_from_playlist(self, action, variant, playlist_id):
        """
            Del from playlist
            @param SimpleAction
            @param GVariant
            @param object id as int
            @param is album as bool
            @param playlist id as int
        """
        def remove(playlist_id):
            tracks = []
            if isinstance(self._object, Album):
                track_ids = Lp().albums.get_track_ids(self._object.id,
                                                      self._object.genre_ids,
                                                      self._object.artist_ids)
                for track_id in track_ids:
                    tracks.append(Track(track_id))
            else:
                tracks = [Track(self._object.id)]
            Lp().playlists.remove_tracks(playlist_id, tracks)
            if playlist_id in Lp().player.get_user_playlist_ids():
                Lp().player.update_user_playlist(
                                     Lp().playlists.get_track_ids(playlist_id))
        t = Thread(target=remove, args=(playlist_id,))
        t.daemon = True
        t.start()

    def __add_to_loved(self, action, variant):
        """
            Add to loved
            @param SimpleAction
            @param GVariant
            @param playlist name as str
        """
        set_loved(self._object.id, True)

    def __del_from_loved(self, action, variant):
        """
            Remove from loved
            @param SimpleAction
            @param GVariant
            @param playlist name as str
        """
        set_loved(self._object.id, False)


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

        if self._object.is_web:
            self.__set_remove_action()
        else:
            dbus_helper = DBusHelper()
            dbus_helper.call("CanLaunchTagEditor", None,
                             self.__on_can_launch_tag_editor, None)

#######################
# PRIVATE             #
#######################
    def __set_remove_action(self):
        """
            Remove album
        """
        remove_action = Gio.SimpleAction(name="remove_action")
        Lp().add_action(remove_action)
        remove_action.connect("activate", self.__remove_object)
        if isinstance(self._object, Album):
            self.append(_("Remove album"), "app.remove_action")
        else:
            self.append(_("Remove track"), "app.remove_action")

    def __set_edit_actions(self):
        """
            Set edit actions
        """
        edit_tag_action = Gio.SimpleAction(name="edit_tag_action")
        Lp().add_action(edit_tag_action)
        edit_tag_action.connect("activate", self.__edit_tag)
        self.append(_("Modify information"), "app.edit_tag_action")

    def __remove_object(self, action, variant):
        """
            Remove album
            @param SimpleAction
            @param GVariant
        """
        self._object.remove()

    def __edit_tag(self, action, variant):
        """
            Run tag editor
            @param SimpleAction
            @param GVariant
        """
        path = GLib.filename_from_uri(self._object.uri)[0]
        dbus_helper = DBusHelper()
        dbus_helper.call("LaunchTagEditor", GLib.Variant("(s)", (path,)),
                         None, None)

    def __on_can_launch_tag_editor(self, source, result, data):
        """
            Add action if launchable
            @param source as GObject.Object
            @param result as Gio.AsyncResult
            @param data as object
        """
        try:
            if source.call_finish(result)[0]:
                self.__set_edit_actions()
        except Exception as e:
            print("EditMenu::__on_can_launch_tag_editor():", e)


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
        self.insert_section(1, _("Queue"),
                            QueueMenu(album))
        self.insert_section(2, _("Playlists"),
                            PlaylistsMenu(album))
        self.insert_section(3, _("Edit"),
                            EditMenu(album))


class TrackMenu(Gio.Menu):
    """
        Contextual menu for a track
    """

    def __init__(self, track):
        """
            Init menu model
            @param track as Track
        """
        Gio.Menu.__init__(self)
        self.insert_section(0, _("Queue"),
                            QueueMenu(track))
        self.insert_section(1, _("Playlists"),
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

        if track.year != track.album.year:
            track_year = str(track.year)
        else:
            track_year = ""

        if track_year != "":
            year = Gtk.Label()
            year.set_text(track_year)
            year.set_margin_end(5)
            year.set_margin_top(5)
            year.set_margin_bottom(5)
            year.get_style_context().add_class("dim-label")
            year.set_property("halign", Gtk.Align.END)
            year.set_property("hexpand", True)
            year.show()

        if track.album.is_web:
            uri = Lp().tracks.get_uri(track.id)
            web = Gtk.LinkButton(uri)
            icon = Gtk.Image.new_from_icon_name("web-browser-symbolic",
                                                Gtk.IconSize.MENU)
            web.set_image(icon)
            web.get_style_context().add_class("no-padding")
            web.set_margin_end(5)
            web.set_tooltip_text(uri)
            web.show_all()
            uri = "https://www.youtube.com/results?search_query=%s" %\
                (track.artists[0] + " " + track.name,)
            search = Gtk.LinkButton(uri)
            icon = Gtk.Image.new_from_icon_name("edit-find-symbolic",
                                                Gtk.IconSize.MENU)
            search.set_image(icon)
            search.get_style_context().add_class("no-padding")
            search.set_margin_end(5)
            search.set_tooltip_text(uri)
            search.show_all()

        # Hack to add two widgets in popover
        # Use a Gtk.PopoverMenu later (GTK>3.16 available on Debian stable)
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
        if Type.CHARTS not in track.genre_ids:
            if not track.album.is_web:
                separator = Gtk.Separator()
                separator.show()
                grid.add(separator)

            rating = RatingWidget(track)
            rating.set_margin_top(5)
            rating.set_margin_bottom(5)
            rating.set_property("halign", Gtk.Align.START)
            rating.set_property("hexpand", True)
            rating.show()

            loved = LovedWidget(track)
            loved.set_margin_end(5)
            loved.set_margin_top(5)
            loved.set_margin_bottom(5)
            if track_year == "":
                loved.set_property("halign", Gtk.Align.END)
            else:
                loved.set_property("halign", Gtk.Align.CENTER)
            loved.set_property("hexpand", True)
            loved.show()

            hgrid.add(rating)
            hgrid.add(loved)

            if track.album.is_web:
                hgrid.add(web)
                hgrid.add(search)
            if track_year != "":
                hgrid.add(year)
            hgrid.show()

        if track.album.is_web:
            grid.set_row_spacing(2)
            uri = Lp().tracks.get_uri(track.id)
            edit = Gtk.Entry()
            edit.set_margin_start(5)
            edit.set_margin_end(5)
            edit.set_margin_bottom(5)
            edit.set_tooltip_text(_("Video address"))
            edit.set_property("hexpand", True)
            edit.set_text(uri)
            edit.connect("changed", self.__on_edit_changed, track.id)
            edit.show()
            grid.add(edit)
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
        Lp().tracks.set_uri(track_id, edit.get_text())


class AlbumMenuPopover(Gtk.Popover):
    """
        Contextual menu widget for a track
    """

    def __init__(self, album, menu):
        """
            Init widget
            @param album as album
            @param menu as Gio.Menu
        """
        Gtk.Popover.__init__(self)
        if menu is not None:
            self.bind_model(menu, None)

        edit = Gtk.Entry()
        edit.set_margin_start(5)
        edit.set_margin_end(5)
        edit.set_margin_bottom(5)
        edit.set_property("hexpand", True)
        edit.set_property("halign", Gtk.Align.CENTER)
        genres = ";".join(Lp().albums.get_genres(album.id))
        if not genres:
            genres = "Web"
        edit.set_text(genres)
        edit.show()

        save = Gtk.Button.new_from_icon_name("document-save-symbolic",
                                             Gtk.IconSize.MENU)
        save.set_margin_end(5)
        save.set_margin_bottom(5)
        save.set_property("hexpand", True)
        save.set_property("halign", Gtk.Align.CENTER)
        save.set_property("valign", Gtk.Align.CENTER)
        save.set_tooltip_text(_("Save genre"))
        save.connect("clicked", self.__on_clicked, edit, album)
        save.show()

        # Hack to add two widgets in popover
        # Use a Gtk.PopoverMenu later (GTK>3.16 available on Debian stable)
        grid = Gtk.Grid()
        grid.set_orientation(Gtk.Orientation.VERTICAL)

        stack = Gtk.Stack()
        stack.add_named(grid, "main")
        stack.show_all()

        menu_widget = self.get_child()
        if menu_widget is not None:
            self.remove(menu_widget)
            grid.add(menu_widget)
        # separator = Gtk.Separator()
        # separator.show()

        if menu is None:
            label = Gtk.Label.new(_("Save into collection"))
            label.show()
            grid.add(label)
        # grid.add(separator)
        hgrid = Gtk.Grid()
        hgrid.add(edit)
        hgrid.add(save)
        hgrid.show()
        grid.add(hgrid)
        self.add(stack)

#######################
# PRIVATE             #
#######################
    def __on_clicked(self, button, edit, album):
        """
            Save album genre
            @param button as Gtk.Button
            @param edit as Gtk.Edit
            @param album as Album
        """
        genres = edit.get_text()
        if not genres:
            return
        orig_genre_ids = Lp().albums.get_genre_ids(album.id)
        Lp().albums.del_genres(album.id)
        for track_id in album.track_ids:
                Lp().tracks.del_genres(track_id)
        for genre in genres.split(";"):
            genre_id = Lp().genres.get_id(genre)
            if genre_id is None:
                genre_id = Lp().genres.add(genre)
                Lp().scanner.emit("genre-updated", genre_id, True)
            Lp().albums.add_genre(album.id, genre_id, int(time()))
            for track_id in album.track_ids:
                Lp().tracks.add_genre(track_id, genre_id, int(time()))
        for genre_id in orig_genre_ids:
            if genre_id >= 0:
                Lp().genres.clean(genre_id)
                GLib.idle_add(Lp().scanner.emit, "genre-updated",
                              genre_id, False)
        with SqlCursor(Lp().db) as sql:
            sql.commit()
        Lp().scanner.emit("album-updated", album.id, True)
