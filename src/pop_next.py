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
        self._inhibited = False
        self.set_position(Gtk.PositionType.BOTTOM)
        self.connect('map', self._on_map)
        self.connect('unmap', self._on_unmap)
        self.connect('enter-notify-event', self._on_enter_notify)
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

    def update(self, unused=None):
        """
            Update widget with next track
        """
        self._artist_label.set_text(", ".join(Lp().player.next_track.artists))
        self._title_label.set_text(Lp().player.next_track.title)
        art = Lp().art.get_album_artwork(
                               Lp().player.next_track.album,
                               ArtSize.MEDIUM,
                               self.get_scale_factor())
        if art is not None:
            self._cover.set_from_surface(art)
            del art
            self._cover.set_tooltip_text(Lp().player.next_track.album.name)
            self._cover.show()
            queue = Lp().player.get_queue()
            if queue and queue[0] == Lp().player.next_track.id:
                self._skip_btn.hide()
            else:
                self._skip_btn.show()
        else:
            self._cover.hide()

    def should_be_shown(self):
        """
            Return True if widget should be shown, not already closed by user
        """
        return not self._inhibited and (
                Lp().player.is_party() or
                Lp().settings.get_enum('shuffle') == Shuffle.TRACKS) and\
            Lp().player.next_track.id is not None and\
            Lp().player.next_track.id >= 0

    def inhibit(self, i):
        """
            Inhibit popover
            @param i as bool
        """
        self._inhibited = i

    @property
    def inhibited(self):
        """
            Inhibited as bool
        """
        return self._inhibited

#######################
# PRIVATE             #
#######################
    def _on_map(self, widget):
        """
            Connect signal
            @param widget as Gtk.Widget
        """
        self._inhibited = False
        self.update()
        self._signal_id = Lp().player.connect('queue-changed', self.update)

    def _on_unmap(self, widget):
        """
            Disconnect signal
            @param widget as Gtk.Widget
        """
        if self._signal_id is not None:
            Lp().player.disconnect(self._signal_id)
            self._signal_id = None

    def _on_enter_notify(self, widget, event):
        """
            Disable overlays
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        Lp().window.disable_overlays()

    def _on_button_enter_notify(self, widget, event):
        """
            Change opacity
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        widget.set_opacity(0.8)

    def _on_button_leave_notify(self, widget, event):
        """
            Change opacity
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        widget.set_opacity(0.2)

    def _on_button_release(self, widget, event):
        """
            Hide popover
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        self.hide()

    def _on_skip_btn_clicked(self, btn):
        """
            Skip next track
            @param btn as Gtk.Button
        """
        Lp().player.set_next()
        Lp().player.emit('queue-changed')
