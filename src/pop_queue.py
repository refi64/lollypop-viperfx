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

from gi.repository import Gtk, GLib, Pango
from cgi import escape

from lollypop.define import Lp, Type, Shuffle
from lollypop.cellrendereralbum import CellRendererAlbum
from lollypop.objects import Track, Album


class QueueWidget(Gtk.Popover):
    """
        Popover with queue management
        @Warning: destroy it self on close
    """

    def __init__(self):
        """
            Init Popover
        """
        Gtk.Popover.__init__(self)
        self.set_position(Gtk.PositionType.BOTTOM)
        self.connect('map', self._on_map)
        self.connect('unmap', self._on_unmap)
        self._timeout = None
        self._in_drag = False
        self._signal_id1 = None
        self._signal_id2 = None

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/QueuePopover.ui')
        builder.connect_signals(self)

        self._clear_btn = builder.get_object('clear_btn')

        self._model = Gtk.ListStore(int,               # Album id
                                    str,               # Artist
                                    str,               # icon
                                    int)               # id

        self._view = builder.get_object('view')
        self._view.set_model(self._model)
        self._view.set_property('fixed_height_mode', True)

        self._widget = builder.get_object('widget')

        renderer0 = CellRendererAlbum()
        renderer1 = Gtk.CellRendererText()
        renderer1.set_property('ellipsize-set', True)
        renderer1.set_property('ellipsize', Pango.EllipsizeMode.END)
        renderer2 = Gtk.CellRendererPixbuf()
        column0 = Gtk.TreeViewColumn('pixbuf', renderer0, album=0)
        column0.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column1 = Gtk.TreeViewColumn('text', renderer1, markup=1)
        column1.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column1.set_expand(True)
        column2 = Gtk.TreeViewColumn('delete', renderer2)
        column2.add_attribute(renderer2, 'icon-name', 2)
        column2.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column2.set_property('fixed_width', 50)

        self._view.append_column(column0)
        self._view.append_column(column1)
        self._view.append_column(column2)

        self.add(self._widget)

    def do_show(self):
        """
            Set widget size
        """
        height = Lp().window.get_size()[1]
        self.set_size_request(400, height*0.7)
        Gtk.Popover.do_show(self)

    def populate(self):
        """
            Populate view
        """
        shuffle = Lp().settings.get_enum('shuffle')
        if Lp().player.get_queue():
            self._clear_btn.set_sensitive(True)
            GLib.idle_add(self._add_tracks, Lp().player.get_queue())
        elif Lp().player.get_albums() and shuffle != Shuffle.TRACKS:
            self._clear_btn.set_sensitive(True)
            GLib.idle_add(self._add_albums, Lp().player.get_albums())

