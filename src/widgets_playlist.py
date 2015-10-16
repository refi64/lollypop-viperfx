# Copyright (c) 2014-2015 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import Gtk, GLib, Pango

from threading import Thread
from cgi import escape
from gettext import gettext as _

from lollypop.define import Lp, Type
from lollypop.cellrendereralbum import CellRendererAlbum
from lollypop.widgets_track import TracksWidget
from lollypop.objects import Track


class PlaylistWidget(Gtk.Bin):
    """
        Show playlist tracks/albums
    """

    def __init__(self, playlist_id):
        """
            Init playlist Widget
            @param playlist id as int
            @param playlist name as str
        """
        Gtk.Bin.__init__(self)
        self._playlist_id = playlist_id
        self._tracks1 = []
        self._tracks2 = []
        self._stop = False

        main_widget = Gtk.Grid()
        main_widget.set_property('margin', 10)
        main_widget.set_property('column-spacing', 10)
        main_widget.show()

        loved = playlist_id != Type.LOVED
        self._tracks_widget1 = TracksWidget(False, loved)
        self._tracks_widget2 = TracksWidget(False, loved)
        self._tracks_widget1.connect('activated',
                                     self._on_activated)
        self._tracks_widget2.connect('activated',
                                     self._on_activated)
        self._tracks_widget1.show()
        self._tracks_widget2.show()

        size_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
        size_group.add_widget(self._tracks_widget1)
        size_group.add_widget(self._tracks_widget2)

        main_widget.add(self._tracks_widget1)
        main_widget.add(self._tracks_widget2)
        self.add(main_widget)

    def populate_list_left(self, tracks, pos):
        """
            Populate left list
            @param track's ids as array of int
            @param track position as int
            @thread safe
        """
        self._stop = False
        GLib.idle_add(self._add_tracks,
                      tracks,
                      self._tracks_widget1,
                      pos)

    def populate_list_right(self, tracks, pos):
        """
            Populate right list
            @param track's ids as array of int
            @param track position as int
            @thread safe
        """
        self._stop = False
        GLib.idle_add(self._add_tracks,
                      tracks,
                      self._tracks_widget2,
                      pos)

    def update_playing_indicator(self):
        """
            Update playing indicator
        """
        self._tracks_widget1.update_playing(Lp.player.current_track.id)
        self._tracks_widget2.update_playing(Lp.player.current_track.id)

    def stop(self):
        """
            Stop loading
        """
        self._stop = True

    def clear(self):
        """
            Clear tracks
        """
        self._tracks = []
        for child in self._tracks_widget1.get_children():
            child.destroy()
        for child in self._tracks_widget2.get_children():
            child.destroy()

#######################
# PRIVATE             #
#######################
    def _add_tracks(self, tracks, widget, pos, previous_album_id=None):
        """
            Add tracks to list
            @param tracks id as array of [int]
            @param widget TracksWidget
            @param track position as int
            @param previous album id as int
        """
        if not tracks or self._stop:
            return

        track = Track(tracks.pop(0))
        name = escape(track.name)
        album = track.album

        if track.id is None:
            GLib.idle_add(self._add_tracks, tracks,
                          widget, pos + 1, previous_album_id)
            return

        # If we are listening to a compilation, prepend artist name
        if (album.artist_id == Type.COMPILATIONS or
                len(track.artist_ids) > 1 or
                album.artist_id not in track.artist_ids):
            name = "<b>%s</b>\n%s" % (escape(track.artist_names), name)

        if widget == self._tracks_widget1:
            self._tracks1.append(track)
        else:
            self._tracks2.append(track)

        if album.id != previous_album_id:
            widget.add_album(track.id, album, pos,
                             name, track.duration, None)
        else:
            widget.add_album(track.id, None, pos, name, track.duration, None)
        GLib.idle_add(self._add_tracks, tracks, widget, pos + 1, album.id)

    def _on_activated(self, widget, track_id):
        """
            On track activation, play track
            @param widget as TracksWidget
            @param track as Track
        """
        if Lp.player.is_party():
            Lp.player.load(Track(track_id))
        else:
            track = Lp.player.set_user_playlist(self._tracks1 + self._tracks2,
                                                track_id)
            Lp.player.set_user_playlist_id(self._playlist_id)
            if track is not None:
                Lp.player.load(track)


