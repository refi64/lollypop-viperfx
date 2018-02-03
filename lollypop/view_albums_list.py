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

from gi.repository import Gtk, GLib, GObject, Gdk, Pango

from gettext import gettext as _

from lollypop.widgets_tracks_responsive import TracksResponsiveWidget
from lollypop.view import LazyLoadingView
from lollypop.objects import Album
from lollypop.define import ArtSize, App, ResponsiveType


class AlbumRow(Gtk.ListBoxRow, TracksResponsiveWidget):
    """
        Album row
    """
    __gsignals__ = {
        "album-moved": (GObject.SignalFlags.RUN_FIRST, None, (str, int, int))
    }

    __MARGIN = 4

    def get_best_height(widget):
        """
            Helper to pass object it's height request
            @param widget as Gtk.Widget
        """
        ctx = widget.get_pango_context()
        layout = Pango.Layout.new(ctx)
        layout.set_text("a", 1)
        font_height = int(AlbumRow.__MARGIN * 2 +
                          2 * layout.get_pixel_size()[1])
        cover_height = AlbumRow.__MARGIN * 2 + ArtSize.MEDIUM
        if font_height > cover_height:
            return font_height + 2
        else:
            return cover_height + 2

    def __init__(self, album, height, responsive_type):
        """
            Init row widgets
            @param album as Album
            @param height as int
            @param responsive_type as ResponsiveType
        """
        self._responsive_widget = None
        self._album = album
        self.__responsive_type = responsive_type
        self.__score = None
        Gtk.ListBoxRow.__init__(self)
        self.__play_indicator = None
        self.set_sensitive(False)
        self.get_style_context().add_class("loading")
        self.set_property("height-request", height)
        self.set_margin_start(5)
        self.set_margin_end(5)

    def populate(self):
        """
            Populate widget content
        """
        self.get_style_context().remove_class("loading")
        self.get_style_context().add_class("albumrow")
        self.set_sensitive(True)
        self.set_property("has-tooltip", True)
        self.connect("query-tooltip", self.__on_query_tooltip)
        row_widget = Gtk.EventBox()
        row_widget.set_property("valign", Gtk.Align.CENTER)
        row_widget.set_margin_top(self.__MARGIN)
        row_widget.set_margin_end(self.__MARGIN)
        grid = Gtk.Grid()
        grid.set_column_spacing(8)
        if self._album.artists:
            artists = GLib.markup_escape_text(", ".join(self._album.artists))
        else:
            artists = _("Compilation")
        self.__artist_label = Gtk.Label.new("<b>%s</b>" % artists)
        self.__artist_label.set_use_markup(True)
        self.__artist_label.set_hexpand(True)
        self.__artist_label.set_property("halign", Gtk.Align.START)
        self.__artist_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.__title_label = Gtk.Label.new(self._album.name)
        self.__title_label.set_ellipsize(Pango.EllipsizeMode.END)
        cover = Gtk.Image()
        cover.get_style_context().add_class("small-cover-frame")
        surface = App().art.get_album_artwork(
                                        self._album,
                                        ArtSize.MEDIUM,
                                        self.get_scale_factor())
        cover.set_from_surface(surface)
        cover.set_size_request(ArtSize.MEDIUM, ArtSize.MEDIUM)
        self.__play_indicator = Gtk.Image.new_from_icon_name(
                                               "media-playback-start-symbolic",
                                               Gtk.IconSize.MENU)
        if self.__responsive_type == ResponsiveType.SEARCH:
            action_icon = "media-playback-start-symbolic"
        else:
            action_icon = "user-trash-symbolic"
        self.__action_button = Gtk.Button.new_from_icon_name(
                                                      action_icon,
                                                      Gtk.IconSize.MENU)
        # Here a hack to make old Gtk version support min-height css attribute
        # min-height = 24px, borders = 2px
        self.__action_button.set_property("height-request", 26)
        self.__action_button.get_image().set_opacity(0.2)
        self.__action_button.set_relief(Gtk.ReliefStyle.NONE)
        self.__action_button.get_style_context().add_class("album-menu-button")
        self.__action_button.get_style_context().add_class("track-menu-button")
        self.__action_button.set_property("valign", Gtk.Align.CENTER)
        self.__action_button.connect("clicked", self.__on_action_clicked)
        vgrid = Gtk.Grid()
        vgrid.set_column_spacing(5)
        vgrid.add(self.__play_indicator)
        vgrid.add(self.__title_label)
        grid.attach(self.__artist_label, 1, 0, 1, 1)
        grid.attach(self.__action_button, 2, 0, 1, 2)
        grid.attach(cover, 0, 0, 1, 2)
        grid.attach(vgrid, 1, 1, 1, 1)
        self.__revealer = Gtk.Revealer.new()
        self.__revealer.show()
        grid.attach(self.__revealer, 0, 2, 3, 1)
        row_widget.add(grid)
        self.add(row_widget)
        self.update_playing_indicator(self._album ==
                                      App().player.current_track.album)
        self.show_all()
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
        self.connect("button-release-event", self.__on_button_release_event)
        if len(self._album.tracks) != self._album.tracks_count:
            self.__on_button_release_event(self, None)

    @property
    def album(self):
        """
            Get album
            @return row id as int
        """
        return self._album

    def update_playing_indicator(self, show):
        """
            Show play indicator
        """
        if self.__play_indicator is None:
            return
        if show:
            self.__play_indicator.set_opacity(1)
        else:
            self.__play_indicator.set_opacity(0)
        if self.__revealer.get_reveal_child():
            TracksResponsiveWidget.update_playing_indicator(self)

