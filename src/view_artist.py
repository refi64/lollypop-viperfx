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

from gi.repository import Gtk, Gdk, Pango

from gettext import gettext as _
from math import pi
from cgi import escape

from lollypop.define import Lp, ArtSize
from lollypop.objects import Track, Album
from lollypop.pop_info import InfoPopover
from lollypop.cache import InfoCache
from lollypop.pop_artwork import ArtworkPopover
from lollypop.view_artist_albums import ArtistAlbumsView


class ArtistView(ArtistAlbumsView):
    """
        Show artist albums and tracks
    """

    def __init__(self, artist_ids, genre_ids):
        """
            Init ArtistView
            @param artist id as int (Current if None)
            @param genre id as int
        """
        ArtistAlbumsView.__init__(self, artist_ids, genre_ids)
        self._art_signal_id = None
        self.connect('realize', self._on_realize)
        self.connect('unrealize', self._on_unrealize)

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/ArtistView.ui')
        builder.connect_signals(self)
        self._artwork = builder.get_object('artwork')
        self._artwork_box = builder.get_object('artwork-box')
        self._label = builder.get_object('artist')
        self._jump_button = builder.get_object('jump-button')
        self._jump_button.set_tooltip_text(_("Go to current track"))
        self._add_button = builder.get_object('add-button')
        self._play_button = builder.get_object('play-button')
        self._grid = builder.get_object('header-grid')
        header = builder.get_object('header')
        header.set_property('valign', Gtk.Align.START)
        self._overlay.add_overlay(header)
        self._empty = Gtk.Grid()
        self._empty.show()
        self._albumbox.add(self._empty)
        self._albumbox.set_row_spacing(20)

        self._set_artwork()
        self._set_add_icon()
        self._on_lock_changed(Lp().player)

        artists = []
        for artist_id in artist_ids:
            artists.append(Lp().artists.get_name(artist_id))
        if Lp().settings.get_value('artist-artwork'):
            self._label.set_markup("<span size='x-large' weight='bold'>" +
                                   escape(", ".join(artists)) +
                                   "</span>")
        else:
            self._label.set_markup("<span size='large' weight='bold'>" +
                                   escape(", ".join(artists)) +
                                   "</span>")

    def jump_to_current(self):
        """
            Jump to current album
        """
        widget = None
        for child in self._albumbox.get_children():
            if child.get_id() == Lp().player.current_track.album.id:
                widget = child
                break
        if widget is not None:
            y = widget.get_current_ordinate(self._albumbox)
            self._scrolled.get_vadjustment().set_value(
                                y - self._empty.get_property('height-request'))

