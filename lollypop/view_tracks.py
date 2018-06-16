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

from gi.repository import GLib, Gtk, GObject

from gettext import gettext as _

from lollypop.define import WindowSize, Loading
from lollypop.widgets_track import TracksWidget, TrackRow
from lollypop.objects import Album
from lollypop.logger import Logger
from lollypop.define import App, Type, ResponsiveType, Shuffle, NextContext


class TracksView:
    """
        Responsive view showing discs on one or two rows
    """
    __gsignals__ = {
        "album-added": (GObject.SignalFlags.RUN_FIRST, None,
                        (int, GObject.TYPE_PYOBJECT)),
        "album-moved": (GObject.SignalFlags.RUN_FIRST, None,
                        (int, GObject.TYPE_PYOBJECT)),
        "track-append": (GObject.SignalFlags.RUN_FIRST, None,
                         (GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT)),
        "track-removed": (GObject.SignalFlags.RUN_FIRST, None,
                          (GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT)),
    }

    def __init__(self, responsive_type):
        """
            Init widget
            @param responsive_type as ResponsiveType
        """
        self._responsive_type = responsive_type
        self.__loading = Loading.NONE
        self._width = None
        self._orientation = None
        self._child_height = TrackRow.get_best_height(self)
        # Header + separator + spacing + margin
        self.__height = self.__total_height = self._child_height + 6
        self._locked_widget_right = True

        self._responsive_widget = Gtk.Grid()
        self._responsive_widget.set_column_homogeneous(True)
        self._responsive_widget.set_property("valign", Gtk.Align.START)
        self._responsive_widget.show()

        self._tracks_widget_left = {}
        self._tracks_widget_right = {}

        if self._responsive_type in [ResponsiveType.DND,
                                     ResponsiveType.LIST,
                                     ResponsiveType.SEARCH]:
            self._album.merge_discs()
        # Discs to load, will be emptied
        self.__discs = list(self._album.discs)
        for disc in self.__discs:
            self.__add_disc_container(disc.number)
            self.__set_disc_height(disc.number, disc.tracks)

    def update_playing_indicator(self):
        """
            Update playing indicator
        """
        try:
            for disc in self._album.discs:
                self._tracks_widget_left[disc.number].update_playing(
                    App().player.current_track.id)
                self._tracks_widget_right[disc.number].update_playing(
                    App().player.current_track.id)
        except Exception as e:
            Logger.error("TrackView::update_playing_indicator(): %s" % e)

    def update_duration(self, track_id):
        """
            Update duration for current track
            @param track id as int
        """
        for disc in self._album.discs:
            self._tracks_widget_left[disc.number].update_duration(track_id)
            self._tracks_widget_right[disc.number].update_duration(track_id)

    def populate(self):
        """
            Populate tracks
            @thread safe
        """
        if self.__discs:
            disc = self.__discs.pop(0)
            disc_number = disc.number
            tracks = disc.tracks
            mid_tracks = int(0.5 + len(tracks) / 2)
            self.populate_list_left(tracks[:mid_tracks],
                                    disc_number,
                                    1)
            self.populate_list_right(tracks[mid_tracks:],
                                     disc_number,
                                     mid_tracks + 1)

    def is_populated(self):
        """
            Return True if populated
            @return bool
        """
        return len(self.__discs) == 0

    def populate_list_left(self, tracks, disc_number, pos):
        """
            Populate left list, thread safe
            @param tracks as [Track]
            @param disc_number as int
            @param pos as int
        """
        GLib.idle_add(self.__add_tracks,
                      tracks,
                      self._tracks_widget_left,
                      disc_number,
                      pos)

    def populate_list_right(self, tracks, disc_number, pos):
        """
            Populate right list, thread safe
            @param tracks as [Track]
            @param disc_number as int
            @param pos as int
        """
        # If we are showing only one column, wait for widget1
        if self._orientation == Gtk.Orientation.VERTICAL and\
           self._locked_widget_right:
            GLib.timeout_add(100, self.populate_list_right,
                             tracks, disc_number, pos)
        else:
            GLib.idle_add(self.__add_tracks,
                          tracks,
                          self._tracks_widget_right,
                          disc_number,
                          pos)

    def append_rows(self, tracks):
        """
            Add track rows
            @param tracks as [Track]
        """
        for track in tracks:
            row = TrackRow(track, self._responsive_type)
            row.connect("destroy", self.__on_row_destroy)
            row.connect("track-moved", self.__on_track_moved)
            row.connect("album-moved", self.__on_album_moved)
            row.show()
            self.boxes[-1].add(row)
        self.recalculate_tracks_position()

    def remove_rows(self, tracks):
        """
            Remove track rows
            @param tracks as [Track]
        """
        track_ids = [track.id for track in tracks]
        for row in self.children:
            if row.track.id in track_ids:
                row.destroy()
        self.recalculate_tracks_position()

    def rows_animation(self, x, y, widget):
        """
            Show animation to help user dnd
            @parma x as int
            @param y as int
            @param relate widget as Gtk.Widget
        """
        if self._responsive_widget is None:
            return None
        for row in self.children:
            coordinates = row.translate_coordinates(widget, 0, 0)
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
            if y <= row_y + row_height / 2:
                row.get_style_context().add_class("drag-up")
                return row
            elif y >= row_y + row_height / 2:
                row.get_style_context().add_class("drag-down")
                return row
        return None

    def recalculate_tracks_position(self):
        """
            Update track number if needed
            Check track are correctly populated between left and right
        """
        # DND allowed, so discs are merged
        disc_number = self._album.discs[0].number
        left_widget = self._tracks_widget_left[disc_number]
        right_widget = self._tracks_widget_right[disc_number]
        left_children = left_widget.get_children()
        right_children = right_widget.get_children()
        if not App().settings.get_value("show-tag-tracknumber"):
            i = 1
            for child in left_widget.get_children() +\
                    right_widget.get_children():
                child.track.set_number(i)
                child.update_num_label()
                i += 1
        if len(right_children) > len(left_children):
            row = right_children[0]
            right_widget.remove(row)
            left_widget.add(row)
        # Take last track of tracks1 and put it at the bottom of tracks2
        elif len(left_children) - 1 > len(right_children):
            row = left_children[-1]
            left_widget.remove(row)
            right_widget.prepend(row)

    def set_filter_func(self, func):
        """
            Set filter function
        """
        for widget in self._tracks_widget_left.values():
            widget.set_filter_func(func)
        for widget in self._tracks_widget_right.values():
            widget.set_filter_func(func)

    def get_current_ordinate(self, parent):
        """
            If current track in widget, return it ordinate,
            @param parent widget as Gtk.Widget
            @return y as int
        """
        for child in self.children:
            if child.id == App().player.current_track.id:
                return child.translate_coordinates(parent, 0, 0)[1]
        return None

    def stop(self):
        """
            Stop loading
        """
        self.__loading = Loading.STOP

    @property
    def height(self):
        """
            Widget height
        """
        if self._orientation == Gtk.Orientation.VERTICAL:
            return self.__total_height
        else:
            return self.__height

    @property
    def children(self):
        """
            Return all rows
            @return [Gtk.ListBoxRow]
        """
        rows = []
        for dic in [self._tracks_widget_left, self._tracks_widget_right]:
            for widget in dic.values():
                for row in widget.get_children():
                    rows.append(row)
        return rows

    @property
    def boxes(self):
        """
            @return [Gtk.ListBox]
        """
        boxes = []
        for widget in self._tracks_widget_left.values():
            boxes.append(widget)
        for widget in self._tracks_widget_right.values():
            boxes.append(widget)
        return boxes

