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

from gi.repository import Gtk, GLib, GObject, Gdk, Pango

from cgi import escape
from gettext import gettext as _

from lollypop.define import Lp, Type, ArtSize, NextContext, WindowSize, Shuffle
from lollypop.widgets_track import TracksWidget
from lollypop.objects import Track
from lollypop.widgets_rating import RatingWidget
from lollypop.pop_menu import AlbumMenu
from lollypop.pop_covers import CoversPopover
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
        self._selected = None
        self._stop = False
        self._cover = None
        self._widget = None
        self._popover = False
        self._limit_to_current = False
        self._play_all_button = None
        self._squared_class = "squared-icon"
        self._rounded_class = "rounded-icon"
        self._scan_signal = Lp().scanner.connect('album-update',
                                                 self._on_album_update)

    def set_cover(self):
        """
            Set cover for album if state changed
        """
        if self._widget is None:
            return
        surface = Lp().art.get_album_artwork(
                            self._album,
                            ArtSize.BIG * self._cover.get_scale_factor())
        self._cover.set_from_surface(surface)
        self._cover.set_size_request(100, 100)
        if surface.get_height() > surface.get_width():
            self._set_overlay_orientation(Gtk.Orientation.VERTICAL)
        else:
            self._set_overlay_orientation(Gtk.Orientation.HORIZONTAL)
        del surface

    def update_cover(self, album_id):
        """
            Update cover for album id id needed
            @param album id as int
        """
        if self._widget is None:
            return
        surface = Lp().art.get_album_artwork(
                            self._album,
                            ArtSize.BIG * self._cover.get_scale_factor())
        self._cover.set_from_surface(surface)
        if surface.get_height() > surface.get_width():
            self._set_overlay_orientation(Gtk.Orientation.VERTICAL)
        else:
            self._set_overlay_orientation(Gtk.Orientation.HORIZONTAL)
        del surface

    def responsive_design(self):
        """
            Update the view based on current size
        """
        pass

    def update_state(self):
        """
            Update widget state
        """
        if self._widget is None:
            return
        selected = self._album.id == Lp().player.current_track.album.id
        if selected != self._selected:
            if selected:
                self._color.get_style_context().add_class(
                                                    'cover-frame-selected')
            else:
                self._color.get_style_context().remove_class(
                                                    'cover-frame-selected')

    def update_playing_indicator(self):
        """
            Update playing indicator
        """
        pass

    def update_overlay(self):
        """
            Update overlay icon
        """
        if self._widget is None or self._popover:
            return
        self._on_pop_cover_closed(self)

    def stop(self):
        """
            Stop populating
        """
        self._stop = True

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

