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

from gi.repository import Gtk, GLib, Gdk, Pango, GObject

from cgi import escape
from gettext import gettext as _

from lollypop.pop_album import AlbumPopover
from lollypop.view import LazyLoadingView
from lollypop.define import Lp, ArtSize, NextContext
from lollypop.objects import Album


class AlbumRow(Gtk.ListBoxRow):
    """
        Album row
    """
    __gsignals__ = {
        'track-moved': (GObject.SignalFlags.RUN_FIRST, None, (int, int, int))
    }

    MARGIN = 2

    def get_best_height(widget):
        """
            Helper to pass object it's preferred height
            @param widget as Gtk.Widget
        """
        ctx = widget.get_pango_context()
        layout = Pango.Layout.new(ctx)
        layout.set_text("a", 1)
        font_height = int(AlbumRow.MARGIN * 2 + 2 * layout.get_pixel_size()[1])
        cover_height = AlbumRow.MARGIN * 2 + ArtSize.MEDIUM
        if font_height > cover_height:
            return font_height + 2
        else:
            return cover_height + 2

    def __init__(self, album_id, height):
        """
            Init row widgets
            @param album id as int
        """
        Gtk.ListBoxRow.__init__(self)
        self._album = Album(album_id)
        self._play_indicator = None
        self.set_sensitive(False)
        self.get_style_context().add_class('loading')
        self._height = height
        self.set_property('height-request', height)
        self.set_margin_start(5)
        self.set_margin_end(5)

    def populate(self):
        """
            Populate widget content
        """
        self.get_style_context().remove_class('loading')
        self.set_sensitive(True)
        self.set_property('has-tooltip', True)
        self.connect('query-tooltip', self._on_query_tooltip)
        row_widget = Gtk.EventBox()
        row_widget.set_property('valign', Gtk.Align.CENTER)
        row_widget.set_margin_top(self.MARGIN)
        row_widget.set_margin_end(self.MARGIN)
        grid = Gtk.Grid()
        grid.set_column_spacing(8)
        self._artist_label = Gtk.Label.new("<b>%s</b>" %
                                           escape(", ".join(
                                                         self._album.artists)))
        self._artist_label.set_use_markup(True)
        self._artist_label.set_hexpand(True)
        self._artist_label.set_property('halign', Gtk.Align.START)
        self._artist_label.set_ellipsize(Pango.EllipsizeMode.END)
        self._title_label = Gtk.Label.new(self._album.name)
        self._title_label.set_ellipsize(Pango.EllipsizeMode.END)
        cover = Gtk.Image()
        cover.get_style_context().add_class('small-cover-frame')
        surface = Lp().art.get_album_artwork(
                                        self._album,
                                        ArtSize.MEDIUM,
                                        self.get_scale_factor())
        cover.set_from_surface(surface)
        cover.set_size_request(ArtSize.MEDIUM, ArtSize.MEDIUM)
        del surface
        self._play_indicator = Gtk.Image.new_from_icon_name(
                                               'media-playback-start-symbolic',
                                               Gtk.IconSize.MENU)
        delete_button = Gtk.Button.new_from_icon_name('user-trash-symbolic',
                                                      Gtk.IconSize.MENU)
        # Here a hack to make old Gtk version support min-height css attribute
        # min-height = 24px, borders = 2px
        delete_button.set_property('height-request', 26)
        delete_button.get_image().set_opacity(0.2)
        delete_button.set_relief(Gtk.ReliefStyle.NONE)
        delete_button.get_style_context().add_class('menu-button')
        delete_button.get_style_context().add_class('track-menu-button')
        delete_button.set_property('valign', Gtk.Align.CENTER)
        delete_button.connect('clicked', self._on_delete_clicked)
        vgrid = Gtk.Grid()
        vgrid.set_column_spacing(5)
        vgrid.add(self._play_indicator)
        vgrid.add(self._title_label)
        grid.attach(self._artist_label, 1, 0, 1, 1)
        grid.attach(delete_button, 2, 0, 1, 2)
        grid.attach(cover, 0, 0, 1, 2)
        grid.attach(vgrid, 1, 1, 1, 1)
        row_widget.add(grid)
        self.add(row_widget)
        self.get_style_context().add_class('trackrow')
        self.show_play_indicator(self._album.id ==
                                 Lp().player.current_track.album.id)
        self.show_all()
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

    def do_get_preferred_height(self):
        """
            Return preferred height
            @return (int, int)
        """
        return (self._height, self._height)

    def get_id(self):
        """
            Get row id
            @return row id as int
        """
        return self._album.id

    def show_play_indicator(self, show):
        """
            Show play indicator
        """
        if self._play_indicator is None:
            return
        if show:
            self._play_indicator.set_opacity(1)
            self.get_style_context().remove_class('trackrow')
            self.get_style_context().add_class('trackrowplaying')
        else:
            self._play_indicator.set_opacity(0)
            self.get_style_context().add_class('trackrow')
            self.get_style_context().remove_class('trackrowplaying')

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
        try:
            self.emit('track-moved', int(data.get_text()), x, y)
        except:
            pass

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
        if Lp().player.current_track.album.id == self._album.id:
            # If not last album, skip it
            if len(Lp().player.get_albums()) > 1:
                Lp().player.set_next_context(NextContext.START_NEW_ALBUM)
                Lp().player.set_next()
                Lp().player.next()
                Lp().player.remove_album(self._album)
            # remove it and stop playback by going to next track
            else:
                Lp().player.remove_album(self._album)
                Lp().player.set_next()
                Lp().player.next()
        else:
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


