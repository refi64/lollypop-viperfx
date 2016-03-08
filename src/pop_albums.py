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

from lollypop.widgets_album_context import AlbumPopoverWidget
from lollypop.define import Lp, ArtSize
from lollypop.objects import Album


class AlbumRow(Gtk.ListBoxRow):
    """
        Album row
    """
    __gsignals__ = {
        'track-moved': (GObject.SignalFlags.RUN_FIRST, None, (int, int, int))
    }

    def __init__(self, album_id):
        """
            Init row widgets
            @param album id as int
        """
        Gtk.ListBoxRow.__init__(self)
        self._album = Album(album_id)
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/AlbumRow.ui')
        builder.connect_signals(self)
        self.set_property('has-tooltip', True)
        self.connect('query-tooltip', self._on_query_tooltip)
        self._row_widget = builder.get_object('row')
        self._row_widget.set_margin_top(2)
        self._row_widget.set_margin_end(2)
        self._artist_label = builder.get_object('artist')
        self._title_label = builder.get_object('title')
        self._cover = builder.get_object('cover')
        self._cover_frame = builder.get_object('frame')
        self._play_indicator = builder.get_object('play-indicator')
        self.add(self._row_widget)
        self.show_play_indicator(self._album.id ==
                                 Lp().player.current_track.album.id)
        self.show()
        self.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, [],
                             Gdk.DragAction.MOVE)
        self.drag_source_add_text_targets()
        self.drag_dest_set(Gtk.DestDefaults.DROP | Gtk.DestDefaults.MOTION,
                           [], Gdk.DragAction.MOVE)
        self.drag_dest_add_text_targets()
        self.connect('drag-begin', self._on_drag_begin)
        self.connect('drag-data-get', self._on_drag_data_get)
        self.connect('drag-data-received', self._on_drag_data_received)
        self.connect('drag-motion', self._on_drag_motion)
        self.connect('drag-leave', self._on_drag_leave)
        self.get_style_context().add_class('trackrow')

    def get_id(self):
        """
            Get row id
            @return row id as int
        """
        return self._album.id

    def set_labels(self):
        """
            Set artist, album and title label
        """
        self._title_label.set_text(self._album.name)
        self._artist_label.set_markup(escape(self._album.artist_name))

    def show_play_indicator(self, show):
        """
            Show play indicator
        """
        if show:
            self._play_indicator.set_opacity(1)
            self.get_style_context().remove_class('trackrow')
            self.get_style_context().add_class('trackrowplaying')
        else:
            self._play_indicator.set_opacity(0)
            self.get_style_context().add_class('trackrow')
            self.get_style_context().remove_class('trackrowplaying')

    def set_cover(self, surface):
        """
            Set cover surface
            @param surface as cairo.Surface
        """
        if surface is None:
            self._cover.clear()
            self._cover_frame.set_shadow_type(Gtk.ShadowType.NONE)
        else:
            self._cover.set_from_surface(surface)
            self._cover_frame.set_shadow_type(Gtk.ShadowType.IN)
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
        widget.drag_source_set_icon_name('emblem-music-symbolic')

    def _on_drag_data_get(self, widget, context, data, info, time):
        """
            Send track id
            @param widget as Gtk.Widget
            @param context as Gdk.DragContext
            @param data as Gtk.SelectionData
            @param info as int
            @param time as int
        """
        track_id = str(self._album.id)
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

    def _on_drag_motion(self, widget, context, x, y, time):
        """
            Add style
            @param widget as Gtk.Widget
            @param context as Gdk.DragContext
            @param x as int
            @param y as int
            @param time as int
        """
        height = self.get_allocated_height()
        if y > height/2:
            self.get_style_context().add_class('drag-up')
            self.get_style_context().remove_class('drag-down')
        else:
            self.get_style_context().remove_class('drag-up')
            self.get_style_context().add_class('drag-down')

    def _on_drag_leave(self, widget, context, time):
        """
            Remove style
            @param widget as Gtk.Widget
            @param context as Gdk.DragContext
            @param time as int
        """
        self.get_style_context().remove_class('drag-up')
        self.get_style_context().remove_class('drag-down')

    def _on_delete_clicked(self, button):
        """
            Delete album
            @param button as Gtk.Button
        """
        Lp().player.remove_album(self._album)
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
        layout_title = self._title_label.get_layout()
        layout_artist = self._artist_label.get_layout()
        if layout_title.is_ellipsized() or layout_artist.is_ellipsized():
            artist = escape(self._artist_label.get_text())
            title = escape(self._title_label.get_text())
            self.set_tooltip_markup("<b>%s</b>\n%s" % (artist, title))
        else:
            self.set_tooltip_text('')


