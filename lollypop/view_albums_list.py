# Copyright (c) 2014-2018 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from lollypop.view_tracks import TracksView
from lollypop.view import LazyLoadingView
from lollypop.art import AlbumArtHelper
from lollypop.objects import Album
from lollypop.logger import Logger
from lollypop.define import ArtSize, App, ResponsiveType, Shuffle
from lollypop.controller_view import ViewController


class AlbumRow(Gtk.ListBoxRow, TracksView, AlbumArtHelper):
    """
        Album row
    """

    __gsignals__ = {
        "album-moved": (GObject.SignalFlags.RUN_FIRST, None, (str, bool)),
        "track-moved": (GObject.SignalFlags.RUN_FIRST, None, (str, str, bool)),
        "album-added": (GObject.SignalFlags.RUN_FIRST, None,
                        (int, GObject.TYPE_PYOBJECT)),
        "track-append": (GObject.SignalFlags.RUN_FIRST, None,
                         (GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT)),
        "track-removed": (GObject.SignalFlags.RUN_FIRST, None,
                          (GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT)),
        "populated": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    # Update padding in application.css => albumrow
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

    def __init__(self, album, height, responsive_type, reveal):
        """
            Init row widgets
            @param album as Album
            @param height as int
            @param responsive_type as ResponsiveType
            @param reveal as bool
        """
        Gtk.ListBoxRow.__init__(self)
        AlbumArtHelper.__init__(self)
        # Later => TracksView.__init__(self)
        self.__revealer = None
        self.__reveal = reveal
        self._responsive_widget = None
        self._album = album
        self.__responsive_type = responsive_type
        self.__play_indicator = None
        self.set_sensitive(False)
        self.get_style_context().add_class("loading")
        self.set_property("height-request", height)
        self.set_margin_start(5)
        # 15 for scrollbar overlay
        self.set_margin_end(15)

    def populate(self):
        """
            Populate widget content
        """
        if self.get_child() is not None:
            return
        AlbumArtHelper.populate(self, ArtSize.MEDIUM, "small-cover-frame",
                                halign=Gtk.Align.FILL)
        self.get_style_context().remove_class("loading")
        self.get_style_context().add_class("albumrow")
        self.set_sensitive(True)
        self.set_property("has-tooltip", True)
        self.connect("query-tooltip", self.__on_query_tooltip)
        row_widget = Gtk.EventBox()
        row_widget.set_property("valign", Gtk.Align.CENTER)
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
        AlbumArtHelper.set_artwork(self)
        self.__play_indicator = Gtk.Image.new_from_icon_name(
            "media-playback-start-symbolic",
            Gtk.IconSize.MENU)
        self.__action_button = None
        if self.__responsive_type == ResponsiveType.SEARCH:
            action_icon = "media-playback-start-symbolic"
        elif self.__responsive_type == ResponsiveType.DND:
            action_icon = "user-trash-symbolic"
        if self.__responsive_type in [ResponsiveType.SEARCH,
                                      ResponsiveType.DND]:
            self.__action_button = Gtk.Button.new_from_icon_name(
                action_icon,
                Gtk.IconSize.MENU)
            self.__action_button.set_relief(Gtk.ReliefStyle.NONE)
            self.__action_button.get_style_context().add_class(
                "album-menu-button")
            self.__action_button.get_style_context().add_class(
                "track-menu-button")
            self.__action_button.set_property("valign", Gtk.Align.CENTER)
            self.__action_button.connect("clicked",
                                         self.__on_action_button_clicked)
        self.__artists_button = None
        if self.__responsive_type == ResponsiveType.SEARCH:
            self.__artists_button = Gtk.Button.new_from_icon_name(
                    'avatar-default-symbolic',
                    Gtk.IconSize.MENU)
            self.__artists_button.set_relief(Gtk.ReliefStyle.NONE)
            self.__artists_button.get_style_context().add_class(
                "album-menu-button")
            self.__artists_button.set_tooltip_text(_("Go to artist view"))
            self.__artists_button.set_property("valign", Gtk.Align.CENTER)
            self.__artists_button.connect("clicked",
                                          self.__on_artists_button_clicked)
        vgrid = Gtk.Grid()
        vgrid.set_column_spacing(5)
        vgrid.add(self.__play_indicator)
        vgrid.add(self.__title_label)
        index = 1
        grid.attach(self.__artist_label, index, 0, 1, 1)
        index += 1
        if self.__artists_button is not None:
            grid.attach(self.__artists_button, index, 0, 1, 2)
            index += 1
        if self.__action_button is not None:
            grid.attach(self.__action_button, index, 0, 1, 2)
            index += 1
        grid.attach(self._artwork, 0, 0, 1, 2)
        grid.attach(vgrid, 1, 1, 1, 1)
        self.__revealer = Gtk.Revealer.new()
        self.__revealer.show()
        grid.attach(self.__revealer, 0, 2, index, 1)
        row_widget.add(grid)
        self.add(row_widget)
        self.set_playing_indicator()
        self.show_all()
        self.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, [],
                             Gdk.DragAction.MOVE)
        self.drag_source_add_text_targets()
        self.drag_dest_set(Gtk.DestDefaults.DROP,
                           [], Gdk.DragAction.MOVE)
        self.drag_dest_add_text_targets()
        self.set_selection()
        self.connect("drag-begin", self.__on_drag_begin)
        self.connect("drag-data-get", self.__on_drag_data_get)
        self.connect("drag-data-received", self.__on_drag_data_received)
        self.connect("drag-leave", self.__on_drag_leave)
        self.connect("button-release-event", self.__on_button_release_event)
        if self.__reveal:
            self.reveal()

    def reveal(self, reveal=None,
               transition_type=Gtk.RevealerTransitionType.SLIDE_DOWN):
        """
            Reveal/Unreveal tracks
            @param revleal as bool or None to just change state
            @param transition_type as Gtk.RevealerTransitionType
        """
        self.__revealer.set_transition_type(transition_type)
        if self.__revealer.get_reveal_child() and reveal is not True:
            self.__revealer.set_reveal_child(False)
            self.set_selection()
            if self.__responsive_type != ResponsiveType.SEARCH and\
                    self.__action_button is not None:
                self.__action_button.set_opacity(1)
                self.__action_button.set_sensitive(True)
        else:
            if self._responsive_widget is None:
                TracksView.__init__(self, self.__responsive_type)
                self.__revealer.add(self._responsive_widget)
                self.connect("size-allocate", self._on_size_allocate)
                TracksView.populate(self)
            self.__revealer.set_reveal_child(True)
            self.set_selection()
            if self.__responsive_type != ResponsiveType.SEARCH and\
                    self.__action_button is not None:
                self.__action_button.set_opacity(0)
                self.__action_button.set_sensitive(False)

    def set_playing_indicator(self):
        """
            Show play indicator
            @param show as bool
        """
        if self.__play_indicator is None:
            return
        if self.album.id == App().player.current_track.album.id:
            self.__play_indicator.set_opacity(1)
        else:
            self.__play_indicator.set_opacity(0)
        if self.__revealer.get_reveal_child():
            TracksView.set_playing_indicator(self)

    def set_selection(self):
        """
            Update widget state
        """
        selected = self._album.id == App().player.current_track.album.id
        revealed = self.__revealer is not None and\
            self.__revealer.get_reveal_child()
        if selected and not revealed:
            self.set_state(Gtk.StateType.SELECTED)
        elif not selected or revealed:
            self.set_state(Gtk.StateType.NORMAL)

    def stop(self):
        """
            Stop view loading
        """
        # FIXME

    @property
    def is_populated(self):
        """
            Return True if populated
            @return bool
        """
        return True

    @property
    def album(self):
        """
            Get album
            @return row id as int
        """
        return self._album

