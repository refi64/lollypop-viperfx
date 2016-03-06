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

from gi.repository import GObject, Gtk, Gdk, Pango

from cgi import escape

from lollypop.define import Lp, ArtSize, Type
from lollypop.pop_menu import TrackMenuPopover, TrackMenu
from lollypop.widgets_indicator import IndicatorWidget
from lollypop.utils import seconds_to_string
from lollypop.objects import Track, Album
from lollypop import utils


class Row(Gtk.ListBoxRow):
    """
        A row
    """
    def __init__(self, show_loved):
        """
            Init row widgets
            @param show loved as bool
        """
        # We do not use Gtk.Builder for speed reasons
        Gtk.ListBoxRow.__init__(self)
        self._indicator = IndicatorWidget()
        self._show_loved = show_loved
        self._id = None
        self._number = 0
        self._row_widget = Gtk.EventBox()
        self._grid = Gtk.Grid()
        self._grid.set_column_spacing(5)
        self._row_widget.add(self._grid)
        self._title_label = Gtk.Label()
        self._title_label.set_property('has-tooltip', True)
        self._title_label.set_property('hexpand', True)
        self._title_label.set_property('halign', Gtk.Align.START)
        self._title_label.set_ellipsize(Pango.EllipsizeMode.END)
        self._duration_label = Gtk.Label()
        self._duration_label.get_style_context().add_class('dim-label')
        self._num_label = Gtk.Label()
        self._num_label.set_ellipsize(Pango.EllipsizeMode.END)
        self._num_label.set_property('valign', Gtk.Align.CENTER)
        self._num_label.set_width_chars(4)
        self._num_label.get_style_context().add_class('dim-label')
        self._menu_button = Gtk.Button.new_from_icon_name('open-menu-symbolic',
                                                          Gtk.IconSize.MENU)
        self._menu_button.set_relief(Gtk.ReliefStyle.NONE)
        self._menu_button.get_style_context().add_class('menu-button')
        self._menu_button.get_style_context().add_class('track-menu-button')
        self._menu_button.get_image().set_opacity(0.2)
        self._menu_button.show()
        self._row_widget.connect('button-press-event', self._on_button_press)
        self._menu_button.connect('clicked', self._on_button_clicked)
        self._grid.add(self._num_label)
        self._grid.add(self._title_label)
        self._grid.add(self._duration_label)
        # TODO Remove this later
        if Gtk.get_minor_version() > 16:
            self._grid.add(self._menu_button)
        else:
            self.connect('map', self._on_map)
        self.add(self._row_widget)
        self.get_style_context().add_class('trackrow')

    def show_indicator(self, playing, loved):
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
            if self._show_loved and loved:
                self._indicator.play_loved()
            else:
                self._indicator.play()
        else:
            self.get_style_context().remove_class('trackrowplaying')
            self.get_style_context().add_class('trackrow')
            if self._show_loved and loved:
                self._indicator.loved()
            else:
                self._indicator.empty()

    def set_num_label(self, label, queued=False):
        """
            Set num label
            @param label as string
        """
        if queued:
            self._num_label.get_style_context().add_class('queued')
        else:
            self._num_label.get_style_context().remove_class('queued')
        self._num_label.set_markup(label)

    def set_title_label(self, label):
        """
            Set title label
            @param label as string
        """
        self._title_label.set_markup(label)

    def set_duration_label(self, label):
        """
            Set duration label
            @param label as string
        """
        self._duration_label.set_text(label)

    def set_id(self, id):
        """
            Store current object id
            @param id as int
        """
        self._id = id
        self._indicator.set_id(id)

    def get_id(self):
        """
            Get object id
            @return Current id as int
        """
        return self._id

    def set_number(self, num):
        """
            Set track number
            @param num as int
        """
        self._number = num

    def get_number(self):
        """
            Get track number
            @return num as int
        """
        return self._number

    def set_cover(self, pixbuf, tooltip):
        """
            Set cover
            @param cover as Gdk.Pixbuf
            @param tooltip as str
        """
        pass