class PlaylistsManagerWidget(Gtk.Bin):
    """
        Widget for playlists management
    """

    def __init__(self, object_id, genre_id, is_album):
        """
            Init widget
            @param object id as int
            @param genre id as int
            @param is album as bool
        """
        Gtk.Bin.__init__(self)
        self._genre_id = genre_id
        self._object_id = object_id
        self._is_album = is_album
        self._deleted_path = None
        self._del_pixbuf = Gtk.IconTheme.get_default().load_icon(
            "list-remove-symbolic",
            22,
            0)

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/'
                                  'PlaylistsManagerWidget.ui')
        self._infobar = builder.get_object('infobar')
        self._infobar_label = builder.get_object('infobarlabel')

        self._model = Gtk.ListStore(bool, str, str, int)
        self._model.set_sort_column_id(1, Gtk.SortType.ASCENDING)
        self._model.set_sort_func(1, self._sort_items)

        self._view = builder.get_object('view')
        self._view.set_model(self._model)

        builder.connect_signals(self)

        self.add(builder.get_object('widget'))

        if self._object_id != Type.NONE:
            renderer0 = Gtk.CellRendererToggle()
            renderer0.set_property('activatable', True)
            renderer0.connect('toggled', self._on_playlist_toggled)
            column0 = Gtk.TreeViewColumn("toggle", renderer0, active=0)

        renderer1 = Gtk.CellRendererText()
        renderer1.set_property('ellipsize-set', True)
        renderer1.set_property('ellipsize', Pango.EllipsizeMode.END)
        renderer1.set_property('editable', True)
        renderer1.connect('edited', self._on_playlist_edited)
        renderer1.connect('editing-started', self._on_playlist_editing_start)
        renderer1.connect('editing-canceled', self._on_playlist_editing_cancel)
        column1 = Gtk.TreeViewColumn('text', renderer1, text=1)
        column1.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column1.set_expand(True)

        renderer2 = Gtk.CellRendererPixbuf()
        column2 = Gtk.TreeViewColumn('delete', renderer2)
        column2.add_attribute(renderer2, 'icon-name', 2)
        column2.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column2.set_property('fixed_width', 50)

        if self._object_id != Type.NONE:
            self._view.append_column(column0)
        self._view.append_column(column1)
        self._view.append_column(column2)

    def populate(self):
        """
            Populate playlists
            @thread safe
        """
        playlists = Lp.playlists.get()
        GLib.idle_add(self._append_playlists, playlists)

    def add_new_playlist(self):
        """
            Add new playlist
        """
        existing_playlists = []
        for item in self._model:
            existing_playlists.append(item[1])

        # Search for an available name
        count = 1
        name = _("New playlist ") + str(count)
        while name in existing_playlists:
            count += 1
            name = _("New playlist ") + str(count)
        Lp.playlists.add(name)
        playlist_id = Lp.playlists.get_id(name)
        self._model.append([True, name, 'user-trash-symbolic', playlist_id])
        self._set_current_object(playlist_id, True)

