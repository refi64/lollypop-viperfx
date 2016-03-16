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

from gi.repository import Gtk, Gdk, GLib
from cgi import escape

from lollypop.pop_menu import TrackMenuPopover
from lollypop.pop_tunein import TuneinPopover
from lollypop.pop_albums import AlbumsPopover
from lollypop.pop_playlists import PlaylistsPopover
from lollypop.pop_externals import ExternalsPopover
from lollypop.pop_queue import QueuePopover
from lollypop.pop_infos import InfosPopover
from lollypop.pop_menu import PopToolbarMenu
from lollypop.controllers import InfosController
from lollypop.objects import Album
from lollypop.define import Lp, Type, ArtSize


class AddedPopover(Gtk.Popover):
    """
        Little popover showing an album
    """
    def __init__(self, builder):
        """
            Init popover
            @param builder as Gtk.Builder
        """
        Gtk.Popover.__init__(self)
        self.set_modal(False)
        self.get_style_context().add_class('osd-popover')
        self._timeout_id = None
        self._cover = builder.get_object('added_cover')
        self._artist = builder.get_object('added_artist')
        self._album = builder.get_object('added_album')
        self.add(builder.get_object('added'))
        Lp().player.connect('album-added', self._on_album_added)

#######################
# PRIVATE             #
#######################
    def _hide(self):
        """
            Hide popover
        """
        self._timeout_id = None
        self.hide()

    def _on_album_added(self, player, album_id):
        """
            Show album
            @param player as Player
            @param album id as int
        """
        if self._timeout_id is not None:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = None
        album = Album(album_id)
        surface = Lp().art.get_album_artwork(album, ArtSize.MEDIUM)
        self._cover.set_from_surface(surface)
        self._artist.set_text(album.artist_name)
        self._album.set_text(album.name)
        self.show()
        self._timeout_id = GLib.timeout_add(1000, self._hide)


class ToolbarInfos(Gtk.Bin, InfosController):
    """
        Informations toolbar
    """

    def __init__(self):
        """
            Init toolbar
        """
        Gtk.Bin.__init__(self)
        InfosController.__init__(self, ArtSize.SMALL)
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/ToolbarInfos.ui')
        builder.connect_signals(self)
        self._pop_tunein = None
        self._pop_infos = None
        self._timeout_id = None
        self._width = 0

        self._infobox = builder.get_object('infos')
        self.add(self._infobox)

        self._labels_event = builder.get_object('label_event')
        self._labels_event.set_property('has-tooltip', True)
        self._labels = builder.get_object('nowplaying_labels')

        self._title_label = builder.get_object('title')
        self._artist_label = builder.get_object('artist')
        self._cover_frame = builder.get_object('frame')
        self._cover = builder.get_object('cover')

        self._popover = AddedPopover(builder)
        self._popover.set_relative_to(self._cover)
        self._popover.set_position(Gtk.PositionType.BOTTOM)

        # Gesture for touchscreen
        # gesture = Gtk.GestureLongPress.new(self._labels_event)
        # gesture.connect('pressed', self._on_title_pressed)
        # gesture.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)

        self.connect('realize', self._on_realize)
        Lp().art.connect('album-artwork-changed', self._update_cover)
        Lp().art.connect('radio-artwork-changed', self._update_logo)

    def do_get_preferred_width(self):
        """
            We force preferred width
            @return (int, int)
        """
        return (self._width, self._width)

    def get_preferred_height(self):
        """
            Return preferred height
            @return (int, int)
        """
        return self._labels.get_preferred_height()

    def set_width(self, width):
        """
            Set widget width
            @param width as int
        """
        self._width = width
        self.set_property('width-request', width)