class AlbumsPopover(Gtk.Popover):
    """
        Popover showing albums
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
        builder.add_from_resource('/org/gnome/Lollypop/AlbumsPopover.ui')
        builder.connect_signals(self)

        self._clear_button = builder.get_object('clear-button')
        self._jump_button = builder.get_object('jump-button')
        self._view = Gtk.ListBox()
        self._view.get_style_context().add_class('trackswidget')
        self._view.set_vexpand(True)
        self._view.set_selection_mode(Gtk.SelectionMode.NONE)
        self._view.set_activate_on_single_click(True)
        self._view.connect("row-activated", self._on_row_activated)
        self._view.show()
        self._scrolled = builder.get_object('scrolled')
        self._scrolled.add(self._view)
        self.add(builder.get_object('widget'))

    def do_show(self):
        """
            Set widget size
        """
        height = Lp().window.get_size()[1]
        self.set_size_request(400, height*0.7)
        Gtk.Popover.do_show(self)

    def populate(self):
        """
            Populate widget with album rows
        """
        albums = list(Lp().player.get_albums())
        self._jump_button.set_sensitive(False)
        if albums:
            self._clear_button.set_sensitive(True)
        self._add_items(albums)

#######################
# PRIVATE             #
#######################
    def _clear(self, clear_albums=False):
        """
            Clear the view
        """
        for child in self._view.get_children():
            child.destroy()
        if clear_albums:
            Lp().player.clear_albums()

    def _add_items(self, items, prev_album_id=None):
        """
            Add items to the view
            @param item ids as [int]
        """
        if items and not self._stop:
            album_id = items.pop(0)
            row = self._row_for_album_id(album_id)
            self._view.add(row)
            GLib.idle_add(self._add_items, items, album_id)
        else:
            if Lp().player.current_track.album.id in Lp().player.get_albums():
                self._jump_button.set_sensitive(True)
                self._jump_button.set_tooltip_text(
                                          Lp().player.current_track.album.name)

    def _row_for_album_id(self, album_id):
        """
            Get a row for track id
            @param album id as int
        """
        row = AlbumRow(album_id)
        surface = Lp().art.get_album_artwork(
                                    Album(album_id),
                                    ArtSize.MEDIUM*self.get_scale_factor())
        row.set_cover(surface)
        row.set_labels()
        row.connect('destroy', self._on_child_destroyed)
        row.connect('track-moved', self._on_track_moved)
        return row

    def _get_current_ordinate(self):
        """
            If current track in widget, return it ordinate,
            @return y as int
        """
        y = None
        for child in self._view.get_children():
            if child.get_id() == Lp().player.current_track.album.id:
                y = child.translate_coordinates(self._view, 0, 0)[1]
        return y

    def _on_map(self, widget):
        """
            Connect signals
            @param widget as Gtk.Widget
        """
        self._stop = False
        self.populate()
        self._signal_id1 = Lp().player.connect('current-changed',
                                               self._on_current_changed)

    def _on_unmap(self, widget):
        """
            Disconnect signals
            @param widget as Gtk.Widget
        """
        self._stop = True
        self._clear()
        if self._signal_id1 is not None:
            Lp().player.disconnect(self._signal_id1)
            self._signal_id1 = None

    def _on_current_changed(self, player):
        """
            Show tracks in a popover
            @param player object
        """
        if self._jump_button.get_sensitive():
            self._jump_button.set_tooltip_text(
                                          Lp().player.current_track.album.name)
        for child in self._view.get_children():
            child.show_play_indicator(child.get_id() ==
                                      Lp().player.current_track.album.id)

    def _on_child_destroyed(self, row):
        """
            Check clear button aspect
            @param row as AlbumRow
        """
        if row.get_id() != Lp().player.current_track.album.id:
            self._jump_button.set_sensitive(False)
            self._jump_button.set_tooltip_text('')
        self._clear_button.set_sensitive(len(self._view.get_children()) != 0)

    def _on_row_activated(self, widget, row):
        """
            Play searched item when selected
            @param widget as Gtk.ListBox
            @param row as AlbumRow
        """
        genre_ids = Lp().player.get_genre_ids(row.get_id())
        # TODO Remove this later
        if Gtk.get_minor_version() > 16:
            popover = AlbumPopoverWidget(
                                     row.get_id(),
                                     genre_ids,
                                     [],
                                     False)
            popover.set_relative_to(row)
            popover.show()
        else:
            album = Album(row.get_id(), genre_ids)
            Lp().player.load(album.tracks[0])

    def _on_jump_button_clicked(self, widget):
        """
            Scroll to album
        """
        y = self._get_current_ordinate()
        if y is not None:
            self._scrolled.get_vadjustment().set_value(y)

    def _on_clear_clicked(self, widget):
        """
            Clear albums
            @param widget as Gtk.Button
        """
        self._stop = True
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
        src_row = self._row_for_album_id(src)
        # Destroy current src row
        i = 0
        row_index = -1
        for child in self._view.get_children():
            if child == row:
                row_index = i
            if child.get_id() == src:
                child.disconnect_by_func(self._on_child_destroyed)
                child.destroy()
            else:
                i += 1

        # Add new row
        if row_index != -1:
            if not up:
                row_index += 1
            self._view.insert(src_row, row_index)
            Lp().player.move_album(src, row_index)