#######################
# PRIVATE             #
#######################
    def _sort_items(self, model, itera, iterb, data):
        """
            Sort model
        """
        a = model.get_value(itera, 1)
        b = model.get_value(iterb, 1)

        return a.lower() > b.lower()

    def _append_playlists(self, playlists):
        """
            Append a playlist
            @param playlists as [str]
            @param playlist selected as bool
        """
        if playlists:
            playlist = playlists.pop(0)
            if self._object_id != Type.NONE:
                if self._is_album:
                    selected = Lp.playlists.exists_album(
                                                       playlist[0],
                                                       self._object_id,
                                                       self._genre_id)
                else:

                    selected = Lp.playlists.exists_track(
                                                       playlist[0],
                                                       self._object_id)
            else:
                selected = False
            self._model.append([selected, playlist[1],
                               'user-trash-symbolic', playlist[0]])
            GLib.idle_add(self._append_playlists, playlists)
        else:
            selection = self._view.get_selection()
            if selection is not None:
                selection.unselect_all()

    def _show_infobar(self, path):
        """
            Show infobar
            @param path as Gtk.TreePath
        """
        iterator = self._model.get_iter(path)
        self._deleted_path = str(path)  # Need a copy, segfault on EOS 3.1
        self._infobar_label.set_text(_("Remove \"%s\"?") %
                                     self._model.get_value(iterator, 1))
        self._infobar.show()

    def _on_response(self, infobar, response_id):
        """
            Hide infobar
            @param widget as Gtk.Infobar
            @param reponse id as int
        """
        if response_id == Gtk.ResponseType.CLOSE:
            self._infobar.hide()
            self._view.grab_focus()
            self._view.get_selection().unselect_all()

    def _on_row_activated(self, view, path, column):
        """
            Delete playlist
            @param TreeView, TreePath, TreeViewColumn
        """
        iterator = self._model.get_iter(path)
        if iterator:
            if column.get_title() == "delete":
                self._show_infobar(path)

    def _on_delete_confirm(self, button):
        """
            Delete playlist after confirmation
            @param button as Gtk.Button
        """
        if self._deleted_path:
            iterator = self._model.get_iter(self._deleted_path)
            Lp.playlists.delete(self._model.get_value(iterator, 1))
            self._model.remove(iterator)
            self._deleted_path = None
            self._infobar.hide()
            self._view.grab_focus()
            self._view.get_selection().unselect_all()

    def _on_keyboard_event(self, widget, event):
        """
            Delete item if Delete was pressed
            @param widget unused, Gdk.Event
        """
        if event.keyval == 65535:
            path, column = self._view.get_cursor()
            self._show_infobar(path)

    def _on_playlist_toggled(self, view, path):
        """
            When playlist is activated, add object to playlist
            @param widget as cell renderer
            @param path as str representation of Gtk.TreePath
        """
        iterator = self._model.get_iter(path)
        toggle = not self._model.get_value(iterator, 0)
        playlist_id = self._model.get_value(iterator, 3)
        self._model.set_value(iterator, 0, toggle)
        self._set_current_object(playlist_id, toggle)

    def _set_current_object(self, playlist_id, add):
        """
            Add/Remove current object to playlist
            @param playlist id as int
            @param add as bool
        """
        def set(playlist_id, add):
            tracks = []
            if self._is_album:
                tracks_ids = Lp.albums.get_tracks(self._object_id,
                                                  self._genre_id)
                for track_id in tracks_ids:
                    tracks.append(Track(track_id))
            else:
                tracks = [Track(self._object_id)]
            if add:
                Lp.playlists.add_tracks(playlist_id, tracks)
            else:
                Lp.playlists.remove_tracks(playlist_id, tracks)
        t = Thread(target=set, args=(playlist_id, add))
        t.daemon = True
        t.start()

    def _on_playlist_edited(self, widget, path, name):
        """
            When playlist is edited, rename playlist
            @param widget as cell renderer
            @param path as str representation of Gtk.TreePath
            @param name as str
        """
        iterator = self._model.get_iter(path)
        old_name = self._model.get_value(iterator, 1)
        playlist_id = self._model.get_value(iterator, 3)
        if name.find("/") != -1 or\
           old_name == name or\
           not name or\
           Lp.playlists.get_id(name) != Type.NONE:
            return
        self._model.remove(iterator)
        self._model.append([True, name, 'user-trash-symbolic', playlist_id])
        Lp.playlists.rename(name, old_name)

    def _on_playlist_editing_start(self, widget, editable, path):
        """
            Disable global shortcuts
            @param widget as cell renderer
            @param editable as Gtk.CellEditable
            @param path as str representation of Gtk.TreePath
        """
        Lp.window.enable_global_shorcuts(False)

    def _on_playlist_editing_cancel(self, widget):
        """
            Enable global shortcuts
            @param widget as cell renderer
        """
        Lp.window.enable_global_shorcuts(True)


class PlaylistEditWidget(Gtk.Bin):
    """
        Widget playlists editor
    """

    def __init__(self, playlist_id):
        """
            Init widget
            @param playlist id as int
        """
        Gtk.Bin.__init__(self)
        self._playlist_id = playlist_id
        self._save_on_disk = True

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/PlaylistEditWidget.ui')
        builder.connect_signals(self)

        self._infobar = builder.get_object('infobar')
        self._infobar_label = builder.get_object('infobarlabel')

        self._view = builder.get_object('view')

        self._model = Gtk.ListStore(int,
                                    str,
                                    str,
                                    int)
        self._model.connect("row-deleted", self._on_row_deleted)

        self._view.set_model(self._model)

        # 3 COLUMNS NEEDED
        renderer0 = CellRendererAlbum()
        column0 = Gtk.TreeViewColumn("pixbuf1", renderer0, album=0)
        renderer1 = Gtk.CellRendererText()
        renderer1.set_property('ellipsize-set', True)
        renderer1.set_property('ellipsize', Pango.EllipsizeMode.END)
        column1 = Gtk.TreeViewColumn("text1", renderer1, markup=1)
        column1.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column1.set_expand(True)
        renderer2 = Gtk.CellRendererPixbuf()
        column2 = Gtk.TreeViewColumn('delete', renderer2)
        column2.add_attribute(renderer2, 'icon-name', 2)
        column2.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column2.set_property('fixed_width', 50)

        self._view.append_column(column0)
        self._view.append_column(column1)
        self._view.append_column(column2)

        self.add(builder.get_object('widget'))

    def populate(self):
        """
            populate view if needed
        """
        if len(self._model) == 0:
            t = Thread(target=self._append_tracks)
            t.daemon = True
            t.start()