#######################
# PRIVATE             #
#######################
    def _set_overlay_orientation(self, orientation):
        """
            Set overlay orientation
            @param orientation as Gtk.Orientation
        """
        pass

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

    def _on_album_update(self, scanner, album_id, deleted):
        """
            On album modified, disable it
            @param scanner as CollectionScanner
            @param album id as int
            @param deleted as bool
        """
        if self._widget is None or self._album.id != album_id:
            return
        if deleted:
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
        self._popover = False
        if self._play_button.get_opacity() == 1:
            self._play_button.set_opacity(0)
            self._play_button.get_style_context().remove_class(
                                                           self._rounded_class)
            if self._play_all_button is not None:
                self._play_all_button.set_opacity(0)
                self._play_all_button.get_style_context().remove_class(
                                                           self._rounded_class)
            self._artwork_button.set_opacity(0)
            self._artwork_button.get_style_context().remove_class(
                                                           self._squared_class)
            self._action_button.set_opacity(0)
            self._action_button.get_style_context().remove_class(
                                                           self._squared_class)

    def _on_enter_notify(self, widget, event):
        """
            Show special buttons
            @param widget as Gtk.Widget
            @param event es Gdk.Event
        """
        if self._play_button.get_opacity() == 0:
            self._cover.get_style_context().add_class('hovereffect')
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
            self._artwork_button.set_opacity(1)
            self._artwork_button.get_style_context().add_class(
                                                           self._squared_class)
            self._artwork_button.show()
            self._show_append(not Lp().player.is_album_present(self._album))
            self._action_button.set_opacity(1)
            self._action_button.get_style_context().add_class(
                                                       self._squared_class)
            self._action_button.show()

    def _on_leave_notify(self, widget, event):
        """
            Hide special buttons
            @param widget as Gtk.Widget
            @param event es Gdk.Event
        """
        allocation = widget.get_allocation()
        if event.x < 5 or\
           event.x > allocation.width - 5 or\
           event.y < 5 or\
           event.y > allocation.height - 5:
            self._cover.get_style_context().remove_class('hovereffect')
            self._play_button.set_opacity(0)
            self._play_button.hide()
            self._play_button.get_style_context().remove_class(
                                                           self._rounded_class)
            if self._play_all_button is not None:
                self._play_all_button.set_opacity(0)
                self._play_all_button.hide()
                self._play_all_button.get_style_context().remove_class(
                                                           self._squared_class)
            self._artwork_button.hide()
            self._artwork_button.set_opacity(0)
            self._artwork_button.get_style_context().remove_class(
                                                           self._squared_class)
            self._action_button.hide()
            self._action_button.set_opacity(0)
            self._action_button.get_style_context().remove_class(
                                                           self._squared_class)

    def _on_play_press_event(self, widget, event):
        """
            Play album
            @param: widget as Gtk.EventBox
            @param: event as Gdk.Event
        """
        self._limit_to_current = True
        Lp().player.play_album(self._album)
        self._show_append(False)
        return True

    def _on_artwork_press_event(self, widget, event):
        """
            Popover with album art downloaded from the web (in fact google :-/)
            @param: widget as Gtk.EventBox
            @param: event as Gdk.Event
        """
        self._popover = True
        popover = CoversPopover(self._album.artist_id, self._album.id)
        popover.set_relative_to(widget)
        popover.populate()
        popover.connect('closed', self._on_pop_cover_closed)
        popover.show()
        return True

    def _on_action_press_event(self, widget, event):
        """
            Append album to current list if not present
            Remove it if present
            @param: widget as Gtk.EventBox
            @param: event as Gdk.Event
        """
        albums = Lp().player.get_albums()
        empty = len(albums) == 0
        if Lp().player.is_album_present(self._album):
            Lp().player.remove_album(self._album)
            self._show_append(True)
        else:
            if empty and Lp().player.current_track.id is None:
                Lp().player.load(self._album.tracks[0], False)
            Lp().player.add_album(self._album)
            self._show_append(False)
        return True