#######################
# PROTECTED           #
#######################

#######################
# PRIVATE             #
#######################
    def __on_button_release_event(self, widget, event):
        """
            Show revealer with tracks
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        self.reveal()

    def __on_drag_begin(self, widget, context):
        """
            Set icon and update view padding
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
        album_str = "a:%s:none" % self._album
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
        from lollypop.view import View
        view = widget.get_ancestor(View)
        if view is not None:
            view.clear_animation()
        if "a:%s:none" % self._album == data.get_text():
            return
        height = self.get_allocated_height()
        if y > height / 2:
            down = True
        else:
            down = False
        try:
            (type_id, object_str, album_str) = data.get_text().split(":")
            if type_id == "t":
                self.emit("track-moved", object_str, album_str, down)
            elif type_id == "a":
                self.emit("album-moved", object_str, down)
        except Exception as e:
            Logger.error("AlbumRow::__on_drag_data_received(): %s" % e)

    def __on_drag_leave(self, widget, context, time):
        """
            Remove style
            @param widget as Gtk.Widget
            @param context as Gdk.DragContext
            @param time as int
        """
        self.get_style_context().remove_class("drag-up")
        self.get_style_context().remove_class("drag-down")

    def __on_action_button_clicked(self, button):
        """
            ResponsiveType.SEARCH: Play album
            Else: Delete album
            @param button as Gtk.Button
        """
        if self.__responsive_type == ResponsiveType.SEARCH:
            App().player.play_album(Album(self._album.id))
            if App().player.is_party:
                App().lookup_action("party").change_state(
                    GLib.Variant("b", False))
        else:
            if App().player.current_track.album.id == self._album.id:
                # If not last album, skip it
                if len(App().player.albums) > 1:
                    App().player.skip_album()
                    App().player.remove_album(self._album)
                # remove it and stop playback by going to next track
                else:
                    App().player.remove_album(self._album)
                    App().player.stop()
            else:
                App().player.remove_album(self._album)
            self.destroy()

    def __on_artists_button_clicked(self, button):
        """
            Jump to artists albums view
            @param button as Gtk.Button
        """
        popover = self.get_ancestor(Gtk.Popover)
        if popover is not None:
            popover.popdown()
        App().window.container.show_artists_albums(self._album.artist_ids)

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


