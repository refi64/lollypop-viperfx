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

from gi.repository import Gtk, GLib, Gdk, GObject, Pango

from cgi import escape
from gettext import gettext as _

from lollypop.define import Lp, ArtSize, NextContext
from lollypop.define import WindowSize, Shuffle, Loading
from lollypop.widgets_track import TracksWidget, TrackRow
from lollypop.objects import Track
from lollypop.widgets_rating import RatingWidget
from lollypop.pop_menu import AlbumMenu
from lollypop.pop_artwork import CoversPopover
from lollypop.objects import Album


class AlbumWidget:
    """
        Base album widget
    """

    def __init__(self, album_id, genre_ids=[]):
        """
            Init widget
        """
        self._album = Album(album_id, genre_ids)
        self._filter_ids = []
        self._selected = None
        self._loading = Loading.NONE
        self._cover = None
        self._widget = None
        self._play_all_button = None
        self._artwork_button = None
        self._action_button = None
        self._show_overlay = False
        self._lock_overlay = False
        self._timeout_id = None
        self._overlay_orientation = Gtk.Orientation.HORIZONTAL
        self._squared_class = "squared-icon"
        self._rounded_class = "rounded-icon"
        self._scan_signal = Lp().scanner.connect('album-update',
                                                 self._on_album_update)
        self.connect('destroy', self._on_destroy)

    def set_cover(self):
        """
            Set cover for album if state changed
        """
        if self._cover is None:
            return
        surface = Lp().art.get_album_artwork(
                            self._album,
                            ArtSize.BIG,
                            self._cover.get_scale_factor())
        self._cover.set_from_surface(surface)
        self._cover.set_size_request(100, 100)
        if surface.get_height() > surface.get_width():
            self._overlay_orientation = Gtk.Orientation.VERTICAL
        else:
            self._overlay_orientation = Gtk.Orientation.HORIZONTAL
        del surface

    def update_cover(self):
        """
            Update cover for album id id needed
        """
        if self._cover is None:
            return
        surface = Lp().art.get_album_artwork(
                            self._album,
                            ArtSize.BIG,
                            self._cover.get_scale_factor())
        self._cover.set_from_surface(surface)
        if surface.get_height() > surface.get_width():
            self._overlay_orientation = Gtk.Orientation.VERTICAL
        else:
            self._overlay_orientation = Gtk.Orientation.HORIZONTAL
        del surface

    def update_state(self):
        """
            Update widget state
        """
        if self._cover is None:
            return
        selected = self._album.id == Lp().player.current_track.album.id
        if selected != self._selected:
            if selected:
                self._cover.get_style_context().add_class(
                                                    'cover-frame-selected')
            else:
                self._cover.get_style_context().remove_class(
                                                    'cover-frame-selected')

    def update_playing_indicator(self):
        """
            Update playing indicator
        """
        pass

    def stop(self):
        """
            Stop populating
        """
        self._loading = Loading.STOP

    def get_id(self):
        """
            Return album id for widget
            @return album id as int
        """
        return self._album.id

    def get_title(self):

        """
            Return album title
            @return album title as str
        """
        return self._album.name

    def lock_overlay(self, lock):
        """
            Lock overlay
            @param lock as bool
        """
        self._lock_overlay = lock

    def show_overlay(self, set):
        """
            Set overlay
            @param set as bool
        """
        # Remove enter notify timeout
        if self._timeout_id is not None:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = None
        self._show_overlay_func(set)