class AlbumSimpleWidget(Gtk.Frame, AlbumWidget):
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
        Gtk.Frame.__init__(self)
        self._artist_ids = artist_ids
        self.set_shadow_type(Gtk.ShadowType.NONE)
        self.get_style_context().add_class('loading')
        AlbumWidget.__init__(self, album_id, genre_ids)

    def init_widget(self):
        """
            Init widget content
        """
        self.get_style_context().remove_class('loading')
        self._rounded_class = "rounded-icon-small"
        self._widget = Gtk.EventBox()
        grid = Gtk.Grid()
        grid.set_orientation(Gtk.Orientation.VERTICAL)
        frame = Gtk.Frame()
        frame.set_property('halign', Gtk.Align.CENTER)
        frame.get_style_context().add_class('cover-frame')
        self._color = Gtk.Frame()
        self._color.get_style_context().add_class('cover-frame-border')
        self._cover = Gtk.Image()
        self._title_label = Gtk.Label()
        self._title_label.set_ellipsize(Pango.EllipsizeMode.END)
        self._title_label.set_property('halign', Gtk.Align.CENTER)
        self._title_label.set_markup("<b>"+escape(self._album.name)+"</b>")
        self._artist_label = Gtk.Label()
        self._artist_label.set_ellipsize(Pango.EllipsizeMode.END)
        self._artist_label.set_property('halign', Gtk.Align.CENTER)
        self._artist_label.set_text(self._album.artist_name)
        self._artist_label.get_style_context().add_class('dim-label')
        self._widget.add(grid)
        grid.add(frame)
        grid.add(self._title_label)
        grid.add(self._artist_label)
        frame.add(self._color)
        overlay = Gtk.Overlay.new()
        overlay.get_style_context().add_class('white')
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
        self._overlay_grid = Gtk.Grid()
        self._overlay_grid.set_column_spacing(5)
        self._overlay_grid.set_row_spacing(5)
        self._overlay_grid.set_property('margin-bottom', 2)
        self._overlay_grid.set_property('margin-start', 2)
        self._overlay_grid.set_property('margin-end', 2)
        overlay.add(self._cover)
        overlay.add_overlay(self._overlay_grid)
        self._color.add(overlay)
        self.add(self._widget)
        self.set_cover()
        self.update_state()
        self._widget.set_property('halign', Gtk.Align.CENTER)
        self._widget.set_property('valign', Gtk.Align.CENTER)
        self.show_all()
        self._play_event.add(self._play_button)
        self._play_all_event.add(self._play_all_button)
        self._artwork_event.add(self._artwork_button)
        self._action_event.add(self._action_button)
        self._widget.connect('enter-notify-event', self._on_enter_notify)
        self._widget.connect('leave-notify-event', self._on_leave_notify)

    def get_id(self):
        """
            Return album id
            @return int
        """
        return self._album.id

    def do_get_preferred_width(self):
        """
            Return preferred width
            @return (int, int)
        """
        if self._cover is not None:
            widths = self._cover.get_preferred_width()
            return (widths[0] + 8, widths[1] + 8)
        else:
            return (0, 0)

#######################
# PRIVATE             #
#######################
    def _set_overlay_orientation(self, orientation):
        """
            Set overlay orientation
            @param orientation as Gtk.Orientation
        """
        for child in self._overlay_grid.get_children():
            self._overlay_grid.remove(child)

        self._overlay_grid.set_orientation(orientation)
        if orientation == Gtk.Orientation.VERTICAL:
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
        self._overlay_grid.add(self._play_event)
        self._overlay_grid.add(self._play_all_event)
        self._overlay_grid.add(self._action_event)
        self._overlay_grid.add(self._artwork_event)

    def _on_play_all_press_event(self, widget, event):
        """
            Play album with context
            @param: widget as Gtk.EventBox
            @param: event as Gdk.Event
        """
        self._show_append(False)
        Lp().player.set_party(False)
        track = Track(self._album.tracks_ids[0])
        Lp().player.load(track)
        Lp().player.set_albums(track.id, self._artist_ids,
                               self._album.genre_ids)
        return True

    def _on_query_tooltip(self, widget, x, y, keyboard, tooltip):
        """
            Show tooltip if needed
            @param widget as Gtk.Widget
            @param x as int
            @param y as int
            @param keyboard as bool
            @param tooltip as Gtk.Tooltip
        """
        layout_title = self._title_label.get_layout()
        layout_artist = self._artist_label.get_layout()
        if layout_title.is_ellipsized() or layout_artist.is_ellipsized():
            artist = escape(self._artist_label.get_text())
            title = escape(self._title_label.get_text())
            self.set_tooltip_markup("<b>%s</b>\n%s" % (artist, title))
        else:
            self.set_tooltip_text('')