#######################
# PROTECTED           #
#######################
    def __set_disc_height(self, disc_number, tracks):
        """
            Set disc widget height
            @param disc_number as int
            @param tracks as [Track]
        """
        tracks = tracks
        count_tracks = len(tracks)
        mid_tracks = int(0.5 + count_tracks / 2)
        left_height = self._child_height * mid_tracks
        right_height = self._child_height * (count_tracks - mid_tracks)
        if left_height > right_height:
            self.__height += left_height
        else:
            self.__height += right_height
        self.__total_height += left_height + right_height
        # Add self._child_height for disc label
        if len(self._album.discs) > 1:
            self.__height += self._child_height
            self.__total_height += self._child_height
        self._tracks_widget_left[disc_number].set_property("height-request",
                                                           left_height)
        self._tracks_widget_right[disc_number].set_property("height-request",
                                                            right_height)

    def _on_album_updated(self, scanner, album_id, destroy):
        """
            On album modified, disable it
            @param scanner as CollectionScanner
            @param album id as int
            @param destroy as bool
        """
        if self._album.id != album_id:
            return
        removed = False
        for dic in [self._tracks_widget_left, self._tracks_widget_right]:
            for widget in dic.values():
                for child in widget.get_children():
                    if child.track.album.id == Type.NONE:
                        removed = True
        if removed:
            for dic in [self._tracks_widget_left, self._tracks_widget_right]:
                for widget in dic.values():
                    for child in widget.get_children():
                        child.destroy()
            self.__discs = list(self._album.discs)
            self.__set_duration()
            self.populate()

    def _on_populated(self):
        """
            Remove height request
        """
        for disc in self._album.discs:
            self._tracks_widget_left[disc.number].set_property(
                "height-request", -1)
            self._tracks_widget_right[disc.number].set_property(
                "height-request", -1)

    def _on_size_allocate(self, widget, allocation):
        """
            Change box max/min children
            @param widget as Gtk.Widget
            @param allocation as Gtk.Allocation
        """
        if self._width == allocation.width:
            return
        self._width = allocation.width
        redraw = False
        # We want vertical orientation
        # when not enought place for cover or tracks
        if allocation.width < WindowSize.MONSTER:
            orientation = Gtk.Orientation.VERTICAL
        else:
            orientation = Gtk.Orientation.HORIZONTAL
        if orientation != self._orientation:
            self._orientation = orientation
            redraw = True

        if redraw:
            for child in self._responsive_widget.get_children():
                self._responsive_widget.remove(child)
            # Grid index
            idx = 0
            # Disc label width / right box position
            if orientation == Gtk.Orientation.VERTICAL:
                width = 1
                pos = 0
            else:
                width = 2
                pos = 1
            for disc in self._album.discs:
                show_label = len(self._album.discs) > 1
                disc_names = self._album.disc_names(disc.number)
                if show_label or disc_names:
                    if disc_names:
                        disc_text = ", ".join(disc_names)
                    elif show_label:
                        disc_text = _("Disc %s") % disc.number
                    box = Gtk.Box()
                    label = Gtk.Label()
                    label.set_text(disc_text)
                    label.set_property("halign", Gtk.Align.START)
                    label.get_style_context().add_class("dim-label")
                    label.show()
                    indicator = Gtk.Button.new_from_icon_name(
                        "go-next-symbolic",
                        Gtk.IconSize.BUTTON)
                    indicator.get_style_context().add_class("menu-button")
                    indicator.connect("clicked",
                                      self.__on_indicator_button_clicked,
                                      box,
                                      disc)
                    indicator.show()
                    box.set_spacing(5)
                    box.add(label)
                    box.add(indicator)
                    box.show()
                    self._responsive_widget.attach(box, 0, idx, width, 1)
                    idx += 1
                GLib.idle_add(self._responsive_widget.attach,
                              self._tracks_widget_left[disc.number],
                              0, idx, 1, 1)
                if orientation == Gtk.Orientation.VERTICAL:
                    idx += 1
                GLib.idle_add(self._responsive_widget.attach,
                              self._tracks_widget_right[disc.number],
                              pos, idx, 1, 1)
                idx += 1

