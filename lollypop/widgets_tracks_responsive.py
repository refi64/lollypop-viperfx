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

from gi.repository import GLib, Gtk, Gdk

from gettext import gettext as _

from lollypop.define import WindowSize, Loading
from lollypop.widgets_track import TracksWidget, TrackRow
from lollypop.objects import Track
from lollypop.define import Lp, NextContext, ArtSize, Type


class TracksResponsiveWidget:
    """
        Widget with two TracksWidget with responsive orientation
        @member _album as Album needed
    """

    def __init__(self):
        """
            Init widget
        """
        self._loading = Loading.NONE
        self.__width = None
        self.__orientation = None
        self.__child_height = TrackRow.get_best_height(self)
        # Header + separator + spacing + margin
        self.__height = self.__child_height + 6
        # Discs to load, will be emptied
        self.__discs = self._album.discs
        self.__locked_widget_right = True

        self._responsive_widget = Gtk.Grid()
        self._responsive_widget.set_column_homogeneous(True)
        self._responsive_widget.set_property("valign", Gtk.Align.START)
        self._responsive_widget.show()

        self._tracks_left = {}
        self._tracks_right = {}

        for disc in self.__discs:
            self.__add_disc_container(disc.number)
            self.__set_disc_height(disc)

    def update_playing_indicator(self):
        """
            Update playing indicator
        """
        for disc in self._album.discs:
            self._tracks_left[disc.number].update_playing(
                Lp().player.current_track.id)
            self._tracks_right[disc.number].update_playing(
                Lp().player.current_track.id)

    def update_duration(self, track_id):
        """
            Update duration for current track
            @param track id as int
        """
        for disc in self._album.discs:
            self._tracks_left[disc.number].update_duration(track_id)
            self._tracks_right[disc.number].update_duration(track_id)

    def populate(self):
        """
            Populate tracks
            @thread safe
        """
        if self.__discs:
            disc = self.__discs.pop(0)
            mid_tracks = int(0.5 + len(disc.tracks) / 2)
            self.populate_list_left(disc.tracks[:mid_tracks],
                                    disc,
                                    1)
            self.populate_list_right(disc.tracks[mid_tracks:],
                                     disc,
                                     mid_tracks + 1)

    def is_populated(self):
        """
            Return True if populated
            @return bool
        """
        return len(self.__discs) == 0

    def populate_list_left(self, tracks, disc, pos):
        """
            Populate left list, thread safe
            @param tracks as [Track]
            @param disc as Disc
            @param pos as int
        """
        GLib.idle_add(self.__add_tracks,
                      tracks,
                      self._tracks_left,
                      disc.number,
                      pos)

    def populate_list_right(self, tracks, disc, pos):
        """
            Populate right list, thread safe
            @param tracks as [Track]
            @param disc as Disc
            @param pos as int
        """
        # If we are showing only one column, wait for widget1
        if self.__orientation == Gtk.Orientation.VERTICAL and\
           self.__locked_widget_right:
            GLib.timeout_add(100, self.populate_list_right, tracks, disc, pos)
        else:
            GLib.idle_add(self.__add_tracks,
                          tracks,
                          self._tracks_right,
                          disc.number,
                          pos)

    def get_current_ordinate(self, parent):
        """
            If current track in widget, return it ordinate,
            @param parent widget as Gtk.Widget
            @return y as int
        """
        for dic in [self._tracks_left, self._tracks_right]:
            for widget in dic.values():
                for child in widget.get_children():
                    if child.id == Lp().player.current_track.id:
                        return child.translate_coordinates(parent, 0, 0)[1]
        return None

    def set_filter_func(self, func):
        """
            Set filter function
        """
        for widget in self._tracks_left.values():
            widget.set_filter_func(func)
        for widget in self._tracks_right.values():
            widget.set_filter_func(func)

    def height(self):
        """
            Widget height
        """
        return self.__height

    @property
    def boxes(self):
        """
            @return [Gtk.ListBox]
        """
        boxes = []
        for widget in self._tracks_left.values():
            boxes.append(widget)
        for widget in self._tracks_right.values():
            boxes.append(widget)
        return boxes