class AlbumDetailedWidget(Gtk.Bin, AlbumWidget):
    """
        Widget with cover and tracks
    """

    __gsignals__ = {
        'finished': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self, album_id, genre_ids, artist_ids,
                 size_group, update_albums=True):
        """
            Init detailed album widget
            @param album id as int
            @param genre ids as [int]
            @param artist ids as [int]
            @param size group as Gtk.SizeGroup
            @param update albums as bool: update albums on play
        """
        Gtk.Bin.__init__(self)
        AlbumWidget.__init__(self, album_id, genre_ids)
        self._artist_ids = artist_ids
        self._limit_to_current = not update_albums
        self.set_property('height-request', ArtSize.BIG)
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/%s.ui' %
                                  type(self).__name__)
        self._widget = builder.get_object('widget')
        self._play_button = builder.get_object('play-button')
        self._play_all_button = builder.get_object('playall-button')
        self._artwork_button = builder.get_object('artwork-button')
        self._action_button = builder.get_object('action-button')
        self._action_event = builder.get_object('action-event')
        builder.connect_signals(self)

        rating = RatingWidget(self._album)
        rating.show()
        self._coverbox = builder.get_object('coverbox')
        self._coverbox.add(rating)
        if Lp().window.get_view_width() < WindowSize.MEDIUM:
            self._coverbox.hide()

        self._artist_label = builder.get_object('artist')
        if len(artist_ids) > 1:
            self._artist_label.set_text(self._album.artist_name)
            self._artist_label.show()
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
        self._box = Gtk.FlowBox()
        self._box.set_selection_mode(Gtk.SelectionMode.NONE)
        self._box.set_hexpand(True)
        self._box.show()
        builder.get_object('albuminfos').add(self._box)
        self._discs = self._album.discs
        self._tracks_left = {}
        self._tracks_right = {}
        show_label = len(self._discs) > 1
        for disc in self._discs:
            index = disc.number
            if show_label:
                label = Gtk.Label()
                label.set_text(_("Disc %s") % index)
                label.set_property('halign', Gtk.Align.START)
                label.get_style_context().add_class('dim-label')
                label.show()
                self._box.insert(label, -1)
                sep = Gtk.Separator()
                sep.set_opacity(0.0)
                sep.show()
                self._box.insert(sep, -1)
            self._tracks_left[index] = TracksWidget(True)
            self._tracks_right[index] = TracksWidget(True)
            self._box.insert(self._tracks_left[index], -1)
            self._box.insert(self._tracks_right[index], -1)
            size_group.add_widget(self._tracks_left[index])
            size_group.add_widget(self._tracks_right[index])

            self._tracks_left[index].connect('activated',
                                             self._on_activated)
            self._tracks_left[index].connect('button-press-event',
                                             self._on_button_press_event)
            self._tracks_right[index].connect('activated', self._on_activated)
            self._tracks_right[index].connect('button-press-event',
                                              self._on_button_press_event)

            self._tracks_left[index].show()
            self._tracks_right[index].show()

        self._cover = builder.get_object('cover')
        self._color = builder.get_object('color')
        self.responsive_design()
        self.set_cover()
        self.update_state()

        builder.get_object('title').set_label(self._album.name)
        if self._album.year:
            year = builder.get_object('year')
            year.set_label(self._album.year)
            year.show()

        self.add(self._widget)

        self._menu = builder.get_object('menu')
        self._menu.connect('clicked', self._pop_menu)
        self._menu.show()

    def disable_play_all(self):
        """
            Disable play all albums button
        """
        self._play_all_button = None

    def responsive_design(self):
        """
            Update the view based on current size
        """
        width = Lp().window.get_view_width()
        if width < WindowSize.MONSTER:
            self._box.set_min_children_per_line(1)
            self._box.set_max_children_per_line(1)
        else:
            self._box.set_min_children_per_line(2)
            self._box.set_max_children_per_line(2)
        if width < WindowSize.MEDIUM:
            self._coverbox.hide()
        else:
            self._coverbox.show()

    def update_playing_indicator(self):
        """
            Update playing indicator
        """
        for disc in self._discs:
            self._tracks_left[disc.number].update_playing(
                Lp().player.current_track.id)
            self._tracks_right[disc.number].update_playing(
                Lp().player.current_track.id)

    def populate(self):
        """
            Populate tracks
            @thread safe
        """
        self._stop = False
        for disc in self._discs:
            mid_tracks = int(0.5 + len(disc.tracks) / 2)
            self.populate_list_left(disc.tracks[:mid_tracks],
                                    disc,
                                    1)
            self.populate_list_right(disc.tracks[mid_tracks:],
                                     disc,
                                     mid_tracks + 1)

    def populate_list_left(self, tracks, disc, pos):
        """
            Populate left list, thread safe
            @param tracks as [Track]
            @param disc as Disc
            @param pos as int
        """
        GLib.idle_add(self._add_tracks,
                      tracks,
                      self._tracks_left[disc.number],
                      pos)

    def populate_list_right(self, tracks, disc, pos):
        """
            Populate right list, thread safe
            @param tracks as [Track]
            @param disc as Disc
            @param pos as int
        """
        GLib.idle_add(self._add_tracks,
                      tracks,
                      self._tracks_right[disc.number],
                      pos)

