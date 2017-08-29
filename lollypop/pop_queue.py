# Copyright (c) 2014-2017 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from lollypop.define import Lp, ArtSize, Type
from lollypop.objects import Track, Album


class QueueRow(Gtk.ListBoxRow):
    """
        Queue row (a track)
    """
    __gsignals__ = {
        "track-moved": (GObject.SignalFlags.RUN_FIRST, None, (int, int, int))
    }

    def __init__(self, track_id):
        """
            Init row widgets
            @param track_id as int
        """
        Gtk.ListBoxRow.__init__(self)
        self.__id = track_id
        self.__number = 0
        self.set_margin_start(5)
        self.set_margin_end(5)
        self.set_margin_top(2)
        self.set_margin_end(2)
        self.__row_widget = Gtk.EventBox()
        grid = Gtk.Grid()
        grid.set_column_spacing(5)
        self.__row_widget.add(grid)
        self.__cover = Gtk.Image()
        self.__cover.set_no_show_all(True)
        self.__cover.set_property("halign", Gtk.Align.CENTER)
        self.__cover.set_property("valign", Gtk.Align.CENTER)
        self.__cover.get_style_context().add_class("small-cover-frame")
        # We force width with a Box
        box = Gtk.Box()
        box.set_homogeneous(True)
        box.add(self.__cover)
        box.set_property("width-request", ArtSize.MEDIUM+2)
        box.show()
        self.__title_label = Gtk.Label()
        self.__title_label.set_margin_start(20)
        self.__title_label.set_property("has-tooltip", True)
        self.__title_label.set_property("hexpand", True)
        self.__title_label.set_property("halign", Gtk.Align.START)
        self.__title_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.__menu_button = Gtk.Button.new_from_icon_name(
                                                         "user-trash-symbolic",
                                                         Gtk.IconSize.MENU)
        # Here a hack to make old Gtk version support min-height css attribute
        # min-height = 24px, borders = 2px
        self.__menu_button.set_property("height-request", 26)
        self.__menu_button.set_relief(Gtk.ReliefStyle.NONE)
        self.__menu_button.get_style_context().add_class("menu-button")
        self.__menu_button.get_style_context().add_class("track-menu-button")
        self.__menu_button.get_image().set_opacity(0.2)
        self.__menu_button.set_property("valign", Gtk.Align.END)
        self.__menu_button.show()
        self.__menu_button.connect("clicked", self.__on_delete_clicked)
        grid.add(box)
        grid.add(self.__title_label)
        grid.add(self.__menu_button)
        self.add(self.__row_widget)
        self.show_all()
        self.__header = Gtk.Grid()
        self.__header.set_column_spacing(5)
        self.__artist_label = Gtk.Label()
        self.__artist_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.__artist_label.get_style_context().add_class("dim-label")
        self.__album_label = Gtk.Label()
        self.__album_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.__album_label.get_style_context().add_class("dim-label")
        self.__header.add(self.__artist_label)
        self.__header.add(self.__album_label)
        self.__title_label.set_property("valign", Gtk.Align.END)
        grid.attach(self.__header, 1, 0, 1, 1)
        self.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, [],
                             Gdk.DragAction.MOVE)
        self.drag_source_add_text_targets()
        self.drag_dest_set(Gtk.DestDefaults.DROP | Gtk.DestDefaults.MOTION,
                           [], Gdk.DragAction.MOVE)
        self.drag_dest_add_text_targets()
        self.connect("drag-begin", self.__on_drag_begin)
        self.connect("drag-data-get", self.__on_drag_data_get)
        self.connect("drag-data-received", self.__on_drag_data_received)
        self.connect("drag-motion", self.__on_drag_motion)
        self.connect("drag-leave", self.__on_drag_leave)
        self.get_style_context().add_class("trackrow")

    def show_header(self, show):
        """
            Show header
        """
        if show:
            self.__header.show_all()
        else:
            self.__header.hide()

    @property
    def id(self):
        """
            Get row id
            @return row id as int
        """
        return self.__id

    def set_labels(self):
        """
            Set artist, album and title label
        """
        track = Track(self.__id)
        self.__artist_label.set_markup(
                                 "<b>" + GLib.markup_escape_text(
                                        ", ".join(track.album.artists))+"</b>")
        self.__album_label.set_text(track.album.name)
        # If we are listening to a compilation, prepend artist name
        title = GLib.markup_escape_text(track.name)
        if track.album.artist_id == Type.COMPILATIONS or\
           len(track.artist_ids) > 1 or\
           track.album.artist_id not in track.artist_ids:
            if track.artist_names != track.album.artist_name:
                title = "<b>%s</b>\n%s" % (
                                   GLib.markup_escape_text(track.artist_names),
                                   title)
        self.__title_label.set_markup(title)

    def set_cover(self, surface):
        """
            Set cover surface
            @param surface as cairo.Surface
        """
        if surface is None:
            self.__cover.clear()
            self.__cover.hide()
        else:
            self.__cover.set_from_surface(surface)
            self.__cover.show()