#######################
# PRIVATE             #
#######################
    def _set_artwork(self):
        """
            Set artist artwork
        """
        artwork_height = 0
        if Lp().settings.get_value('artist-artwork'):
            if len(self._artist_ids) == 1 and\
                    Lp().settings.get_value('artist-artwork'):
                artist = Lp().artists.get_name(self._artist_ids[0])

                for suffix in ["lastfm", "spotify", "wikipedia"]:
                    uri = InfoCache.get_artwork(
                                            artist, suffix,
                                            ArtSize.ARTIST_SMALL * 2 *
                                            self._artwork.get_scale_factor())
                    if uri is not None:
                        self._artwork.set_from_file(uri)
                        artwork_height = ArtSize.ARTIST_SMALL * 2
                        self._artwork.get_style_context().remove_class(
                                                                'artwork-icon')
                        self._artwork.show()
                        self._artwork_box.show()
                        break
            # Add a default icon
            if len(self._artist_ids) == 1 and artwork_height == 0:
                self._artwork.set_from_icon_name(
                                            'avatar-default-symbolic',
                                            Gtk.IconSize.DND)
                artwork_height = 32
                self._artwork.get_style_context().add_class('artwork-icon')
                self._artwork.show()
                self._artwork_box.show()

        # Create an self._empty widget with header height
        ctx = self._label.get_pango_context()
        layout = Pango.Layout.new(ctx)
        layout.set_text("a", 1)
        # Font scale 2
        font_height = int(layout.get_pixel_size()[1]) * 2

        if artwork_height > font_height:
            self._empty.set_property('height-request', artwork_height)
        else:
            self._empty.set_property('height-request', font_height)

    def _update_jump_button(self):
        """
            Update jump button status
        """
        found = False
        for child in self._get_children():
            if child.get_id() == Lp().player.current_track.album.id:
                found = True
                break
        if found:
            self._jump_button.set_sensitive(True)
        else:
            self._jump_button.set_sensitive(False)

    def _set_add_icon(self):
        """
            Set add icon based on player albums
        """
        albums = Lp().albums.get_ids(self._artist_ids, self._genre_ids)
        player_albums = Lp().player.get_albums()
        if len(set(albums) & set(player_albums)) == len(albums):
            self._add_button.set_tooltip_text(_("Remove"))
            self._add_button.get_image().set_from_icon_name(
                                                        'list-remove-symbolic',
                                                        Gtk.IconSize.MENU)
        else:
            self._add_button.set_tooltip_text(_("Add"))
            self._add_button.get_image().set_from_icon_name(
                                                           'list-add-symbolic',
                                                           Gtk.IconSize.MENU)

    def _on_realize(self, widget):
        """
            Connect signal
            @param widget as Gtk.Widget
        """
        self._art_signal_id = Lp().art.connect('artist-artwork-changed',
                                               self._on_artist_artwork_changed)
        self._party_signal_id = Lp().player.connect('party-changed',
                                                    self._on_album_changed)
        self._added_signal_id = Lp().player.connect('album-added',
                                                    self._on_album_changed)
        self._removed_signal_id = Lp().player.connect('album-removed',
                                                      self._on_album_changed)
        self._lock_signal_id = Lp().player.connect('lock-changed',
                                                   self._on_lock_changed)

    def _on_unrealize(self, widget):
        """
            Disconnect signal
            @param widget as Gtk.Widget
        """
        if self._art_signal_id is not None:
            Lp().art.disconnect(self._art_signal_id)
            self._art_signal_id = None
        if self._party_signal_id is not None:
            Lp().player.disconnect(self._party_signal_id)
            self._party_signal_id = None
        if self._added_signal_id is not None:
            Lp().player.disconnect(self._added_signal_id)
            self._added_signal_id = None
        if self._removed_signal_id is not None:
            Lp().player.disconnect(self._removed_signal_id)
            self._removed_signal_id = None
        if self._lock_signal_id is not None:
            Lp().player.disconnect(self._lock_signal_id)
            self._lock_signal_id = None

    def _on_album_changed(self, player, unused):
        """
            Update add icon
            @param player as Player
            @param unused
        """
        self._set_add_icon()

    def _on_lock_changed(self, player):
        """
            Lock buttons
            @param player as Player
        """
        self._add_button.set_sensitive(not player.locked)
        self._play_button.set_sensitive(not player.locked)

    def _on_artist_artwork_changed(self, art, prefix):
        """
            Update artwork if needed
            @param art as Art
            @param prefix as str
        """
        artist = Lp().artists.get_name(self._artist_ids[0])
        if prefix == artist:
            self._artwork.clear()
            self._set_artwork()

    def _on_jump_button_clicked(self, widget):
        """
            Scroll to album
        """
        self.jump_to_current()

    def _on_value_changed(self, adj):
        """
            Update scroll value and check for lazy queue
            @param adj as Gtk.Adjustment
        """
        ArtistAlbumsView._on_value_changed(self, adj)
        if adj.get_value() == adj.get_lower():
            if self._artwork.get_pixbuf() is not None:
                self._artwork.show()
                self._artwork_box.show()
            self._grid.get_style_context().remove_class('header-borders')
            self._grid.get_style_context().add_class('header')
            self._grid.set_property('valign', Gtk.Align.CENTER)
        else:
            if self._artwork.get_pixbuf() is not None:
                self._artwork.hide()
                self._artwork_box.hide()
            self._grid.get_style_context().add_class('header-borders')
            self._grid.get_style_context().remove_class('header')
            self._grid.set_property('valign', Gtk.Align.START)

    def _on_populated(self, widget, widgets, scroll_value):
        """
            Set jump button state
            @param widget as AlbumDetailedWidget
            @param widgets as pending AlbumDetailedWidgets
            @param scroll value as float
        """
        self._update_jump_button()
        ArtistAlbumsView._on_populated(self, widget, widgets, scroll_value)

    def _on_current_changed(self, player):
        """
            Set playing button status
            @param player as Player
        """
        ArtistAlbumsView._on_current_changed(self, player)
        self._update_jump_button()

    def _on_label_realize(self, eventbox):
        """
            Change cursor on label
            @param eventbox as Gtk.EventBox
        """
        if InfoPopover.should_be_shown() and self._artist_ids:
            eventbox.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND1))

    def _on_artwork_realize(self, eventbox):
        """
            Change cursor on image
            @param eventbox as Gtk.EventBox
        """
        eventbox.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND1))

    def _on_label_button_release(self, eventbox, event):
        """
            Show artists information
            @param eventbox as Gtk.EventBox
            @param event as Gdk.Event
        """
        if InfoPopover.should_be_shown() and self._artist_ids:
            pop = InfoPopover(self._artist_ids, False)
            pop.set_relative_to(eventbox)
            pop.show()

    def _on_image_button_release(self, eventbox, event):
        """
            Show artist artwork manager
            @param eventbox as Gtk.EventBox
            @param event as Gdk.Event
        """
        if InfoPopover.should_be_shown() and self._artist_ids:
            pop = ArtworkPopover(self._artist_ids[0])
            pop.set_relative_to(eventbox)
            pop.show()

    def _on_play_clicked(self, widget):
        """
            Play artist albums
        """
        if Lp().player.is_party():
            Lp().player.set_party(False)
        album_id = Lp().albums.get_ids(self._artist_ids, self._genre_ids)[0]
        track = Track(Album(album_id).track_ids[0])
        Lp().player.load(track)
        Lp().player.set_albums(track.id, self._artist_ids,
                               self._genre_ids)
        self._set_add_icon()

    def _on_add_clicked(self, widget):
        """
            Add artist albums
        """
        albums = Lp().albums.get_ids(self._artist_ids, self._genre_ids)
        if self._add_button.get_image().get_icon_name(
                                                   )[0] == 'list-add-symbolic':
            for album_id in albums:
                album = Album(album_id)
                # If playing and no albums, play it
                if not Lp().player.has_album(album):
                    if Lp().player.is_playing() and\
                            not Lp().player.get_albums():
                        Lp().player.play_album(album)
                    else:
                        Lp().player.add_album(album)
        else:
            for album_id in albums:
                album = Album(album_id)
                if Lp().player.has_album(album):
                    Lp().player.remove_album(album)
        self._set_add_icon()

    def _on_artwork_draw(self, image, ctx):
        """
            Draw rounded image
            @param image as Gtk.Image
            @param ctx as cairo.Context
        """
        if not image.is_drawable():
            return
        pixbuf = image.get_pixbuf()
        if pixbuf is None:
            return

        surface = Gdk.cairo_surface_create_from_pixbuf(
                                                     pixbuf,
                                                     image.get_scale_factor(),
                                                     None)
        ctx.translate(2, 2)
        size = ArtSize.ARTIST_SMALL * 2 - 4
        ctx.new_sub_path()
        radius = size / 2
        ctx.arc(size/2, size/2, radius, 0, 2 * pi)
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill_preserve()
        ctx.set_line_width(2)
        ctx.set_source_rgba(0, 0, 0, 0.3)
        ctx.stroke_preserve()
        ctx.set_source_surface(surface, 0, 0)
        ctx.clip()
        ctx.paint()
        return True
