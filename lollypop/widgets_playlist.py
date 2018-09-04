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

from gi.repository import Gtk, GLib, Gdk, Pango, GObject

from gettext import gettext as _

from lollypop.define import App, Type, WindowSize, Loading, ResponsiveType
from lollypop.cellrenderer import CellRendererAlbum
from lollypop.widgets_track import TracksWidget, PlaylistRow
from lollypop.objects import Track, Album, Disc
from lollypop.helper_task import TaskHelper
from lollypop.widgets_base import BaseWidget


class PlaylistsWidget(Gtk.Grid, BaseWidget):
    """
        Show playlist tracks/albums
    """
    __gsignals__ = {
        "populated": (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self, playlist_ids):
        """
            Init playlist Widget
            @param playlist ids as [int]
        """
        Gtk.Grid.__init__(self)
        self.set_row_spacing(5)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.__playlist_ids = playlist_ids
        self.__row_tracks_left = []
        self.__row_tracks_right = []
        self.__width = None
        self.__orientation = None
        self.__loading = Loading.NONE
        # Used to block widget2 populate while showing one column
        self.__locked_widget_right = True

        self.set_margin_start(5)
        # 15 for scrollbar overlay
        self.set_margin_end(15)

        self.__grid = Gtk.Grid()
        self.__grid.set_vexpand(True)
        self.__grid.set_column_homogeneous(True)
        self.__grid.show()

        self.connect("size-allocate", self.__on_size_allocate)

        self.__tracks_widget_left = TracksWidget(ResponsiveType.DND)
        self.__tracks_widget_left.set_vexpand(True)
        self.__tracks_widget_right = TracksWidget(ResponsiveType.DND)
        self.__tracks_widget_right.set_vexpand(True)
        self.__tracks_widget_left.connect("activated",
                                          self.__on_activated)
        self.__tracks_widget_right.connect("activated",
                                           self.__on_activated)
        self.__tracks_widget_left.show()
        self.__tracks_widget_right.show()

        self.drag_dest_set(Gtk.DestDefaults.DROP,
                           [], Gdk.DragAction.MOVE)
        self.drag_dest_add_text_targets()
        self.connect("drag-data-received", self.__on_drag_data_received)

        self.add(self.__grid)

    def set_filter_func(self, func):
        """
            Set filter function
        """
        self.__tracks_widget_left.set_filter_func(func)
        self.__tracks_widget_right.set_filter_func(func)

    def update_allocation(self):
        """
            Update widget allocation
        """
        self.__width = 0
        self.__on_size_allocate(self, self.get_allocation())

    def get_current_ordinate(self):
        """
            If current track in widget, return it ordinate,
            @return y as int
        """
        ordinate = None
        for child in self.__tracks_widget_left.get_children() + \
                self.__tracks_widget_right.get_children():
            if child.track.id == App().player.current_track.id:
                ordinate = child.translate_coordinates(self.__grid, 0, 0)[1]
        return ordinate

    def populate_list_left(self, tracks, pos):
        """
            Populate left list
            @param track's ids as array of int (not null)
            @param track position as int
            @thread safe
        """
        # We reset width here to allow size allocation code to run
        self.__width = None
        GLib.idle_add(self.__add_tracks,
                      tracks,
                      self.__tracks_widget_left,
                      pos)

    def populate_list_right(self, tracks, pos):
        """
            Populate right list
            @param track"s ids as array of int (not null)
            @param track position as int
            @thread safe
        """
        # If we are showing only one column, wait for widget1
        if self.__orientation == Gtk.Orientation.VERTICAL and\
           self.__locked_widget_right:
            GLib.timeout_add(100, self.populate_list_right, tracks, pos)
        else:
            # We reset width here to allow size allocation code to run
            self.__width = None
            GLib.idle_add(self.__add_tracks,
                          tracks,
                          self.__tracks_widget_right,
                          pos)

    def update_playing_indicator(self):
        """
            Update playing indicator
        """
        track_id = App().player.current_track.id
        self.__tracks_widget_left.update_playing(track_id)
        self.__tracks_widget_right.update_playing(track_id)

    def stop(self):
        """
            Stop loading
        """
        self.__loading = Loading.STOP

    def insert(self, track_id, pos=-1):
        """
            Add track to widget
            @param track id as int
            @param pos as int
        """
        children_len = len(self.__tracks_widget_left.get_children() +
                           self.__tracks_widget_right.get_children())
        if pos > children_len / 2:
            widget = self.__tracks_widget_right
            pos -= len(self.__tracks_widget_left.get_children())
        elif pos == -1:
            widget = self.__tracks_widget_right
        else:
            widget = self.__tracks_widget_left
        self.__add_tracks([track_id], widget, pos)
        self.__update_position()
        self.__update_headers()
        self.__tracks_widget_left.update_indexes(1)
        track_left_children = self.__tracks_widget_left.get_children()
        self.__tracks_widget_right.update_indexes(len(track_left_children) + 1)

    def remove(self, track_id):
        """
            Del track from widget
            @param track id as int
        """
        children = self.__tracks_widget_left.get_children() + \
            self.__tracks_widget_right.get_children()
        # Clear the widget
        if track_id is None:
            for child in children:
                child.destroy()
        else:
            for child in children:
                if child.track.id == track_id:
                    child.destroy()
                    break
            self.__update_position()
            self.__update_headers()
            self.__tracks_widget_left.update_indexes(1)
            track_left_children = self.__tracks_widget_left.get_children()
            self.__tracks_widget_right.update_indexes(
                len(track_left_children) + 1)

    def rows_animation(self, x, y, widget):
        """
            Show animation to help user dnd
            @param x as int
            @param y as int
            @param widget as Gtk.Widget (related widget)
            @return child as PlaylistRow/None
        """
        rows = self.__tracks_widget_left.get_children() +\
            self.__tracks_widget_right.get_children()
        for row in rows:
            coordinates = row.translate_coordinates(widget, 0, 0)
            if coordinates is None:
                continue
            (row_x, row_y) = coordinates
            row_width = row.get_allocated_width()
            row_height = row.get_allocated_height()
            if x < row_x or\
                    x > row_x + row_width or\
                    y < row_y or\
                    y > row_y + row_height:
                continue
            if y <= row_y + row_height / 2:
                row.get_style_context().add_class("drag-up")
                return row
            elif y >= row_y + row_height / 2:
                row.get_style_context().add_class("drag-down")
                return row
        return None

    @property
    def id(self):
        """
            Return playlist widget id
            @return int
        """
        return Type.PLAYLISTS

    @property
    def boxes(self):
        """
            @return [Gtk.ListBox]
        """
        return [self.__tracks_widget_left, self.__tracks_widget_right]

#######################
# PRIVATE             #
#######################
    def __add_tracks(self, tracks, widget, pos, previous_album_id=None):
        """
            Add tracks to list
            @param tracks id as array of [int]
            @param widget TracksWidget
            @param track position as int
            @param pos as int
            @param previous album id as int
        """
        if self.__loading == Loading.STOP:
            self.__loading = Loading.NONE
            return
        if not tracks:
            if widget == self.__tracks_widget_right:
                self.__loading |= Loading.RIGHT
            elif widget == self.__tracks_widget_left:
                self.__loading |= Loading.LEFT
            if self.__loading == Loading.ALL:
                self.emit("populated")
            self.__locked_widget_right = False
            return

        track = Track(tracks.pop(0))
        track.set_number(pos)
        row = PlaylistRow(track, track.album.id != previous_album_id)
        row.connect("track-moved", self.__on_track_moved)
        row.show()
        widget.insert(row, pos)
        GLib.idle_add(self.__add_tracks, tracks, widget,
                      pos + 1, track.album.id)

    def __update_position(self):
        """
            Update widget position

        """
        row_tracks_left = self.__get_row_tracks(Loading.LEFT)
        row_tracks_right = self.__get_row_tracks(Loading.RIGHT)
        len_row_tracks_left = len(row_tracks_left)
        len_row_tracks_right = len(row_tracks_right)
        # Take first track from tracks2 and put it at the end of tracks1
        if len_row_tracks_right > len_row_tracks_left:
            src_track = row_tracks_right[0]
            if row_tracks_left:
                dst_track = row_tracks_left[-1]
            else:
                dst_track = None
            self.__move_track(dst_track, src_track, False)
        # Take last track of tracks1 and put it at the bottom of tracks2
        elif len_row_tracks_left - 1 > len_row_tracks_right:
            src_track = row_tracks_left[-1]
            if row_tracks_right:
                dst_track = row_tracks_right[0]
            else:
                dst_track = None
            self.__move_track(dst_track, src_track, True)

    def __update_headers(self):
        """
            Update headers for all tracks
        """
        self.__tracks_widget_left.update_headers()
        prev_album_id = None
        if self.__orientation == Gtk.Orientation.VERTICAL:
            row_tracks_left = self.__tracks_widget_left.get_children()
            if row_tracks_left:
                prev_album_id = row_tracks_left[-1].track.album.id
        self.__tracks_widget_right.update_headers(prev_album_id)

    def __get_row_tracks(self, loading):
        """
            Get tracks for loading
            @param loading as Loading
        """
        if loading == Loading.LEFT:
            widget = self.__tracks_widget_left
        else:
            widget = self.__tracks_widget_right
        tracks = []
        for row in widget.get_children():
            tracks.append(row.track)
        return tracks

    def __move_track(self, dst_track, src_track, down):
        """
            Move track from src to row
            @param dst_track as Track
            @param src_track as Track
            @param down as bool
        """
        row_tracks_left = self.__get_row_tracks(Loading.LEFT)
        row_tracks_right = self.__get_row_tracks(Loading.RIGHT)
        tracks1_len = len(row_tracks_left)
        tracks2_len = len(row_tracks_right)
        if src_track in row_tracks_left:
            src_widget = self.__tracks_widget_left
        else:
            src_widget = self.__tracks_widget_right
        if tracks1_len == 0 or dst_track in row_tracks_left:
            dst_widget = self.__tracks_widget_left
            dst_tracks = row_tracks_left
        elif tracks2_len == 0 or dst_track in row_tracks_right:
            dst_widget = self.__tracks_widget_right
            dst_tracks = row_tracks_right
        else:
            return
        # Remove src from src_widget
        for child in src_widget.get_children():
            if child.track == src_track:
                child.destroy()
                break
        prev_track = Track()
        name = GLib.markup_escape_text(src_track.name)
        index = 0
        # Get previous track
        if dst_track is not None:
            for child in dst_widget.get_children():
                if child.track == dst_track:
                    break
                index += 1
            if down:
                index += 1
            # Get previous track (in dst context)
            prev_index = dst_tracks.index(dst_track)
            if not down:
                prev_index -= 1
            prev_track = dst_tracks[prev_index]
            # If we are listening to a compilation, prepend artist name
            if (src_track.album.artist_id == Type.COMPILATIONS or
                    len(src_track.artist_ids) > 1 or
                    src_track.album.artist_id not in src_track.artist_ids):
                name = "<b>%s</b>\n%s" % (
                    GLib.markup_escape_text(", ".join(src_track.artists)),
                    name)
        src_track.set_number(index)
        row = PlaylistRow(src_track, index == 0 or
                          src_track.album.id != prev_track.album.id)
        row.connect("track-moved", self.__on_track_moved)
        row.show()
        dst_widget.insert(row, index)

    def __on_drag_data_received(self, widget, context, x, y, data, info, time):
        """
            ONLY HAPPEN IN VERTICAL ORIENTATION
            Horizontal orientation is handled by TracksWidget
            @param widget as Gtk.Widget
            @param context as Gdk.DragContext
            @param x as int
            @param y as int
            @param data as Gtk.SelectionData
            @param info as int
            @param time as int
        """
        from lollypop.view import View
        view = widget.get_ancestor(View)
        if view is not None:
            view.clear_animation()
        try:
            value = int(data.get_text())
            try:
                child = self.__tracks_widget_right.get_children()[-1]
            except:
                child = self.__tracks_widget_left.get_children()[-1]
            self.__on_track_moved(widget, child.track.id, value, False)
        except:
            if len(self.__playlist_ids) == 1:
                App().playlists.import_uri(self.__playlist_ids[0],
                                           data.get_text())

    def __on_track_moved(self, widget, dst, src, up):
        """
            Move track from src to row
            Recalculate track position
            @param widget as TracksWidget
            @param dst as str
            @param src as str
            @param up as bool
        """
        def update_playlist():
            # Save playlist in db only if one playlist visible
            if len(self.__playlist_ids) == 1 and self.__playlist_ids[0] >= 0:
                row_tracks_left = self.__get_row_tracks(Loading.LEFT)
                row_tracks_right = self.__get_row_tracks(Loading.RIGHT)
                tracks = row_tracks_left + row_tracks_right
                App().playlists.clear(self.__playlist_ids[0], False)
                App().playlists.add_tracks(self.__playlist_ids[0],
                                           tracks,
                                           False)
            if not (set(self.__playlist_ids) -
                    set(App().player.get_playlist_ids())):
                App().player.update_playlist(tracks)
        src_track = dst_track = None
        row_tracks_left = self.__get_row_tracks(Loading.LEFT)
        row_tracks_right = self.__get_row_tracks(Loading.RIGHT)
        for track in row_tracks_left + row_tracks_right:
            if track.id == int(dst):
                dst_track = track
            elif track.id == int(src):
                src_track = track
            elif src_track is not None and dst_track is not None:
                break
        self.__move_track(dst_track, src_track, up)
        self.__update_position()
        self.__update_headers()
        self.__tracks_widget_left.update_indexes(1)
        self.__tracks_widget_right.update_indexes(len(row_tracks_left) + 1)
        helper = TaskHelper()
        helper.run(update_playlist)

    def __on_size_allocate(self, widget, allocation):
        """
            Change box max/min children
            @param widget as Gtk.Widget
            @param allocation as Gtk.Allocation
        """
        if self.__width == allocation.width:
            return
        self.__width = allocation.width
        redraw = False
        if allocation.width < WindowSize.MONSTER or\
                not App().settings.get_value("split-view"):
            self.__grid.set_property("valign", Gtk.Align.START)
            self.__grid.set_column_spacing(0)
            orientation = Gtk.Orientation.VERTICAL
        else:
            self.__grid.set_property("valign", Gtk.Align.FILL)
            self.__grid.set_column_spacing(5)
            orientation = Gtk.Orientation.HORIZONTAL
        if orientation != self.__orientation:
            self.__orientation = orientation
            redraw = True
        self.__grid.set_orientation(orientation)
        if redraw:
            for child in self.__grid.get_children():
                self.__grid.remove(child)
            GLib.idle_add(self.__grid.add, self.__tracks_widget_left)
            GLib.idle_add(self.__grid.add, self.__tracks_widget_right)
        self.__update_headers()

    def __on_activated(self, widget, track):
        """
            On track activation, play track
            @param widget as TracksWidget
            @param track as Track
        """
        # Add to queue by default
        if App().player.locked:
            if track.id in App().player.queue:
                App().player.del_from_queue(track.id)
            else:
                App().player.append_to_queue(track.id)
        else:
            App().player.load(track)
            if not App().player.is_party:
                row_tracks_left = self.__get_row_tracks(Loading.LEFT)
                row_tracks_right = self.__get_row_tracks(Loading.RIGHT)
                App().player.populate_playlist_by_tracks(
                    row_tracks_left +
                    row_tracks_right,
                    self.__playlist_ids)


class PlaylistsManagerWidget(Gtk.Bin):
    """
        Widget for playlists management
    """

    def __init__(self, object):
        """
            Init widget
            @param object as Track/Album/Disc
        """
        Gtk.Bin.__init__(self)
        self.__object = object
        self.__deleted_path = None

        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/"
                                  "PlaylistsManagerWidget.ui")
        self.__infobar = builder.get_object("infobar")
        self.__infobar_label = builder.get_object("infobarlabel")

        self.__model = Gtk.ListStore(bool, str, str, int)
        self.__model.set_sort_column_id(1, Gtk.SortType.ASCENDING)
        self.__model.set_sort_func(1, self.__sort_items)

        self.__view = builder.get_object("view")
        self.__view.set_model(self.__model)
        self.__view.drag_dest_set(
            Gtk.DestDefaults.DROP | Gtk.DestDefaults.MOTION,
            [], Gdk.DragAction.MOVE)
        self.__view.drag_dest_add_text_targets()
        self.__view.connect("drag-data-received", self.__on_drag_data_received)

        builder.connect_signals(self)

        self.add(builder.get_object("widget"))

        if object is not None:
            renderer0 = Gtk.CellRendererToggle()
            renderer0.set_property("activatable", True)
            renderer0.connect("toggled", self.__on_playlist_toggled)
            column0 = Gtk.TreeViewColumn(" ✓", renderer0, active=0)
            column0.set_clickable(True)
            column0.connect("clicked", self.__on_column0_clicked)

        renderer1 = Gtk.CellRendererText()
        renderer1.set_property("ellipsize-set", True)
        renderer1.set_property("ellipsize", Pango.EllipsizeMode.END)
        renderer1.set_property("editable", True)
        renderer1.connect("edited",
                          self.__on_playlist_edited)
        renderer1.connect("editing-started",
                          self.__on_playlist_editing_start)
        renderer1.connect("editing-canceled",
                          self.__on_playlist_editing_cancel)
        column1 = Gtk.TreeViewColumn(_("Playlists"), renderer1, text=1)
        column1.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column1.set_expand(True)

        renderer2 = Gtk.CellRendererPixbuf()
        column2 = Gtk.TreeViewColumn("", renderer2)
        column2.add_attribute(renderer2, "icon-name", 2)
        column2.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column2.set_property("fixed_width", 50)

        if self.__object is not None:
            self.__view.append_column(column0)
        self.__view.append_column(column1)
        self.__view.append_column(column2)

    def populate(self):
        """
            Populate playlists
            @thread safe
        """
        playlists = App().playlists.get()
        self.__append_playlists(playlists)

    def add_new_playlist(self):
        """
            Add new playlist
        """
        existing_playlists = []
        for item in self.__model:
            existing_playlists.append(item[1])

        # Search for an available name
        count = 1
        name = _("New playlist ") + str(count)
        while name in existing_playlists:
            count += 1
            name = _("New playlist ") + str(count)
        App().playlists.add(name)
        playlist_id = App().playlists.get_id(name)
        iterator = self.__model.append([True,
                                        name,
                                        "user-trash-symbolic",
                                        playlist_id])
        self.__view.get_selection().select_iter(iterator)
        self.__view.grab_focus()
        self.__set_current_object(playlist_id, True)