#######################
# PRIVATE             #
#######################
    def __on_drag_begin(self, widget, context):
        """
            Set icon
            @param widget as Gtk.Widget
            @param context as Gdk.DragContext
        """
        widget.drag_source_set_icon_name("emblem-music-symbolic")

    def __on_drag_data_get(self, widget, context, data, info, time):
        """
            Send track id
            @param widget as Gtk.Widget
            @param context as Gdk.DragContext
            @param data as Gtk.SelectionData
            @param info as int
            @param time as int
        """
        track_id = str(self.__id)
        data.set_text(track_id, len(track_id))

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
        self.emit("track-moved", int(data.get_text()), x, y)

    def __on_drag_motion(self, widget, context, x, y, time):
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
            self.get_style_context().add_class("drag-up")
            self.get_style_context().remove_class("drag-down")
        else:
            self.get_style_context().remove_class("drag-up")
            self.get_style_context().add_class("drag-down")

    def __on_drag_leave(self, widget, context, time):
        """
            Remove style
            @param widget as Gtk.Widget
            @param context as Gdk.DragContext
            @param time as int
        """
        self.get_style_context().remove_class("drag-up")
        self.get_style_context().remove_class("drag-down")

    def __on_delete_clicked(self, button):
        """
            Delete track from queue
            @param button as Gtk.Button
        """
        Lp().player.del_from_queue(self.__id)
        self.destroy()

    def __on_query_tooltip(self, widget, x, y, keyboard, tooltip):
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
            artist = GLib.markup_escape_text(self._artist.get_text())
            title = GLib.markup_escape_text(self._title.get_text())
            self.set_tooltip_markup("<b>%s</b>\n%s" % (artist, title))
        else:
            self.set_tooltip_text("")


class QueuePopover(Gtk.Popover):
    """
        Popover showing queue
    """

    def __init__(self):
        """
            Init Popover
        """
        Gtk.Popover.__init__(self)
        self.set_position(Gtk.PositionType.BOTTOM)
        self.connect("map", self.__on_map)
        self.connect("unmap", self.__on_unmap)

        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/QueuePopover.ui")
        builder.connect_signals(self)

        self.__clear_button = builder.get_object("clear-button")

        self.__view = Gtk.ListBox()
        self.__view.get_style_context().add_class("trackswidget")
        self.__view.set_selection_mode(Gtk.SelectionMode.NONE)
        self.__view.set_activate_on_single_click(True)
        self.__view.connect("row-activated", self.__on_row_activated)
        self.__view.show()

        self.drag_dest_set(Gtk.DestDefaults.DROP | Gtk.DestDefaults.MOTION,
                           [], Gdk.DragAction.MOVE)
        self.drag_dest_add_text_targets()
        self.connect("drag-data-received", self.__on_drag_data_received)

        builder.get_object("scrolled").add(self.__view)
        self.add(builder.get_object("widget"))

    def populate(self):
        """
            Populate widget with queue rows
        """
        if Lp().player.queue:
            self.__clear_button.set_sensitive(True)
        self.__add_items(list(Lp().player.queue))