#######################
# PRIVATE             #
#######################
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

    def _on_button_press(self, widget, event):
        """
            Popup menu for track relative to track row
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        if event.button == 3:
            window = widget.get_window()
            if window == event.window:
                self._popup_menu(widget, event.x, event.y)
            # Happens when pressing button over menu btn
            else:
                self._popup_menu(self._menu_button)
            return True
        elif event.button == 2:
            if self._id in Lp().player.get_queue():
                Lp().player.del_from_queue(self._id)
            else:
                Lp().player.append_to_queue(self._id)

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
        popover = TrackMenuPopover(self._id, TrackMenu(self._id))
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

    def _on_title_query_tooltip(self, widget, x, y, keyboard, tooltip):
        """
            Show tooltip if needed
            @param widget as Gtk.Widget
            @param x as int
            @param y as int
            @param keyboard as bool
            @param tooltip as Gtk.Tooltip
        """
        layout = self._title_label.get_layout()
        if layout.is_ellipsized():
            label = self._title_label.get_label()
            self._title_label.set_tooltip_markup(label)
        else:
            self._title_label.set_tooltip_text('')


class PlaylistRow(Row):
    """
        A track row with album cover
    """
    __gsignals__ = {
        'track-moved': (GObject.SignalFlags.RUN_FIRST, None, (int, int, int))
    }

    def __init__(self, show_loved):
        """
            Init row widget and show it
        """
        Row.__init__(self, show_loved)
        self._indicator.set_margin_start(5)
        self._row_widget.set_margin_start(10)
        self._row_widget.set_margin_top(2)
        self._row_widget.set_margin_end(10)
        self._grid.insert_row(0)
        self._grid.insert_column(0)
        self._grid.insert_column(1)
        self._grid.attach(self._indicator, 1, 1, 1, 2)
        self._cover = Gtk.Image()
        self._cover_frame = Gtk.Frame()
        self._cover_frame.set_shadow_type(Gtk.ShadowType.NONE)
        self._cover_frame.set_property('halign', Gtk.Align.CENTER)
        self._cover_frame.set_property('valign', Gtk.Align.CENTER)
        self._cover_frame.get_style_context().add_class('small-cover-frame')
        self._cover_frame.add(self._cover)
        # We force width with a Box
        box = Gtk.Box()
        box.set_homogeneous(True)
        box.add(self._cover_frame)
        box.set_property('width-request', ArtSize.MEDIUM+2)
        box.show()
        self._grid.attach(box, 0, 0, 1, 2)
        self.show_all()
        self._header = Gtk.Grid()
        self._header.set_column_spacing(5)
        self._artist_label = Gtk.Label()
        self._artist_label.set_ellipsize(Pango.EllipsizeMode.END)
        self._artist_label.get_style_context().add_class('dim-label')
        self._album_label = Gtk.Label()
        self._album_label.set_ellipsize(Pango.EllipsizeMode.END)
        self._album_label.get_style_context().add_class('dim-label')
        self._header.add(self._artist_label)
        self._header.add(self._album_label)
        self._num_label.set_property('valign', Gtk.Align.END)
        self._title_label.set_property('valign', Gtk.Align.END)
        self._duration_label.set_property('valign', Gtk.Align.END)
        self._indicator.set_property('valign', Gtk.Align.END)
        self._grid.attach(self._header, 1, 0, 4, 1)
        self.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, [],
                             Gdk.DragAction.MOVE)
        self.drag_source_add_text_targets()
        self.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.MOVE)
        self.drag_dest_add_text_targets()
        self.connect('drag-begin', self._on_drag_begin)
        self.connect('drag-data-get', self._on_drag_data_get)
        self.connect('drag-data-received', self._on_drag_data_received)

    def set_id(self, id):
        """
            Store current object and show row
            @param id as int
        """
        Row.set_id(self, id)
        self._object = Album(self._id)

    def show_header(self, show):
        """
            Show header
            @param show as bool
        """
        if show:
            self._header.show_all()
        else:
            self._header.hide()

    def set_cover(self, surface, tooltip):
        """
            Set cover
            @param cover as cairo.Surface
            @param tooltip as str
        """
        self._cover.set_tooltip_text(tooltip)
        if surface is None:
            self._cover.clear()
            self._cover_frame.set_shadow_type(Gtk.ShadowType.NONE)
        else:
            self._cover.set_from_surface(surface)
            self._cover_frame.set_shadow_type(Gtk.ShadowType.IN)

    def set_album_and_artist(self, album_id):
        """
            Set artist and album labels
            @param album id as int
        """
        artist = Lp().albums.get_artist_name(album_id)
        album = Lp().albums.get_name(album_id)
        self._artist_label.set_markup("<b>"+escape(artist)+"</b>")
        self._album_label.set_text(escape(album))

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
        track_id = str(self._id)
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


class TrackRow(Row):
    """
        A track row
    """

    def __init__(self, show_loved):
        """
            Init row widget and show it
            @param show loved as bool
        """
        Row.__init__(self, show_loved)
        self._grid.insert_column(0)
        self._grid.attach(self._indicator, 0, 0, 1, 1)
        self.show_all()

    def set_id(self, id):
        """
            Store current id and object
            @param id as int
        """
        Row.set_id(self, id)
        self._object = Track(self._id)

#######################
# PRIVATE             #
#######################


class TracksWidget(Gtk.ListBox):
    """
        A list of tracks
    """

    __gsignals__ = {
        'activated': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        'track-moved': (GObject.SignalFlags.RUN_FIRST, None, (int, int, bool))
    }

    def __init__(self, show_loved=False):
        """
            Init track widget
            @param show_loved as bool
        """
        Gtk.ListBox.__init__(self)
        self.connect('destroy', self._on_destroy)
        self._queue_signal_id = Lp().player.connect('queue-changed',
                                                    self._on_queue_changed)
        self._loved_signal_id = Lp().playlists.connect(
                                               'playlist-changed',
                                               self._on_loved_playlist_changed)
        self._show_loved = show_loved
        self.connect("row-activated", self._on_activate)
        self.get_style_context().add_class('trackswidget')
        self.set_property('hexpand', True)
        self.set_property('selection-mode', Gtk.SelectionMode.NONE)

    def add_track(self, track_id, num, title, length):
        """
            Add track to list
            @param track id as int
            @param track number as int
            @param title as str
            @param length as str
            @param show cover as bool
        """
        track_row = TrackRow(self._show_loved)
        track_row.show_indicator(Lp().player.current_track.id == track_id,
                                 utils.is_loved(track_id))
        track_row.set_number(num)
        self._update_pos_label(track_row, track_id)
        track_row.set_title_label(title)
        track_row.set_duration_label(seconds_to_string(length))
        track_row.set_id(track_id)
        track_row.show()
        self.add(track_row)

    def add_track_playlist(self, track_id, album, num, title, length):
        """
            Add album row to the list
            @param track id as int
            @param album as Album or None
            @param track number as int
            @param title as str
            @param length as str
        """
        album_row = PlaylistRow(self._show_loved)
        album_row.connect('track-moved', self._on_track_moved)
        album_row.show_indicator(Lp().player.current_track.id == track_id,
                                 utils.is_loved(track_id))
        album_row.set_number(num)
        self._update_pos_label(album_row, track_id)
        album_row.set_title_label(title)
        album_row.set_duration_label(seconds_to_string(length))
        album_row.set_id(track_id)
        if album is not None:
            album_row.set_album_and_artist(album.id)
            surface = Lp().art.get_album_artwork(
                        album,
                        ArtSize.MEDIUM*album_row.get_scale_factor())
            album_row.set_cover(surface, Lp().albums.get_name(album.id))
            del surface
            album_row.show_header(True)
        album_row.show()
        self.insert(album_row, num)

    def update_headers(self):
        """
            Update headers
        """
        prev_album_id = None
        for child in self.get_children():
            track = Track(child.get_id())
            if track.album.id == prev_album_id:
                child.set_cover(None, '')
                child.show_header(False)
            else:
                surface = Lp().art.get_album_artwork(
                                        Album(track.album.id),
                                        ArtSize.MEDIUM*self.get_scale_factor())
                child.set_cover(surface, Lp().albums.get_name(track.album.id))
                child.show_header(True)
            prev_album_id = track.album.id

    def update_indexes(self, start):
        """
            Update indexes
            @param start index as int
        """
        for row in self.get_children():
            row.set_num_label(str(start))
            start += 1

    def update_playing(self, track_id):
        """
            Update playing track
            @param track id as int
        """
        for row in self.get_children():
            row.show_indicator(row.get_id() == track_id,
                               utils.is_loved(row.get_id()))

#######################
# PRIVATE             #
#######################
    def _update_pos_label(self, row, track_id):
        """
            Update position label for row
            @param row as Row
            @param track id as int
        """
        if Lp().player.is_in_queue(track_id):
            pos = Lp().player.get_track_position(track_id)
            row.set_num_label(str(pos), True)
        elif row.get_number() > 0:
            row.set_num_label(str(row.get_number()))
        else:
            row.set_num_label('')

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
        self.emit('track-moved', row.get_id(), src, up)

    def _on_queue_changed(self, widget):
        """
            Update all position labels
            @param player
            @param track id as int
        """
        for row in self.get_children():
            track_id = row.get_id()
            self._update_pos_label(row, track_id)

    def _on_loved_playlist_changed(self, widget, playlist_id):
        """
            Updates the loved icon
        """
        if playlist_id != Type.LOVED:
            return

        for row in self.get_children():
            track_id = row.get_id()
            row.show_indicator(track_id == Lp().player.current_track.id,
                               utils.is_loved(track_id))

    def _on_destroy(self, widget):
        """
            Remove signals
            @param widget as Gtk.Widget
        """
        if self._queue_signal_id is not None:
            Lp().player.disconnect(self._queue_signal_id)
            self._queue_signal_id = None
        if self._loved_signal_id is not None:
            Lp().playlists.disconnect(self._loved_signal_id)
            self._loved_signal_id = None

    def _on_activate(self, widget, row):
        """
            Play activated item
            @param widget as TracksWidget
            @param row as TrackRow
        """
        self.emit('activated', row.get_id())
