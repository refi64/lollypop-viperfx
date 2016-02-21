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

from gi.repository import Gtk, GLib, Gdk, Pango
from cgi import escape

from lollypop.define import Lp
from lollypop.cellrendereralbum import CellRendererAlbum
from lollypop.widgets_album_context import AlbumPopoverWidget


class AlbumsPopover(Gtk.Popover):
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
        self._rect = Gdk.Rectangle()
        self._timeout = None
        self._in_drag = False
        self._signal_id1 = None
        self._signal_id2 = None
        self._stop = False

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/AlbumsPopover.ui')
        builder.connect_signals(self)

        self._clear_btn = builder.get_object('clear_btn')

        self._model = Gtk.ListStore(int,               # Album id
                                    str,               # Artist
                                    str)              # icon

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
        albums = list(Lp().player.get_albums())
        if albums:
            self._clear_btn.set_sensitive(True)
        self._add_albums(albums)

#######################
# PRIVATE             #
#######################
    def _add_albums(self, albums):
        """
            Add albums to the view
            @param albums as [int]
        """
        if albums and not self._stop:
            album_id = albums.pop(0)
            album_name = Lp().albums.get_name(album_id)
            artist_id = Lp().albums.get_artist_id(album_id)
            artist_name = Lp().artists.get_name(artist_id)
            title = "<b>%s</b>\n%s" %\
                (escape(artist_name),
                 escape(album_name))
            self._model.append([album_id,
                                title,
                                'user-trash-symbolic'])
            GLib.idle_add(self._add_albums, albums)
        else:
            self._on_current_changed(Lp().player)
            self._connect_signals()

    def _connect_signals(self):
        """
            Connect signals
        """
        if self._signal_id1 is None:
            self._signal_id1 = Lp().player.connect('current-changed',
                                                   self._on_current_changed)
        if self._signal_id2 is None:
                self._signal_id2 = self._model.connect('row-deleted',
                                                       self._on_row_deleted)

    def _disconnect_signals(self):
        """
            Disconnect signals
        """
        if self._signal_id1 is not None:
            Lp().player.disconnect(self._signal_id1)
            self._signal_id1 = None
        if self._signal_id2 is not None:
            self._model.disconnect(self._signal_id2)
            self._signal_id2 = None

    def _on_map(self, widget):
        """
            Connect signals
            @param widget as Gtk.Widget
        """
        self._stop = False
        self.populate()

    def _on_unmap(self, widget):
        """
            Disconnect signals
            @param widget as Gtk.Widget
        """
        self._stop = True
        self._disconnect_signals()
        self._model.clear()

    def _on_keyboard_event(self, widget, event):
        """
            Delete item if Delete was pressed
            @param widget unused, Gdk.Event
        """
        if Lp().player.get_queue():
            if event.keyval == 65535:
                path, column = self._view.get_cursor()
                iterator = self._model.get_iter(path)
                self._model.remove(iterator)

    def _delete_row(self, iterator):
        """
            Delete row
            @param GtkTreeIter
        """
        self._model.remove(iterator)
        if len(self._model) == 0:
            self._clear_btn.set_sensitive(False)

    def _show_popover(self, iterator):
        """
            Show album popover
            @param GtkTreeIter
        """
        self._timeout = None
        if not self._in_drag:
            album_id = self._model.get_value(iterator, 0)
            popover = AlbumPopoverWidget(album_id, None, False)
            popover.set_relative_to(self._view)
            popover.set_pointing_to(self._rect)
            popover.show()

    def _set_albums(self):
        """
            Update player albums with model ones
        """
        albums = []
        for row in self._model:
            albums.append(row[0])
        Lp().player.set_albums2(albums)

    def _on_row_deleted(self, path, data):
        """
            Update queue when a row has been deleted
            @param path as Gtk.TreePath
            @param data as unused
        """
        self._set_albums()

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

    def _on_current_changed(self, player):
        """
            Pop first item in queue if it's current track id
            @param player object
        """
        for row in self._model:
            if row[0] == Lp().player.current_track.album_id:
                self._view.set_cursor(row.path)

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
                # We don't want to show popover if we are
                # starting a drag & drop, so delay
                self._timeout = GLib.timeout_add(250,
                                                 self._show_popover,
                                                 iterator)

    def _on_button_press(self, widget, event):
        """
            Store current position
        """
        self._rect = Gdk.Rectangle()
        self._rect.x = event.x
        self._rect.y = event.y
        self._rect.width = 1
        self._rect.height = 1

    def _on_button_clicked(self, widget):
        """
            Clear queue
            @param widget as Gtk.Button
        """
        self._disconnect_signals()
        self._model.clear()
        self._connect_signals()
        self._set_albums()
        self._clear_btn.set_sensitive(False)
