#!/usr/bin/python
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

from gi.repository import Gtk

from lollypop.define import Lp, ArtSize


# Show next track to play
class NextPopover(Gtk.Popover):
    """
        Init popover
    """
    def __init__(self):
        Gtk.Popover.__init__(self)
        self.set_modal(False)
        self.get_style_context().add_class('osd-popover')
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/NextPopover.ui')
        self.add(builder.get_object('widget'))
        self._title_label = builder.get_object('title')
        self._artist_label = builder.get_object('artist')
        self._cover = builder.get_object('cover')
        self._scale = self._cover.get_scale_factor()
        Lp.player.connect('queue-changed', self.update)

    """
        Update widget with current track
    """
    def update(self, player=None):
        self._artist_label.set_text(Lp.player.next_track.artist)
        self._title_label.set_text(Lp.player.next_track.title)
        art = Lp.art.get_album(Lp.player.next_track.album_id,
                               ArtSize.MEDIUM*self._scale)
        if art is not None:
            self._cover.set_from_pixbuf(art)
            del art
            self._cover.set_tooltip_text(Lp.player.next_track.album)
            self._cover.show()
        else:
            self._cover.hide()