#######################
# PROTECTED           #
#######################
    def _on_response(self, infobar, response_id):
        """
            Hide infobar
            @param widget as Gtk.Infobar
            @param reponse id as int
        """
        if response_id == Gtk.ResponseType.CLOSE:
            self.__infobar.hide()
            self.__get_focus()

    def _on_row_activated(self, view, path, column):
        """
            Delete playlist
            @param TreeView, TreePath, TreeViewColumn
        """
        iterator = self.__model.get_iter(path)
        if iterator:
            if column.get_title() == "":
                self.__show_infobar(path)

    def _on_delete_confirm(self, button):
        """
            Delete playlist after confirmation
            @param button as Gtk.Button
        """
        if self.__deleted_path:
            iterator = self.__model.get_iter(self.__deleted_path)
            App().playlists.delete(self.__model.get_value(iterator, 1))
            self.__model.remove(iterator)
            self.__deleted_path = None
            self.__infobar.hide()
            self.__get_focus()

    def _on_keyboard_event(self, widget, event):
        """
            Delete item if Delete was pressed
            @param widget unused, Gdk.Event
        """
        if event.keyval == 65535:
            path, column = self.__view.get_cursor()
            self.__show_infobar(path)

#######################
# PRIVATE             #
#######################
    def __get_focus(self):
        """
            Give focus to view
        """
        self.__view.grab_focus()
        self.__view.get_selection().unselect_all()

    def __sort_items(self, model, itera, iterb, data):
        """
            Sort model
        """
        a = model.get_value(itera, 1)
        b = model.get_value(iterb, 1)

        return a.lower() > b.lower()

    def __append_playlists(self, playlists):
        """
            Append a playlist
            @param playlists as [str]
            @param playlist selected as bool
        """
        for playlist in playlists:
            if self.__object is not None:
                if isinstance(self.__object, Album) or\
                        isinstance(self.__object, Disc):
                    selected = App().playlists.exists_album(
                        playlist[0],
                        self.__object)
                else:

                    selected = App().playlists.exists_track(
                        playlist[0],
                        self.__object)
            else:
                selected = False
            self.__model.append([selected, playlist[1],
                                 "user-trash-symbolic", playlist[0]])

    def __show_infobar(self, path):
        """
            Show infobar
            @param path as Gtk.TreePath
        """
        iterator = self.__model.get_iter(path)
        self.__deleted_path = str(path)  # Need a copy, segfault on EOS 3.1
        self.__infobar_label.set_text(_("Remove \"%s\"?") %
                                      self.__model.get_value(iterator, 1))
        self.__infobar.show()
        # GTK 3.20 https://bugzilla.gnome.org/show_bug.cgi?id=710888
        self.__infobar.queue_resize()

    def __on_drag_data_received(self, widget, context, x, y, data, info, time):
        """
            @param widget as Gtk.Widget
            @param context as Gdk.DragContext
            @param x as int
            @param y as int
            @param data as Gtk.SelectionData
            @param info as int
            @param time as int
        """
        try:
            path = self.__view.get_path_at_pos(x, y)[0]
            iterator = self.__model.get_iter(path)
            if iterator is not None:
                playlist_id = self.__model.get_value(iterator, 3)
                App().playlists.import_uri(playlist_id, data.get_text())
        except:
            pass

    def __on_playlist_toggled(self, view, path):
        """
            When playlist is activated, add object to playlist
            @param widget as cell renderer
            @param path as str representation of Gtk.TreePath
        """
        iterator = self.__model.get_iter(path)
        toggle = not self.__model.get_value(iterator, 0)
        playlist_id = self.__model.get_value(iterator, 3)
        self.__model.set_value(iterator, 0, toggle)
        self.__set_current_object(playlist_id, toggle)

    def __set_current_object(self, playlist_id, add):
        """
            Add/Remove current object to playlist
            @param playlist id as int
            @param add as bool
        """
        def set(playlist_id, add):
            if isinstance(self.__object, Disc):
                tracks = self.__object.tracks
            elif isinstance(self.__object, Album):
                tracks = self.__object.tracks
            else:
                tracks = [self.__object]
            if add:
                App().playlists.add_tracks(playlist_id, tracks)
            else:
                App().playlists.remove_tracks(playlist_id, tracks)
        helper = TaskHelper()
        helper.run(set, playlist_id, add)

    def __on_playlist_edited(self, widget, path, name):
        """
            When playlist is edited, rename playlist
            @param widget as cell renderer
            @param path as str representation of Gtk.TreePath
            @param name as str
        """
        iterator = self.__model.get_iter(path)
        old_name = self.__model.get_value(iterator, 1)
        playlist_id = self.__model.get_value(iterator, 3)
        if name.find("/") != -1 or\
           old_name == name or\
           not name or\
           App().playlists.get_id(name) != Type.NONE:
            return
        self.__model.remove(iterator)
        self.__model.append([True, name, "user-trash-symbolic", playlist_id])
        App().playlists.rename(name, old_name)

    def __on_playlist_editing_start(self, widget, editable, path):
        """
            Disable global shortcuts
            @param widget as cell renderer
            @param editable as Gtk.CellEditable
            @param path as str representation of Gtk.TreePath
        """
        # FIXME Not needed with GTK >= 3.18
        App().window.enable_global_shortcuts(False)

    def __on_playlist_editing_cancel(self, widget):
        """
            Enable global shortcuts
            @param widget as cell renderer
        """
        # FIXME Not needed with GTK >= 3.18
        App().window.enable_global_shortcuts(True)

    def __on_column0_clicked(self, column):
        """
            Select/Unselect all playlists checkboxes
            @param column as Gtk.TreeViewColumn
        """
        selected = False
        for item in self.__model:
            if item[0]:
                selected = True
        for item in self.__model:
            item[0] = not selected
            self.__set_current_object(item[3], item[0])


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
        self.__playlist_id = playlist_id

        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/PlaylistEditWidget.ui")
        builder.connect_signals(self)

        self.__infobar = builder.get_object("infobar")
        self.__infobar_label = builder.get_object("infobarlabel")

        self.__view = builder.get_object("view")

        self.__model = Gtk.ListStore(int,
                                     str,
                                     str,
                                     int)

        self.__view.set_model(self.__model)

        # 3 COLUMNS NEEDED
        renderer0 = CellRendererAlbum()
        column0 = Gtk.TreeViewColumn("pixbuf1", renderer0, album=0)
        renderer1 = Gtk.CellRendererText()
        renderer1.set_property("ellipsize-set", True)
        renderer1.set_property("ellipsize", Pango.EllipsizeMode.END)
        column1 = Gtk.TreeViewColumn("text1", renderer1, markup=1)
        column1.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column1.set_expand(True)
        renderer2 = Gtk.CellRendererPixbuf()
        column2 = Gtk.TreeViewColumn("delete", renderer2)
        column2.add_attribute(renderer2, "icon-name", 2)
        column2.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column2.set_property("fixed_width", 50)

        self.__view.append_column(column0)
        self.__view.append_column(column1)
        self.__view.append_column(column2)

        self.add(builder.get_object("widget"))

    def populate(self):
        """
            populate view if needed
        """
        if len(self.__model) == 0:
            helper = TaskHelper()
            helper.run(self.__append_tracks, callback=(self.__append_track,))

