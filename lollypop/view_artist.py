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

from gi.repository import Gtk, Gdk, Pango, GLib

from gettext import gettext as _

from lollypop.define import App, ArtSize
from lollypop.utils import get_network_available
from lollypop.objects import Album
from lollypop.pop_artwork import ArtworkPopover
from lollypop.view_artist_albums import ArtistAlbumsView
from lollypop.logger import Logger


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
        ArtistAlbumsView.__init__(self, artist_ids, genre_ids, True)
        self.__art_signal_id = None

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
        if App().lastfm is None:
            builder.get_object("lastfm-button").hide()
        elif not get_network_available():
            builder.get_object("lastfm-button").set_sensitive(False)
            builder.get_object("lastfm-button").set_tooltip_text(
                _("Network access disabled"))
        self._overlay.add_overlay(self.__grid)
        self.__empty = Gtk.Grid()
        self.__empty.show()
        self._album_box.add(self.__empty)
        self._album_box.set_row_spacing(20)
        self._album_box.set_margin_start(10)
        self._album_box.set_margin_end(10)

        self.__scale_factor = self.__artwork.get_scale_factor()
        self.__set_artwork()
        self.__on_album_changed(App().player)
        self.__on_lock_changed(App().player)

        artists = []
        for artist_id in artist_ids:
            artists.append(App().artists.get_name(artist_id))
        if App().settings.get_value("artist-artwork"):
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
        for child in self._album_box.get_children():
            if child.album.id == App().player.current_track.album.id:
                widget = child
                break
        if widget is not None:
            y = widget.get_current_ordinate(self._album_box)
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
            if self.__artwork.get_visible():
                self.__artwork_box.show()
            self.__grid.get_style_context().remove_class("header-borders")
            self.__grid.get_style_context().add_class("header")
        else:
            if self.__artwork.get_visible():
                self.__artwork_box.hide()
            self.__grid.get_style_context().add_class("header-borders")
            self.__grid.get_style_context().remove_class("header")

    def _on_label_realize(self, eventbox):
        """
            Change cursor on label
            @param eventbox as Gtk.EventBox
        """
        try:
            if len(self._artist_ids) == 1:
                eventbox.get_window().set_cursor(
                    Gdk.Cursor(Gdk.CursorType.HAND2))
        except:
            Logger.warning(_("You are using a broken cursor theme!"))

    def _on_artwork_box_realize(self, eventbox):
        """
            Change cursor on image
            @param eventbox as Gtk.EventBox
        """
        try:
            eventbox.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))
        except:
            Logger.warning(_("You are using a broken cursor theme!"))

    def _on_label_button_release(self, eventbox, event):
        """
            Show artists information
            @param eventbox as Gtk.EventBox
            @param event as Gdk.Event
        """
        if len(self._artist_ids) == 1:
            from lollypop.pop_information import InformationPopover
            self.__pop_info = InformationPopover(True)
            self.__pop_info.set_relative_to(eventbox)
            self.__pop_info.populate(self._artist_ids[0])
            self.__pop_info.show()

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
            if App().player.is_party:
                App().lookup_action("party").change_state(
                    GLib.Variant("b", False))
            App().player.play_albums(None,
                                     self._genre_ids,
                                     self._artist_ids)
            self.__update_icon(False)
        except Exception as e:
            Logger.error("ArtistView::_on_play_clicked: %s" % e)

    def _on_add_clicked(self, widget):
        """
            Add artist albums
        """
        try:
            album_ids = App().albums.get_ids(self._artist_ids, self._genre_ids)
            len_album_ids = len(album_ids)
            player_album_ids = App().player.album_ids
            len_player_album_ids = len(player_album_ids)
            icon_name = self.__add_button.get_image().get_icon_name()[0]
            add = icon_name == "list-add-symbolic"
            for album_id in album_ids:
                if add and album_id not in player_album_ids:
                    App().player.add_album(Album(album_id))
                elif not add and album_id in player_album_ids:
                    if len_player_album_ids > len_album_ids and\
                            App().player.current_track.album.id == album_id:
                        App().player.skip_album()
                    App().player.remove_album_by_id(album_id)
            if len_player_album_ids == len_album_ids:
                App().player.stop()
            self.__update_icon(not add)
        except Exception as e:
            Logger.error("ArtistView::_on_add_clicked: %s" % e)

    def _on_jump_button_clicked(self, button):
        """
            Scroll to album
            @parma button as Gtk.Button
        """
        self.jump_to_current()

    def _on_lastfm_button_toggled(self, button):
        """
            Show lastfm similar artists
            @param button as Gtk.Button
        """
        if button.get_active():
            from lollypop.pop_lastfm import LastfmPopover
            popover = LastfmPopover()
            popover.set_relative_to(button)
            popover.populate(self._artist_ids)
            popover.connect("closed", lambda x: button.set_active(False))
            popover.popup()

    def _on_current_changed(self, player):
        """
            Set playing button status
            @param player as Player
        """
        ArtistAlbumsView._on_current_changed(self, player)
        self.__update_jump_button()

    def _on_populated(self, widget):
        """
            Set jump button state
            @param widget as AlbumDetailedWidget
        """
        self.__update_jump_button()
        ArtistAlbumsView._on_populated(self, widget)

    def _on_map(self, widget):
        """
            Connect signals and set active ids
            @param widget as Gtk.Widget
        """
        self.__art_signal_id = App().art.connect(
                                           "artist-artwork-changed",
                                           self.__on_artist_artwork_changed)
        self.__party_signal_id = App().player.connect(
                                                "party-changed",
                                                self.__on_album_changed)
        self.__added_signal_id = App().player.connect(
                                                "album-added",
                                                self.__on_album_changed)
        self.__removed_signal_id = App().player.connect(
                                                  "album-removed",
                                                  self.__on_album_changed)
        self.__lock_signal_id = App().player.connect(
                                               "lock-changed",
                                               self.__on_lock_changed)
        App().settings.set_value("state-one-ids",
                                 GLib.Variant("ai", self._genre_ids))
        App().settings.set_value("state-two-ids",
                                 GLib.Variant("ai", self._artist_ids))

    def _on_unmap(self, widget):
        """
            Disconnect signals
            @param widget as Gtk.Widget
        """
        if self.__art_signal_id is not None:
            App().art.disconnect(self.__art_signal_id)
            self.__art_signal_id = None
        if self.__party_signal_id is not None:
            App().player.disconnect(self.__party_signal_id)
            self.__party_signal_id = None
        if self.__added_signal_id is not None:
            App().player.disconnect(self.__added_signal_id)
            self.__added_signal_id = None
        if self.__removed_signal_id is not None:
            App().player.disconnect(self.__removed_signal_id)
            self.__removed_signal_id = None
        if self.__lock_signal_id is not None:
            App().player.disconnect(self.__lock_signal_id)
            self.__lock_signal_id = None