#######################
# PRIVATE             #
#######################
    def __on_button_release_event(self, widget, event):
        """
            Show revealer with tracks
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        if self.__revealer.get_reveal_child():
            self.__revealer.set_reveal_child(False)
            if self.__responsive_type != ResponsiveType.SEARCH:
                self.__action_button.set_opacity(1)
                self.__action_button.set_sensitive(True)
        else:
            if self._responsive_widget is None:
                TracksResponsiveWidget.__init__(self, self.__responsive_type)
                self.__revealer.add(self._responsive_widget)
                self.connect("size-allocate", self._on_size_allocate)
                TracksResponsiveWidget.populate(self)
            self.__revealer.set_reveal_child(True)
            if self.__responsive_type != ResponsiveType.SEARCH:
                self.__action_button.set_opacity(0)
                self.__action_button.set_sensitive(False)

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
        album_str = "a:%s" % self._album.id
        data.set_text(album_str, len(album_str))

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
            self.emit("album-moved", data.get_text(), x, y)
        except Exception as e:
            print("AlbumsPopover::__on_drag_data_received()", e)

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

    def __on_action_clicked(self, button):
        """
            ResponsiveType.SEARCH: Play album
            Else: Delete album
            @param button as Gtk.Button
        """
        if self.__responsive_type == ResponsiveType.SEARCH:
            App().player.play_album(Album(self._album.id))
        else:
            if App().player.current_track.album.id == self._album.id:
                # If not last album, skip it
                if len(App().player.albums) > 1:
                    App().player.skip_album()
                    App().player.remove_album(self._album)
                # remove it and stop playback by going to next track
                else:
                    App().player.remove_album(self._album)
                    App().player.set_next()
                    App().player.next()
            else:
                App().player.remove_album(self._album)
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
        layout_title = self.__title_label.get_layout()
        layout_artist = self.__artist_label.get_layout()
        if layout_title.is_ellipsized() or layout_artist.is_ellipsized():
            artist = GLib.markup_escape_text(self.__artist_label.get_text())
            title = GLib.markup_escape_text(self.__title_label.get_text())
            self.set_tooltip_markup("<b>%s</b>\n%s" % (artist, title))
        else:
            self.set_tooltip_text("")


class AlbumsListView(LazyLoadingView):
    """
        View showing albums
    """

    def __init__(self, responsive_type):
        """
            Init Popover
        """
        LazyLoadingView.__init__(self)
        self.__responsive_type = responsive_type
        # Calculate default album height based on current pango context
        # We may need to listen to screen changes
        self.__height = AlbumRow.get_best_height(self)
        self.connect("map", self.__on_map)
        self.connect("unmap", self.__on_unmap)
        self.__view = Gtk.ListBox()
        self.__view.get_style_context().add_class("trackswidget")
        self.__view.set_vexpand(True)
        self.__view.set_selection_mode(Gtk.SelectionMode.NONE)
        self.__view.set_activate_on_single_click(True)
        self.__view.show()
        self._viewport.add(self.__view)
        self._scrolled.set_property("expand", True)
        self.add(self._scrolled)
        self.drag_dest_set(Gtk.DestDefaults.DROP | Gtk.DestDefaults.MOTION,
                           [], Gdk.DragAction.MOVE)
        self.drag_dest_add_text_targets()
        self.connect("drag-data-received", self.__on_drag_data_received)

    def populate(self, albums):
        """
            Populate widget with album rows
            @param albums as [Album]
        """
        self._stop = False
        self.__add_albums(list(albums))

    def on_current_changed(self, player):
        """
            Show tracks in a popover
            @param player object
        """
        for child in self.__view.get_children():
            child.update_playing_indicator(child.album ==
                                           App().player.current_track.album)

    def jump_to_current(self):
        """
            Scroll to album
        """
        y = self.__get_current_ordinate()
        if y is not None:
            self._scrolled.get_vadjustment().set_value(y)

    def clear(self, clear_albums=False):
        """
            Clear the view
        """
        for child in self.__view.get_children():
            GLib.idle_add(child.destroy)
        if clear_albums:
            App().player.clear_albums()

#######################
# PRIVATE             #
#######################
    def __add_albums(self, albums):
        """
            Add items to the view
            @param albums ids as [Album]
        """
        if albums and not self._stop:
            album = albums.pop(0)
            row = self.__row_for_album(album)
            row.show()
            self.__view.add(row)
            self._lazy_queue.append(row)
            GLib.idle_add(self.__add_albums, albums)
        else:
            GLib.idle_add(self.lazy_loading)
            if self._viewport.get_child() is None:
                self._viewport.add(self.__view)

    def __row_for_album(self, album):
        """
            Get a row for track id
            @param album as Album
        """
        row = AlbumRow(album, self.__height, self.__responsive_type)
        row.connect("destroy", self.__on_child_destroyed)
        row.connect("album-moved", self.__on_album_moved)
        return row

    def __get_current_ordinate(self):
        """
            If current track in widget, return it ordinate,
            @return y as int
        """
        y = None
        for child in self.__view.get_children():
            if child.album == App().player.current_track.album:
                y = child.translate_coordinates(self.__view, 0, 0)[1]
        return y

    def __on_map(self, widget):
        """
            Connect signals
            @param widget as Gtk.Widget
        """
        self._signal_id1 = App().player.connect("current-changed",
                                                self.on_current_changed)

    def __on_unmap(self, widget):
        """
            Disconnect signals
            @param widget as Gtk.Widget
        """
        if self._signal_id1 is not None:
            App().player.disconnect(self._signal_id1)
            self._signal_id1 = None

    def __on_child_destroyed(self, row):
        """
            Check clear button aspect
            @param row as AlbumRow
        """
        # Send signal for parent

    def __on_album_moved(self, row, album_str, x, y):
        """
            Pass signal
            @param row as PlaylistRow
            @param album_str as str
            @param x as int
            @param y as int
        """
        if "a:%s" % row.album.id == album_str:
            return
        # Destroy current album row and search for album row
        i = 0
        row_index = -1
        album = None
        for child in self.__view.get_children():
            if child == row:
                row_index = i
            if "a:%s" % child.album.id == album_str:
                album = child.album
                child.disconnect_by_func(self.__on_child_destroyed)
                child.destroy()
            else:
                i += 1
        # Create new row
        if album is not None:
            height = row.get_allocated_height()
            if y > height/2:
                up = False
            else:
                up = True
            album_row = self.__row_for_album(album)
            album_row.populate()

            # Add new row
            if row_index != -1:
                if not up:
                    row_index += 1
                self.__view.insert(album_row, row_index)
                App().player.move_album(album, row_index)

    def __on_drag_data_received(self, widget, context, x, y, data, info, time):
        """
            Move album
            @param widget as Gtk.Widget
            @param context as Gdk.DragContext
            @param x as int
            @param y as int
            @param data as Gtk.SelectionData
            @param info as int
            @param time as int
        """
        try:
            self.__on_album_moved(self.__view.get_children()[-1],
                                  data.get_text(), x, y)
        except:
            pass