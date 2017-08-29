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

from gi.repository import Gtk, Gdk, Pango, GLib, Gio, GdkPixbuf

from gettext import gettext as _
from math import pi
from random import choice

from lollypop.define import Lp, ArtSize, Shuffle, Type
from lollypop.utils import get_network_available
from lollypop.objects import Album
from lollypop.pop_info import InfoPopover
from lollypop.cache import InfoCache
from lollypop.pop_artwork import ArtworkPopover
from lollypop.view_artist_albums import ArtistAlbumsView
from lollypop.lio import Lio


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
        ArtistAlbumsView.__init__(self, artist_ids, genre_ids, ArtSize.BIG)
        self.__art_signal_id = None
        self.connect("realize", self.__on_realize)
        self.connect("unrealize", self.__on_unrealize)

        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/ArtistView.ui")
        builder.connect_signals(self)
        self.__artwork = builder.get_object("artwork")
        self.__artwork_box = builder.get_object("artwork-box")
        self.__label = builder.get_object("artist")
        self.__jump_button = builder.get_object("jump-button")
        self.__jump_button.set_tooltip_text(_("Go to current track"))
        self.__add_button = builder.get_object("add-button")
        self.__play_button = builder.get_object("play-button")
        self.__grid = builder.get_object("header")
        if Lp().lastfm is None:
            builder.get_object("lastfm-button").hide()
        elif not get_network_available():
            builder.get_object("lastfm-button").set_sensitive(False)
            builder.get_object("lastfm-button").set_tooltip_text(
                                                  _("Network access disabled"))
        self._overlay.add_overlay(self.__grid)
        self.__empty = Gtk.Grid()
        self.__empty.show()
        self._albumbox.add(self.__empty)
        self._albumbox.set_row_spacing(20)

        self.__scale_factor = self.__artwork.get_scale_factor()
        self.__set_artwork()
        self.__set_add_icon()
        self.__on_lock_changed(Lp().player)

        artists = []
        for artist_id in artist_ids:
            artists.append(Lp().artists.get_name(artist_id))
        if Lp().settings.get_value("artist-artwork"):
            self.__label.set_markup(
                                '<span size="x-large" weight="bold">' +
                                GLib.markup_escape_text(", ".join(artists)) +
                                "</span>")
        else:
            self.__label.set_markup(
                                '<span size="large" weight="bold">' +
                                GLib.markup_escape_text(", ".join(artists)) +
                                "</span>")

    def jump_to_current(self):
        """
            Jump to current album
        """
        widget = None
        for child in self._albumbox.get_children():
            if child.id == Lp().player.current_track.album.id:
                widget = child
                break
        if widget is not None:
            y = widget.get_current_ordinate(self._albumbox)
            self._scrolled.get_vadjustment().set_value(
                               y - self.__empty.get_property("height-request"))