#######################
# PRIVATE             #
#######################
    def _set_play_all_image(self):
        """
            Set play all image based on current shuffle status
        """
        if Lp().settings.get_enum('shuffle') == Shuffle.NONE:
            self._play_all_button.set_from_icon_name(
                                        'media-playlist-consecutive-symbolic',
                                        Gtk.IconSize.BUTTON)
        else:
            self._play_all_button.set_from_icon_name(
                                        'media-playlist-shuffle-symbolic',
                                        Gtk.IconSize.BUTTON)

    def _show_overlay_func(self, set):
        """
            Set overlay
            @param set as bool
        """
        if self._lock_overlay or\
           self._show_overlay == set or\
           (set is True and Lp().player.locked):
            return
        self._show_overlay = set
        if set:
            if self._play_button is not None:
                self._play_button.set_opacity(1)
                self._play_button.get_style_context().add_class(
                                                           self._rounded_class)
                self._play_button.show()
            if self._play_all_button is not None:
                self._play_all_button.set_opacity(1)
                self._play_all_button.get_style_context().add_class(
                                                           self._squared_class)
                self._set_play_all_image()
                self._play_all_button.show()
            if self._artwork_button is not None:
                self._artwork_button.set_opacity(1)
                self._artwork_button.get_style_context().add_class(
                                                           self._squared_class)
                self._artwork_button.show()
            if self._action_button is not None:
                self._show_append(not Lp().player.has_album(self._album))
                self._action_button.set_opacity(1)
                self._action_button.get_style_context().add_class(
                                                       self._squared_class)
                self._action_button.show()
        else:
            if self._play_button is not None:
                self._play_button.set_opacity(0)
                self._play_button.hide()
                self._play_button.get_style_context().remove_class(
                                                           self._rounded_class)
            if self._play_all_button is not None:
                self._play_all_button.set_opacity(0)
                self._play_all_button.hide()
                self._play_all_button.get_style_context().remove_class(
                                                           self._squared_class)
            if self._artwork_button is not None:
                self._artwork_button.hide()
                self._artwork_button.set_opacity(0)
                self._artwork_button.get_style_context().remove_class(
                                                           self._squared_class)
            if self._action_button is not None:
                self._action_button.hide()
                self._action_button.set_opacity(0)
                self._action_button.get_style_context().remove_class(
                                                           self._squared_class)

    def _show_append(self, append):
        """
            Show append button if append, else remove button
        """
        if append:
            self._action_button.set_from_icon_name('list-add-symbolic',
                                                   Gtk.IconSize.BUTTON)
            self._action_event.set_tooltip_text(_("Append"))
        else:
            self._action_button.set_from_icon_name('list-remove-symbolic',
                                                   Gtk.IconSize.BUTTON)
            self._action_event.set_tooltip_text(_("Remove"))

    def _on_destroy(self, widget):
        """
            Disconnect signal
            @param widget as Gtk.Widget
        """
        if self._scan_signal is not None:
            Lp().scanner.disconnect(self._scan_signal)

    def _on_album_update(self, scanner, album_id):
        """
            On album modified, disable it
            @param scanner as CollectionScanner
            @param album id as int
            @param deleted as bool
        """
        if self._cover is None or self._album.id != album_id:
            return
        self._widget.set_sensitive(False)

    def _on_eventbox_realize(self, eventbox):
        """
            Change cursor over eventbox
            @param eventbox as Gdk.Eventbox
        """
        window = eventbox.get_window()
        if window is not None:
            window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND1))

    def _on_pop_cover_closed(self, widget):
        """
            Remove selected style
            @param widget as Gtk.Popover
        """
        self._lock_overlay = False
        GLib.idle_add(self.show_overlay, False)

    def _on_enter_notify(self, widget, event):
        """
            Show overlay buttons after a timeout
            @param widget as Gtk.Widget
            @param event es Gdk.Event
        """
        self._cover.set_opacity(0.9)
        if self._timeout_id is None:
            self._timeout_id = GLib.timeout_add(250,
                                                self._on_enter_notify_timeout)

    def _on_enter_notify_timeout(self):
        """
            Show overlay buttons
        """
        self._timeout_id = None
        if not self._show_overlay:
            self._show_overlay_func(True)

    def _on_leave_notify(self, widget, event):
        """
            Hide overlay buttons
            @param widget as Gtk.Widget
            @param event es Gdk.Event
        """
        allocation = widget.get_allocation()
        if event.x <= 0 or\
           event.x >= allocation.width or\
           event.y <= 0 or\
           event.y >= allocation.height:
            self._cover.set_opacity(1)
            # Remove enter notify timeout
            if self._timeout_id is not None:
                GLib.source_remove(self._timeout_id)
                self._timeout_id = None
            if self._show_overlay:
                self._show_overlay_func(False)

    def _on_play_press_event(self, widget, event):
        """
            Play album
            @param: widget as Gtk.EventBox
            @param: event as Gdk.Event
        """
        Lp().player.play_album(self._album)
        self._show_append(False)
        return True

    def _on_play_all_press_event(self, widget, event):
        """
            Play album with context
            @param: widget as Gtk.EventBox
            @param: event as Gdk.Event
        """
        self._show_append(False)
        if Lp().player.is_party():
            Lp().player.set_party(False)
        track = Track(self._album.track_ids[0])
        Lp().player.load(track)
        Lp().player.set_albums(track.id, self._filter_ids,
                               self._album.genre_ids)
        return True

    def _on_artwork_press_event(self, widget, event):
        """
            Popover with album art downloaded from the web (in fact google :-/)
            @param: widget as Gtk.EventBox
            @param: event as Gdk.Event
        """
        popover = CoversPopover(self._album)
        popover.set_relative_to(widget)
        popover.connect('closed', self._on_pop_cover_closed)
        self._lock_overlay = True
        popover.show()
        return True

    def _on_action_press_event(self, widget, event):
        """
            Append album to current list if not present
            Remove it if present
            @param: widget as Gtk.EventBox
            @param: event as Gdk.Event
        """
        if Lp().player.has_album(self._album):
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
            self._show_append(True)
        else:
            if Lp().player.is_playing() and not Lp().player.get_albums():
                Lp().player.play_album(self._album)
            else:
                Lp().player.add_album(self._album)
            self._show_append(False)
        return True


