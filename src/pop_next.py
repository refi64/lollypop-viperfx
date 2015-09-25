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

from lollypop.define import Lp, ArtSize, Shuffle


class NextPopover(Gtk.Popover):
    """
        Popover with next track
    """

    def __init__(self):
        """
            Init popover
        """
        Gtk.Popover.__init__(self)
        self.connect('map', self._on_map)
        self.connect('unmap', self._on_unmap)
        self.set_modal(False)
        self.get_style_context().add_class('osd-popover')
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/NextPopover.ui')
        builder.connect_signals(self)
        self.add(builder.get_object('widget'))
        self._title_label = builder.get_object('title')
        self._artist_label = builder.get_object('artist')
        self._cover = builder.get_object('cover')
        self._skip_btn = builder.get_object('skip_btn')
        self._signal_id = Lp.player.connect('queue-changed', self.update)

    def update(self, player=None):
        """
            Update widget with current track
        """
        if Lp.player.is_party() or\
                Lp.settings.get_enum('shuffle') == Shuffle.TRACKS:
            self._skip_btn.show()
        self._artist_label.set_text(Lp.player.next_track.artist)
        self._title_label.set_text(Lp.player.next_track.title)
        art = Lp.art.get_album(Lp.player.next_track.album,
                               ArtSize.MEDIUM * self.get_scale_factor())
        if art is not None:
            self._cover.set_from_surface(art)
            del art
            self._cover.set_tooltip_text(Lp.player.next_track.album.name)
            self._cover.show()
        else:
            self._cover.hide()

#######################
# PRIVATE             #
#######################
    def _on_map(self, widget):
        """
            Connect signal
            @param widget as Gtk.Widget
        """
        self._signal_id = Lp.player.connect('queue-changed', self.update)
        print('map')

    def _on_unmap(self, widget):
        """
            Disconnect signal
            @param widget as Gtk.Widget
        """
        print('unmap')
        if self._signal_id is not None:
            Lp.player.disconnect(self._signal_id)

    def _on_skip_btn_clicked(self, btn):
        """
            Skip next track
            @param btn as Gtk.Button
        """
        Lp.player.set_next()
        Lp.player.emit('queue-changed')
