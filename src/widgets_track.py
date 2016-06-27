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

from gi.repository import GObject, Gtk, Gdk, Pango, GLib, Gst

from cgi import escape

from lollypop.define import Lp, ArtSize, Type
from lollypop.pop_menu import TrackMenuPopover, TrackMenu
from lollypop.widgets_indicator import IndicatorWidget
from lollypop.utils import seconds_to_string
from lollypop.objects import Track
from lollypop import utils


class Row(Gtk.ListBoxRow):
    """
        A row
    """
    def __init__(self, rowid, num):
        """
            Init row widgets
            @param rowid as int
            @param num as int
            @param show loved as bool
        """
        # We do not use Gtk.Builder for speed reasons
        Gtk.ListBoxRow.__init__(self)
        self._artists_label = None
        self._track = Track(rowid)
        self._number = num
        self._timeout_id = None
        self._player_preview = None
        self._indicator = IndicatorWidget(self._track.id)
        self.set_indicator(Lp().player.current_track.id == self._track.id,
                           utils.is_loved(self._track.id))
        self._row_widget = Gtk.EventBox()
        self._row_widget.connect('button-press-event', self._on_button_press)
        self._row_widget.connect('enter-notify-event', self._on_enter_notify)
        self._grid = Gtk.Grid()
        self._grid.set_column_spacing(5)
        self._row_widget.add(self._grid)
        self._title_label = Gtk.Label.new(self._track.name)
        self._title_label.set_property('has-tooltip', True)
        self._title_label.connect('query-tooltip',
                                  self._on_query_tooltip)
        self._title_label.set_property('hexpand', True)
        self._title_label.set_property('halign', Gtk.Align.START)
        self._title_label.set_ellipsize(Pango.EllipsizeMode.END)
        if self._track.non_album_artists:
            self._artists_label = Gtk.Label.new(escape(
                                     ", ".join(self._track.non_album_artists)))
            self._artists_label.set_use_markup(True)
            self._artists_label.set_property('has-tooltip', True)
            self._artists_label.connect('query-tooltip',
                                        self._on_query_tooltip)
            self._artists_label.set_property('hexpand', True)
            self._artists_label.set_property('halign', Gtk.Align.END)
            self._artists_label.set_ellipsize(Pango.EllipsizeMode.END)
            self._artists_label.set_opacity(0.3)
            self._artists_label.set_margin_end(5)
            self._artists_label.show()
        self._duration_label = Gtk.Label.new(
                                       seconds_to_string(self._track.duration))
        self._duration_label.get_style_context().add_class('dim-label')
        self._num_label = Gtk.Label()
        self._num_label.set_ellipsize(Pango.EllipsizeMode.END)
        self._num_label.set_property('valign', Gtk.Align.CENTER)
        self._num_label.set_width_chars(4)
        self._num_label.get_style_context().add_class('dim-label')
        self.update_num_label()
        self._menu_button = Gtk.Button.new()
        # Here a hack to make old Gtk version support min-height css attribute
        # min-height = 24px, borders = 2px, we set directly on stack
        # min-width = 24px, borders = 2px, padding = 8px
        self._menu_button.set_size_request(34, 26)
        self._menu_button.set_relief(Gtk.ReliefStyle.NONE)
        self._menu_button.get_style_context().add_class('menu-button')
        self._menu_button.get_style_context().add_class('track-menu-button')
        self._grid.add(self._num_label)
        self._grid.add(self._title_label)
        if self._artists_label is not None:
            self._grid.add(self._artists_label)
        self._grid.add(self._duration_label)
        # TODO Remove this later
        if Gtk.get_minor_version() > 16:
            self._grid.add(self._menu_button)
        else:
            self.connect('map', self._on_map)
        self.add(self._row_widget)
        self.get_style_context().add_class('trackrow')

    def set_indicator(self, playing, loved):
        """
            Show indicator
            @param widget name as str
            @param playing as bool
            @param loved as bool
        """
        self._indicator.clear()
        if playing:
            self.get_style_context().remove_class('trackrow')
            self.get_style_context().add_class('trackrowplaying')
            if loved:
                self._indicator.play_loved()
            else:
                self._indicator.play()
        else:
            self.get_style_context().remove_class('trackrowplaying')
            self.get_style_context().add_class('trackrow')
            if loved:
                self._indicator.loved()
            else:
                self._indicator.empty()

    def set_number(self, num):
        """
            Set number
            @param number as int
        """
        self._number = num

    def update_num_label(self):
        """
            Update position label for row
        """
        if Lp().player.is_in_queue(self._track.id):
            self._num_label.get_style_context().add_class('queued')
            pos = Lp().player.get_track_position(self._track.id)
            self._num_label.set_text(str(pos))
        elif self._number > 0:
            self._num_label.get_style_context().remove_class('queued')
            self._num_label.set_text(str(self._number))
        else:
            self._num_label.get_style_context().remove_class('queued')
            self._num_label.set_text('')

    def get_id(self):
        """
            Get object id
            @return Current id as int
        """
        return self._track.id