class AlbumSimpleWidget(Gtk.FlowBoxChild, AlbumWidget):
    """
        Album widget showing cover, artist and title
    """

    def __init__(self, album_id, genre_ids, artist_ids):
        """
            Init simple album widget
            @param album id as int
            @param genre ids as [int]
            @param artist_ids as [int]
        """
        # We do not use Gtk.Builder for speed reasons
        Gtk.FlowBoxChild.__init__(self)
        self.set_size_request(ArtSize.BIG, ArtSize.BIG)
        self.get_style_context().add_class('loading')
        AlbumWidget.__init__(self, album_id, genre_ids)
        self._filter_ids = artist_ids

    def populate(self):
        """
            Populate widget content
        """
        self.get_style_context().remove_class('loading')
        self._rounded_class = "rounded-icon-small"
        self._widget = Gtk.EventBox()
        grid = Gtk.Grid()
        grid.set_orientation(Gtk.Orientation.VERTICAL)
        self._cover = Gtk.Image()
        self._cover.set_property('halign', Gtk.Align.CENTER)
        self._cover.get_style_context().add_class('cover-frame')
        self._title_label = Gtk.Label()
        self._title_label.set_ellipsize(Pango.EllipsizeMode.END)
        self._title_label.set_property('halign', Gtk.Align.CENTER)
        self._title_label.set_markup("<b>"+escape(self._album.name)+"</b>")
        self._artist_label = Gtk.Label()
        self._artist_label.set_ellipsize(Pango.EllipsizeMode.END)
        self._artist_label.set_property('halign', Gtk.Align.CENTER)
        self._artist_label.set_text(", ".join(self._album.artists))
        self._artist_label.get_style_context().add_class('dim-label')
        self._widget.set_property('has-tooltip', True)
        self._widget.connect('query-tooltip', self._on_query_tooltip)
        self._widget.add(grid)
        self._overlay = Gtk.Overlay.new()
        self._overlay.set_property('halign', Gtk.Align.CENTER)
        self._overlay.set_property('valign', Gtk.Align.CENTER)
        self._overlay_grid = Gtk.Grid()
        self._overlay_grid.set_column_spacing(6)
        self._overlay_grid.set_row_spacing(6)
        self._overlay_grid.set_margin_top(6)
        self._overlay_grid.set_margin_bottom(6)
        self._overlay_grid.set_margin_start(6)
        self._overlay_grid.set_margin_end(6)
        self._overlay.add(self._cover)
        self._overlay.add_overlay(self._overlay_grid)
        color = Gtk.Grid()
        color.set_property('halign', Gtk.Align.CENTER)
        color.set_property('valign', Gtk.Align.CENTER)
        color.get_style_context().add_class('white')
        color.add(self._overlay)
        grid.add(color)
        grid.add(self._title_label)
        grid.add(self._artist_label)
        self.add(self._widget)
        self.set_cover()
        self.update_state()
        self._widget.set_property('halign', Gtk.Align.CENTER)
        self._widget.set_property('valign', Gtk.Align.CENTER)
        self.show_all()
        self._widget.connect('enter-notify-event', self._on_enter_notify)
        self._widget.connect('leave-notify-event', self._on_leave_notify)

    def get_id(self):
        """
            Return album id
            @return int
        """
        return self._album.id

    def get_cover(self):
        """
            Get album cover
            @return cover as Gtk.Image
        """
        return self._cover

    def do_get_preferred_width(self):
        """
            Return preferred width
            @return (int, int)
        """
        # Padding: 3px, border: 1px + spacing
        width = ArtSize.BIG + 12
        return (width, width)

    def _show_overlay_func(self, set):
        """
            Set overlay
            @param set as bool
        """
        if self._lock_overlay or\
           self._show_overlay == set or\
           (set is True and Lp().player.locked):
            return
        if set:
            # Play button
            self._play_event = Gtk.EventBox()
            self._play_event.set_property('has-tooltip', True)
            self._play_event.set_tooltip_text(_("Play"))
            self._play_event.connect('realize', self._on_eventbox_realize)
            self._play_event.connect('button-press-event',
                                     self._on_play_press_event)
            self._play_button = Gtk.Image.new_from_icon_name(
                                               'media-playback-start-symbolic',
                                               Gtk.IconSize.BUTTON)
            self._play_button.set_opacity(0)
            # Play all button
            self._play_all_event = Gtk.EventBox()
            self._play_all_event.set_property('has-tooltip', True)
            self._play_all_event.set_tooltip_text(_("Play albums"))
            self._play_all_event.set_property('halign', Gtk.Align.END)
            self._play_all_event.connect('realize', self._on_eventbox_realize)
            self._play_all_event.connect('button-press-event',
                                         self._on_play_all_press_event)
            self._play_all_button = Gtk.Image.new()
            self._play_all_button.set_opacity(0)
            # Artwork button
            self._artwork_event = Gtk.EventBox()
            self._artwork_event.set_property('has-tooltip', True)
            self._artwork_event.set_tooltip_text(_("Change artwork"))
            self._artwork_event.set_property('halign', Gtk.Align.END)
            self._artwork_event.connect('realize', self._on_eventbox_realize)
            self._artwork_event.connect('button-press-event',
                                        self._on_artwork_press_event)
            self._artwork_button = Gtk.Image.new_from_icon_name(
                                               'image-x-generic-symbolic',
                                               Gtk.IconSize.BUTTON)
            self._artwork_button.set_opacity(0)
            # Action button
            self._action_event = Gtk.EventBox()
            self._action_event.set_property('has-tooltip', True)
            self._action_event.set_property('halign', Gtk.Align.END)
            self._action_event.connect('realize', self._on_eventbox_realize)
            self._action_event.connect('button-press-event',
                                       self._on_action_press_event)
            self._action_button = Gtk.Image.new()
            self._action_button.set_opacity(0)
            self._overlay_grid.set_orientation(self._overlay_orientation)
            if self._overlay_orientation == Gtk.Orientation.VERTICAL:
                self._play_event.set_hexpand(False)
                self._play_event.set_vexpand(True)
                self._play_event.set_property('halign', Gtk.Align.END)
                self._play_event.set_property('valign', Gtk.Align.START)
                self._overlay_grid.set_property('valign', Gtk.Align.FILL)
                self._overlay_grid.set_property('halign', Gtk.Align.END)
            else:
                self._play_event.set_hexpand(True)
                self._play_event.set_vexpand(False)
                self._play_event.set_property('halign', Gtk.Align.START)
                self._play_event.set_property('valign', Gtk.Align.END)
                self._overlay_grid.set_property('halign', Gtk.Align.FILL)
                self._overlay_grid.set_property('valign', Gtk.Align.END)
            self._play_event.add(self._play_button)
            self._play_all_event.add(self._play_all_button)
            self._artwork_event.add(self._artwork_button)
            self._action_event.add(self._action_button)
            self._overlay_grid.add(self._play_event)
            self._overlay_grid.add(self._play_all_event)
            self._overlay_grid.add(self._action_event)
            self._overlay_grid.add(self._artwork_event)
            self._overlay_grid.show_all()
            AlbumWidget._show_overlay_func(self, True)
        else:
            AlbumWidget._show_overlay_func(self, False)
            self._play_event.destroy()
            self._play_event = None
            self._play_button.destroy()
            self._play_button = None
            self._play_all_event.destroy()
            self._play_all_event = None
            self._play_all_button.destroy()
            self._play_all_button = None
            self._action_event.destroy()
            self._action_event = None
            self._action_button.destroy()
            self._action_button = None
            self._artwork_event.destroy()
            self._artwork_event = None
            self._artwork_button.destroy()
            self._artwork_button = None