#######################
# PRIVATE             #
#######################
    def _add_albums(self, album_ids):
        """
            Add albums to the view
            @param album ids as int
        """
        if not album_ids or self._signal_id1 is None:
            return
        album_id = album_ids.pop(0)
        album_name = Lp().albums.get_name(album_id)
        artist_id = Lp().albums.get_artist_id(album_id)
        artist_name = Lp().artists.get_name(artist_id)
        title = "<b>%s</b>\n%s" %\
            (escape(artist_name),
             escape(album_name))
        self._model.append([album_id,
                            title,
                            'user-trash-symbolic',
                            Type.NONE])
        GLib.idle_add(self._add_albums, album_ids)

    def _add_tracks(self, track_ids):
        """
            Add tracks to the view
            @param item ids as [int]
        """
        if not track_ids or self._signal_id1 is None:
            return
        track_id = track_ids.pop(0)
        album_id = Lp().tracks.get_album_id(track_id)
        artist_id = Lp().albums.get_artist_id(album_id)
        artist_name = Lp().artists.get_name(artist_id)
        track_name = Lp().tracks.get_name(track_id)
        title = "<b>%s</b>\n%s" %\
            (escape(artist_name),
             escape(track_name))
        self._model.append([album_id,
                            title,
                            'user-trash-symbolic',
                            track_id])
        GLib.idle_add(self._add_tracks, track_ids)

    def _on_map(self, widget):
        """
            Connect signals
            @param widget as Gtk.Widget
        """
        self._model.clear()
        self.populate()
        self._signal_id1 = Lp().player.connect('current-changed',
                                               self._on_current_changed)
        self._signal_id2 = self._model.connect('row-deleted',
                                               self._updated_rows)

    def _on_unmap(self, widget):
        """
            Disconnect signals
            @param widget as Gtk.Widget
        """
        if self._signal_id1:
            Lp().player.disconnect(self._signal_id1)
            self._signal_id1 = None
        if self._signal_id2:
            self._model.disconnect(self._signal_id2)
            self._signal_id2 = None

    def _on_keyboard_event(self, widget, event):
        """
            Delete item if Delete was pressed
            @param widget unused, Gdk.Event
        """
        if len(self._model) > 0:
            if event.keyval == 65535:
                path, column = self._view.get_cursor()
                iterator = self._model.get_iter(path)
                self._model.remove(iterator)

    def _on_current_changed(self, player):
        """
            Pop first item in queue if it's current track id
            @param player object
        """
        if len(self._model) > 0:
            start = self._model[0]
            end = self._model[-1]
            start_iter = self._model.get_iter(start.path)
            end_iter = self._model.get_iter(end.path)
            if start[3] == player.current_track.id:
                self._model.remove(start_iter)
            elif end[3] == Type.NONE and\
                    end[0] == player.current_track.album_id:
                self._model.move_before(end_iter, start_iter)
            elif start[3] == Type.NONE and\
                    start[0] != player.current_track.album_id:
                self._model.move_after(start_iter, end_iter)

    def _on_drag_begin(self, widget, context):
        """
            Mark as in drag
            @param unused
        """
        self._in_drag = True

    def _on_drag_end(self, widget, context):
        """
            Mark as not in drag
            @param unused
        """
        self._in_drag = False

    def _updated_rows(self, path, data):
        """
            Update queue when a row has been deleted
            @param path as Gtk.TreePath
            @param data as unused
        """
        if Lp().player.get_queue():
            queue = []
            for row in self._model:
                if row[3] != Type.NONE:
                    queue.append(row[3])
            Lp().player.set_queue(queue)
        elif Lp().player.get_albums():
            albums = []
            for row in self._model:
                albums.append(row[0])
            Lp().player.set_albums(albums)

    def _delete_row(self, iterator):
        """
            Delete row
            @param GtkTreeIter
        """
        self._model.remove(iterator)
        if len(self._model) == 0:
            self._clear_btn.set_sensitive(False)

    def _move_all_after(self, album_id):
        """
            Move all entries after album
            @param album id as int
        """
        for row in self._model:
            if row[0] == album_id:
                break
            end = self._model[-1]
            current_iter = self._model.get_iter(row.path)
            end_iter = self._model.get_iter(end.path)
            self._model.move_after(current_iter, end_iter)

    def _play(self, iterator):
        """
            Play album/track for selected iter
            @param GtkTreeIter
        """
        self._timeout = None
        if not self._in_drag:
            track_id = self._model.get_value(iterator, 3)
            if track_id == Type.NONE:
                album_id = self._model.get_value(iterator, 0)
                album = Album(album_id)
                Lp().player.load(album.tracks[0])
                self._move_all_after(album_id)
            else:
                Lp().player.load(Track(track_id))

    def _on_row_activated(self, view, path, column):
        """
            Play clicked item
            @param TreeView, TreePath, TreeViewColumn
        """
        if self._timeout:
            return
        iterator = self._model.get_iter(path)
        if iterator:
            if column.get_title() == "delete":
                self._delete_row(iterator)
            else:
                # We don't want to play if we are
                # starting a drag & drop, so delay
                self._timeout = GLib.timeout_add(500,
                                                 self._play,
                                                 iterator)

    def _on_button_clicked(self, widget):
        """
            Clear queue
            @param widget as Gtk.Button
        """
        self._model.clear()