#######################
# PRIVATE             #
#######################
    def _update_cover(self, art, album_id):
        """
            Update cover for album_id
            @param art as Art
            @param album id as int
        """
        if Lp().player.current_track.album.id == album_id:
            surface = Lp().art.get_album_artwork(
                                       Lp().player.current_track.album,
                                       ArtSize.SMALL)
            self._cover.set_from_surface(surface)
            del surface

    def _update_logo(self, art, name):
        """
            Update logo for name
            @param art as Art
            @param name as str
        """
        if Lp().player.current_track.album_artist == name:
            pixbuf = Lp().art.get_radio_artwork(name, ArtSize.SMALL)
            self._cover.set_from_surface(pixbuf)
            del pixbuf

    def _show_track_menu(self):
        """
            Show current track menu
        """
        self._timeout_id = None
        if Lp().player.current_track.id >= 0:
            popover = TrackMenuPopover(
                        Lp().player.current_track.id,
                        PopToolbarMenu(Lp().player.current_track.id))
            popover.set_relative_to(self._labels_event)
            popover.show()

    def _on_album_press_event(self, eventbox, event):
        """
            Pop albums/radios/playlists/externals
            @param eventbox as Gtk.EventBox
            @param event as Gdk.Event
        """
        if Lp().player.current_track.id == Type.EXTERNALS:
            expopover = ExternalsPopover()
            expopover.set_relative_to(self._cover)
            expopover.populate()
            expopover.show()
        elif Lp().player.current_track.id == Type.RADIOS:
            if self._pop_tunein is None:
                self._pop_tunein = TuneinPopover()
                self._pop_tunein.populate()
                self._pop_tunein.set_relative_to(self._cover)
                self._pop_tunein.show()
        elif Lp().player.get_queue():
            pop_queue = QueuePopover()
            pop_queue.set_relative_to(self._cover)
            pop_queue.show()
        elif Lp().player.get_user_playlist_ids():
            pop_playlist = PlaylistsPopover()
            pop_playlist.set_relative_to(self._cover)
            pop_playlist.show()
        else:
            pop_albums = AlbumsPopover()
            pop_albums.set_relative_to(self._cover)
            pop_albums.show()
        return True

    def _on_title_press_event(self, widget, event):
        """
            On long press: show current track menu
            @param widget as Gtk.Widget
            @param event as Gdk.Event

        """
        self._timeout_id = GLib.timeout_add(500, self._show_track_menu)
        return True

    def _on_title_release_event(self, widget, event):
        """
            Show track information popover
            On long press/right click: show current track menu
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        if self._timeout_id is not None:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = None
            if Lp().player.current_track.id == Type.EXTERNALS:
                expopover = ExternalsPopover()
                expopover.set_relative_to(widget)
                expopover.populate()
                expopover.show()
            elif Lp().player.current_track.id is not None:
                if event.button == 1:
                    if Lp().player.current_track.id == Type.RADIOS:
                        if self._pop_tunein is None:
                            self._pop_tunein = TuneinPopover()
                            self._pop_tunein.populate()
                            self._pop_tunein.set_relative_to(widget)
                        self._pop_tunein.show()
                    else:
                        if self._pop_infos is None:
                            self._pop_infos = InfosPopover()
                            self._pop_infos.set_relative_to(widget)
                        self._pop_infos.show()
                else:
                    self._show_track_menu()
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
        # Can't add a \n in markup
        # GTK bug => https://bugzilla.gnome.org/show_bug.cgi?id=749965
        layout_title = self._title_label.get_layout()
        layout_artist = self._artist_label.get_layout()
        if layout_title.is_ellipsized() or layout_artist.is_ellipsized():
            artist = escape(self._artist_label.get_text())
            title = escape(self._title_label.get_text())
            tooltip.set_markup("<b>%s</b> - %s" % (artist, title))
        else:
            return False
        return True

    def _on_realize(self, toolbar):
        """
            @param toolbar as ToolbarInfos
        """
        style = self.get_style_context()
        padding = style.get_padding(style.get_state())
        ArtSize.SMALL = self.get_allocated_height()\
            - padding.top - padding.bottom - 2

    def _on_eventbox_realize(self, eventbox):
        """
            Show hand cursor over
        """
        eventbox.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND1))
