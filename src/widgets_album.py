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

from gi.repository import Gtk, GLib, Gdk
from cgi import escape
from gettext import gettext as _

from lollypop.define import Objects, Type, ArtSize, NextContext
from lollypop.widgets_track import TracksWidget
from lollypop.track import Track
from lollypop.popmenu import PopAlbumMenu
from lollypop.pop_album_covers import PopAlbumCovers
from lollypop.utils import translate_artist_name


# Base class for album widgets
class AlbumWidget(Gtk.Bin):
    def __init__(self, album_id):
        Gtk.Bin.__init__(self)
        self._album_id = album_id
        self._selected = None
        self._stop = False
        self._cover = None

    """
        Set cover for album if state changed
        @param force as bool
    """
    def set_cover(self, force=False):
        selected = self._album_id==Objects.player.current_track.album_id
        if self._cover and (selected != self._selected or force):
            self._selected = selected
            pixbuf = Objects.art.get(self._album_id,
                                     ArtSize.BIG,
                                     selected)
            self._cover.set_from_pixbuf(pixbuf)
            del pixbuf

    """
        Update cover for album id id needed
        @param album id as int
    """
    def update_cover(self, album_id):
        if self._cover and self._album_id == album_id:
            self._selected = self._album_id==Objects.player.current_track.album_id
            pixbuf = Objects.art.get(self._album_id,
                                     ArtSize.BIG,
                                     self._selected)
            self._cover.set_from_pixbuf(pixbuf)
            del pixbuf

    """
        Update playing indicator
    """
    def update_playing_indicator(self):
        pass

    """
        Stop populating
    """
    def stop(self):
        self._stop = True

#######################
# PRIVATE             #
#######################
    """
        Add hover style
        @param widget as Gtk.Widget
        @param event es Gdk.Event
    """
    def _on_enter_notify(self, widget, event):
        self.get_style_context().add_class('hovereffect')

    """
        Remove hover style
        @param widget as Gtk.Widget
        @param event es Gdk.Event
    """
    def _on_leave_notify(self, widget, event):
        self.get_style_context().remove_class('hovereffect')


# Album widget is a pixbuf with two labels: album name and artist name
class AlbumSimpleWidget(AlbumWidget):
    """
        Init album widget ui with an vertical grid:
            - Album cover
            - Album name
            - Artist name
    """
    def __init__(self, album_id):
        AlbumWidget.__init__(self, album_id)

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/AlbumSimpleWidget.ui')
        builder.connect_signals(self)
        widget = builder.get_object('widget')
        self._cover = builder.get_object('cover')
        widget.set_property('has-tooltip', True)
        album_name = Objects.albums.get_name(album_id)
        self._title_label = builder.get_object('title')
        self._title_label.set_text(album_name)
        artist_name = Objects.albums.get_artist_name(album_id)
        artist_name = translate_artist_name(artist_name)
        self._artist_label = builder.get_object('artist')
        self._artist_label.set_text(artist_name)
        self.add(widget)
        self.set_cover()
        self.set_property('halign', Gtk.Align.START)
        # Set minimum width
        self.set_property('width-request', ArtSize.BIG+ArtSize.BORDER*2)

    """
        Set maximum width
    """
    def do_get_preferred_width(self):
        return (ArtSize.BIG+ArtSize.BORDER*2, ArtSize.BIG+ArtSize.BORDER*2)

    """
        Return album id for widget
        @return album id as int
    """
    def get_id(self):
        return self._album_id

#######################
# PRIVATE             #
#######################
    """
        Show tooltip if needed
        @param widget as Gtk.Widget
        @param x as int
        @param y as int
        @param keyboard as bool
        @param tooltip as Gtk.Tooltip
    """
    def _on_query_tooltip(self, widget, x, y, keyboard, tooltip):
        layout_title = self._title_label.get_layout()
        layout_artist = self._artist_label.get_layout()
        if layout_title.is_ellipsized() or layout_artist.is_ellipsized():
            artist = escape(self._artist_label.get_text())
            title = escape(self._title_label.get_text())
            self.set_tooltip_markup("<b>%s</b>\n%s" % (artist, title))
        else:
            self.set_tooltip_text('')