#######################
# PROTECTED           #
#######################
    def _on_button_clicked(self, widget):
        """
            Clear queue
            @param widget as Gtk.Button
        """
        self._stop = True
        self.__clear(True)
        self.hide()

#######################
# PRIVATE             #
#######################
    def __clear(self, clear_queue=False):
        """
            Clear the view
        """
        for child in self.__view.get_children():
            child.destroy()
        if clear_queue:
            Lp().player.clear_queue()

    def __add_items(self, items, prev_album_id=None):
        """
            Add items to the view
            @param item ids as [int]
        """
        if items and not self._stop:
            track_id = items.pop(0)
            album_id = Lp().tracks.get_album_id(track_id)
            row = self.__row_for_track_id(track_id)
            if album_id != prev_album_id:
                surface = Lp().art.get_album_artwork(
                                        Album(album_id),
                                        ArtSize.MEDIUM,
                                        self.get_scale_factor())
                row.set_cover(surface)
                row.show_header(True)
            self.__view.add(row)
            GLib.idle_add(self.__add_items, items, album_id)

    def __row_for_track_id(self, track_id):
        """
            Get a row for track id
            @param track id as int
        """
        row = QueueRow(track_id)
        row.set_labels()
        row.connect("destroy", self.__on_child_destroyed)
        row.connect("track-moved", self.__on_track_moved)
        return row

    def __on_map(self, widget):
        """
            Connect signals, populate, and resize
            @param widget as Gtk.Widget
        """
        self._stop = False
        height = Lp().window.get_size()[1]
        self.set_size_request(400, height*0.7)
        self.populate()
        self._signal_id1 = Lp().player.connect("current-changed",
                                               self.__on_current_changed)

    def __on_unmap(self, widget):
        """
            Disconnect signals
            @param widget as Gtk.Widget
        """
        self.__clear()
        self._stop = True
        if self._signal_id1 is not None:
            Lp().player.disconnect(self._signal_id1)
            self._signal_id1 = None

    def __on_current_changed(self, player):
        """
            Pop first item in queue if it"s current track id
            @param player object
        """
        if len(self.__view.get_children()) > 0:
            row = self.__view.get_children()[0]
            if row.id == player.current_track.id:
                row.destroy()

    def __update_headers(self):
        """
            Update row headers based on current queue
        """
        prev_album_id = None
        for child in self.__view.get_children():
            track = Track(child.id)
            if track.album.id == prev_album_id:
                child.set_cover(None)
                child.show_header(False)
            else:
                surface = Lp().art.get_album_artwork(
                                        Album(track.album.id),
                                        ArtSize.MEDIUM,
                                        self.get_scale_factor())
                child.set_cover(surface)
                child.show_header(True)
            prev_album_id = track.album.id

    def __on_child_destroyed(self, row):
        """
            Check clear button aspect
            @param row as QueueRow
        """
        self.__clear_button.set_sensitive(len(self.__view.get_children()) != 0)
        self.__update_headers()

    def __on_row_activated(self, widget, row):
        """
            Play item
            @param widget as Gtk.ListBox
            @param row as QueueRow
        """
        if not Lp().player.locked:
            Lp().player.load(Track(row.id))
            GLib.idle_add(row.destroy)

    def __on_track_moved(self, row, src, x, y):
        """
            Pass signal
            @param row as PlaylistRow
            @param src as int
            @param x as int
            @param y as int
        """
        if row.id == src:
            return
        height = row.get_allocated_height()
        if y > height/2:
            up = False
        else:
            up = True
        src_row = self.__row_for_track_id(src)
        # Destroy current src row
        i = 0
        row_index = -1
        for child in self.__view.get_children():
            if child == row:
                row_index = i
            if child.id == src:
                Lp().player.del_from_queue(src, False)
                child.disconnect_by_func(self.__on_child_destroyed)
                child.destroy()
            else:
                i += 1

        # Add new row
        if row_index != -1:
            if not up:
                row_index += 1
            self.__view.insert(src_row, row_index)
            Lp().player.insert_in_queue(src, row_index)
        self.__update_headers()

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
            self.__on_track_moved(self.__view.get_children()[-1],
                                  int(data.get_text()), x, y)
        except:
            pass
