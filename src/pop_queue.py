# Copyright (c) 2014-2016 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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
from cgi import escape

from lollypop.define import Lp, ArtSize
from lollypop.objects import Track, Album


class QueueRow(Gtk.ListBoxRow):
    """
        Queue row (a track)
    """
    __gsignals__ = {
        'track-moved': (GObject.SignalFlags.RUN_FIRST, None, (int, int, int))
    }

    def __init__(self, track_id):
        """
            Init row widgets
            @param track_id as int
        """
        Gtk.ListBoxRow.__init__(self)
        self.id = track_id
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/QueueRow.ui')
        builder.connect_signals(self)
        self.set_property('has-tooltip', True)
        self.connect('query-tooltip', self._on_query_tooltip)
        self._row_widget = builder.get_object('row')
        self._artist = builder.get_object('artist')
        self._title = builder.get_object('title')
        self._cover = builder.get_object('cover')
        self.add(self._row_widget)
        self.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, [],
                             Gdk.DragAction.MOVE)
        self.drag_source_add_text_targets()
        self.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.MOVE)
        self.drag_dest_add_text_targets()
        self.connect('drag-begin', self._on_drag_begin)
        self.connect('drag-data-get', self._on_drag_data_get)
        self.connect('drag-data-received', self._on_drag_data_received)

    def set_text(self, artist, title):
        """
            Set artist and title label
            @param artist name as string
            @param item name as string
        """
        self._artist.set_text(artist)
        self._title.set_text(title)

    def set_cover(self, surface):
        """
            Set cover surface
            @param surface as cairo surface
        """
        self._cover.set_from_surface(surface)
        del surface

#######################
# PRIVATE             #
#######################
    def _on_drag_begin(self, widget, context):
        """
            Set icon
            @param widget as Gtk.Widget
            @param context as Gdk.DragContext
        """
        widget.drag_source_set_icon_name('view-list-symbolic')

    def _on_drag_data_get(self, widget, context, data, info, time):
        """
            Send track id
            @param widget as Gtk.Widget
            @param context as Gdk.DragContext
            @param data as Gtk.SelectionData
            @param info as int
            @param time as int
        """
        track_id = str(self.id)
        data.set_text(track_id, len(track_id))

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
        self.emit('track-moved', int(data.get_text()), x, y)

    def _on_delete_clicked(self, button):
        """
            Delete track from queue
            @param button as Gtk.Button
        """
        Lp().player.del_from_queue(self.id)
        self.destroy()

    def _on_query_tooltip(self, widget, x, y, keyboard, tooltip):
        """
            Show tooltip if needed
            @param widget as Gtk.Widget
            @param x as int
            @param y as int
            @param keyboard as bool
            @param tooltip as Gtk.Tooltip
        """
        layout_title = self._title.get_layout()
        layout_artist = self._artist.get_layout()
        if layout_title.is_ellipsized() or layout_artist.is_ellipsized():
            artist = escape(self._artist.get_text())
            title = escape(self._title.get_text())
            self.set_tooltip_markup("<b>%s</b>\n%s" % (artist, title))
        else:
            self.set_tooltip_text('')


class QueuePopover(Gtk.Popover):
    """
        Popover showing queue with a filtering widget
    """

    def __init__(self):
        """
            Init Popover
        """
        Gtk.Popover.__init__(self)
        self.set_position(Gtk.PositionType.BOTTOM)
        self.connect('map', self._on_map)
        self.connect('unmap', self._on_unmap)

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/QueuePopover.ui')
        builder.connect_signals(self)

        self._clear_button = builder.get_object('clear-button')

        self._view = Gtk.ListBox()
        self._view.connect('button-press-event', self._plop)
        self._view.set_selection_mode(Gtk.SelectionMode.NONE)
        self._view.set_activate_on_single_click(False)
        self._view.connect("row-activated", self._on_row_activated)
        self._view.show()

        builder.get_object('scrolled').add(self._view)
        self.add(builder.get_object('widget'))

    def _plop(self, widget, event):
        return True

    def do_show(self):
        """
            Set widget size
        """
        height = Lp().window.get_size()[1]
        self.set_size_request(400, height*0.7)
        Gtk.Popover.do_show(self)

    def populate(self):
        """
            Populate widget with queue rows
        """
        if Lp().player.get_queue():
            self._clear_button.set_sensitive(True)
        self._add_items(list(Lp().player.get_queue()))

#######################
# PRIVATE             #
#######################
    def _clear(self, clear_queue=False):
        """
            Clear the view
        """
        for child in self._view.get_children():
            child.destroy()
        if clear_queue:
            Lp().player.set_queue([])

    def _add_items(self, items):
        """
            Add items to the view
            @param item ids as [int]
        """
        if items and not self._stop:
            track_id = items.pop(0)
            album_id = Lp().tracks.get_album_id(track_id)
            artist_id = Lp().albums.get_artist_id(album_id)
            artist_name = Lp().artists.get_name(artist_id)
            track_name = Lp().tracks.get_name(track_id)
            track_row = QueueRow(track_id)
            track_row.set_text(artist_name, track_name)
            track_row.set_cover(Lp().art.get_album_artwork(
                                    Album(album_id),
                                    ArtSize.MEDIUM*self.get_scale_factor()))
            track_row.show()
            track_row.connect('destroy', self._on_child_destroyed)
            track_row.connect('track-moved', self._on_track_moved)
            self._view.add(track_row)
            GLib.idle_add(self._add_items, items)

    def _on_map(self, widget):
        """
            Connect signals
            @param widget as Gtk.Widget
        """
        self._stop = False
        self._clear()
        self.populate()
        self._signal_id1 = Lp().player.connect('current-changed',
                                               self._on_current_changed)

    def _on_unmap(self, widget):
        """
            Disconnect signals
            @param widget as Gtk.Widget
        """
        self._stop = True
        if self._signal_id1 is not None:
            Lp().player.disconnect(self._signal_id1)
            self._signal_id1 = None

    def _on_current_changed(self, player):
        """
            Pop first item in queue if it's current track id
            @param player object
        """
        if len(self._view.get_children()) > 0:
            row = self._view.get_children()[0]
            if row.id == player.current_track.id:
                row.destroy()

    def _updated_rows(self, path, data):
        """
            Update queue when a row has been deleted
            @param path as Gtk.TreePath
            @param data as unused
        """
        if self.is_visible():
            new_queue = []
            for row in self._model:
                if row[3]:
                    new_queue.append(row[3])
            Lp().player.set_queue(new_queue)

    def _on_child_destroyed(self, row):
        """
            Check clear button aspect
            @param row as QueueRow
        """
        self._clear_button.set_sensitive(len(self._view.get_children()) != 0)

    def _on_row_activated(self, widget, row):
        """
            Play searched item when selected
            @param widget as Gtk.ListBox
            @param row as SearchRow
        """
        Lp().player.load(Track(row.id))

    def _on_button_clicked(self, widget):
        """
            Clear queue
            @param widget as Gtk.Button
        """
        self._clear(True)

    def _on_track_moved(self, row, src, x, y):
        """
            Pass signal
            @param row as PlaylistRow
            @param src as int
            @param x as int
            @param y as int
        """
        if row.get_id() == src:
            return
        height = row.get_allocated_height()
        if y > height/2:
            up = False
        else:
            up = True
        print(row)
        return
        self.emit('track-moved', row.get_id(), src, up)