#######################
# PRIVATE             #
#######################
    def _pop_menu(self, widget):
        """
            Popup menu for album
            @param widget as Gtk.Button
            @param album id as int
        """
        pop_menu = AlbumMenu(self._album.id, self._album.genre_id)
        popover = Gtk.Popover.new_from_model(self._menu, pop_menu)
        popover.connect('closed', self._on_pop_menu_closed)
        self.get_style_context().add_class('album-menu-selected')
        popover.show()

    def _add_tracks(self, tracks, widget, i):
        """
            Add tracks for to tracks widget
            @param tracks as [(track_id, title, length, [artist ids])]
            @param widget as TracksWidget
            @param i as int
        """
        if not tracks or self._stop:
            self._stop = False
            # Emit finished signal if we are on the last disc for
            # the right tracks widget
            if widget == self._tracks_right[self._discs[-1].number]:
                self.emit('finished')
            return

        track = tracks.pop(0)

        # If we are listening to a compilation, prepend artist name
        title = escape(track.name)
        if self._album.artist_id == Type.COMPILATIONS or\
           len(track.artist_ids) > 1 or\
           self._album.artist_id not in track.artist_ids:
            if track.artist_names != self._album.artist_name:
                title = "<b>%s</b>\n%s" % (escape(track.artist_names),
                                           title)

        if not Lp().settings.get_value('show-tag-tracknumber'):
            track_number = i
        else:
            track_number = track.number

        widget.add_track(track.id,
                         track_number,
                         title,
                         track.duration)

        GLib.idle_add(self._add_tracks, tracks, widget, i + 1)

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
        # Play track with no album, force repeat on track
        if self._button_state & Gdk.ModifierType.SHIFT_MASK:
            Lp().player.clear_albums()
            Lp().player.load(Track(track_id))
        else:
            if not Lp().player.is_party() and\
               not self._limit_to_current and\
               not Lp().player.is_album_present(self._album):
                Lp().player.set_albums(track_id,
                                       self._artist_ids,
                                       self._album.genre_ids)
            Lp().player.load(Track(track_id))
            if self._button_state & Gdk.ModifierType.CONTROL_MASK:
                Lp().player.context.next = NextContext.STOP_TRACK

    def _on_play_all_press_event(self, widget, event):
        """
            Play album with context
            @param: widget as Gtk.EventBox
            @param: event as Gdk.Event
        """
        self._show_append(False)
        Lp().player.set_party(False)
        track = Track(self._album.tracks_ids[0])
        Lp().player.load(track)
        Lp().player.set_albums(track.id, self._artist_ids,
                               self._album.genre_ids)
        return True

    def _on_button_press_event(self, widget, event):
        """
            Keep track of mask
            @param widget as TrackWidget
            @param event as Gdk.Event
        """
        self._button_state = event.get_state()
