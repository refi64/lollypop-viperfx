#!/usr/bin/python
# Copyright (c) 2014-2015 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import GObject, Gtk

from lollypop.define import Objects, ArtSize
from lollypop.popmenu import PopTrackMenu
from lollypop.utils import seconds_to_string, rgba_to_hex


# A track row with track informations
class TrackRow(Gtk.ListBoxRow):
    """
        Init row widgets
    """
    def __init__(self):
        Gtk.ListBoxRow.__init__(self)
        self._object_id = None
        self._number = 0
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/TrackRow.ui')
        builder.connect_signals(self)
        self._row_widget = builder.get_object('row')
        self._title_label = builder.get_object('title')
        self._title_label.set_property('has-tooltip', True)
        self._duration_label = builder.get_object('duration')
        self._num_label = builder.get_object('num')
        self._cover = builder.get_object('cover')
        self._menu = builder.get_object('menu')
        self._icon = builder.get_object('icon')
        self.add(self._row_widget)
        self.get_style_context().add_class('trackrow')
        self.show()

    """
        Show cover
        @param show as bool
    """
    def show_cover(self, show):
        if show:
            self._cover.show()
        else:
            self._cover.hide()

    """
        Show play icon
        @param widget name as str
        @param show as bool
    """
    def show_icon(self, show):
        if show:
            self._icon.set_from_icon_name('media-playback-start-symbolic', 1)
            self.get_style_context().remove_class('trackrow')
            self.get_style_context().add_class('trackrowplaying')
        else:
            self._icon.clear()
            self.get_style_context().remove_class('trackrowplaying')
            self.get_style_context().add_class('trackrow')

    """
        Show menu
    """
    def show_menu(self, show):
        if show:
            self._menu.show()
        else:
            self._menu.hide()

    """
        Set num label
        @param label as string
    """
    def set_num_label(self, label):
        self._num_label.set_markup(label)

    """
        Set title label
        @param label as string
    """
    def set_title_label(self, label):
        self._title_label.set_markup(label)

    """
        Set duration label
        @param label as string
    """
    def set_duration_label(self, label):
        self._duration_label.set_text(label)

    """
        Store current object id
        @param object id as int
    """
    def set_object_id(self, object_id):
        self._object_id = object_id

    """
        Get object id
        @return Current object id as int
    """
    def get_object_id(self):
        return self._object_id

    """
        Set track number
        @param num as int
    """
    def set_number(self, num):
        self._number = num

    """
        Get track number
        @return num as int
    """
    def get_number(self):
        return self._number

    """
        Set cover
        @param cover as Gdk.Pixbuf
    """
    def set_cover(self, pixbuf):
        self._cover.set_from_pixbuf(pixbuf)
        del pixbuf

#######################
# PRIVATE             #
#######################
    """
        Popup menu for track
        @param widget as Gtk.Button
    """
    def _on_menu_clicked(self, widget):
        menu = PopTrackMenu(self._object_id, None)
        popover = Gtk.Popover.new_from_model(self._menu, menu)
        popover.connect('closed', self._on_closed)
        self.get_style_context().add_class('track-menu-selected')
        popover.show()
    """
        Remove selected style
        @param widget as Gtk.Popover
    """
    def _on_closed(self, widget):
        self.get_style_context().remove_class('track-menu-selected')

    """
        Show tooltip if needed
        @param widget as Gtk.Widget
        @param x as int
        @param y as int
        @param keyboard as bool
        @param tooltip as Gtk.Tooltip
    """
    def _on_title_query_tooltip(self, widget, x, y, keyboard, tooltip):
        layout = self._title_label.get_layout()
        if layout.is_ellipsized():
            label = self._title_label.get_label()
            self._title_label.set_tooltip_markup(label)
        else:
            self._title_label.set_tooltip_text('')


# Track list of track rows
class TracksWidget(Gtk.ListBox):

    __gsignals__ = {
        'activated': (GObject.SignalFlags.RUN_FIRST, None, (int,))
    }

    """
        Init track widget
        @param show_menu as bool if menu need to be displayed
    """
    def __init__(self, show_menu):
        Gtk.ListBox.__init__(self)
        self._signal_id = None
        self._show_menu = show_menu
        self.connect("row-activated", self._on_activate)
        self.get_style_context().add_class('trackswidget')
        self.set_property('hexpand', True)

    """
        Add track to list
        @param track id as int
        @param track number as int
        @param title as str
        @param length as str
        @param pos as int
        @param show cover as bool
    """
    def add_track(self, track_id, num, title, length,
                  pos, show_cover=False):
        track_row = TrackRow()
        track_row.show_menu(self._show_menu)
        if Objects.player.current_track.id == track_id:
            track_row.show_icon(True)
        if pos:
            track_row.set_num_label(
                        '''<span foreground="%s"\
                        font_desc="Bold">%s</span>''' %\
                        (rgba_to_hex(Objects.window.get_selected_color()),
                         str(pos)))
        elif num > 0:
            track_row.set_num_label(str(num))
        track_row.set_number(num)
        track_row.set_title_label(title)
        track_row.set_duration_label(seconds_to_string(length))
        track_row.set_object_id(track_id)
        if show_cover:
            album_id = Objects.tracks.get_album_id(track_id)
            pixbuf = Objects.art.get(album_id, ArtSize.MEDIUM)
            track_row.set_cover(pixbuf)
            track_row.show_cover(True)
        track_row.show()
        self.add(track_row)

    """
        Update playing track
        @param track id as int
    """
    def update_playing(self, track_id):
        for row in self.get_children():
            if row.get_object_id() == track_id:
                row.show_icon(True)
            else:
                row.show_icon(False)

    """
        Set signals callback
    """
    def do_show(self):
        self._signal_id = Objects.player.connect("queue-changed",
                                                 self._update_pos_label)
        Gtk.ListBox.do_show(self)

    """
        Clean signals callback
    """
    def do_hide(self):
        if self._signal_id:
            Objects.player.disconnect(self._signal_id)
            self._signal_id = None
        Gtk.ListBox.do_hide(self)

#######################
# PRIVATE             #
#######################
    """
        Update position label
        @param player
        @param track id as int
    """
    def _update_pos_label(self, widget):
        for row in self.get_children():
            track_id = row.get_object_id()
            if Objects.player.is_in_queue(track_id):
                pos = Objects.player.get_track_position(track_id)
                row.set_num_label(
                        '''<span foreground="%s"\
                        font_desc="Bold">%s</span>''' %\
                        (rgba_to_hex(Objects.window.get_selected_color()),
                         str(pos)))
            elif row.get_number() > 0:
                row.set_num_label(str(row.get_number()))
            else:
                row.set_num_label('')

    """
        Play activated item
        @param widget as TracksWidget
        @param row as TrackRow
    """
    def _on_activate(self, widget, row):
        self.emit('activated', row.get_object_id())