class AlbumsListView(LazyLoadingView, ViewController):
    """
        View showing albums
    """

    def __init__(self, responsive_type):
        """
            Init Popover
            @param responsive_type as ResponsiveType
        """
        LazyLoadingView.__init__(self)
        ViewController.__init__(self)
        self.__responsive_type = responsive_type
        self.__autoscroll_timeout_id = None
        self.__reveals = []
        self.__prev_animated_rows = []
        # Calculate default album height based on current pango context
        # We may need to listen to screen changes
        self.__height = AlbumRow.get_best_height(self)
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
        self.connect("drag-motion", self.__on_drag_motion)
        self.connect_current_changed_signal()
        self.connect_artwork_changed_signal("album")

    def set_reveal(self, album_ids):
        """
            Set albums to reveal on populate
            @param album_ids as [int]s
        """
        self.__reveals = album_ids

    def populate(self, albums):
        """
            Populate widget with album rows
            @param albums as [Album]
        """
        self._lazy_queue = []
        for child in self.__view.get_children():
            GLib.idle_add(child.destroy)
        self.__add_albums(list(albums))

    def rows_animation(self, x, y):
        """
            Show animation to help user dnd
            @param x as int
            @param y as int
        """
        self.clear_animation()
        for row in self.__view.get_children():
            coordinates = row.translate_coordinates(self, 0, 0)
            if coordinates is None:
                continue
            (row_x, row_y) = coordinates
            row_width = row.get_allocated_width()
            row_height = row.get_allocated_height()
            if x < row_x or\
                    x > row_x + row_width or\
                    y < row_y or\
                    y > row_y + row_height:
                continue
            if y <= row_y + ArtSize.MEDIUM / 2:
                self.__prev_animated_rows.append(row)
                row.get_style_context().add_class("drag-up")
                break
            elif y >= row_y + row_height - ArtSize.MEDIUM / 2:
                self.__prev_animated_rows.append(row)
                row.get_style_context().add_class("drag-down")
                GLib.timeout_add(1000, self.__reveal_row, row)
                break
            else:
                subrow = row.rows_animation(x, y, self)
                if subrow is not None:
                    self.__prev_animated_rows.append(subrow)

    def clear_animation(self):
        """
            Clear any animation
        """
        for row in self.__prev_animated_rows:
            ctx = row.get_style_context()
            ctx.remove_class("drag-up")
            ctx.remove_class("drag-down")

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

    @property
    def children(self):
        """
            Get view children
            @return [AlbumRow]
        """
        return self.__view.get_children()

