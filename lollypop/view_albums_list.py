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

from gi.repository import Gtk, Gdk, GLib, GObject, Pango

from gettext import gettext as _

from lollypop.view_tracks import TracksView
from lollypop.view import LazyLoadingView
from lollypop.objects import Album, Track
from lollypop.define import ArtSize, App, RowListType
from lollypop.controller_view import ViewController, ViewControllerType
from lollypop.widgets_row_dnd import DNDRow


class AlbumRow(Gtk.ListBoxRow, TracksView, DNDRow):
    """
        Album row
    """

    __gsignals__ = {
        "insert-album": (
            GObject.SignalFlags.RUN_FIRST, None,
            (int, GObject.TYPE_PYOBJECT, bool)),
        "insert-track": (GObject.SignalFlags.RUN_FIRST, None, (int, bool)),
        "insert-album-after": (GObject.SignalFlags.RUN_FIRST, None,
                               (GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT)),
        "remove-album": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "populated": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "do-selection": (GObject.SignalFlags.RUN_FIRST, None, ())
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

    def __init__(self, album, height, list_type, reveal, parent):
        """
            Init row widgets
            @param album as Album
            @param height as int
            @param list_type as RowListType
            @param reveal as bool
            @param parent as AlbumListView
        """
        Gtk.ListBoxRow.__init__(self)
        TracksView.__init__(self, list_type)
        if list_type & RowListType.DND:
            DNDRow.__init__(self)
        self.__revealer = None
        self.__parent = parent
        self.__reveal = reveal
        self._artwork = None
        self._album = album
        self.__list_type = list_type
        self.__play_indicator = None
        self.set_sensitive(False)
        self.set_property("height-request", height)
        # 15 for scrollbar overlay
        self.set_margin_end(15)
        self.connect("destroy", self.__on_destroy)

    def populate(self):
        """
            Populate widget content
        """
        if self.get_child() is not None:
            return
        self._artwork = App().art_helper.get_image(ArtSize.MEDIUM,
                                                   ArtSize.MEDIUM,
                                                   "small-cover-frame")
        self._artwork.set_margin_start(self.__MARGIN)
        # Little hack: we do not set margin_bottom because already set by
        # get_best_height(): we are Align.FILL
        # This allow us to not Align.CENTER row_widget and not jump up
        # and down on reveal()
        self._artwork.set_margin_top(self.__MARGIN)
        self.get_style_context().add_class("albumrow")
        self.get_style_context().add_class("albumrow-hover")
        self.set_sensitive(True)
        self.set_selectable(False)
        self.set_property("has-tooltip", True)
        self.connect("query-tooltip", self.__on_query_tooltip)
        row_widget = Gtk.EventBox()
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
        self.__title_label.set_property("halign", Gtk.Align.START)
        self.__title_label.get_style_context().add_class("dim-label")
        self.set_artwork()
        self.__action_button = None
        if self.__list_type & RowListType.SEARCH:
            action_icon = "media-playback-start-symbolic"
            action_tooltip_text = _("Play")
        elif self.__list_type & RowListType.DND:
            action_icon = "list-remove-symbolic"
            action_tooltip_text = _("Remove from current playlist")
        if self.__list_type & (RowListType.SEARCH | RowListType.DND):
            self.__action_button = Gtk.Button.new_from_icon_name(
                action_icon,
                Gtk.IconSize.MENU)
            self.__action_button.set_relief(Gtk.ReliefStyle.NONE)
            self.__action_button.get_style_context().add_class(
                "album-menu-button")
            self.__action_button.get_style_context().add_class(
                "track-menu-button")
            self.__action_button.set_tooltip_text(action_tooltip_text)
            self.__action_button.set_property("valign", Gtk.Align.CENTER)
            self.__action_button.connect("button-release-event",
                                         self.__on_action_button_release_event)
        self.__artists_button = None
        if self.__list_type & RowListType.SEARCH:
            self.__artists_button = Gtk.Button.new_from_icon_name(
                    'avatar-default-symbolic',
                    Gtk.IconSize.MENU)
            self.__artists_button.set_relief(Gtk.ReliefStyle.NONE)
            self.__artists_button.get_style_context().add_class(
                "album-menu-button")
            self.__artists_button.set_tooltip_text(_("Go to artist view"))
            self.__artists_button.set_property("valign", Gtk.Align.CENTER)
            self.__artists_button.connect(
                                      "button-release-event",
                                      self.__on_artists_button_release_event)
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
        grid.attach(self.__title_label, 1, 1, 1, 1)
        self.__revealer = Gtk.Revealer.new()
        self.__revealer.show()
        grid.attach(self.__revealer, 0, 2, index, 1)
        row_widget.add(grid)
        self.add(row_widget)
        self.set_playing_indicator()
        row_widget.connect("button-release-event",
                           self.__on_button_release_event)
        if self.__reveal:
            self.reveal()

    def append_rows(self, tracks):
        """
            Add track rows (only works for albums with merged discs)
            @param tracks as [Track]
        """
        if self._responsive_widget is not None:
            TracksView.append_rows(self, tracks)

    def prepend_rows(self, tracks):
        """
            Add track rows (only works for albums with merged discs)
            @param tracks as [Track]
        """
        if self._responsive_widget is not None:
            TracksView.prepend_rows(self, tracks)

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
            self.get_style_context().add_class("albumrow-hover")
            if self.album.id == App().player.current_track.album.id:
                self.set_state_flags(Gtk.StateFlags.VISITED, True)
        else:
            if self._responsive_widget is None:
                TracksView.populate(self)
                self._responsive_widget.show()
                self.__revealer.add(self._responsive_widget)
            self.get_style_context().remove_class("albumrow-hover")
            self.__revealer.set_reveal_child(True)
            self.set_state_flags(Gtk.StateFlags.NORMAL, True)

    def set_playing_indicator(self):
        """
            Show play indicator
            @param show as bool
        """
        if self._artwork is None:
            return
        selected = self.album.id == App().player.current_track.album.id
        if self.__revealer.get_reveal_child():
            TracksView.set_playing_indicator(self)
            self.set_state_flags(Gtk.StateFlags.NORMAL, True)
        elif selected:
            self.set_state_flags(Gtk.StateFlags.VISITED, True)
        else:
            self.set_state_flags(Gtk.StateFlags.NORMAL, True)

    def stop(self):
        """
            Stop view loading
        """
        self._artwork = None
        if self._responsive_widget is not None:
            TracksView.stop(self)

    def set_artwork(self):
        """
            Set album artwork
        """
        App().art_helper.set_album_artwork(self._album,
                                           ArtSize.MEDIUM,
                                           ArtSize.MEDIUM,
                                           self._artwork.get_scale_factor(),
                                           self.__on_album_artwork)

    @property
    def parent(self):
        """
            Get parent view
            @return AlbumListView
        """
        return self.__parent

    @property
    def is_populated(self):
        """
            Return True if populated
            @return bool
        """
        return True if self._responsive_widget is None or self.__reveal\
            else TracksView.get_populated(self)

    def set_filtered(self, b):
        """
            Set widget filtered
        """
        self.__filtered = b

    @property
    def filtered(self):
        """
            True if filtered by parent
        """
        return self.__filtered

    @property
    def filter(self):
        """
            @return str
        """
        return " ".join([self._album.name] + self._album.artists)

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
    def _on_tracks_populated(self, disc_number):
        """
            Populate remaining discs
            @param disc_number as int
        """
        if not self.is_populated:
            TracksView.populate(self)

#######################
# PRIVATE             #
#######################
    def __on_album_artwork(self, surface):
        """
            Set album artwork
            @param surface as str
        """
        if self._artwork is None:
            return
        if surface is None:
            self._artwork.set_from_icon_name("folder-music-symbolic",
                                             Gtk.IconSize.BUTTON)
        else:
            self._artwork.set_from_surface(surface)
        self.emit("populated")
        self.show_all()

    def __on_button_release_event(self, widget, event):
        """
            Show revealer with tracks
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        if event.state & Gdk.ModifierType.CONTROL_MASK and\
                self.__list_type & RowListType.DND:
            if self.get_state_flags() & Gtk.StateFlags.SELECTED:
                self.set_state_flags(Gtk.StateFlags.NORMAL, True)
            else:
                self.set_state_flags(Gtk.StateFlags.SELECTED, True)
        elif event.state & Gdk.ModifierType.SHIFT_MASK and\
                self.__list_type & RowListType.DND:
            self.emit("do-selection")
        else:
            self.reveal()

    def __on_action_button_release_event(self, button, event):
        """
            RowListType.SEARCH: Play album
            Else: Delete album
            @param button as Gtk.Button
            @param event as Gdk.Event
        """
        if self.__list_type & RowListType.SEARCH:
            album = self._album.clone(True)
            App().player.add_album(album)
            App().player.load(album.tracks[0])
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
        return True

    def __on_artists_button_release_event(self, button, event):
        """
            Jump to artists albums view
            @param button as Gtk.Button
            @param event as Gdk.Event
        """
        popover = self.get_ancestor(Gtk.Popover)
        if popover is not None:
            popover.popdown()
        if App().settings.get_value("show-sidebar"):
            App().window.container.show_artists_albums(self._album.artist_ids)
        else:
            App().window.container.show_view(self._album.artist_ids[0])
        return True

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

    def __on_destroy(self, widget):
        """
            Destroyed widget
            @param widget as Gtk.Widget
        """
        self._artwork = None


class AlbumsListView(LazyLoadingView, ViewController):
    """
        View showing albums
    """

    def __init__(self, list_type, artist_ids=[], genre_ids=[]):
        """
            Init widget
            @param list_type as RowListType
            @param artist_ids as int
            @param genre_ids as int
        """
        LazyLoadingView.__init__(self, True)
        ViewController.__init__(self, ViewControllerType.ALBUM)
        self.__list_type = list_type
        self.__genre_ids = genre_ids
        self.__artist_ids = artist_ids
        self.__autoscroll_timeout_id = None
        self.__reveals = []
        self.__prev_animated_rows = []
        # Calculate default album height based on current pango context
        # We may need to listen to screen changes
        self.__height = AlbumRow.get_best_height(self)
        self._box = Gtk.ListBox()
        self._box.get_style_context().add_class("trackswidget")
        self._box.set_vexpand(True)
        self._box.set_selection_mode(Gtk.SelectionMode.NONE)
        self._box.set_activate_on_single_click(True)
        self._box.set_filter_func(self._filter_func)
        self._box.show()
        self._scrolled.set_property("expand", True)
        self.add(self._scrolled)

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
        for child in self._box.get_children():
            GLib.idle_add(child.destroy)
        self.__add_albums(list(albums))

    def rows_animation(self, x, y):
        """
            Show animation to help user dnd
            @param x as int
            @param y as int
        """
        # FIXME autoscroll continue after drop
        self.clear_animation()
        for row in self._box.get_children():
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
        for child in self._box.get_children():
            GLib.idle_add(child.destroy)
        if clear_albums:
            App().player.clear_albums()

    @property
    def children(self):
        """
            Get view children
            @return [AlbumRow]
        """
        return self._box.get_children()

#######################
# PROTECTED           #
#######################
    def _on_current_changed(self, player):
        """
            Update children state
            @param player as Player
        """
        for child in self._box.get_children():
            child.set_playing_indicator()

    def _on_artwork_changed(self, artwork, album_id):
        """
            Update children artwork if matching album id
            @param artwork as Artwork
            @param album_id as int
        """
        for child in self._box.get_children():
            if child.album.id == album_id:
                child.set_artwork()

    def _on_map(self, widget):
        """
            Connect signals and set active ids
            @param widget as Gtk.Widget
        """
        if not self.__genre_ids and not self.__artist_ids:
            return
        if self.__genre_ids:
            App().settings.set_value("state-one-ids",
                                     GLib.Variant("ai", self.__genre_ids))
            App().settings.set_value("state-two-ids",
                                     GLib.Variant("ai", self.__artist_ids))
        else:
            App().settings.set_value("state-one-ids",
                                     GLib.Variant("ai", self.__artist_ids))
            App().settings.set_value("state-two-ids",
                                     GLib.Variant("ai", []))

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

    def __add_albums(self, albums, previous_row=None):
        """
            Add items to the view
            @param albums ids as [Album]
            @param previous_row as AlbumRow
        """
        if self._lazy_queue is None or self._viewport is None:
            return
        if albums:
            album = albums.pop(0)
            row = self.__row_for_album(album, album.id in self.__reveals)
            row.set_previous_row(previous_row)
            if previous_row is not None:
                previous_row.set_next_row(row)
            row.show()
            self._box.add(row)
            self._lazy_queue.append(row)
            GLib.idle_add(self.__add_albums, albums, row)
        else:
            # If only one album, we want to reveal it
            # Stop lazy loading and populate
            children = self._box.get_children()
            if len(children) == 1:
                self.stop()
                children[0].populate()
                children[0].reveal(True)
            else:
                GLib.idle_add(self.lazy_loading)
            if self._viewport.get_child() is None:
                self._viewport.add(self._box)

    def __row_for_album(self, album, reveal=False):
        """
            Get a row for track id
            @param album as Album
            @param reveal as bool
        """
        row = AlbumRow(album, self.__height, self.__list_type, reveal, self)
        row.connect("insert-track", self.__on_insert_track)
        row.connect("insert-album", self.__on_insert_album)
        row.connect("insert-album-after", self.__on_insert_album_after)
        row.connect("remove-album", self.__on_remove_album)
        row.connect("do-selection", self.__on_do_selection)
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
        for child in self._box.get_children():
            if child.album == App().player.current_track.album:
                child.populate()
                child.reveal(True)
                y = child.translate_coordinates(self._box, 0, 0)[1]
        return y

    def __on_insert_track(self, row, new_track_id, down):
        """
            Insert a new row at position
            @param row as PlaylistRow
            @param new_track_id as int
            @param down as bool
        """
        new_track = Track(new_track_id)
        children = self._box.get_children()
        position = children.index(row)
        lenght = len(children)
        if down:
            position += 1
        # Append track to current/next album
        if position < lenght and\
                children[position].album.id == new_track.album.id:
            new_track.set_album(children[position].album)
            children[position].prepend_rows([new_track])
            children[position].album.insert_track(new_track, 0)
        # Append track to previous/current album
        elif position - 1 < lenght and\
                children[position - 1].album.id == new_track.album.id:
            new_track.set_album(children[position - 1].album)
            children[position - 1].append_rows([new_track])
            children[position - 1].album.insert_track(new_track)
        # Add a new album
        else:
            album = Album(new_track.album.id)
            album.set_tracks([new_track])
            new_row = self.__row_for_album(album)
            new_row.populate()
            new_row.show()
            self._box.insert(new_row, position)
            App().player.add_album(album, position)
            if row.previous_row is not None and\
                    row.previous_row.album.id ==\
                    App().player.current_track.album.id:
                App().player.set_next()
                App().player.set_prev()

    def __on_insert_album(self, row, new_album_id, track_ids, down):
        """
            Insert a new row at position
            @param row as AlbumRow
            @param new_track_id as int
            @param track_ids as [int]
            @param down as bool
        """
        position = self._box.get_children().index(row)
        if down:
            position += 1
        album = Album(new_album_id)
        album.set_tracks([Track(track_id) for track_id in track_ids])
        new_row = self.__row_for_album(album)
        new_row.populate()
        new_row.show()
        self._box.insert(new_row, position)
        App().player.add_album(album, position)

    def __on_insert_album_after(self, view, after_album, album):
        """
            Insert album after after_album
            @param view as TracksView
            @param after_album as Album
            @param album as Album
        """
        position = 0
        children = self._box.get_children()
        # If after_album is undefined, prepend)
        if after_album.id is not None:
            for row in children:
                if row.album == after_album:
                    break
                position += 1
        new_row = self.__row_for_album(album)
        new_row.populate()
        new_row.set_previous_row(children[position])
        new_row.set_next_row(children[position].next_row)
        children[position].set_next_row(new_row)
        if new_row.next_row is not None:
            new_row.next_row.set_previous_row(new_row)
        new_row.show()
        self._box.insert(new_row, position + 1)
        App().player.add_album(album, position + 1)

    def __on_remove_album(self, row):
        """
            Remove album from player
            @param row as AlbumRow
        """
        App().player.remove_album(row.album)

    def __on_do_selection(self, row):
        """
            Select rows from start (or any selected row) to track
            @param row as AlbumRow
        """
        children = self._box.get_children()
        selected = None
        end = children.index(row) + 1
        for child in children:
            if child == row:
                break
            if child.get_state_flags() & Gtk.StateFlags.SELECTED:
                selected = child
        if selected is None:
            start = 0
        else:
            start = children.index(selected)
        for child in children[start:end]:
            child.set_state_flags(Gtk.StateFlags.SELECTED, True)
        for child in children[end:]:
            child.set_state_flags(Gtk.StateFlags.NORMAL, True)