#######################
# PRIVATE             #
#######################
    def _on_query_tooltip(self, eventbox, x, y, keyboard, tooltip):
        """
            Show tooltip if needed
            @param eventbox as Gtk.EventBox
            @param x as int
            @param y as int
            @param keyboard as bool
            @param tooltip as Gtk.Tooltip
        """
        eventbox.set_tooltip_text('')
        for widget in [self._title_label, self._artist_label]:
            layout = widget.get_layout()
            if layout.is_ellipsized():
                text = "<b>%s</b> - %s" % (
                                    escape(self._artist_label.get_text()),
                                    escape(self._title_label.get_text()))
                eventbox.set_tooltip_markup(text)
                break


class AlbumDetailedWidget(Gtk.Bin, AlbumWidget):
    """
        Widget with cover and tracks
    """
    __gsignals__ = {
        'populated': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self, album_id, genre_ids, artist_ids, show_cover):
        """
            Init detailed album widget
            @param album id as int
            @param genre ids as [int]
            @param artist ids as [int]
            @param lazy as LazyLoadingView
            @param show cover as bool
        """
        Gtk.Bin.__init__(self)
        AlbumWidget.__init__(self, album_id, genre_ids)
        self._album.set_artists(artist_ids)
        self._width = None
        # Cover + rating + spacing
        self._height = ArtSize.BIG + 26
        self._orientation = None
        self._child_height = TrackRow.get_best_height(self)
        # Header + separator + spacing + margin
        self._requested_height = self._child_height + 6
        # Discs to load, will be emptied
        self._discs = self._album.discs
        self._locked_widget_right = True
        self._filter_ids = artist_ids
        self.set_property('height-request', self._height)
        self.connect('size-allocate', self._on_size_allocate)
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/AlbumDetailedWidget.ui')
        self._widget = builder.get_object('widget')
        self._overlay = builder.get_object('overlay')
        self._play_button = builder.get_object('play-button')
        self._artwork_button = builder.get_object('artwork-button')
        self._action_button = builder.get_object('action-button')
        self._action_event = builder.get_object('action-event')

        builder.connect_signals(self)
        rating = RatingWidget(self._album)
        rating.show()

        artist_label = builder.get_object('artist')
        if show_cover:
            self._cover = builder.get_object('cover')
            builder.get_object('duration').set_hexpand(True)
            self._cover.get_style_context().add_class('cover-frame')
            self._coverbox = builder.get_object('coverbox')
            self._coverbox.show()
            # 6 for 2*3px (application.css)
            self._coverbox.set_property('width-request', ArtSize.BIG + 6)
            self._coverbox.add(rating)
            if Lp().window.get_view_width() < WindowSize.MEDIUM:
                self._coverbox.hide()
            if len(artist_ids) > 1:
                artist_label.set_text(", ".join(self._album.artists))
                artist_label.show()
        else:
            builder.get_object('header').attach(rating, 4, 0, 1, 1)
            rating.set_hexpand(True)
            rating.set_property('halign', Gtk.Align.END)
            rating.set_property('valign', Gtk.Align.CENTER)
            artist_label.set_text(", ".join(self._album.artists))
            artist_label.show()
            self._cover = None

        label = builder.get_object('duration')
        duration = Lp().albums.get_duration(album_id, genre_ids)
        hours = int(duration / 3600)
        mins = int(duration / 60)
        if hours > 0:
            mins -= hours * 60
            if mins > 0:
                label.set_text(_("%s h  %s m") % (hours, mins))
            else:
                label.set_text(_("%s h") % hours)
        else:
            label.set_text(_("%s m") % mins)

        self._box = Gtk.Grid()
        self._box.set_column_homogeneous(True)
        self._box.set_property('valign', Gtk.Align.START)
        self._box.show()
        builder.get_object('albuminfo').add(self._box)

        self._tracks_left = {}
        self._tracks_right = {}

        self.set_cover()
        self.update_state()

        builder.get_object('title').set_label(self._album.name)
        if self._album.year:
            year = builder.get_object('year')
            year.set_label(self._album.year)
            year.show()

        for disc in self._discs:
            self._add_disc_container(disc.number)
            self._set_disc_height(disc)

        self.add(self._widget)
        # We start transparent, we switch opaque at size allocation
        # This prevent artifacts
        self.set_opacity(0)

        self._menu = builder.get_object('menu')
        self._menu.connect('clicked', self._pop_menu)
        # TODO Remove this later
        if Gtk.get_minor_version() > 16:
            self._menu.show()
        else:
            self.connect('map', self._on_map)

    def update_playing_indicator(self):
        """
            Update playing indicator
        """
        for disc in self._album.discs:
            self._tracks_left[disc.number].update_playing(
                Lp().player.current_track.id)
            self._tracks_right[disc.number].update_playing(
                Lp().player.current_track.id)

    def populate(self):
        """
            Populate tracks
            @thread safe
        """
        if self._discs:
            disc = self._discs.pop(0)
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
        return len(self._discs) == 0

    def populate_list_left(self, tracks, disc, pos):
        """
            Populate left list, thread safe
            @param tracks as [Track]
            @param disc as Disc
            @param pos as int
        """
        GLib.idle_add(self._add_tracks,
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
        if self._orientation == Gtk.Orientation.VERTICAL and\
           self._locked_widget_right:
            GLib.timeout_add(100, self.populate_list_right, tracks, disc, pos)
        else:
            GLib.idle_add(self._add_tracks,
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
                    if child.get_id() == Lp().player.current_track.id:
                        return child.translate_coordinates(parent, 0, 0)[1]
        return None

    @property
    def requested_height(self):
        """
            Requested height
        """
        if self._requested_height < self._height:
            return self._height
        else:
            return self._requested_height

#######################
# PRIVATE             #
#######################
    def _set_disc_height(self, disc):
        """
            Set disc widget height
            @param disc as Disc
        """
        count_tracks = len(disc.tracks)
        mid_tracks = int(0.5 + count_tracks / 2)
        left_height = self._child_height * mid_tracks
        right_height = self._child_height * (count_tracks - mid_tracks)
        if left_height > right_height:
            self._requested_height += left_height
        else:
            self._requested_height += right_height
        self._tracks_left[disc.number].set_property('height-request',
                                                    left_height)
        self._tracks_right[disc.number].set_property('height-request',
                                                     right_height)

    def _add_disc_container(self, disc_number):
        """
            Add disc container to box
            @param disc_number as int
        """
        self._tracks_left[disc_number] = TracksWidget()
        self._tracks_right[disc_number] = TracksWidget()
        self._tracks_left[disc_number].connect('activated',
                                               self._on_activated)
        self._tracks_left[disc_number].connect('button-press-event',
                                               self._on_button_press_event)
        self._tracks_right[disc_number].connect('activated',
                                                self._on_activated)
        self._tracks_right[disc_number].connect('button-press-event',
                                                self._on_button_press_event)
        self._tracks_left[disc_number].show()
        self._tracks_right[disc_number].show()

    def _pop_menu(self, widget):
        """
            Popup menu for album
            @param widget as Gtk.Button
            @param album id as int
        """
        pop_menu = AlbumMenu(self._album)
        popover = Gtk.Popover.new_from_model(self._menu, pop_menu)
        popover.connect('closed', self._on_pop_menu_closed)
        self.get_style_context().add_class('album-menu-selected')
        popover.show()

    def _add_tracks(self, tracks, widget, disc_number, i):
        """
            Add tracks for to tracks widget
            @param tracks as [int]
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
                self.emit('populated')
            self._locked_widget_right = False
            return

        track = tracks.pop(0)
        if not Lp().settings.get_value('show-tag-tracknumber'):
            track_number = i
        else:
            track_number = track.number

        row = TrackRow(track.id, track_number)
        row.show()
        widget[disc_number].add(row)
        GLib.idle_add(self._add_tracks, tracks, widget, disc_number, i + 1)

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
            self._menu.show()

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
        if allocation.width < WindowSize.MEDIUM or (
                allocation.width < WindowSize.MONSTER and
                self._cover is not None):
            orientation = Gtk.Orientation.VERTICAL
        else:
            orientation = Gtk.Orientation.HORIZONTAL
        if orientation != self._orientation:
            self._orientation = orientation
            redraw = True

        if redraw:
            for child in self._box.get_children():
                self._box.remove(child)
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
                if show_label:
                    label = Gtk.Label()
                    disc_text = _("Disc %s") % disc.number
                    disc_names = self._album.disc_names(disc.number)
                    if disc_names:
                        disc_text += ": " + ", ".join(disc_names)
                    label.set_text(disc_text)
                    label.set_property('halign', Gtk.Align.START)
                    label.get_style_context().add_class('dim-label')
                    label.show()
                    self._box.attach(label, 0, idx, width, 1)
                    idx += 1
                GLib.idle_add(self._box.attach,
                              self._tracks_left[disc.number],
                              0, idx, 1, 1)
                if orientation == Gtk.Orientation.VERTICAL:
                    idx += 1
                GLib.idle_add(self._box.attach,
                              self._tracks_right[disc.number],
                              pos, idx, 1, 1)
                idx += 1
                GLib.idle_add(self.set_opacity, 1)
        if self._cover is not None:
            if allocation.width < WindowSize.MEDIUM:
                self._coverbox.hide()
            else:
                self._coverbox.show()

    def _on_pop_menu_closed(self, widget):
        """
            Remove selected style
            @param widget as Gtk.Popover
        """
        self.get_style_context().remove_class('album-menu-selected')

    def _on_activated(self, widget, track_id):
        """
            On track activation, play track
            @param widget as TracksWidget
            @param track id as int
        """
        # Add to queue by default
        if Lp().player.locked:
            if track_id in Lp().player.get_queue():
                Lp().player.del_from_queue(track_id)
            else:
                Lp().player.append_to_queue(track_id)
        # Play track with no album, force repeat on track
        elif self._button_state & Gdk.ModifierType.SHIFT_MASK:
            Lp().player.clear_albums()
            Lp().player.load(Track(track_id))
        else:
            # Do not modify album list if in party mode
            if not Lp().player.is_party():
                # If in artist view, reset album list
                if self._filter_ids:
                    Lp().player.set_albums(track_id,
                                           self._filter_ids,
                                           self._album.genre_ids)
                # Else, add album if missing
                elif not Lp().player.has_album(self._album):
                    Lp().player.add_album(self._album)
            Lp().player.load(Track(track_id))
            if self._button_state & Gdk.ModifierType.CONTROL_MASK:
                Lp().player.set_next_context(NextContext.STOP_TRACK)

    def _on_button_press_event(self, widget, event):
        """
            Keep track of mask
            @param widget as TrackWidget
            @param event as Gdk.Event
        """
        self._button_state = event.get_state()
