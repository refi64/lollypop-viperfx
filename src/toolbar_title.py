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

from gi.repository import Gtk, GLib, Gdk

from lollypop.define import Lp, Type
from lollypop.pop_slider import SliderPopover
from lollypop.utils import seconds_to_string


class ToolbarTitle(Gtk.Bin):
    """
        Title toolbar
    """

    def __init__(self):
        """
            Init toolbar
        """
        # Prevent updating progress while seeking
        self._seeking = False
        # Update pogress position
        self._timeout = None
        Gtk.Bin.__init__(self)
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/ToolbarTitle.ui')
        builder.connect_signals(self)

        self.add(builder.get_object('title'))

        self._progress = builder.get_object('progress_scale')
        self._progress.set_sensitive(False)

        self._popover = SliderPopover()
        self._popover.set_relative_to(self._progress)

        self._timelabel = builder.get_object('playback')
        self._total_time_label = builder.get_object('duration')

    def set_progress_width(self, width):
        """
            Set Gtk.Scale progress width
            @param width as int
        """
        self._progress.set_property("width_request", width)

    def update_position(self, value=None):
        """
            Update progress bar position
            @param value as int
        """
        if not self._seeking:
            if value is None:
                value = Lp.player.get_position_in_track()/1000000
            self._progress.set_value(value)
            self._timelabel.set_text(seconds_to_string(value/60))
        return True

    def on_current_changed(self, player):
        """
            Update scale on current changed
            @param player as Player
        """
        self._progress.set_value(0.0)
        if player.current_track.id == Type.RADIOS:
            self._progress.set_sensitive(False)
            self._total_time_label.hide()
            self._timelabel.hide()
            self._progress.set_range(0.0, 0.0)
        else:
            self._progress.set_range(0.0, player.current_track.duration * 60)
            self._total_time_label.set_text(
                seconds_to_string(player.current_track.duration))
            self._total_time_label.show()
            self._timelabel.set_text("0:00")
            self._timelabel.show()

    def on_status_changed(self, player):
        """
            Update buttons and progress bar
            @param player as Player
        """
        if player.current_track.id != Type.RADIOS:
            self._progress.set_sensitive(player.current_track.id is not None)

        if player.is_playing():
            self.set_opacity(1)
            if player.current_track.id == Type.RADIOS and self._timeout:
                GLib.source_remove(self._timeout)
                self._timeout = None
            elif not self._timeout:
                self._timeout = GLib.timeout_add(1000, self.update_position)
        else:
            self.set_opacity(0.5)
            self.update_position()
            if self._timeout:
                GLib.source_remove(self._timeout)
                self._timeout = None

#######################
# PRIVATE             #
#######################
    def _on_progress_motion_notify(self, eventbox, event):
        """
            Show progress popover
            @param eventbox as Gtk.EventBox
            @param event as Gdk.Event
        """
        if Gtk.get_minor_version() > 14:
            slider_width = self._progress.style_get_property(
                                                            'slider-width') / 2
        else:
            slider_width = 14
        rect = self._progress.get_range_rect()
        if event.x < slider_width or\
           event.x > rect.width - slider_width:
            return

        current = (event.x - slider_width) *\
            self._progress.get_adjustment().get_upper() /\
            (rect.width - slider_width * 2)
        self._popover.set(seconds_to_string(current/60))
        r = Gdk.Rectangle()
        r.x = event.x
        r.y = rect.height
        r.width = 1
        r.height = 1
        self._popover.set_pointing_to(r)
        self._popover.show()

    def _on_progress_leave_notify(self, eventbox, event):
        """
            Show progress popover
            @param eventbox as Gtk.EventBox
            @param event as Gdk.Event
        """
        self._popover.delayed_hide()

    def _on_progress_press_button(self, scale, event):
        """
            On press, mark player as seeking
            @param scale as Gtk.Scale
            @param event as Gdk.Event
        """
        self._seeking = True

    def _on_progress_release_button(self, scale, event):
        """
            Callback for scale release button
            Seek player to scale value
            @param scale as Gtk.Scale
            @param event as Gdk.Event
        """
        value = scale.get_value()
        self._seeking = False
        self.update_position(value)
        Lp.player.seek(value/60)