# Album detailed Widget is a pixbuf with album name and tracks list
class AlbumDetailedWidget(AlbumWidget):
    """
        Init album widget songs ui with a complex grid:
            - Album cover
            - Album name
            - Albums tracks aligned on two columns
        if cover_add True, let user change album cover
        @param album id as int
        @param genre id as int
        @param parent width as int
        @param show_menu as bool if menu need to be displayed
        @param scrolled as bool
        @param size group as Gtk.SizeGroup
    """
    def __init__(self, album_id, genre_id, show_menu, scrolled, size_group):
        AlbumWidget.__init__(self, album_id)

        self._artist_id = Objects.albums.get_artist_id(album_id)
        self._album_id = album_id
        self._genre_id = genre_id

        builder = Gtk.Builder()
        if scrolled:
            builder.add_from_resource(
                    '/org/gnome/Lollypop/AlbumContextWidget.ui')
        else:
            builder.add_from_resource(
                    '/org/gnome/Lollypop/AlbumDetailedWidget.ui')
        builder.connect_signals(self)

        self._stars = []
        self._stars.append(builder.get_object('star0'))
        self._stars.append(builder.get_object('star1'))
        self._stars.append(builder.get_object('star2'))
        self._stars.append(builder.get_object('star3'))
        self._stars.append(builder.get_object('star4'))
        self._on_leave_notify(None, None)

        grid = builder.get_object('tracks')
        self._discs = Objects.albums.get_discs(album_id, genre_id)
        self._tracks_left = {}
        self._tracks_right = {}
        show_label = len(self._discs) > 1
        i = 0
        for disc in self._discs:
            if show_label:
                label = Gtk.Label()
                label.set_text(_("Disc %s") % disc)
                label.set_property('halign', Gtk.Align.START)
                label.get_style_context().add_class('dim-label')
                if i:
                    label.set_property('margin-top', 30)
                label.show()
                grid.attach(label, 0, i, 2, 1)
                i += 1
                sep = Gtk.Separator()
                sep.show()
                grid.attach(sep, 0, i ,2 ,1)
                i += 1
            self._tracks_left[disc] = TracksWidget(show_menu)
            self._tracks_right[disc] = TracksWidget(show_menu)
            grid.attach(self._tracks_left[disc], 0, i, 1, 1)
            grid.attach(self._tracks_right[disc], 1, i, 1, 1)
            size_group.add_widget(self._tracks_left[disc])
            size_group.add_widget(self._tracks_right[disc])

            self._tracks_left[disc].connect('activated', self._on_activated)
            self._tracks_left[disc].connect('button-press-event',
                                         self._on_button_press_event)
            self._tracks_right[disc].connect('activated', self._on_activated)
            self._tracks_right[disc].connect('button-press-event',
                                     self._on_button_press_event)
       
            self._tracks_left[disc].show()
            self._tracks_right[disc].show()
            i += 1

        self._cover = builder.get_object('cover')
        self.set_cover()

        builder.get_object('title').set_label(
                                            Objects.albums.get_name(album_id))
        builder.get_object('year').set_label(
                                            Objects.albums.get_year(album_id))
        self.add(builder.get_object('AlbumDetailedWidget'))

        if show_menu:
            self._menu = builder.get_object('menu')
            self._eventbox = builder.get_object('eventbox')
            self._eventbox.connect('realize', self._on_eventbox_realize)
            self._eventbox.connect("button-press-event",
                                   self._show_web_art)
            self._menu.connect('clicked',
                               self._pop_menu)
            self._menu.show()
        else:
            self._eventbox = None

    """
        Update playing indicator
    """
    def update_playing_indicator(self):
        for disc in self._discs:
            self._tracks_left[disc].update_playing(Objects.player.current_track.id)
            self._tracks_right[disc].update_playing(Objects.player.current_track.id)

    """
        Return album id for widget
        @return album id as int
    """
    def get_id(self):
        return self._album_id

    """
        Populate tracks
        @thread safe
    """
    def populate(self):
        self._stop = False
        sql = Objects.db.get_cursor()
        for disc in self._discs:
            mid_tracks = int(0.5+Objects.albums.get_count_for_disc(
                                                          self._album_id,
                                                          self._genre_id,
                                                          disc,
                                                          sql)/2)
            tracks = Objects.albums.get_tracks_infos(self._album_id,
                                                     self._genre_id,
                                                     disc,
                                                     sql)
            self.populate_list_left(tracks[:mid_tracks],
                                    disc,
                                    1)
            self.populate_list_right(tracks[mid_tracks:],
                                     disc,
                                     mid_tracks + 1)

    """
        Populate left list, thread safe
        @param track's ids as array of int
        @param track position as int
    """
    def populate_list_left(self, tracks, disc,pos):
        GLib.idle_add(self._add_tracks,
                      tracks,
                      self._tracks_left[disc],
                      pos)

    """
        Populate right list, thread safe
        @param track's ids as array of int
        @param track position as int
    """
    def populate_list_right(self, tracks, disc, pos):
        GLib.idle_add(self._add_tracks,
                      tracks,
                      self._tracks_right[disc],
                      pos)

