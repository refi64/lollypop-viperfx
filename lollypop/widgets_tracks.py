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

from gi.repository import GObject, Gtk, Gdk

from lollypop.define import App, Type, ResponsiveType
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
            self.drag_dest_set(Gtk.DestDefaults.DROP,
                               [], Gdk.DragAction.MOVE)
            self.drag_dest_add_text_targets()
            self.connect("drag-data-received", self.__on_drag_data_received)

    def update_headers(self, prev_album_id=None):
        """
            Update headers
            @param previous album id as int
        """
        for child in self.get_children():
            if child.track.album.id == prev_album_id:
                child.show_headers(False)
            else:
                child.show_headers(True)
            prev_album_id = child.track.album.id

    def update_indexes(self, start):
        """
            Update indexes
            @param start index as int
        """
        for row in self.get_children():
            row.track.set_number(start)
            row.update_number_label()
            start += 1

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
    def __on_drag_data_received(self, widget, context, x, y, data, info, time):
        """
            Move track
            @param widget as Gtk.Widget
            @param context as Gdk.DragContext
            @param x as int
            @param y as int
            @param data as Gtk.SelectionData
            @param info as int
            @param time as int
        """
        try:
            from lollypop.view import View
            view = widget.get_ancestor(View)
            if view is not None:
                view.clear_animation()
            value = int(data.get_text())
            bottom_row = self.get_children()[-1]
            bottom_row.emit("track-moved", bottom_row.id, value, False)
        except:
            if len(App().window.container.view.playlist_ids) == 1:
                App().playlists.import_uri(
                    App().window.container.view.playlist_ids[0],
                    data.get_text())

    def __on_queue_changed(self, unused):
        """
            Update all position labels
        """
        for row in self.get_children():
            row.update_number_label()

    def __on_loved_playlist_changed(self, widget, playlist_id, uri, pos):
        """
            Updates the loved icon
            @param playlist as Playlist
            @param playlist id as int
            @param track id as int
            @param pos as int
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