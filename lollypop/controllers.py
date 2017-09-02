# Copyright (c) 2014-2017 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from lollypop.define import Type, Lp
from lollypop.utils import seconds_to_string


class PlaybackController:
    """
        Button controller (for toolbars)
    """

    def __init__(self):
        """
            Init controller
        """
        pass

    def on_current_changed(self, player):
        """
            Update toolbar
            @param player as Player
        """
        self._play_btn.set_sensitive(True)
        self._prev_btn.set_sensitive(not Lp().player.locked)
        self._next_btn.set_sensitive(not Lp().player.locked)

    def on_prev_changed(self, player):
        """
            Update prev button
            @param player as Player
        """
        if player.prev_track.id == Type.RADIOS:
            self._prev_btn.set_tooltip_text(
                                    ", ".join(player.prev_track.album_artists))
        elif player.prev_track.id is not None:
            prev_artists = GLib.markup_escape_text(
                                          ", ".join(player.prev_track.artists))
            prev_title = GLib.markup_escape_text(player.prev_track.title)
            self._prev_btn.set_tooltip_markup("<b>%s</b> - %s" %
                                              (prev_artists,
                                               prev_title))
        else:
            self._prev_btn.set_tooltip_text("")

    def on_next_changed(self, player):
        """
            Update toolbar
            @param player as Player
        """
        if player.next_track.id == Type.RADIOS:
            self._next_btn.set_tooltip_text(
                                    ", ".join(player.next_track.album_artists))
        elif player.next_track.id is not None:
            next_artists = GLib.markup_escape_text(
                                          ", ".join(player.next_track.artists))
            next_title = GLib.markup_escape_text(player.next_track.title)
            self._next_btn.set_tooltip_markup("<b>%s</b> - %s" %
                                              (next_artists,
                                               next_title))
        else:
            self._prev_btn.set_tooltip_text("")

    def on_status_changed(self, player):
        """
            Update buttons and progress bar
            @param player as Player
        """
        # GTK bug, should not be needed, see #1214
        self._play_btn.set_sensitive(True)
        if player.is_playing:
            self.__change_play_btn_status(self._pause_image, _("Pause"))
        else:
            self.__change_play_btn_status(self._play_image, _("Play"))

#######################
# PROTECTED           #
#######################
    def _on_prev_btn_clicked(self, button):
        """
            Previous track on prev button clicked
            @param button as Gtk.Button
        """
        Lp().player.prev()

    def _on_play_btn_clicked(self, button):
        """
            Play/Pause on play button clicked
            @param button as Gtk.Button
        """
        if Lp().player.is_playing:
            Lp().player.pause()
            self.__change_play_btn_status(self._play_image, _("Play"))
        else:
            Lp().player.play()
            self.__change_play_btn_status(self._pause_image, _("Pause"))

    def _on_next_btn_clicked(self, button):
        """
            Next track on next button clicked
            @param button as Gtk.Button
        """
        Lp().player.next()

#######################
# PRIVATE             #
#######################
    def __change_play_btn_status(self, image, status):
        """
            Update play button with image and status as tooltip
            @param image as Gtk.Image
            @param status as str
        """
        self._play_btn.set_image(image)
        self._play_btn.set_tooltip_text(status)


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
        self._show_volume_control = False
        Lp().player.connect("duration-changed", self.__on_duration_changed)

    def on_current_changed(self, player):
        """
            Update scale on current changed
            @param player as Player
        """
        if self._show_volume_control:
            return
        self._progress.clear_marks()
        if player.current_track.id is None:
            self._progress.set_sensitive(False)
            self._total_time_label.set_text("")
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
                                                     self._update_position)
        else:
            self._update_position()
            if self.__timeout_id is not None:
                GLib.source_remove(self.__timeout_id)
                self.__timeout_id = None