#######################
# PROTECTED           #
#######################
    def _on_value_changed(self, adj):
        """
            Update scroll value and check for lazy queue
            @param adj as Gtk.Adjustment
        """
        ArtistAlbumsView._on_value_changed(self, adj)
        if adj.get_value() == adj.get_lower():
            if self.__artwork.props.surface is not None or\
                    self.__artwork.get_pixbuf() is not None:
                self.__artwork.show()
                self.__artwork_box.show()
            self.__grid.get_style_context().remove_class("header-borders")
            self.__grid.get_style_context().add_class("header")
        else:
            if self.__artwork.props.surface is not None or\
                    self.__artwork.get_pixbuf() is not None:
                self.__artwork.hide()
                self.__artwork_box.hide()
            self.__grid.get_style_context().add_class("header-borders")
            self.__grid.get_style_context().remove_class("header")

    def _on_label_realize(self, eventbox):
        """
            Change cursor on label
            @param eventbox as Gtk.EventBox
        """
        if InfoPopover.should_be_shown() and self._artist_ids:
            eventbox.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))

    def _on_artwork_realize(self, eventbox):
        """
            Change cursor on image
            @param eventbox as Gtk.EventBox
        """
        eventbox.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))

    def _on_label_button_release(self, eventbox, event):
        """
            Show artists information
            @param eventbox as Gtk.EventBox
            @param event as Gdk.Event
        """
        if InfoPopover.should_be_shown() and self._artist_ids:
            pop = InfoPopover(self._artist_ids, Type.NONE)
            pop.set_relative_to(eventbox)
            pop.show()

    def _on_image_button_release(self, eventbox, event):
        """
            Show artist artwork manager
            @param eventbox as Gtk.EventBox
            @param event as Gdk.Event
        """
        if self._artist_ids:
            pop = ArtworkPopover(self._artist_ids[0])
            pop.set_relative_to(eventbox)
            pop.show()

    def _on_play_clicked(self, widget):
        """
            Play artist albums
        """
        try:
            if Lp().player.is_party:
                Lp().player.set_party(False)
            album_id = Lp().albums.get_ids(self._artist_ids,
                                           self._genre_ids)[0]
            if Lp().settings.get_enum("shuffle") == Shuffle.TRACKS:
                track = choice(Album(album_id).tracks)
            else:
                track = Album(album_id).tracks[0]
            Lp().player.load(track)
            Lp().player.set_albums(track.id, self._artist_ids,
                                   self._genre_ids)
            self.__set_add_icon()
        except:
            pass  # Artist not available anymore for this context

    def _on_add_clicked(self, widget):
        """
            Add artist albums
        """
        try:
            albums = Lp().albums.get_ids(self._artist_ids, self._genre_ids)
            if self.__add_button.get_image().get_icon_name(
                                                   )[0] == "list-add-symbolic":
                for album_id in albums:
                    album = Album(album_id)
                    # If playing and no albums, play it
                    if not Lp().player.has_album(album):
                        if Lp().player.is_playing and\
                                not Lp().player.get_albums():
                            Lp().player.play_album(album)
                        else:
                            Lp().player.add_album(album)
            else:
                for album_id in albums:
                    album = Album(album_id)
                    if Lp().player.has_album(album):
                        Lp().player.remove_album(album)
            self.__set_add_icon()
        except:
            pass  # Artist not available anymore for this context

    def _on_jump_button_clicked(self, widget):
        """
            Scroll to album
        """
        self.jump_to_current()

    def _on_lastfm_button_clicked(self, widget):
        """
            Show lastfm similar artists
        """
        from lollypop.pop_lastfm import LastfmPopover
        popover = LastfmPopover()
        popover.set_relative_to(widget)
        popover.populate(self._artist_ids)
        popover.show()

    def _on_artwork_draw(self, image, ctx):
        """
            Draw rounded image
            @param image as Gtk.Image
            @param ctx as cairo.Context
        """
        # Update image if scale factor changed
        if self.__scale_factor != image.get_scale_factor():
            self.__scale_factor = image.get_scale_factor()
            self.__set_artwork()
        if not image.is_drawable():
            return

        if image.props.surface is None:
            pixbuf = image.get_pixbuf()
            if pixbuf is None:
                return
            surface = Gdk.cairo_surface_create_from_pixbuf(
                                                         pixbuf,
                                                         self.__scale_factor,
                                                         None)
            del pixbuf
        else:
            surface = image.props.surface

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

    def _on_current_changed(self, player):
        """
            Set playing button status
            @param player as Player
        """
        ArtistAlbumsView._on_current_changed(self, player)
        self.__update_jump_button()

    def _on_populated(self, widget, widgets, scroll_value):
        """
            Set jump button state
            @param widget as AlbumDetailedWidget
            @param widgets as pending AlbumDetailedWidgets
            @param scroll value as float
        """
        self.__update_jump_button()
        ArtistAlbumsView._on_populated(self, widget, widgets, scroll_value)