class AlbumsView(LazyLoadingView):
    """
        View showing albums
    """

    def __init__(self):
        """
            Init Popover
        """
        LazyLoadingView.__init__(self)
        # Calculate default album height based on current pango context
        # We may need to listen to screen changes
        self._height = AlbumRow.get_best_height(self)
        self.connect('map', self._on_map)
        self.connect('unmap', self._on_unmap)
        self._clear_button = Gtk.Button.new_from_icon_name(
                                                    'edit-clear-all-symbolic',
                                                    Gtk.IconSize.MENU)
        self._clear_button.set_relief(Gtk.ReliefStyle.NONE)
        self._clear_button.set_tooltip_text(_("Clear albums"))
        self._clear_button.set_sensitive(False)
        self._clear_button.connect('clicked', self._on_clear_clicked)
        self._jump_button = Gtk.Button.new_from_icon_name(
                                                    'go-jump-symbolic',
                                                    Gtk.IconSize.MENU)
        self._jump_button.set_relief(Gtk.ReliefStyle.NONE)
        self._jump_button.connect('clicked', self._on_jump_clicked)
        self._jump_button.set_tooltip_text(_("Go to current track"))
        label = Gtk.Label.new("<b>"+_("Playing albums")+"</b>")
        label.set_use_markup(True)
        label.set_hexpand(True)
        label.set_margin_start(2)
        label.get_style_context().add_class('dim-label')
        label.set_property('halign', Gtk.Align.START)
        self.set_row_spacing(2)
        grid = Gtk.Grid()
        grid.set_column_spacing(5)
        grid.add(label)
        grid.add(self._jump_button)
        grid.add(self._clear_button)
        grid.show_all()
        self._view = Gtk.ListBox()
        self._view.get_style_context().add_class('trackswidget')
        self._view.set_vexpand(True)
        self._view.set_selection_mode(Gtk.SelectionMode.NONE)
        self._view.set_activate_on_single_click(True)
        self._view.connect("row-activated", self._on_row_activated)
        self._view.show()
        self.add(grid)
        self._scrolled.set_property('expand', True)
        self.add(self._scrolled)
        self.drag_dest_set(Gtk.DestDefaults.DROP | Gtk.DestDefaults.MOTION,
                           [], Gdk.DragAction.MOVE)
        self.drag_dest_add_text_targets()
        self.connect('drag-data-received', self._on_drag_data_received)

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
        self._clear_button.set_sensitive(False)

    def _add_items(self, items, prev_album_id=None):
        """
            Add items to the view
            @param item ids as [int]
        """
        if items and not self._stop:
            album_id = items.pop(0)
            row = self._row_for_album_id(album_id)
            row.show()
            self._view.add(row)
            self._lazy_queue.append(row)
            GLib.idle_add(self._add_items, items, album_id)
        else:
            GLib.idle_add(self.lazy_loading)
            if self._viewport.get_child() is None:
                self._viewport.add(self._view)
            if Lp().player.current_track.album.id in Lp().player.get_albums():
                self._jump_button.set_sensitive(True)

    def _row_for_album_id(self, album_id):
        """
            Get a row for track id
            @param album id as int
        """
        row = AlbumRow(album_id, self._height)
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
        self._lazy_queue = []
        self._clear()
        if self._signal_id1 is not None:
            Lp().player.disconnect(self._signal_id1)
            self._signal_id1 = None

    def _on_current_changed(self, player):
        """
            Show tracks in a popover
            @param player object
        """
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
        self._clear_button.set_sensitive(len(self._view.get_children()) != 0)

    def _on_row_activated(self, widget, row):
        """
            Play searched item when selected
            @param widget as Gtk.ListBox
            @param row as AlbumRow
        """
        genre_ids = Lp().player.get_genre_ids(row.get_id())
        artist_ids = Lp().player.get_artist_ids(row.get_id())
        # TODO Remove this later
        if Gtk.get_minor_version() > 16:
            popover = AlbumPopover(
                                     row.get_id(),
                                     genre_ids,
                                     [])
            popover.set_relative_to(row)
            popover.show()
        else:
            album = Album(row.get_id(), genre_ids, artist_ids)
            Lp().player.load(album.tracks[0])

    def _on_jump_clicked(self, widget):
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
        GLib.idle_add(self._clear, True)

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
        src_row.populate()
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
        try:
            self._on_track_moved(self._view.get_children()[-1],
                                 int(data.get_text()), x, y)
        except:
            pass


class AlbumsPopover(Gtk.Popover):
    """
        Popover showing Albums View
    """

    def __init__(self):
        """
            Init popover
        """
        Gtk.Popover.__init__(self)
        view = AlbumsView()
        view.show()
        self.set_position(Gtk.PositionType.BOTTOM)
        self.connect('map', self._on_map)
        self.add(view)

    def _on_map(self, widget):
        """
            Resize
            @param widget as Gtk.Widget
        """
        height = Lp().window.get_size()[1]
        self.set_size_request(400, height*0.7)
