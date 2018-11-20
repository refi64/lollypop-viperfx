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

from gi.repository import Gtk, GLib, GObject

from lollypop.define import App, Type, WindowSize, Loading, ResponsiveType
from lollypop.widgets_tracks import TracksWidget
from lollypop.widgets_row_playlist import PlaylistRow
from lollypop.objects import Track


class PlaylistsWidget(Gtk.Grid):
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
        self.__tracks = {}
        self.__row_tracks_left = []
        self.__row_tracks_right = []
        self.__width = None
        self.__last_drag_id = None
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

        if len(self.__playlist_ids) == 1:
            self.__responsive_type = ResponsiveType.DND
        else:
            self.__responsive_type = ResponsiveType.FIXED
        self.__tracks_widget_left = TracksWidget()
        self.__tracks_widget_left.set_vexpand("True")
        self.__tracks_widget_right = TracksWidget()
        self.__tracks_widget_right.set_vexpand("True")
        self.__tracks_widget_left.connect("activated",
                                          self.__on_activated)
        self.__tracks_widget_right.connect("activated",
                                           self.__on_activated)
        self.__tracks_widget_left.show()
        self.__tracks_widget_right.show()

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

    def populate(self, tracks):
        """
            Populate view with two columns
            @param tracks as [Track]
        """
        # We are looking for middle
        # Ponderate with this:
        # Tracks with cover == 2
        # Tracks without cover == 1
        prev_album_id = None
        heights = {}
        total = 0
        idx = 0
        for track in tracks:
            if track.album_id != prev_album_id:
                heights[idx] = 2
                total += 2
            else:
                heights[idx] = 1
                total += 1
            prev_album_id = track.album_id
            idx += 1
        half = int(total / 2 + 0.5)
        mid_tracks = 1
        count = 0
        for height in heights.values():
            count += height
            if count >= half:
                break
            mid_tracks += 1
        self.populate_list_left(tracks[:mid_tracks], 1)
        self.populate_list_right(tracks[mid_tracks:], mid_tracks + 1)

    def populate_list_left(self, tracks, pos):
        """
            Populate left list
            @param tracks as [Track]
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
            @param tracks as [Track]
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

    def insert(self, track_id):
        """
            Add track to widget
            @param track id as int
        """
        length = len(self.children)
        if length == 0:
            widget = self.__tracks_widget_left
        else:
            widget = self.__tracks_widget_right
        pos = length + 1
        self.__add_tracks([track_id], widget, pos)
        self.__make_homogeneous()

    def remove(self, track_id, position):
        """
            Remove track from widget
            @param track_id as int
            @param position as int
        """
        index = 0
        for row in self.children:
            if row.track.id == track_id and index == position:
                row.destroy()
                break

    @property
    def id(self):
        """
            Return playlist widget id
            @return int
        """
        return Type.PLAYLISTS

    @property
    def children(self):
        """
            Return all rows
            @return [Gtk.ListBoxRow]
        """
        rows = []
        for listbox in [self.__tracks_widget_left, self.__tracks_widget_right]:
            rows += listbox.get_children()
        return rows

    @property
    def boxes(self):
        """
            @return [Gtk.ListBox]
        """
        return [self.__tracks_widget_left, self.__tracks_widget_right]

#######################
# PRIVATE             #
#######################
    def __make_homogeneous(self):
        """
            Move a track from right to left and vice versa
        """
        # Force linking as we are going to move tracks
        # Allow us to not garbage chained list
        self.__linking(True)
        if len(self.__tracks_widget_right.get_children()) >\
                len(self.__tracks_widget_left.get_children()):
            child = self.__tracks_widget_right.get_children()[0]
            self.__tracks_widget_right.remove(child)
            self.__tracks_widget_left.add(child)
        elif len(self.__tracks_widget_left.get_children()) >\
                len(self.__tracks_widget_right.get_children()) + 1:
            child = self.__tracks_widget_left.get_children()[-1]
            self.__tracks_widget_left.remove(child)
            self.__tracks_widget_right.insert(child, 0)
        self.__linking(self.__orientation == Gtk.Orientation.VERTICAL)

    def __linking(self, link):
        """
            Handle linking between left and right
            @param link as bool
        """
        if len(self.__tracks_widget_left) == 0 or\
                len(self.__tracks_widget_right) == 0:
            return
        last_left = self.__tracks_widget_left.get_children()[-1]
        first_right = self.__tracks_widget_right.get_children()[0]
        if link:
            last_left.set_next_row(first_right)
            first_right.set_previous_row(last_left)
        else:
            last_left.set_next_row(None)
            first_right.set_previous_row(None)

    def __add_tracks(self, tracks, widget, pos, previous_row=None):
        """
            Add tracks to list
            @param tracks id as array of [int]
            @param widget TracksWidget
            @param track position as int
            @param pos as int
            @param previous_row as Row
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

        track = tracks.pop(0)
        track.set_number(pos)
        row = PlaylistRow(track, self.__responsive_type)
        row.set_previous_row(previous_row)
        if previous_row is not None:
            previous_row.set_next_row(row)
        row.connect("insert-track", self.__on_insert_track)
        row.connect("remove-track", self.__on_remove_track)
        row.show()
        widget.insert(row, pos)
        GLib.idle_add(self.__add_tracks, tracks, widget, pos + 1, row)

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
            self.__linking(True)
        else:
            self.__grid.set_property("valign", Gtk.Align.FILL)
            self.__grid.set_column_spacing(5)
            orientation = Gtk.Orientation.HORIZONTAL
            self.__linking(False)
        if orientation != self.__orientation:
            self.__orientation = orientation
            redraw = True
        self.__grid.set_orientation(orientation)
        if redraw:
            for child in self.__grid.get_children():
                self.__grid.remove(child)
            GLib.idle_add(self.__grid.add, self.__tracks_widget_left)
            GLib.idle_add(self.__grid.add, self.__tracks_widget_right)

    def __on_activated(self, widget, track):
        """
            On track activation, play track
            @param widget as TracksWidget
            @param track as Track
        """
        # Add to queue by default
        if App().player.is_locked:
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

    def __on_insert_track(self, row, new_track_id, down):
        """
            Insert a new row at position
            @param row as PlaylistRow
            @param new_track_id as int
            @param down as bool
        """
        self.__last_drag_id = new_track_id
        position = self.children.index(row)
        track = Track(new_track_id)
        new_row = PlaylistRow(track, self.__responsive_type)
        new_row.connect("insert-track", self.__on_insert_track)
        new_row.connect("remove-track", self.__on_remove_track)
        new_row.show()
        if down:
            position += 1
            new_row.set_previous_row(row)
            new_row.set_next_row(row.next_row)
            if row.next_row is not None:
                row.next_row.set_previous_row(new_row)
            row.set_next_row(new_row)
        else:
            new_row.set_previous_row(row.previous_row)
            new_row.set_next_row(row)
            if row.previous_row is not None:
                row.previous_row.set_next_row(new_row)
            row.set_previous_row(new_row)
        new_row.update_number(position + 1)
        left_count = len(self.__tracks_widget_left.get_children())
        if position < left_count:
            row.get_parent().insert(new_row, position)
        else:
            row.get_parent().insert(new_row, position - left_count)
        App().player.insert_track(track, position)
        if len(self.__playlist_ids) == 1 and self.__playlist_ids[0] >= 0:
            App().playlists.insert_track(self.__playlist_ids[0],
                                         track, position)
        self.__make_homogeneous()

    def __on_remove_track(self, row):
        """
            Remove row's track
            @param row as PlaylistRow
        """
        App().player.remove_track(row.track.id)
        if row.track.id != self.__last_drag_id and (
                len(self.__playlist_ids) == 1 or self.__playlist_ids[0] > 0):
            App().playlists.remove_uri(self.__playlist_ids[0], row.track.uri)
        self.__last_drag_id = None
        if row.previous_row is None:
            row.next_row.set_previous_row(None)
        elif row.next_row is None:
            row.previous_row.set_next_row(None)
        else:
            row.next_row.set_previous_row(row.previous_row)
            row.previous_row.set_next_row(row.next_row)
        self.__make_homogeneous()