#######################
# PRIVATE             #
#######################
    def __add_disc_container(self, disc_number):
        """
            Add disc container to box
            @param disc_number as int
        """
        self._tracks_widget_left[disc_number] = TracksWidget(
            self._responsive_type)
        self._tracks_widget_right[disc_number] = TracksWidget(
            self._responsive_type)
        self._tracks_widget_left[disc_number].connect("activated",
                                                      self.__on_activated)
        self._tracks_widget_right[disc_number].connect("activated",
                                                       self.__on_activated)
        self._tracks_widget_left[disc_number].show()
        self._tracks_widget_right[disc_number].show()

    def __add_tracks(self, tracks, widget, disc_number, i):
        """
            Add tracks for to tracks widget
            @param tracks as [Track]
            @param widget as TracksWidget
            @param disc number as int
            @param i as int
        """
        if self.__loading == Loading.STOP:
            self.__loading = Loading.NONE
            return
        if not tracks:
            if widget == self._tracks_widget_right:
                self.__loading |= Loading.RIGHT
            elif widget == self._tracks_widget_left:
                self.__loading |= Loading.LEFT
            if self.__loading == Loading.ALL:
                self._on_populated()
            self._locked_widget_right = False
            return

        track = tracks.pop(0)
        if not App().settings.get_value("show-tag-tracknumber"):
            track.set_number(i)
        track.set_featuring_ids(self._album.artist_ids)
        row = TrackRow(track, self._responsive_type)
        row.connect("destroy", self.__on_row_destroy)
        row.connect("track-moved", self.__on_track_moved)
        row.connect("album-moved", self.__on_album_moved)
        row.show()
        widget[disc_number].add(row)
        GLib.idle_add(self.__add_tracks, tracks, widget, disc_number, i + 1)

    def __move_track(self, src_index, dst_index):
        """
            Move track in album
            @param src_index as int/None
            @param dst_index as int
        """
        # DND allowed, so discs are merged
        disc_number = self._album.discs[0].number
        src_widget = self._tracks_widget_left[disc_number]
        dst_widget = self._tracks_widget_left[disc_number]
        # Search parent widget for src and dst
        if src_index is not None and\
                src_index >= len(src_widget.get_children()):
            src_index -= len(src_widget.get_children())
            src_widget = self._tracks_widget_right[disc_number]
        if dst_index >= len(dst_widget.get_children()):
            dst_index -= len(dst_widget.get_children())
            dst_widget = self._tracks_widget_right[disc_number]
        # Get source row
        if src_index is not None:
            row = src_widget.get_children()[src_index]
            src_widget.remove(row)
            dst_widget.insert(row, dst_index)
        if App().settings.get_enum("shuffle") != Shuffle.TRACKS:
            App().player.set_next()

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
            albums = App().player.albums
            src_track = App().player.object_by_name(src_track_str,
                                                    src_album_str)
            if src_track is None:
                return
            # Search album
            album_index = albums.index(self._album)
            tracks = self._album.tracks
            track_index = tracks.index(row.track)
            # DND inside same widget
            if src_album_str == str(self._album):
                src_index = self._album.tracks.index(src_track)
                tracks.remove(src_track)
                track_index = tracks.index(row.track)
                tracks.insert(track_index, src_track)
                if down:
                    track_index += 1
                self.__move_track(src_index, track_index)
            # Move src track into row
            else:
                # Search for src album, we need to remove track
                src_album = App().player.object_by_name(None,
                                                        src_album_str)
                if src_album is None:
                    return
                src_album.remove_track(src_track)
                self.emit("track-removed", src_album, [src_track])
                # Special case when moving src at top
                if (track_index == 0 and not down) or\
                        (track_index + 1 == len(tracks) and down):
                    # We just create a new album at top/bottom
                    if album_index == 0 or album_index + 1 == len(albums):
                        if down:
                            album_index += 1
                        # Create a new album for src
                        new_src_album = Album(src_track.album.id)
                        new_src_album.set_tracks([src_track])
                        albums.insert(album_index, new_src_album)
                        self.emit("album-added", album_index, new_src_album)
                    # We need to check if an album merge is possible
                    else:
                        if track_index == 0:
                            prev_next_index = album_index - 1
                        else:
                            prev_next_index = album_index + 1
                        prev_next_album = albums[prev_next_index]
                        # Merge
                        if prev_next_album.id == src_track.album.id:
                            prev_next_album.add_track(src_track)
                            self.emit("track-append",
                                      prev_next_album,
                                      [src_track])
                        # Add an album up
                        else:
                            # Create a new album for src
                            new_src_album = Album(src_track.album.id)
                            new_src_album.set_tracks([src_track])
                            self.emit("album-added",
                                      prev_next_index,
                                      new_src_album)
                else:
                    if down:
                        track_index += 1
                    # Split orig album
                    tracks = list(self._album.tracks)
                    self._album.set_tracks(tracks[0:track_index])
                    self.emit("track-removed", self._album,
                              tracks[track_index:])
                    # Create a new album for src
                    new_src_album = Album(src_track.album.id)
                    new_src_album.set_tracks([src_track])
                    # Split album
                    split_album = Album(self._album.id)
                    split_album.set_tracks(tracks[track_index + 1:-1])
                    albums.insert(album_index + 1, new_src_album)
                    albums.insert(album_index + 2, split_album)
                    self.emit("album-added", album_index + 1, new_src_album)
                    self.emit("album-added", album_index + 2, split_album)
            self.recalculate_tracks_position()
        except Exception as e:
            Logger.error("TracksView::__on_track_moved(): %s" % e)

    def __on_album_moved(self, row, src_album_str, down):
        """
            Move src album to row
            Recalculate track position
            @param row as TrackRow
            @param src_album_str as str
            @param down as bool
        """
        try:
            albums = App().player.albums
            # Search track in album
            tracks = list(self._album.tracks)
            track_index = tracks.index(row.track)
            album_index = App().player.albums.index(self._album)
            if down:
                track_index += 1
            # Split orig album
            self._album.set_tracks(tracks[0:track_index])
            self.emit("track-removed", self._album,
                      tracks[track_index:])
            # Get album for src
            src_album = App().player.object_by_name(None, src_album_str)
            if src_album is None:
                return
            # Split album
            split_album = Album(self._album.id)
            split_album.set_tracks(tracks[track_index:])
            albums.remove(src_album)
            albums.insert(album_index + 1, src_album)
            albums.insert(album_index + 2, split_album)
            self.emit("album-moved", album_index + 1, src_album)
            self.emit("album-added", album_index + 2, split_album)
            self.recalculate_tracks_position()
        except Exception as e:
            Logger.error("TracksView::__on_album_moved(): %s" % e)

    def __on_row_destroy(self, widget):
        """
            Destroy self if no more row
        """
        contain_children = False
        for box in self.boxes:
            if box.get_children():
                contain_children = True
                break
        if not contain_children:
            self.destroy()

    def __on_indicator_button_clicked(self, button, box, disc):
        """
            Popup menu for track relative to button
            @param button as Gtk.Button
            @param box as Gtk.Box
            @param disc as Disc
        """
        def on_hide(widget):
            button.emit("clicked")
        from lollypop.widgets_context import ContextWidget
        context_widget = None
        for child in box.get_children():
            if isinstance(child, ContextWidget):
                context_widget = child
                break
        image = button.get_image()
        if context_widget is None:
            image.set_from_icon_name("go-previous-symbolic",
                                     Gtk.IconSize.MENU)
            context_widget = ContextWidget(disc, button)
            context_widget.connect("hide", on_hide)
            context_widget.show()
            box.add(context_widget)
        else:
            image.set_from_icon_name("go-next-symbolic",
                                     Gtk.IconSize.MENU)
            context_widget.destroy()
        return True

    def __on_activated(self, widget, track):
        """
            On track activation, play track
            @param widget as TracksWidget
            @param track as Track
        """
        # Add to queue by default
        if App().player.locked:
            if track.id in App().player.queue:
                App().player.del_from_queue(track.id)
            else:
                App().player.append_to_queue(track.id)
        else:
            playback = App().settings.get_enum("playback")
            # Do not update album list if in party or album already available
            if not App().player.is_party and\
                    playback != NextContext.STOP and\
                    not App().player.track_in_playback(track):
                App().player.add_album(self._album)
            App().player.load(track)
