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

from lollypop.define import Type, Lp
from lollypop.pop_info import InfoPopover
from lollypop.widgets_album import AlbumDetailedWidget


class AlbumContextWidget(AlbumDetailedWidget):
    """
        Widget with cover and tracks
    """

    def __init__(self, album_id, genre_ids, artist_ids, update_albums=True):
        """
            Init detailed album widget
            @param album id as int
            @param genre ids as [int]
            @param artist ids as [int]
            @param update albums as bool: update albums on play
        """
        AlbumDetailedWidget.__init__(self, album_id, genre_ids, artist_ids,
                                     update_albums)
        self._artist_label.set_text(", ".join(self._album.artists))
        self._artist_label.show()

#######################
# PRIVATE             #
#######################
    def _on_label_realize(self, eventbox):
        """
            Change pointer on label
            @param eventbox as Gtk.EventBox
        """
        if InfoPopover.should_be_shown() and\
                self._album.artist_ids[0] != Type.COMPILATIONS:
            eventbox.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND1))

    def _on_label_button_release(self, eventbox, event):
        """
            On clicked label, show artist informations in a popover
            @param eventbox as Gtk.EventBox
            @param event as Gdk.Event
        """
        if InfoPopover.should_be_shown() and\
                self._album.artist_ids[0] != Type.COMPILATIONS:
            pop = InfoPopover(self._album.artist_ids)
            pop.set_relative_to(eventbox)
            pop.show()


class AlbumPopoverWidget(Gtk.Popover):
    """
        An AlbumContextWidget in a popover
    """

    def __init__(self, album_id, genre_ids, artist_ids, update_albums=True):
        """
            Init popover
            @param album id as int
            @param genre ids as [int]
            @param artist ids as [int]
            @param update albums as bool: update albums on play
        """
        Gtk.Popover.__init__(self)
        self.connect('hide', self._on_hide)
        self._widget = AlbumContextWidget(album_id,
                                          genre_ids,
                                          artist_ids,
                                          update_albums)
        self._widget.populate()
        self._widget.show()
        self._current_signal = Lp().player.connect('current-changed',
                                                   self._on_current_changed)
        self._cover_signal = Lp().art.connect('album-artwork-changed',
                                              self._on_cover_changed)
        self.add(self._widget)

    def do_get_preferred_width(self):
        """
            Set maximum width
        """
        width = min(900, Lp().window.get_size()[0] - 10)
        return (width, width)

#######################
# PRIVATE             #
#######################
    def _on_current_changed(self, player):
        """
            Update indicator
            @param player as Player
        """
        self._widget.update_playing_indicator()

    def _on_cover_changed(self, art, album_id):
        """
            Update album cover in view
            @param art as Art
            @param album id as int
        """
        self._widget.update_cover(album_id)

    def _on_hide(self, widget):
        """
            Destroy itself
            @param widget as Gtk.Widget
        """
        if self._current_signal:
            Lp().player.disconnect(self._current_signal)
            self._current_signal = None
        if self._cover_signal:
            Lp().art.disconnect(self._cover_signal)
            self._cover_signal = None