#######################
# PROTECTED           #
#######################
    def _on_current_changed(self, player):
        """
            Update children state
            @param player as Player
        """
        for child in self.__view.get_children():
            child.set_selection()
            child.set_playing_indicator()

    def _on_artwork_changed(self, artwork, album_id):
        """
            Update children artwork if matching album id
            @param artwork as Artwork
            @param album_id as int
        """
        for child in self.__view.get_children():
            if child.album.id == album_id:
                child.set_artwork()

#######################
# PRIVATE             #
#######################
    def __reveal_row(self, row):
        """
            Reveal row if style always present
        """
        style_context = row.get_style_context()
        if style_context.has_class("drag-down"):
            row.reveal(True)

    def __add_albums(self, albums):
        """
            Add items to the view
            @param albums ids as [Album]
        """
        if self._lazy_queue is None:
            return
        if albums:
            album = albums.pop(0)
            row = self.__row_for_album(album, album.id in self.__reveals)
            row.show()
            self.__view.add(row)
            self._lazy_queue.append(row)
            GLib.idle_add(self.__add_albums, albums)
        else:
            # If only one album, we want to reveal it
            # Stop lazy loading and populate
            children = self.__view.get_children()
            if len(children) == 1:
                self.stop()
                children[0].populate()
                children[0].reveal(True)
            else:
                GLib.idle_add(self.lazy_loading)
            if self._viewport.get_child() is None:
                self._viewport.add(self.__view)

    def __row_for_album(self, album, reveal=False):
        """
            Get a row for track id
            @param album as Album
            @param reveal as bool
        """
        row = AlbumRow(album, self.__height, self.__responsive_type, reveal)
        row.connect("destroy", self.__on_child_destroyed)
        row.connect("track-moved", self.__on_track_moved)
        row.connect("album-moved", self.__on_album_moved)
        row.connect("album-added", self.__on_album_added)
        row.connect("track-append", self.__on_track_added)
        row.connect("track-removed", self.__on_track_removed)
        return row

    def __auto_scroll(self, up):
        """
            Auto scroll up/down
            @param up as bool
        """
        adj = self._scrolled.get_vadjustment()
        value = adj.get_value()
        if up:
            adj_value = value - ArtSize.SMALL
            adj.set_value(adj_value)
            if adj.get_value() == 0:
                self.__autoscroll_timeout_id = None
                self.get_style_context().remove_class("drag-down")
                self.get_style_context().remove_class("drag-up")
                return False
            else:
                self.get_style_context().remove_class("drag-down")
                self.get_style_context().add_class("drag-up")
        else:
            adj_value = value + ArtSize.SMALL
            adj.set_value(adj_value)
            if adj.get_value() < adj_value:
                self.__autoscroll_timeout_id = None
                self.get_style_context().remove_class("drag-down")
                self.get_style_context().remove_class("drag-up")
                return False
            else:
                self.get_style_context().add_class("drag-down")
                self.get_style_context().remove_class("drag-up")
        return True

    def __get_current_ordinate(self):
        """
            If current track in widget, return it ordinate,
            @return y as int
        """
        y = None
        for child in self.__view.get_children():
            if child.album == App().player.current_track.album:
                child.populate()
                child.reveal(True)
                y = child.translate_coordinates(self.__view, 0, 0)[1]
        return y

    def __on_child_destroyed(self, row):
        """
            @param row as AlbumRow
        """
        # Send signal for parent
        # TODO

    def __on_album_added(self, row, index, album):
        """
            Add album as index
            @param row as AlbumRow
            @param index as int
            @param count as int
            @param src_widget_str
        """
        row = self.__row_for_album(album)
        row.populate()
        row.reveal(Gtk.RevealerTransitionType.NONE)
        row.show()
        self.__view.insert(row, index)
        if App().settings.get_enum("shuffle") != Shuffle.TRACKS:
            App().player.set_next()

    def __on_track_added(self, row, album, tracks):
        """
            Remove track from widgets
            @param row as TrackRow
            @param album as Album
            @param tracks as [Track]
        """
        for album_row in self.__view.get_children():
            if album_row.album == album:
                album_row.append_rows(tracks)
                break

    def __on_track_removed(self, row, album, tracks):
        """
            Remove track from widgets
            @param row as TrackRow
            @param album as Album
            @param tracks as [Track]
        """
        for album_row in self.__view.get_children():
            if album_row.album == album:
                album_row.remove_rows(tracks)
                break

    def __on_track_moved(self, row, src_track_str, src_album_str, down):
        """
            Move src track to row
            Recalculate track position
            @param row as TrackRow
            @param src_track_str as str
            @param src_widget_str as str
            @param down as bool
        """
        try:
            children = self.__view.get_children()
            row_index = children.index(row)
            src_track = App().player.object_by_name(src_track_str,
                                                    src_album_str)
            src_album = App().player.object_by_name(None, src_album_str)
            if src_track is None or src_album is None:
                return
            src_album.remove_track(src_track)
            if not src_album.tracks:
                App().player.remove_album(src_album)
            children[row_index].emit("track-removed", src_album, [src_track])
            new_album = Album(src_track.album.id)
            new_album.set_tracks([src_track])
            album_row = self.__row_for_album(new_album)
            album_row.populate()
            album_row.show()
            if down:
                row_index += 1
            self.__view.insert(album_row, row_index)
            App().player.add_album(new_album, row_index)
        except Exception as e:
            Logger.error("AlbumsListView::__on_track_moved(): %s" % e)

    def __on_album_moved(self, row, src, down):
        """
            Pass signal
            @param row as PlaylistRow
            @param src as str
            @param down as bool
        """
        # Destroy current album row and search for album row
        i = 0
        row_index = -1
        album = None
        for child in self.__view.get_children():
            if child == row:
                row_index = i
            if str(child.album) == src:
                album = child.album
                child.disconnect_by_func(self.__on_child_destroyed)
                child.destroy()
            else:
                i += 1
        # Create new row
        if album is not None:
            album_row = self.__row_for_album(album)
            album_row.populate()

            # Add new row
            if row_index != -1:
                if down:
                    row_index += 1
                self.__view.insert(album_row, row_index)
                App().player.move_album(album, row_index)

    def __on_drag_motion(self, widget, context, x, y, time):
        """
            Add style
            @param widget as Gtk.Widget
            @param context as Gdk.DragContext
            @param x as int
            @param y as int
            @param time as int
        """
        auto_scroll = False
        up = y <= ArtSize.MEDIUM
        if up:
            auto_scroll = True
        elif y >= self._scrolled.get_allocated_height() - ArtSize.MEDIUM:
            auto_scroll = True
        else:
            self.get_style_context().remove_class("drag-down")
            self.get_style_context().remove_class("drag-up")
            if self.__autoscroll_timeout_id is not None:
                GLib.source_remove(self.__autoscroll_timeout_id)
                self.__autoscroll_timeout_id = None
            self.rows_animation(x, y)
            return
        if self.__autoscroll_timeout_id is None and auto_scroll:
            self.clear_animation()
            self.__autoscroll_timeout_id = GLib.timeout_add(100,
                                                            self.__auto_scroll,
                                                            up)

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
            self.clear_animation()
            (type_id, object_str, album_str) = data.get_text().split(":")
            if type_id == "a":
                self.__on_album_moved(self.__view.get_children()[-1],
                                      object_str, True)
            elif type_id == "t":
                self.__on_track_moved(self.__view.get_children()[-1],
                                      object_str, album_str, True)
        except Exception as e:
            Logger.error("AlbumsListView::__on_drag_data_received(): %s" % e)