#######################
# PRIVATE             #
#######################
    def _unselectall(self):
        """
            Unselect all in view
        """
        self._view.get_selection().unselect_all()
        self._view.grab_focus()

    def _append_tracks(self):
        """
            Append tracks
        """
        track_ids = Lp.playlists.get_tracks_ids(self._playlist_id)
        GLib.idle_add(self._append_track, track_ids)

    def _append_track(self, track_ids):
        """
            Append track while tracks not empty
            @param track_ids as [track_id as int]
        """
        if track_ids:
            track = Track(track_ids.pop(0))
            if track.album.artist_id == Type.COMPILATIONS:
                artist_name = track.artist_names
            else:
                artist_name = track.album.artist_name
            self._model.append([track.album.id,
                               "<b>%s</b>\n%s" % (
                                   escape(artist_name),
                                   escape(track.name)),
                                'user-trash-symbolic', track.id])
            GLib.idle_add(self._append_track, track_ids)
        else:
            self._view.grab_focus()
            self._in_thread = False

    def _update_on_disk(self):
        """
            Update playlist on disk
        """
        def update():
            Lp.playlists.clear(self._playlist_id)
            tracks = []
            for item in self._model:
                tracks.append(Track(item[3]))
            Lp.playlists.add_tracks(self._playlist_id, tracks)
        t = Thread(target=update)
        t.daemon = True
        t.start()

    def _show_infobar(self, path):
        """
            Show infobar
            @param path as Gtk.TreePath
        """
        iterator = self._model.get_iter(path)
        self._infobar_label.set_markup(_("Remove \"%s\"?") %
                                       self._model.get_value(iterator,
                                                             1).replace('\n',
                                                                        ' - '))
        self._infobar.show()

    def _on_keyboard_event(self, widget, event):
        """
            Delete item if Delete was pressed
            @param widget unused, Gdk.Event
        """
        if event.keyval == 65535:
            path, column = self._view.get_cursor()
            self._show_infobar(path)

    def _on_response(self, infobar, response_id):
        """
            Hide infobar
            @param widget as Gtk.Infobar
            @param reponse id as int
        """
        if response_id == Gtk.ResponseType.CLOSE:
            self._infobar.hide()
            self._view.grab_focus()
            self._view.get_selection().unselect_all()

    def _on_row_activated(self, view, path, column):
        """
            Delete playlist
            @param TreeView, TreePath, TreeViewColumn
        """
        iterator = self._model.get_iter(path)
        if iterator:
            if column.get_title() == "delete":
                self._show_infobar(path)
            else:
                self._infobar.hide()

    def _on_selection_changed(self, selection):
        """
            On selection changed, show infobar
            @param selection as Gtk.TreeSelection
        """
        count = selection.count_selected_rows()
        if count > 1:
            self._infobar_label.set_markup(_("Remove these tracks?"))
            self._infobar.show()

    def _on_row_deleted(self, path, data):
        """
            Only catch drag & drop successful
            @param path as Gtk.TreePath
            @param data as unused
        """
        if self._save_on_disk:
            self._update_on_disk()

    def _on_delete_confirm(self, button):
        """
            Delete tracks after confirmation
            @param button as Gtk.Button
        """
        self._save_on_disk = False
        selection = self._view.get_selection()
        selected = selection.get_selected_rows()
        rows = []
        for item in selected[1]:
            rows.append(Gtk.TreeRowReference.new(self._model, item))

        for row in rows:
            iterator = self._model.get_iter(row.get_path())
            track = Track(self._model.get_value(iterator, 3))
            if track.album.artist_id == Type.COMPILATIONS:
                artist_name = track.artist_names
            else:
                artist_name = track.album.artist_name
            if Lp.lastfm is not None:
                t = Thread(target=Lp.lastfm.unlove,
                           args=(artist_name, track.name))
                t.daemon = True
                t.start()
            self._model.remove(iterator)
        self._infobar.hide()
        self._save_on_disk = True
        self._unselectall()
        self._update_on_disk()
