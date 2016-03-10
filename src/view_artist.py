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

from lollypop.define import Lp
from lollypop.pop_infos import InfosPopover
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
        if len(artist_ids) > 1:
            self._artist_id = None
        else:
            self._artist_id = artist_ids[0]

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/ArtistView.ui')
        builder.connect_signals(self)
        self._jump_button = builder.get_object('jump-button')
        self.attach(builder.get_object('ArtistView'), 0, 0, 1, 1)
        artists = ""
        for artist_id in artist_ids:
            artists += Lp().artists.get_name(artist_id) + ", "
        builder.get_object('artist').set_label(artists[:-2])

#######################
# PRIVATE             #
#######################
    def _update_jump_button(self):
        """
            Update jump button status
        """
        if Lp().player.current_track.album.id in self._albums:
            self._jump_button.set_sensitive(True)
            self._jump_button.set_tooltip_text(
                                          Lp().player.current_track.name)
        else:
            self._jump_button.set_sensitive(False)
            self._jump_button.set_tooltip_text('')

    def _on_jump_button_clicked(self, widget):
        """
            Scroll to album
        """
        self.jump_to_current()

    def _on_album_finished(self, album):
        """
            Add another album
            @param album as AlbumDetailedWidget
        """
        if not self._albums:
            self._update_jump_button()
        ArtistAlbumsView._on_album_finished(self, album)

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
        if InfosPopover.should_be_shown() and\
                self._artist_id is not None:
            eventbox.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND1))

    def _on_label_button_release(self, eventbox, event):
        """
            On clicked label, show artist informations in a popover
            @param eventbox as Gtk.EventBox
            @param event as Gdk.Event
        """
        if InfosPopover.should_be_shown() and\
                self._artist_id is not None:
            pop = InfosPopover(self._artist_id, False)
            pop.set_relative_to(eventbox)
            pop.show()
