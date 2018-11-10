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

from gi.repository import GObject, Gtk, Gdk, GLib

from lollypop.define import App, ArtSize, Type, ResponsiveType
from lollypop.objects import Track


class TracksWidget(Gtk.ListBox):
    """
        A list of tracks
    """

    __gsignals__ = {
        "activated": (GObject.SignalFlags.RUN_FIRST,
                      None, (GObject.TYPE_PYOBJECT,))
    }

    def __init__(self, responsive_type):
        """
            Init track widget
            @param responsive_type as ResponsiveType
        """
        Gtk.ListBox.__init__(self)
        self.__autoscroll_timeout_id = None
        self.__prev_animated_rows = []
        self.connect("destroy", self.__on_destroy)
        self.__queue_signal_id = App().player.connect("queue-changed",
                                                      self.__on_queue_changed)
        self.__loved_signal_id1 = App().playlists.connect(
            "playlist-track-added",
            self.__on_loved_playlist_changed)
        self.__loved_signal_id2 = App().playlists.connect(
            "playlist-track-removed",
            self.__on_loved_playlist_changed)
        self.connect("row-activated", self.__on_activate)
        self.get_style_context().add_class("trackswidget")
        self.set_property("hexpand", True)
        self.set_property("selection-mode", Gtk.SelectionMode.NONE)
        if responsive_type == ResponsiveType.DND:
            self.drag_dest_set(Gtk.DestDefaults.DROP | Gtk.DestDefaults.MOTION,
                               [], Gdk.DragAction.MOVE)
            self.drag_dest_add_text_targets()
            self.connect("drag-motion", self.__on_drag_motion)
            self.connect("drag-data-received", self.__on_drag_data_received)

    def update_playing(self, track_id):
        """
            Update playing track
            @param track id as int
        """
        for row in self.get_children():
            row.set_indicator(row.track.id == track_id,
                              Track(row.track.id).loved)

    def show_spinner(self, track_id):
        """
            Show spinner for track_id
        """
        for row in self.get_children():
            if row.id == track_id:
                row.show_spinner()
                break

#######################
# PRIVATE             #
#######################
    def __rows_animation(self, x, y):
        """
            Show animation to help user dnd
            @param x as int
            @param y as int
            @return child as PlaylistRow/None
        """
        rows = self.get_children()
        for row in rows:
            coordinates = row.translate_coordinates(self, 0, 0)
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

    def __clear_animation(self):
        """
            Clear any animation
        """
        for row in self.__prev_animated_rows:
            ctx = row.get_style_context()
            ctx.remove_class("drag-up")
            ctx.remove_class("drag-down")

    def __auto_scroll(self, up):
        """
            Auto scroll up/down
            @param up as bool
        """
        adj = self._scrolled.get_vadjustment()
        value = adj.get_value()
        if up:
            adj_value = value - ArtSize.SMALL
            adj.set_value(adj_value)
            if adj.get_value() == 0:
                self.__autoscroll_timeout_id = None
                self.get_style_context().remove_class("drag-down")
                self.get_style_context().remove_class("drag-up")
                return False
            else:
                self.get_style_context().add_class("drag-up")
                self.get_style_context().remove_class("drag-down")
        else:
            adj_value = value + ArtSize.SMALL
            adj.set_value(adj_value)
            if adj.get_value() < adj_value:
                self.__autoscroll_timeout_id = None
                self.get_style_context().remove_class("drag-down")
                self.get_style_context().remove_class("drag-up")
                return False
            else:
                self.get_style_context().add_class("drag-down")
                self.get_style_context().remove_class("drag-up")
        return True

    def __on_drag_motion(self, widget, context, x, y, time):
        """
            Add style
            @param widget as Gtk.Widget
            @param context as Gdk.DragContext
            @param x as int
            @param y as int
            @param time as int
        """
        auto_scroll = False
        up = y <= ArtSize.MEDIUM
        scrolled = self.get_ancestor(Gtk.ScrolledWindow)
        if scrolled is None:
            return
        if up:
            auto_scroll = True
        elif y >= scrolled.get_allocated_height() - ArtSize.MEDIUM:
            auto_scroll = True
        else:
            self.get_style_context().remove_class("drag-down")
            self.get_style_context().remove_class("drag-up")
            if self.__autoscroll_timeout_id is not None:
                GLib.source_remove(self.__autoscroll_timeout_id)
                self.__autoscroll_timeout_id = None
            self.__clear_animation()
            row = self.__rows_animation(x, y)
            if row is not None:
                self.__prev_animated_rows.append(row)
            return
        if self.__autoscroll_timeout_id is None and auto_scroll:
            self.__clear_animation()
            self.__autoscroll_timeout_id = GLib.timeout_add(100,
                                                            self.__auto_scroll,
                                                            up)

    def __on_drag_data_received(self, widget, context, x, y, data, info, time):
        """
            Move track at view bounds
            @param widget as Gtk.Widget
            @param context as Gdk.DragContext
            @param x as int
            @param y as int
            @param data as Gtk.SelectionData
            @param info as int
            @param time as int
        """
        if self.get_children():
            row = self.get_children()[-1]
            y = row.get_allocated_height()
            row.emit("drag-data-received",
                     context,
                     x,
                     y,
                     data,
                     info,
                     time)

    def __on_queue_changed(self, unused):
        """
            Update all position labels
        """
        for row in self.get_children():
            row.update_number_label()

    def __on_loved_playlist_changed(self, widget, playlist_id, uri):
        """
            Updates the loved icon
            @param playlist as Playlist
            @param playlist id as int
            @param track id as int
        """
        if playlist_id != Type.LOVED:
            return
        track_id = App().tracks.get_id_by_uri(uri)
        for row in self.get_children():
            if track_id == row.track.id:
                row.set_indicator(track_id == App().player.current_track.id,
                                  Track(track_id).loved)

    def __on_destroy(self, widget):
        """
            Remove signals
            @param widget as Gtk.Widget
        """
        if self.__queue_signal_id is not None:
            App().player.disconnect(self.__queue_signal_id)
            self.__queue_signal_id = None
        if self.__loved_signal_id1 is not None:
            App().playlists.disconnect(self.__loved_signal_id1)
            self.__loved_signal_id1 = None
        if self.__loved_signal_id2 is not None:
            App().playlists.disconnect(self.__loved_signal_id2)
            self.__loved_signal_id2 = None

    def __on_activate(self, widget, row):
        """
            Play activated item
            @param widget as TracksWidget
            @param row as TrackRow
        """
        self.emit("activated", row.track)
