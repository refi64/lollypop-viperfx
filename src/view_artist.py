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

from lollypop.define import Lp, Type
from lollypop.pop_infos import InfosPopover
from lollypop.view_artist_albums import ArtistAlbumsView


class ArtistView(ArtistAlbumsView):
    """
        Show artist albums and tracks
    """

    def __init__(self, artist_id, genre_id):
        """
            Init ArtistView
            @param artist id as int (Current if None)
            @param genre id as int
        """
        ArtistAlbumsView.__init__(self, artist_id, genre_id)
        self._artist_id = artist_id
        self._genre_id = genre_id
        self._signal_id = None

        self._popover = InfosPopover(artist_id, False)
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/ArtistView.ui')
        builder.connect_signals(self)
        self.attach(builder.get_object('ArtistView'), 0, 0, 1, 1)
        builder.get_object('artist').set_label(
                                            Lp.artists.get_name(artist_id))

#######################
# PRIVATE             #
#######################
    def _on_label_realize(self, eventbox):
        """
            Change pointer on label
            @param eventbox as Gtk.EventBox
        """
        if InfosPopover.should_be_shown() and\
                self._artist_id != Type.COMPILATIONS:
            eventbox.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND1))

    def _on_label_button_release(self, eventbox, event):
        """
            On clicked label, show artist informations in a popover
            @param eventbox as Gtk.EventBox
            @param event as Gdk.Event
        """
        if InfosPopover.should_be_shown() and\
                self._artist_id != Type.COMPILATIONS:
            self._popover.set_relative_to(eventbox)
            self._popover.show()
