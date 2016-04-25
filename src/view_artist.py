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

from gi.repository import Gtk, Gdk

from gettext import gettext as _
from math import pi

from lollypop.define import Lp, ArtSize
from lollypop.pop_info import InfoPopover
from lollypop.cache import InfoCache
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
        self._signal_id = None
        self._artist_ids = artist_ids

        empty = Gtk.Grid()
        if Lp().settings.get_value('artist-artwork'):
            empty.set_property('height-request', ArtSize.ARTIST_SMALL * 2)
        else:
            empty.set_property('height-request', ArtSize.ARTIST_SMALL)
        empty.show()
        self._albumbox.add(empty)

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/ArtistView.ui')
        builder.connect_signals(self)
        self._artwork = builder.get_object('artwork')
        self._label = builder.get_object('artist')
        self._jump_button = builder.get_object('jump-button')
        self._jump_button.set_tooltip_text(_("Go to current track"))
        self._spinner = builder.get_object('spinner')
        header = builder.get_object('header')
        header.set_property('valign', Gtk.Align.START)
        self._overlay.add_overlay(header)
        self._overlay.set_overlay_pass_through(header, True)
        if len(artist_ids) == 1 and Lp().settings.get_value('artist-artwork'):
            artist = Lp().artists.get_name(artist_ids[0])
            for suffix in ["lastfm", "spotify", "wikipedia"]:
                uri = InfoCache.get_artwork(artist, suffix,
                                            ArtSize.ARTIST_SMALL * 2 *
                                            self._artwork.get_scale_factor())
                if uri is not None:
                    self._artwork.set_from_file(uri)
                    self._artwork.show()
                    break

        artists = []
        for artist_id in artist_ids:
            artists.append(Lp().artists.get_name(artist_id))
        self._label.set_label(", ".join(artists))

#######################
# PRIVATE             #
#######################
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
            self._artwork.show()
            self._label.get_style_context().remove_class('header')
            self._jump_button.get_style_context().remove_class('header')
            self._jump_button.set_property('valign', Gtk.Align.END)
        else:
            self._artwork.hide()
            self._label.get_style_context().add_class('header')
            self._jump_button.get_style_context().add_class('header')
            self._jump_button.set_property('valign', Gtk.Align.START)

    def _on_populated(self, widget, widgets, scroll_value):
        """
            Set jump button state
            @param widget as AlbumDetailedWidget
            @param widgets as pending AlbumDetailedWidgets
            @param scroll value as float
        """
        self._update_jump_button()
        self._spinner.stop()
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
            Change pointer on label
            @param eventbox as Gtk.EventBox
        """
        if InfoPopover.should_be_shown() and self._artist_ids:
            eventbox.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND1))

    def _on_label_button_release(self, eventbox, event):
        """
            On clicked label, show artist informations in a popover
            @param eventbox as Gtk.EventBox
            @param event as Gdk.Event
        """
        if InfoPopover.should_be_shown() and self._artist_ids:
            pop = InfoPopover(self._artist_ids, False)
            pop.set_relative_to(eventbox)
            pop.show()

    def _on_artwork_draw(self, image, ctx):
        """
            Draw rounded image
            @param image as Gtk.Image
            @param ctx as cairo.Context
        """
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