#######################
# PRIVATE             #
#######################
    def __set_header_height(self):
        """
            Set header height based on font height and artwork height
        """
        # Create an self.__empty widget with header height
        ctx = self.__label.get_pango_context()
        layout = Pango.Layout.new(ctx)
        layout.set_text("a", 1)
        # Font scale 2
        font_height = int(layout.get_pixel_size()[1]) * 2
        if self.__artwork.props.surface is not None:
            artwork_height = self.__artwork.props.surface.get_height()
        else:
            self.__artwork.get_style_context().add_class("artwork-icon")
            artwork_height = 32
        if artwork_height > font_height:
            self.__empty.set_property("height-request", artwork_height)
        else:
            self.__empty.set_property("height-request", font_height)

    def __set_artwork(self):
        """
            Set artist artwork
        """
        if len(self._artist_ids) == 1 and\
                App().settings.get_value("artist-artwork"):
            artist = App().artists.get_name(self._artist_ids[0])
            size = ArtSize.ARTIST_SMALL
            if not App().window.is_adaptive:
                size *= 2
            App().art_helper.set_artist_artwork(
                                        artist,
                                        size,
                                        size,
                                        self.__artwork.get_scale_factor(),
                                        self.__on_artist_artwork)
        else:
            self.__set_header_height()

    def __update_jump_button(self):
        """
            Update jump button status
        """
        found = False
        for child in self.children:
            if child.album.id == App().player.current_track.album.id:
                found = True
                break
        if found:
            self.__jump_button.set_sensitive(True)
        else:
            self.__jump_button.set_sensitive(False)

    def __update_icon(self, add):
        """
            Set icon for Artist +/-
            @param add as bool
        """
        if add:
            # Translators: artist context
            self.__add_button.set_tooltip_text(_("Add to current playlist"))
            self.__add_button.get_image().set_from_icon_name(
                "list-add-symbolic",
                Gtk.IconSize.MENU)
        else:
            # Translators: artist context
            self.__add_button.set_tooltip_text(
                _("Remove from current playlist"))
            self.__add_button.get_image().set_from_icon_name(
                "list-remove-symbolic",
                Gtk.IconSize.MENU)

    def __on_album_changed(self, player, album_id=None):
        """
            Update icon
            @param player as Player
            @param album_id as int
        """
        albums = App().albums.get_ids(self._artist_ids, self._genre_ids)
        album_ids = App().player.album_ids
        self.__update_icon(len(set(albums) & set(album_ids)) != len(albums))

    def __on_lock_changed(self, player):
        """
            Lock buttons
            @param player as Player
        """
        self.__add_button.set_sensitive(not player.is_locked)
        self.__play_button.set_sensitive(not player.is_locked)

    def __on_artist_artwork_changed(self, art, prefix):
        """
            Update artwork if needed
            @param art as Art
            @param prefix as str
        """
        artist = App().artists.get_name(self._artist_ids[0])
        if prefix == artist:
            self.__artwork.clear()
            self.__set_artwork()

    def __on_artist_artwork(self, surface):
        """
            Set artist artwork
            @param surface as cairo.Surface
        """
        if surface is None:
            self.__artwork.set_from_icon_name("avatar-default-symbolic",
                                              Gtk.IconSize.DND)
        else:
            self.__artwork.set_from_surface(surface)
            self.__artwork.get_style_context().remove_class("artwork-icon")
        self.__artwork.show()
        self.__set_header_height()
