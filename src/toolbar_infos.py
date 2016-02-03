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
from cgi import escape

from lollypop.pop_menu import TrackMenuPopover
from lollypop.pop_tunein import TuneinPopover
from lollypop.pop_externals import ExternalsPopover
from lollypop.pop_infos import InfosPopover
from lollypop.pop_menu import PopToolbarMenu
from lollypop.define import Lp, Type, ArtSize


class ToolbarInfos(Gtk.Bin):
    """
        Informations toolbar
    """

    def __init__(self):
        """
            Init toolbar
        """
        Gtk.Bin.__init__(self)
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/ToolbarInfos.ui')
        builder.connect_signals(self)
        self._pop_tunein = None
        self._pop_infos = None
        self._width = 0

        self._infobox = builder.get_object('infos')
        self._infobox.set_property('has-tooltip', True)
        self.add(self._infobox)

        self._labels = builder.get_object('nowplaying_labels')
        self._title_label = builder.get_object('title')
        self._artist_label = builder.get_object('artist')
        self._cover_frame = builder.get_object('frame')
        self._cover = builder.get_object('cover')

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

    def on_current_changed(self, player):
        """
            Update toolbar on current changed
            @param player as Player
        """
        art = None

        self._artist_label.set_text(player.current_track.artist)
        self._title_label.set_text(player.current_track.title)

        if player.current_track.id == Type.RADIOS:
            art = Lp().art.get_radio_artwork(
                                   player.current_track.artist,
                                   ArtSize.SMALL*self.get_scale_factor())
        elif player.current_track.id == Type.EXTERNALS:
            art = Lp().art.get_album_artwork2(
                    player.current_track.uri,
                    ArtSize.SMALL*self.get_scale_factor())
        elif player.current_track.id is not None:
            art = Lp().art.get_album_artwork(
                                   player.current_track.album,
                                   ArtSize.SMALL*self.get_scale_factor())
        if art is not None:
            self._cover.set_from_surface(art)
            del art
            self._cover.set_tooltip_text(player.current_track.album.name)
            self._cover_frame.show()
        else:
            self._cover_frame.hide()

    def on_status_changed(self, player):
        """
            Update infos on status changed
            @param player as Player
        """
        pass

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

    def _on_infobox_clicked(self, eventbox, event):
        """
            Pop albums from current artistleft click
            Show playlist menu on right
            @param eventbox as Gtk.EventBox
            @param event as Gdk.Event
        """
        if Lp().player.current_track.id == Type.EXTERNALS:
            expopover = ExternalsPopover()
            expopover.set_relative_to(eventbox)
            expopover.populate()
            expopover.show()
        elif Lp().player.current_track.id is not None:
            if event.button == 1:
                if Lp().player.current_track.id == Type.RADIOS:
                    if self._pop_tunein is None:
                        self._pop_tunein = TuneinPopover()
                        self._pop_tunein.populate()
                        self._pop_tunein.set_relative_to(self._infobox)
                    self._pop_tunein.show()
                else:
                    if self._pop_infos is None:
                        self._pop_infos = InfosPopover()
                        self._pop_infos.set_relative_to(self._infobox)
                    self._pop_infos.show()
            elif Lp().player.current_track.id >= 0:
                popover = TrackMenuPopover(
                            Lp().player.current_track.id,
                            PopToolbarMenu(Lp().player.current_track.id))
                popover.set_relative_to(self._infobox)
                popover.show()
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

    def _on_eventbox_realize(self, eventbox):
        """
            Show hand cursor over
        """
        style = self.get_style_context()
        padding = style.get_padding(style.get_state())
        ArtSize.SMALL = self.get_allocated_height()\
            - padding.top - padding.bottom - 2
        eventbox.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND1))