#######################
# PRIVATE             #
#######################
    def _play_preview(self):
        """
            Play track
            @param widget as Gtk.Widget
        """
        Lp().player.preview.set_property('uri', self._track.uri)
        Lp().player.preview.set_state(Gst.State.PLAYING)
        self.set_indicator(True, False)
        self._timeout_id = None

    def _on_map(self, widget):
        """
            Fix for Gtk < 3.18,
            if we are in a popover, do not show menu button
        """
        widget = self.get_parent()
        while widget is not None:
            if isinstance(widget, Gtk.Popover):
                break
            widget = widget.get_parent()
        if widget is None:
            self._grid.add(self._menu_button)
            self._menu_button.show()

    def _on_enter_notify(self, widget, event):
        """
            Set image on buttons now, speed reason
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        if Lp().settings.get_value('preview-output').get_string() != '':
            widget.connect('leave-notify-event', self._on_leave_notify)
            self._timeout_id = GLib.timeout_add(500, self._play_preview)
        if self._menu_button.get_image() is None:
            image = Gtk.Image.new_from_icon_name('open-menu-symbolic',
                                                 Gtk.IconSize.MENU)
            image.set_opacity(0.2)
            self._menu_button.set_image(image)
            self._menu_button.connect('clicked', self._on_button_clicked)
            self._indicator.update_button()

    def _on_leave_notify(self, widget, event):
        """
            Stop preview
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        if self._timeout_id is not None:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = None
        self.set_indicator(Lp().player.current_track.id == self._track.id,
                           utils.is_loved(self._track.id))
        Lp().player.preview.set_state(Gst.State.NULL)
        widget.disconnect_by_func(self._on_leave_notify)

    def _on_button_press(self, widget, event):
        """
            Popup menu for track relative to track row
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        if event.button == 3 and Gtk.get_minor_version() > 16:
            window = widget.get_window()
            if window == event.window:
                self._popup_menu(widget, event.x, event.y)
            # Happens when pressing button over menu btn
            else:
                self._popup_menu(self._menu_button)
            return True
        elif event.button == 2:
            if self._track.id in Lp().player.get_queue():
                Lp().player.del_from_queue(self._track.id)
            else:
                Lp().player.append_to_queue(self._track.id)

    def _on_button_clicked(self, widget):
        """
            Popup menu for track relative to button
            @param widget as Gtk.Button
        """
        self._popup_menu(widget)

    def _popup_menu(self, widget, xcoordinate=None, ycoordinate=None):
        """
            Popup menu for track
            @param widget as Gtk.Button
            @param xcoordinate as int (or None)
            @param ycoordinate as int (or None)
        """
        popover = TrackMenuPopover(self._track.id, TrackMenu(self._track.id))
        popover.set_relative_to(widget)
        if xcoordinate is not None and ycoordinate is not None:
            rect = widget.get_allocation()
            rect.x = xcoordinate
            rect.y = ycoordinate
            rect.width = rect.height = 1
            popover.set_pointing_to(rect)
        popover.connect('closed', self._on_closed)
        self.get_style_context().add_class('track-menu-selected')
        popover.show()

    def _on_closed(self, widget):
        """
            Remove selected style
            @param widget as Gtk.Popover
        """
        self.get_style_context().remove_class('track-menu-selected')

    def _on_query_tooltip(self, widget, x, y, keyboard, tooltip):
        """
            Show tooltip if needed
            @param widget as Gtk.Widget
            @param x as int
            @param y as int
            @param keyboard as bool
            @param tooltip as Gtk.Tooltip
        """
        text = ''
        layout = widget.get_layout()
        label = widget.get_text()
        if layout.is_ellipsized():
            text = "%s" % (escape(label))
        widget.set_tooltip_markup(text)


class PlaylistRow(Row):
    """
        A track row with album cover
    """
    __gsignals__ = {
        'track-moved': (GObject.SignalFlags.RUN_FIRST, None, (int, int, bool))
    }

    def __init__(self, rowid, num, show_headers):
        """
            Init row widget
            @param rowid as int
            @param num as int
            @param show headers as bool
        """
        Row.__init__(self, rowid, num)
        self._show_headers = show_headers
        self._indicator.set_margin_start(5)
        self._row_widget.set_margin_start(5)
        self._row_widget.set_margin_top(2)
        self._row_widget.set_margin_end(5)
        self._grid.insert_row(0)
        self._grid.insert_column(0)
        self._grid.insert_column(1)
        self._grid.attach(self._indicator, 1, 1, 1, 2)
        self._cover = Gtk.Image()
        self._cover.set_property('halign', Gtk.Align.CENTER)
        self._cover.set_property('valign', Gtk.Align.CENTER)
        self._cover.get_style_context().add_class('small-cover-frame')
        self._cover.set_no_show_all(True)
        # We force width with a Box
        box = Gtk.Box()
        box.set_homogeneous(True)
        box.add(self._cover)
        box.set_property('width-request', ArtSize.MEDIUM+2)
        self._grid.attach(box, 0, 0, 1, 2)
        self.show_all()
        self._header = Gtk.Grid()
        self._header.set_column_spacing(5)
        if self._track.album.artist_ids[0] != Type.COMPILATIONS:
            self._album_artist_label = Gtk.Label()
            self._album_artist_label.set_markup(
                                 "<b>" +
                                 escape(", ".join(self._track.album.artists)) +
                                 "</b>")
            self._album_artist_label.set_ellipsize(Pango.EllipsizeMode.END)
            self._album_artist_label.get_style_context().add_class('dim-label')
            self._header.add(self._album_artist_label)
        self._album_label = Gtk.Label.new(self._track.album.name)
        self._album_label.set_ellipsize(Pango.EllipsizeMode.END)
        self._album_label.get_style_context().add_class('dim-label')
        self._header.add(self._album_label)
        self._num_label.set_property('valign', Gtk.Align.END)
        self._title_label.set_property('valign', Gtk.Align.END)
        if self._artists_label is not None:
            self._artists_label.set_property('valign', Gtk.Align.END)
        self._duration_label.set_property('valign', Gtk.Align.END)
        self._indicator.set_property('valign', Gtk.Align.END)
        self._grid.attach(self._header, 1, 0, 4, 1)
        self.set_indicator(Lp().player.current_track.id == self._track.id,
                           utils.is_loved(self._track.id))
        self.show_headers(self._show_headers)
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

    def show_headers(self, show):
        """
            Show header
            @param show as bool
        """
        if not self.get_sensitive():
            return
        if self._header.is_visible() == show:
            return
        self._show_headers = show
        if show:
            self._cover.set_tooltip_text(self._track.album.name)
            surface = Lp().art.get_album_artwork(
                                        self._track.album,
                                        ArtSize.MEDIUM,
                                        self.get_scale_factor())
            self._cover.set_from_surface(surface)
            self._cover.show()
            del surface
            self._header.show_all()
        else:
            self._cover.set_tooltip_text('')
            self._cover.clear()
            self._cover.hide()
            self._header.hide()

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
        track_id = str(self._track.id)
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
            src = int(data.get_text())
            if self._track.id == src:
                return
            height = self.get_allocated_height()
            if y > height/2:
                up = False
            else:
                up = True
            self.emit('track-moved', self._track.id, src, up)
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


class TrackRow(Row):
    """
        A track row
    """

    def get_best_height(widget):
        """
            Calculate widget height
            @param widget as Gtk.Widget
        """
        ctx = widget.get_pango_context()
        layout = Pango.Layout.new(ctx)
        layout.set_text("a", 1)
        font_height = int(layout.get_pixel_size()[1])
        # Button min height + borders (application.css)
        menu_height = 24 + 2
        if font_height > menu_height:
            height = font_height
        else:
            height = menu_height
        return height

    def __init__(self, rowid, num):
        """
            Init row widget and show it
            @param rowid as int
            @param num as int
        """
        Row.__init__(self, rowid, num)
        self._grid.insert_column(0)
        self._grid.attach(self._indicator, 0, 0, 1, 1)
        self.show_all()

#######################
# PRIVATE             #
#######################


class TracksWidget(Gtk.ListBox):
    """
        A list of tracks
    """

    __gsignals__ = {
        'activated': (GObject.SignalFlags.RUN_FIRST, None, (int,))
    }

    def __init__(self, dnd=False):
        """
            Init track widget
            @param drag and drop as bool
        """
        Gtk.ListBox.__init__(self)
        self.connect('destroy', self._on_destroy)
        self._queue_signal_id = Lp().player.connect('queue-changed',
                                                    self._on_queue_changed)
        self._loved_signal_id1 = Lp().playlists.connect(
                                               'playlist-add',
                                               self._on_loved_playlist_changed)
        self._loved_signal_id2 = Lp().playlists.connect(
                                               'playlist-del',
                                               self._on_loved_playlist_changed)
        self.connect("row-activated", self._on_activate)
        self.get_style_context().add_class('trackswidget')
        self.set_property('hexpand', True)
        self.set_property('selection-mode', Gtk.SelectionMode.NONE)
        if dnd:
            self.drag_dest_set(Gtk.DestDefaults.DROP | Gtk.DestDefaults.MOTION,
                               [], Gdk.DragAction.MOVE)
            self.drag_dest_add_text_targets()
            self.connect('drag-data-received', self._on_drag_data_received)

    def update_headers(self, prev_album_id=None):
        """
            Update headers
            @param previous album id as int
        """
        for child in self.get_children():
            track = Track(child.get_id())
            if track.album.id == prev_album_id:
                child.show_headers(False)
            else:
                child.show_headers(True)
            prev_album_id = track.album.id

    def update_indexes(self, start):
        """
            Update indexes
            @param start index as int
        """
        for row in self.get_children():
            row.set_number(start)
            row.update_num_label()
            start += 1

    def update_playing(self, track_id):
        """
            Update playing track
            @param track id as int
        """
        for row in self.get_children():
            row.set_indicator(row.get_id() == track_id,
                              utils.is_loved(row.get_id()))

#######################
# PRIVATE             #
#######################
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
            bottom_row = self.get_children()[-1]
            bottom_row.emit('track-moved', bottom_row.get_id(),
                            int(data.get_text()), False)
        except:
            pass

    def _on_queue_changed(self, unused):
        """
            Update all position labels
        """
        for row in self.get_children():
            row.update_num_label()

    def _on_loved_playlist_changed(self, widget, playlist_id, track_id):
        """
            Updates the loved icon
            @param playlist as Playlist
            @param playlist id as int
            @param track id as int
        """
        if playlist_id != Type.LOVED:
            return

        for row in self.get_children():
            if track_id == row.get_id():
                row.set_indicator(track_id == Lp().player.current_track.id,
                                  utils.is_loved(track_id))

    def _on_destroy(self, widget):
        """
            Remove signals
            @param widget as Gtk.Widget
        """
        if self._queue_signal_id is not None:
            Lp().player.disconnect(self._queue_signal_id)
            self._queue_signal_id = None
        if self._loved_signal_id1 is not None:
            Lp().playlists.disconnect(self._loved_signal_id1)
            self._loved_signal_id1 = None
        if self._loved_signal_id2 is not None:
            Lp().playlists.disconnect(self._loved_signal_id2)
            self._loved_signal_id2 = None

    def _on_activate(self, widget, row):
        """
            Play activated item
            @param widget as TracksWidget
            @param row as TrackRow
        """
        self.emit('activated', row.get_id())