#######################
# PRIVATE             #
#######################
    def __set_artwork(self):
        """
            Set artist artwork
        """
        artwork_height = 0
        if Lp().settings.get_value("artist-artwork"):
            if len(self._artist_ids) == 1 and\
                    Lp().settings.get_value("artist-artwork"):
                artist = Lp().artists.get_name(self._artist_ids[0])
                size = ArtSize.ARTIST_SMALL * 2 * self.__scale_factor
                for suffix in ["lastfm", "spotify", "wikipedia"]:
                    uri = InfoCache.get_artwork(artist, suffix, size)
                    if uri is not None:
                        f = Lio.File.new_for_path(uri)
                        (status, data, tag) = f.load_contents(None)
                        if not status:
                            continue
                        bytes = GLib.Bytes(data)
                        stream = Gio.MemoryInputStream.new_from_bytes(bytes)
                        bytes.unref()
                        pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(
                                                                       stream,
                                                                       size,
                                                                       size,
                                                                       True,
                                                                       None)
                        stream.close()
                        surface = Gdk.cairo_surface_create_from_pixbuf(
                                            pixbuf, self.__scale_factor, None)
                        del pixbuf
                        self.__artwork.set_from_surface(surface)
                        del surface
                        artwork_height = ArtSize.ARTIST_SMALL * 2
                        self.__artwork.get_style_context().remove_class(
                                                                "artwork-icon")
                        self.__artwork.show()
                        self.__artwork_box.show()
                        break
            # Add a default icon
            if len(self._artist_ids) == 1 and artwork_height == 0:
                self.__artwork.set_from_icon_name(
                                            "avatar-default-symbolic",
                                            Gtk.IconSize.DND)
                artwork_height = 32
                self.__artwork.get_style_context().add_class("artwork-icon")
                self.__artwork.show()
                self.__artwork_box.show()

        # Create an self.__empty widget with header height
        ctx = self.__label.get_pango_context()
        layout = Pango.Layout.new(ctx)
        layout.set_text("a", 1)
        # Font scale 2
        font_height = int(layout.get_pixel_size()[1]) * 2

        if artwork_height > font_height:
            self.__empty.set_property("height-request", artwork_height)
        else:
            self.__empty.set_property("height-request", font_height)

    def __update_jump_button(self):
        """
            Update jump button status
        """
        found = False
        for child in self._get_children():
            if child.id == Lp().player.current_track.album.id:
                found = True
                break
        if found:
            self.__jump_button.set_sensitive(True)
        else:
            self.__jump_button.set_sensitive(False)

    def __set_add_icon(self):
        """
            Set add icon based on player albums
        """
        albums = Lp().albums.get_ids(self._artist_ids, self._genre_ids)
        player_albums = Lp().player.get_albums()
        if len(set(albums) & set(player_albums)) == len(albums):
            # Translators: artist context
            self.__add_button.set_tooltip_text(_("Remove"))
            self.__add_button.get_image().set_from_icon_name(
                                                        "list-remove-symbolic",
                                                        Gtk.IconSize.MENU)
        else:
            # Translators: artist context
            self.__add_button.set_tooltip_text(_("Add"))
            self.__add_button.get_image().set_from_icon_name(
                                                           "list-add-symbolic",
                                                           Gtk.IconSize.MENU)

    def __on_realize(self, widget):
        """
            Connect signal
            @param widget as Gtk.Widget
        """
        self.__art_signal_id = Lp().art.connect(
                                              "artist-artwork-changed",
                                              self.__on_artist_artwork_changed)
        self.__party_signal_id = Lp().player.connect("party-changed",
                                                     self.__on_album_changed)
        self.__added_signal_id = Lp().player.connect("album-added",
                                                     self.__on_album_changed)
        self.__removed_signal_id = Lp().player.connect("album-removed",
                                                       self.__on_album_changed)
        self.__lock_signal_id = Lp().player.connect("lock-changed",
                                                    self.__on_lock_changed)

    def __on_unrealize(self, widget):
        """
            Disconnect signal
            @param widget as Gtk.Widget
        """
        if self.__art_signal_id is not None:
            Lp().art.disconnect(self.__art_signal_id)
            self.__art_signal_id = None
        if self.__party_signal_id is not None:
            Lp().player.disconnect(self.__party_signal_id)
            self.__party_signal_id = None
        if self.__added_signal_id is not None:
            Lp().player.disconnect(self.__added_signal_id)
            self.__added_signal_id = None
        if self.__removed_signal_id is not None:
            Lp().player.disconnect(self.__removed_signal_id)
            self.__removed_signal_id = None
        if self.__lock_signal_id is not None:
            Lp().player.disconnect(self.__lock_signal_id)
            self.__lock_signal_id = None

    def __on_album_changed(self, player, unused):
        """
            Update add icon
            @param player as Player
            @param unused
        """
        self.__set_add_icon()

    def __on_lock_changed(self, player):
        """
            Lock buttons
            @param player as Player
        """
        self.__add_button.set_sensitive(not player.locked)
        self.__play_button.set_sensitive(not player.locked)

    def __on_artist_artwork_changed(self, art, prefix):
        """
            Update artwork if needed
            @param art as Art
            @param prefix as str
        """
        artist = Lp().artists.get_name(self._artist_ids[0])
        if prefix == artist:
            self.__artwork.clear()
            self.__set_artwork()