#######################
# PROTECTED           #
#######################
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
        for dic in [self._tracks_left, self._tracks_right]:
            for widget in dic.values():
                for child in widget.get_children():
                    track = Track(child.id)
                    if track.album.id == Type.NONE:
                        removed = True
        if removed:
            for dic in [self._tracks_left, self._tracks_right]:
                for widget in dic.values():
                    for child in widget.get_children():
                        child.destroy()
            self.__discs = self._album.discs
            self.__set_duration()
            self.populate()

    def _on_size_allocate(self, widget, allocation):
        """
            Change box max/min children
            @param widget as Gtk.Widget
            @param allocation as Gtk.Allocation
        """
        if self.__width == allocation.width:
            return
        self.__width = allocation.width
        redraw = False
        # We want vertical orientation
        # when not enought place for cover or tracks
        if allocation.width < WindowSize.MEDIUM or (
                allocation.width < WindowSize.MONSTER and
                self._art_size == ArtSize.BIG):
            orientation = Gtk.Orientation.VERTICAL
        else:
            orientation = Gtk.Orientation.HORIZONTAL
        if orientation != self.__orientation:
            self.__orientation = orientation
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
                    label = Gtk.Label()
                    if disc_names:
                        disc_text = ", ".join(disc_names)
                    elif show_label:
                        disc_text = _("Disc %s") % disc.number
                    label.set_text(disc_text)
                    label.set_property("halign", Gtk.Align.START)
                    label.get_style_context().add_class("dim-label")
                    label.show()
                    eventbox = Gtk.EventBox()
                    eventbox.add(label)
                    eventbox.connect("realize",
                                     self.__on_disc_label_realize)
                    eventbox.connect("button-press-event",
                                     self.__on_disc_press_event, disc.number)
                    eventbox.show()
                    self._responsive_widget.attach(eventbox, 0, idx, width, 1)
                    idx += 1
                GLib.idle_add(self._responsive_widget.attach,
                              self._tracks_left[disc.number],
                              0, idx, 1, 1)
                if orientation == Gtk.Orientation.VERTICAL:
                    idx += 1
                GLib.idle_add(self._responsive_widget.attach,
                              self._tracks_right[disc.number],
                              pos, idx, 1, 1)
                idx += 1

    def _on_populated(self):
        """
            Override this when you want to know that tracks are populated
        """
        pass

#######################
# PRIVATE             #
#######################
    def __set_disc_height(self, disc):
        """
            Set disc widget height
            @param disc as Disc
        """
        count_tracks = len(disc.tracks)
        mid_tracks = int(0.5 + count_tracks / 2)
        left_height = self.__child_height * mid_tracks
        right_height = self.__child_height * (count_tracks - mid_tracks)
        if left_height > right_height:
            self.__height += left_height
        else:
            self.__height += right_height
        self._tracks_left[disc.number].set_property("height-request",
                                                    left_height)
        self._tracks_right[disc.number].set_property("height-request",
                                                     right_height)

    def __add_disc_container(self, disc_number):
        """
            Add disc container to box
            @param disc_number as int
        """
        self._tracks_left[disc_number] = TracksWidget()
        self._tracks_right[disc_number] = TracksWidget()
        self._tracks_left[disc_number].connect("activated",
                                               self.__on_activated)
        self._tracks_right[disc_number].connect("activated",
                                                self.__on_activated)
        self._tracks_left[disc_number].show()
        self._tracks_right[disc_number].show()

    def __add_tracks(self, tracks, widget, disc_number, i):
        """
            Add tracks for to tracks widget
            @param tracks as [Track]
            @param widget as TracksWidget
            @param disc number as int
            @param i as int
        """
        if self._loading == Loading.STOP:
            self._loading = Loading.NONE
            return
        if not tracks:
            if widget == self._tracks_right:
                self._loading |= Loading.RIGHT
            elif widget == self._tracks_left:
                self._loading |= Loading.LEFT
            if self._loading == Loading.ALL:
                self._on_populated()
            self.__locked_widget_right = False
            return

        track = tracks.pop(0)
        if not Lp().settings.get_value("show-tag-tracknumber"):
            track.set_number(i)
        track.set_featuring_ids(self._album.artist_ids)
        row = TrackRow(track)
        row.connect("destroy", self.__on_row_destroy)
        row.show()
        widget[disc_number].add(row)
        GLib.idle_add(self.__add_tracks, tracks, widget, disc_number, i + 1)

    def __on_disc_label_realize(self, eventbox):
        """
            Set mouse cursor
            @param eventbox as Gtk.EventBox
        """
        eventbox.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))

    def __on_disc_press_event(self, eventbox, event, idx):
        """
            Add/Remove disc to/from queue
            @param eventbox as Gtk.EventBox
            @param event as Gdk.Event
            @param idx as int
        """
        disc = None
        for d in self._album.discs:
            if d.number == idx:
                disc = d
                break
        if disc is None:
            return
        for track in disc.tracks:
            if Lp().player.track_in_queue(track):
                Lp().player.del_from_queue(track.id, False)
            else:
                Lp().player.append_to_queue(track.id, False)
        Lp().player.emit("queue-changed")

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

    def __on_activated(self, widget, track):
        """
            On track activation, play track
            @param widget as TracksWidget
            @param track as Track
        """
        # Add to queue by default
        if Lp().player.locked:
            if track.id in Lp().player.queue:
                Lp().player.del_from_queue(track.id)
            else:
                Lp().player.append_to_queue(track.id)
        else:
            # Do not update album list
            if not Lp().player.is_party and not\
                    Lp().settings.get_enum("playback") == NextContext.STOP:
                # If in artist view, reset album list
                if self._album.artist_ids:
                    Lp().player.play_albums(track,
                                            self._album.genre_ids,
                                            self._album.artist_ids)
                # Else, add album if missing
                elif self._album not in Lp().player.albums:
                    Lp().player.add_album(self._album)
                    Lp().player.load(track)
            # Clear albums if user clicked on a track from a new album
            elif Lp().settings.get_enum("playback") == NextContext.STOP:
                if not Lp().player.has_album(self._album):
                    Lp().player.clear_albums()
