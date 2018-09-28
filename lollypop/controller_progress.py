# Copyright (c) 2014-2018 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import GLib, Gst

from gettext import gettext as _

from lollypop.define import Type, App
from lollypop.utils import seconds_to_string


class ProgressController:
    """
        Progress controller (for toolbars)
    """

    def __init__(self):
        """
            Init progress controller (for toolbars)
        """
        # Prevent updating progress while seeking
        self.__seeking = False
        # Update pogress position
        self.__timeout_id = None
        # Show volume control
        self.__show_volume_control = False

    def show_hide_volume_control(self):
        """
            Show/Hide volume control
        """
        self._progress.clear_marks()
        self.__show_volume_control = not self.__show_volume_control
        self._update_state()

    def on_current_changed(self, player):
        """
            Update scale on current changed
            @param player as Player
        """
        if self.__show_volume_control:
            return
        self._progress.clear_marks()
        if player.current_track.id is None:
            self._progress.set_sensitive(False)
            self._total_time_label.set_text("")
            self._timelabel.set_text("")
            return

        self._progress.set_value(0.0)
        self._timelabel.set_text("0:00")
        if player.current_track.id == Type.RADIOS:
            self._progress.set_sensitive(False)
            self._total_time_label.set_text("")
            self._progress.set_range(0.0, 0.0)
        else:
            self._progress.set_sensitive(True)
            self._progress.set_range(0.0, player.current_track.duration)
            self._total_time_label.set_text(
                seconds_to_string(player.current_track.duration))

    def on_status_changed(self, player):
        """
            Update buttons and progress bar
            @param player as Player
        """
        if player.is_playing:
            if self.__timeout_id is None:
                self.__timeout_id = GLib.timeout_add(1000,
                                                     self.update_position)
        else:
            self.update_position()
            if self.__timeout_id is not None:
                GLib.source_remove(self.__timeout_id)
                self.__timeout_id = None

    def update_position(self, value=None):
        """
            Update progress bar position
            @param value as int
        """
        if self.__show_volume_control:
            # We need this to allow crossfade while volume is shown
            App().player.position
            if value is None:
                value = App().player.volume
            self._progress.set_value(value)
            volume = str(int(value * 100)) + " %"
            self._total_time_label.set_text(volume)
        elif not self.__seeking:
            if value is None and App().player.get_status() != Gst.State.PAUSED:
                value = App().player.position / Gst.SECOND
            if value is not None:
                self._progress.set_value(value)
                self._timelabel.set_text(seconds_to_string(value))
        return True

    def do_destroy(self):
        """
            Remove timeout
        """
        if self.__timeout_id is not None:
            GLib.source_remove(self.__timeout_id)
            self.__timeout_id = None

    @property
    def show_volume_control(self):
        """
            True if volume control is shown
            @return bool
        """
        return self.__show_volume_control

#######################
# PROTECTED           #
#######################
    def _update_state(self):
        """
            Update controller state volume vs progress
        """
        if self.__show_volume_control:
            self._timelabel.set_text(_("Volume"))
            # Inhibit _on_value_changed()
            self.__show_volume_control = False
            self._progress.set_range(0.0, 1.0)
            self.__show_volume_control = True
            self._progress.set_sensitive(True)
            self.update_position()
        else:
            ProgressController.on_current_changed(self, App().player)
            if App().player.current_track.id is None:
                self._timelabel.set_text("")
                self._progress.set_value(0.0)
                self._progress.set_range(0.0, 0.0)
                self._progress.set_sensitive(False)
            else:
                self.update_position()

    def _on_value_changed(self, scale):
        """
            Adjust volume
        """
        if not self.__show_volume_control:
            return
        App().player.set_volume(scale.get_value())
        self.update_position(scale.get_value())

    def _on_title_press_button(self, widget, event):
        """
            Show/Hide volume control
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        if event.button != 1:
            self.show_hide_volume_control()
        return True

    def _on_progress_press_button(self, scale, event):
        """
            On press, mark player as seeking
            @param scale as Gtk.Scale
            @param event as Gdk.Event
        """
        if event.button != 1:
            self.show_hide_volume_control()
            return True
        if self.__show_volume_control:
            return
        if App().player.is_locked:
            return True
        self.__seeking = True

    def _on_progress_release_button(self, scale, event):
        """
            Callback for scale release button
            Seek player to scale value
            @param scale as Gtk.Scale
            @param event as Gdk.Event
        """
        if self.__show_volume_control or event.button != 1:
            return
        value = scale.get_value()
        App().player.seek(value)
        self.__seeking = False
        self.update_position(value)

    def _on_scroll_event(self, scale, event):
        """
            Seek forward or backward
            @param scale as Gtk.Scale
            @param event as Gdk.Event
        """
        (smooth, x, y) = event.get_scroll_deltas()
        if smooth:
            if self.__show_volume_control:
                volume = App().player.volume
                if y > 0:
                    volume -= 0.1
                else:
                    volume += 0.1
                if volume < 0:
                    volume = 0.0
                elif volume > 1:
                    volume = 1.0
                App().player.set_volume(volume)
                self.update_position(volume)
            elif App().player.is_playing:
                position = App().player.position
                if y > 0:
                    seek = position - 5 * Gst.SECOND
                else:
                    seek = position + 5 * Gst.SECOND
                if seek < 0:
                    seek = 0
                if seek > App().player.current_track.duration:
                    seek = App().player.current_track.duration - 2
                App().player.seek(seek)
                self.update_position(seek)

#######################
# PRIVATE             #
#######################
