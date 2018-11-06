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

from gi.repository import Gtk, Gdk

from lollypop.define import App


class DNDRow:
    """
        Allow Drag & drop on a Row
    """

    def __init__(self):
        """
            Init drag & drop
        """
        self.__next_row = None
        self.__previous_row = None
        self.__drag_data_delete_id = None
        self.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, [],
                             Gdk.DragAction.MOVE)
        self.drag_source_add_text_targets()
        self.drag_dest_set(Gtk.DestDefaults.DROP,
                           [], Gdk.DragAction.MOVE)
        self.drag_dest_add_text_targets()
        self.connect("drag-begin", self._on_drag_begin)
        self.connect("drag-data-get", self._on_drag_data_get)
        self.connect("drag-data-received", self._on_drag_data_received)

    def update_number(self, position):
        """
            Update row number
            @param position as int
        """
        if App().settings.get_value("show-tag-tracknumber"):
            return
        self._track.set_number(position)
        self.update_number_label()
        if self.next_row is not None:
            self.next_row.update_number(position + 1)

    def set_next_row(self, row):
        """
            Set next row
            @param row as Row
        """
        self.__next_row = row

    def set_previous_row(self, row):
        """
            Set previous row
            @param row as Row
        """
        self.__previous_row = row

    @property
    def next_row(self):
        """
            Get next row
            @return row as Row
        """
        return self.__next_row

    @property
    def previous_row(self):
        """
            Get previous row
            @return row as Row
        """
        return self.__previous_row

#######################
# PROTECTED           #
#######################
    def _on_drag_begin(self, widget, context):
        """
            @param widget as Gtk.Widget
            @param context as Gdk.DragContext
        """
        if self.__drag_data_delete_id is None:
            self.__drag_data_delete_id = self.connect(
                                                  "drag-data-delete",
                                                  self._on_drag_data_delete)

    def _on_drag_data_delete(self, widget, context):
        """
            Destroy row and update neighbours
            @param widget as Gtk.Widget
            @param context as Gdk.DragContext
        """
        if hasattr(widget, "_track"):
            self.emit("remove-track")
            widget.destroy()
            if widget.previous_row is not None:
                widget.previous_row.set_next_row(widget.next_row)
                widget.previous_row.update_number(
                    widget.previous_row.track.number)
            else:
                widget.update_number(widget.track.number - 1)
            if widget.next_row is not None:
                widget.next_row.set_previous_row(widget.previous_row)
        elif hasattr(widget, "_album"):
            self.emit("remove-album")
            widget.destroy()

    def _on_drag_data_get(self, widget, context, data, info, time):
        """
            Send track id
            @param widget as Gtk.Widget
            @param context as Gdk.DragContext
            @param data as Gtk.SelectionData
            @param info as int
            @param time as int
        """
        import json
        wstr = str(widget)
        if hasattr(self, "_track"):
            info = {"data": (wstr, self._track.id, None)}
        elif hasattr(self, "_album"):
            info = {"data": (wstr, self._album.id, self._album.track_ids)}
        text = json.dumps(info)
        data.set_text(text, len(text))

    def _on_drag_data_received(self, widget, context, x, y, data, info, time):
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
        height = self.get_allocated_height()
        if y > height / 2:
            down = True
        else:
            down = False
        try:
            import json
            info = json.loads(data.get_text())
            (wstr, item_id, track_ids) = info["data"]
            if str(widget) == wstr:
                self.disconnect(self.__drag_data_delete_id)
                self.__drag_data_delete_id = None
                return
            if wstr.find("AlbumRow") == -1:
                self.emit("insert-track", item_id, down)
            else:
                self.emit("insert-album", item_id, track_ids, down)
        except:
            if len(App().window.container.view.playlist_ids) == 1:
                App().playlists.import_uri(
                    App().window.container.view.playlist_ids[0],
                    data.get_text(), self._track.id, down)

#######################
# PRIVATE             #
#######################
