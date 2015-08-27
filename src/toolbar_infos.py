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

from gi.repository import Gtk, Gdk
from cgi import escape

from lollypop.widgets_rating import RatingWidget
from lollypop.pop_tunein import TuneinPopover
from lollypop.pop_externals import ExternalsPopover
from lollypop.playlists import RadiosManager
from lollypop.pop_albums import AlbumsPopover
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

        infobox = builder.get_object('infos')
        infobox.set_property('has-tooltip', True)
        self.add(infobox)

        self._title_label = builder.get_object('title')
        self._artist_label = builder.get_object('artist')
        self._cover = builder.get_object('cover')
        self._pop_albums = AlbumsPopover()
        self._pop_albums.set_relative_to(infobox)
        self._pop_tunein = TuneinPopover(RadiosManager())
        self._pop_tunein.set_relative_to(infobox)

        Lp.art.connect('cover-changed', self._update_cover)
        Lp.art.connect('logo-changed', self._update_logo)

    def on_current_changed(self, player):
        """
            Update toolbar on current changed
            @param player as Player
        """
        art = None

        if player.current_track.artist == '':
            self._artist_label.hide()
        else:
            self._artist_label.show()
            self._artist_label.set_text(player.current_track.artist)
        if player.current_track.title == '':
            self._title_label.hide()
        else:
            self._title_label.show()
            self._title_label.set_text(player.current_track.title)

        if player.current_track.id == Type.RADIOS:
            art = Lp.art.get_radio(player.current_track.artist,
                                   ArtSize.SMALL,
                                   self.get_scale_factor())
        elif player.current_track.id == Type.EXTERNALS:
            art = Lp.art.get_cover_for_uri(
                    player.current_track.uri,
                    ArtSize.SMALL,
                    self.get_scale_factor(),
                    False)
        else:
            art = Lp.art.get_album(player.current_track.album_id,
                                   ArtSize.SMALL,
                                   self.get_scale_factor())
        if art is not None:
            self._cover.set_from_surface(art)
            del art
            self._cover.set_tooltip_text(player.current_track.album.name)
            self._cover.show()
        else:
            self._cover.hide()

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
        if Lp.player.current_track.album_id == album_id:
            pixbuf = Lp.art.get_album(album_id, ArtSize.SMALL)
            self._cover.set_from_surface(pixbuf)
            del pixbuf

    def _update_logo(self, art, name):
        """
            Update logo for name
            @param art as Art
            @param name as str
        """
        if Lp.player.current_track.artist == name:
            pixbuf = Lp.art.get_radio(name, ArtSize.SMALL)
            self._cover.set_from_surface(pixbuf)
            del pixbuf

    def _on_infobox_clicked(self, eventbox, event):
        """
            Pop albums from current artistleft click
            Show playlist menu on right
            @param eventbox as Gtk.EventBox
            @param event as Gdk.Event
        """
        if Lp.player.current_track.id == Type.EXTERNALS:
            expopover = ExternalsPopover()
            expopover.set_relative_to(eventbox)
            expopover.populate()
            expopover.show()
        elif Lp.player.current_track.id is not None:
            if event.button == 1:
                if Lp.player.current_track.id == Type.RADIOS:
                    self._pop_tunein.populate()
                    self._pop_tunein.show()
                else:
                    self._pop_albums.populate()
                    self._pop_albums.show()
            elif Lp.player.current_track.id >= 0:
                menu = PopToolbarMenu(Lp.player.current_track.id, None)
                popover = Gtk.Popover.new_from_model(eventbox, menu)
                rating = RatingWidget(Lp.player.current_track)
                rating.set_property('margin_top', 5)
                rating.set_property('margin_bottom', 5)
                rating.show()
                # Hack to add two widgets in popover
                # Use a Gtk.PopoverMenu later (GTK>3.16 available on Debian stable)
                stack = Gtk.Stack()
                grid = Gtk.Grid()
                grid.set_orientation(Gtk.Orientation.VERTICAL)
                stack.add_named(grid, 'main')
                stack.show_all()
                menu_widget = popover.get_child()
                menu_widget.reparent(grid)
                separator = Gtk.Separator()
                separator.show()
                grid.add(separator)
                grid.add(rating)
                popover.add(stack)
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
        eventbox.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND1))
