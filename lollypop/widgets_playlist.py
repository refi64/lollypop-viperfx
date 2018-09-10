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

from gi.repository import Gtk, GLib, Gdk, GObject

from lollypop.define import App, Type, WindowSize, Loading, ResponsiveType
from lollypop.widgets_track import TracksWidget, PlaylistRow
from lollypop.objects import Track
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

    def set_playing_indicator(self):
        """
            Set playing indicator
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