#######################
# PRIVATE             #
#######################
    """
        Popup menu for album
        @param widget as Gtk.Button
        @param album id as int
    """
    def _pop_menu(self, widget):
        pop_menu = PopAlbumMenu(self._album_id, self._genre_id)
        popover = Gtk.Popover.new_from_model(self._menu, pop_menu)
        popover.connect('closed', self._on_closed)
        self.get_style_context().add_class('album-menu-selected')
        popover.show()

    """
        Remove selected style
        @param widget as Gtk.Popover
    """
    def _on_closed(self, widget):
        self.get_style_context().remove_class('album-menu-selected')

    """
        Add tracks for to tracks widget
        @param tracks as [(track_id, title, length, [artist ids])]
        @param widget as TracksWidget
        @param i as int
    """
    def _add_tracks(self, tracks, widget, i):
        if not tracks or self._stop:
            self._stop = False
            return

        track = tracks.pop(0)
        track_id = track[0]
        title = escape(track[1])
        length = track[2]
        tracknumber = track[3]
        artist_ids = track[4]

        # If we are listening to a compilation, prepend artist name
        if self._artist_id == Type.COMPILATIONS or\
           len(artist_ids) > 1 or\
           self._artist_id not in artist_ids:
            artist_name = ""
            for artist_id in artist_ids:
                artist_name += translate_artist_name(
                                Objects.artists.get_name(artist_id)) + ", "
            title = "<b>%s</b>\n%s" % (escape(artist_name[:-2]),
                                       title)

        # Get track position in queue
        pos = None
        if Objects.player.is_in_queue(track_id):
            pos = Objects.player.get_track_position(track_id)

        if Objects.settings.get_value('show-tag-tracknumber'):
            widget.add_track(track_id,
                             tracknumber,
                             title,
                             length,
                             pos)
        else:
            widget.add_track(track_id,
                             i,
                             title,
                             length,
                             pos)
        GLib.idle_add(self._add_tracks, tracks, widget, i+1)

    """
        On track activation, play track
        @param widget as TracksWidget
        @param track id as int
    """
    def _on_activated(self, widget, track_id):
        Objects.player.context.next = NextContext.NONE
        if not Objects.player.is_party():
            Objects.player.set_albums(track_id,
                                      self._artist_id,
                                      self._genre_id) 
        Objects.player.load(Track(track_id))
        if self._button_state&Gdk.ModifierType.CONTROL_MASK:
            Objects.player.context.next = NextContext.STOP_TRACK

    """
        Keep track of mask
        @param widget as TrackWidget
        @param event as Gdk.Event
    """
    def _on_button_press_event(self, widget, event):
        self._button_state = event.get_state()

    """
        Change cursor over eventbox
        @param eventbox as Gdk.Eventbox
    """
    def _on_eventbox_realize(self, eventbox):
        eventbox.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.PENCIL))

    """
        Popover with album art downloaded from the web (in fact google :-/)
        @param: widget as eventbox
        @param: data as unused
    """
    def _show_web_art(self, widget, data):
        popover = PopAlbumCovers(self._artist_id, self._album_id)
        popover.set_relative_to(widget)
        popover.populate()
        popover.show()

    """
        On enter notify, change star opacity
        @param widget as Gtk.EventBox
        @param event as Gdk.Event
    """
    def _on_enter_notify(self, widget, event):
        event_star = widget.get_children()[0]
        # First star is hidden (used to clear score)
        if event_star.get_property("opacity") == 0.0:
            found = True
        else:
            found = False
        for star in self._stars:
            if found:
                star.set_property("opacity", 0.2)
            else:
                star.set_property("opacity", 1.0)
            if star == event_star:
                found = True

    """
        On leave notify, change star opacity
        @param widget as Gtk.EventBox (can be None)
        @param event as Gdk.Event (can be None)
    """
    def _on_leave_notify(self, widget, event):
        avg_popularity = Objects.albums.get_avg_popularity()
        if avg_popularity > 0:
            popularity = Objects.albums.get_popularity(self._album_id)
            stars = popularity*5/avg_popularity+0.5
            if stars < 1:
                for i in range(5):
                    self._stars[i].set_property("opacity", 0.2)
            else:
                if stars >= 1:
                    self._stars[0].set_property("opacity", 1.0)
                else:
                    self._stars[0].set_property("opacity", 0.2)
                if stars >= 2:
                    self._stars[1].set_property("opacity", 1.0)
                else:
                    self._stars[1].set_property("opacity", 0.2)
                if stars >= 3:
                    self._stars[2].set_property("opacity", 1.0)
                else:
                    self._stars[2].set_property("opacity", 0.2)
                if stars >= 4:
                    self._stars[3].set_property("opacity", 1.0)
                else:
                    self._stars[3].set_property("opacity", 0.2)
                if stars >= 4.75:
                    self._stars[4].set_property("opacity", 1.0)
                else:
                    self._stars[4].set_property("opacity", 0.2)
        else:
            for i in range(5):
                self._stars[i].set_property("opacity", 0.2)

    """
        On button press, set album popularity
        @param widget as Gtk.EventBox
        @param event as Gdk.Event
    """
    def _on_button_press(self, widget, event):
        if Objects.scanner.is_locked():
            return
        event_star = widget.get_children()[0]
        try:
            position = self._stars.index(event_star)
            avg_popularity = Objects.albums.get_avg_popularity()
            popularity = int(((position+1)*avg_popularity/5)+0.5)
            Objects.albums.set_popularity(self._album_id, popularity)
        except:
            Objects.albums.set_popularity(self._album_id, 0)
        Objects.sql.commit()
