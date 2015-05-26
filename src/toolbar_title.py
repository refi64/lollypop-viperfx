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

from gi.repository import Gtk, GLib

from lollypop.define import Lp, Type
from lollypop.utils import seconds_to_string


class ToolbarTitle(Gtk.Bin):
    """
        Init title toolbar
    """
    def __init__(self):
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

        self._timelabel = builder.get_object('playback')
        self._total_time_label = builder.get_object('duration')

    """
        Set Gtk.Scale progress width
        @param width as int
    """
    def set_progress_width(self, width):
        self._progress.set_property("width_request", width)

    """
        Update progress bar position
        @param value as int
    """
    def update_position(self, value=None):
        if not self._seeking:
            if value is None:
                value = Lp.player.get_position_in_track()/1000000
            self._progress.set_value(value)
            self._timelabel.set_text(seconds_to_string(value/60))
        return True

    """
        Update scale on current changed
        @param player as Player
    """
    def on_current_changed(self, player):
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

    """
        Update buttons and progress bar
        @param player as Player
    """
    def on_status_changed(self, player):
        if player.current_track.id != Type.RADIOS:
            self._progress.set_sensitive(player.is_playing())

        if player.is_playing():
            if player.current_track.id == Type.RADIOS and self._timeout:
                GLib.source_remove(self._timeout)
                self._timeout = None
            elif not self._timeout:
                self._timeout = GLib.timeout_add(1000, self.update_position)
        else:
            self.update_position()
            if self._timeout:
                GLib.source_remove(self._timeout)
                self._timeout = None

#######################
# PRIVATE             #
#######################
    """
        On press, mark player as seeking
        @param unused
    """
    def _on_progress_press_button(self, scale, data):
        self._seeking = True

    """
        Callback for scale release button
        Seek player to scale value
        @param scale as Gtk.Scale, data as unused
    """
    def _on_progress_release_button(self, scale, data):
        value = scale.get_value()
        self._seeking = False
        self.update_position(value)
        Lp.player.seek(value/60)
