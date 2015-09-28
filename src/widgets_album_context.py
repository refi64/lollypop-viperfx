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

from gi.repository import Gdk

from lollypop.define import Type
from lollypop.pop_infos import InfosPopover
from lollypop.widgets_album import AlbumDetailedWidget


class AlbumContextWidget(AlbumDetailedWidget):
    """
        Widget with cover and tracks
    """

    def __init__(self, album_id, genre_id, pop_allowed, size_group):
        """
            Init detailed album widget
            @param album id as int
            @param genre id as int
            @param parent width as int
            @param pop_allowed as bool if widget can show popovers
            @param size group as Gtk.SizeGroup
        """
        AlbumDetailedWidget.__init__(self, album_id, genre_id,
                                     pop_allowed, size_group)
        self._artist_label.set_text(self._album.artist_name)
        self._artist_label.show()

#######################
# PRIVATE             #
#######################
    def _on_label_realize(self, eventbox):
        """
            Change pointer on label
            @param eventbox as Gtk.EventBox
        """
        if InfosPopover.should_be_shown() and\
                self._album.artist_id != Type.COMPILATIONS:
            eventbox.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND1))

    def _on_label_button_release(self, eventbox, event):
        """
            On clicked label, show artist informations in a popover
            @param eventbox as Gtk.EventBox
            @param event as Gdk.Event
        """
        if InfosPopover.should_be_shown() and\
                self._album.artist_id != Type.COMPILATIONS:
            pop = InfosPopover(self._album.artist_id)
            pop.set_relative_to(eventbox)
            pop.show()