#######################
# PROTECTED           #
#######################
    def _update_state(self):
        """
            Update controller state volume vs progress
        """
        if self._show_volume_control:
            self._timelabel.set_text(_("Volume"))
            # Inhibit _on_value_changed()
            self._show_volume_control = False
            self._progress.set_range(0.0, 1.0)
            self._show_volume_control = True
            self._progress.set_sensitive(True)
            self._update_position()
        else:
            self.on_current_changed(Lp().player)
            if Lp().player.current_track.id is None:
                self._timelabel.set_text("")
                self._progress.set_value(0.0)
                self._progress.set_range(0.0, 0.0)
                self._progress.set_sensitive(False)
            else:
                self._update_position()

    def _on_value_changed(self, scale):
        """
            Adjust volume
        """
        if not self._show_volume_control:
            return
        Lp().player.set_volume(scale.get_value())
        self._update_position(scale.get_value())

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
        if self._show_volume_control:
            return
        if Lp().player.locked:
            return True
        self.__seeking = True

    def _on_progress_release_button(self, scale, event):
        """
            Callback for scale release button
            Seek player to scale value
            @param scale as Gtk.Scale
            @param event as Gdk.Event
        """
        if self._show_volume_control or event.button != 1:
            return
        value = scale.get_value()
        Lp().player.seek(value)
        self.__seeking = False
        self._update_position(value)

    def _on_scroll_event(self, scale, event):
        """
            Seek forward or backward
            @param scale as Gtk.Scale
            @param event as Gdk.Event
        """
        (smooth, x, y) = event.get_scroll_deltas()
        if smooth:
            if self._show_volume_control:
                volume = Lp().player.volume
                if y > 0:
                    volume -= 0.1
                else:
                    volume += 0.1
                if volume < 0:
                    volume = 0.0
                elif volume > 1:
                    volume = 1.0
                Lp().player.set_volume(volume)
                self._update_position(volume)
            elif Lp().player.is_playing:
                position = Lp().player.position
                if y > 0:
                    seek = position - 5 * Gst.SECOND
                else:
                    seek = position + 5 * Gst.SECOND
                if seek < 0:
                    seek = 0
                if seek > Lp().player.current_track.duration:
                    seek = Lp().player.current_track.duration - 2
                Lp().player.seek(seek)
                self._update_position(seek)

    def _update_position(self, value=None):
        """
            Update progress bar position
            @param value as int
        """
        if self._show_volume_control:
            if value is None:
                value = Lp().player.volume
            self._progress.set_value(value)
            volume = str(int(value * 100)) + " %"
            self._total_time_label.set_text(volume)
        elif not self.__seeking:
            if value is None and Lp().player.get_status() != Gst.State.PAUSED:
                value = Lp().player.position / Gst.SECOND
            if value is not None:
                self._progress.set_value(value)
                self._timelabel.set_text(seconds_to_string(value))
        return True

#######################
# PRIVATE             #
#######################
    def __on_duration_changed(self, player, track_id):
        """
            Update duration
            @param player as Player
            @param track id as int
        """
        if track_id == player.current_track.id:
            self._progress.set_range(0.0, player.current_track.duration)
            self._total_time_label.set_text(
                    seconds_to_string(player.current_track.duration))


class InfoController:
    """
        Infos controller (for toolbars)
    """

    def __init__(self, artsize):
        """
            Init controller
        """
        self._infobox = None
        self._spinner = None
        self._artsize = artsize

    def on_current_changed(self, player):
        """
            Update toolbar on current changed
            @param player as Player
        """
        art = None

        if player.current_track.id is None:
            if self._infobox is not None:
                self._infobox.hide()
            self._cover.hide()
            return

        # Stop spinner if running
        if self._spinner is not None:
            self._spinner.hide()
            self._spinner.stop()

        self._artist_label.set_text(", ".join(player.current_track.artists))
        self._artist_label.show()
        self._title_label.set_text(player.current_track.title)
        self._title_label.show()

        if player.current_track.id == Type.RADIOS:
            art = Lp().art.get_radio_artwork(
                                   ", ".join(player.current_track.artists),
                                   self._artsize,
                                   self.get_scale_factor())
        elif player.current_track.id == Type.EXTERNALS:
            art = Lp().art.get_album_artwork2(
                    player.current_track.uri,
                    self._artsize,
                    self.get_scale_factor())
        elif player.current_track.id is not None:
            art = Lp().art.get_album_artwork(
                                   player.current_track.album,
                                   self._artsize,
                                   self.get_scale_factor())
        if art is not None:
            self._cover.set_from_surface(art)
            del art
            self._cover.set_tooltip_text(player.current_track.album.name)
            self._cover.show()
        else:
            self._cover.hide()
        if self._infobox is not None:
            self._infobox.show()

    @property
    def artsize(self):
        """
            Art size as int
        """
        return self._artsize