#######################
# PROTECTED           #
#######################
    def _on_response(self, infobar, response_id):
        """
            Hide infobar
            @param widget as Gtk.Infobar
            @param reponse id as int
        """
        if response_id == Gtk.ResponseType.CLOSE:
            self.__infobar.hide()
            self.__view.grab_focus()
            self.__view.get_selection().unselect_all()

    def _on_selection_changed(self, selection):
        """
            On selection changed, show infobar
            @param selection as Gtk.TreeSelection
        """
        (model, paths) = selection.get_selected_rows()
        for item in self.__model:
            if item.path in paths:
                item[2] = "checkbox-checked-symbolic"
            else:
                item[2] = "checkbox-symbolic"
        count = selection.count_selected_rows()
        if count == 1:
            iterator = model.get_iter(paths[0])
            self.__infobar_label.set_markup(_("Remove \"%s\"?") %
                                            model.get_value(iterator,
                                                            1).replace("\n",
                                                                       " - "))
            self.__infobar.show()
            # GTK 3.20 https://bugzilla.gnome.org/show_bug.cgi?id=710888
            self.__infobar.queue_resize()
        elif count > 0:
            self.__infobar_label.set_markup(_("Remove these tracks?"))
            self.__infobar.show()
            # GTK 3.20 https://bugzilla.gnome.org/show_bug.cgi?id=710888
            self.__infobar.queue_resize()
        else:
            self.__infobar.hide()

    def _on_delete_confirm(self, button):
        """
            Delete tracks after confirmation
            @param button as Gtk.Button
        """
        selection = self.__view.get_selection()
        selected = selection.get_selected_rows()[1]
        rows = []
        for item in selected:
            rows.append(Gtk.TreeRowReference.new(self.__model, item))

        tracks = []
        for row in rows:
            iterator = self.__model.get_iter(row.get_path())
            track = Track(self.__model.get_value(iterator, 3))
            tracks.append(track)
            if self.__playlist_id == Type.LOVED and App().lastfm is not None:
                if track.album.artist_id == Type.COMPILATIONS:
                    artist_name = ", ".join(track.artists)
                else:
                    artist_name = ", ".join(track.album.artists)
                helper = TaskHelper()
                helper.run(App().lastfm.unlove, artist_name, track.name)
            self.__model.remove(iterator)
        App().playlists.remove_tracks(self.__playlist_id, tracks)
        self.__infobar.hide()
        self.__unselectall()

#######################
# PRIVATE             #
#######################
    def __unselectall(self):
        """
            Unselect all in view
        """
        self.__view.get_selection().unselect_all()
        self.__view.grab_focus()

    def __append_tracks(self):
        """
            Append tracks
        """
        return App().playlists.get_track_ids(self.__playlist_id)

    def __append_track(self, track_ids):
        """
            Append track while tracks not empty
            @param track_ids as [track_id as int]
        """
        if track_ids:
            track = Track(track_ids.pop(0))
            if track.album.artist_ids[0] == Type.COMPILATIONS:
                artists = ", ".join(track.artists)
            else:
                artists = ", ".join(track.album.artists)
            self.__model.append([track.album.id,
                                 "<b>%s</b>\n%s" % (
                                     GLib.markup_escape_text(artists),
                                     GLib.markup_escape_text(track.name)),
                                 "checkbox-symbolic", track.id])
            GLib.idle_add(self.__append_track, track_ids)
        else:
            self.__in_thread = False
