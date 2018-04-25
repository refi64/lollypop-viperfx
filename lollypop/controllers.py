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
        is_radio = App().player.current_track.id == Type.RADIOS
        self._play_btn.set_sensitive(True)
        self._prev_btn.set_sensitive(not App().player.locked and not is_radio)
        self._next_btn.set_sensitive(not App().player.locked and not is_radio)

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
        App().player.prev()

    def _on_play_btn_clicked(self, button):
        """
            Play/Pause on play button clicked
            @param button as Gtk.Button
        """
        if App().player.is_playing:
            App().player.pause()
            self.__change_play_btn_status(self._play_image, _("Play"))
        else:
            App().player.play()
            self.__change_play_btn_status(self._pause_image, _("Pause"))

    def _on_next_btn_clicked(self, button):
        """
            Next track on next button clicked
            @param button as Gtk.Button
        """
        App().player.next()

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
        App().player.connect("duration-changed", self.__on_duration_changed)

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
                                                     self._update_position)
        else:
            self._update_position()
            if self.__timeout_id is not None:
                GLib.source_remove(self.__timeout_id)
                self.__timeout_id = None

    def do_destroy(self):
        """
            Remove timeout
        """
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
            self.on_current_changed(App().player)
            if App().player.current_track.id is None:
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
        App().player.set_volume(scale.get_value())
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
        if App().player.locked:
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
        App().player.seek(value)
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
                self._update_position(volume)
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
                self._update_position(seek)

    def _update_position(self, value=None):
        """
            Update progress bar position
            @param value as int
        """
        if self._show_volume_control:
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

    def __init__(self):
        """
            Init controller
        """
        self._infobox = None

    def on_current_changed(self, art_size, font_size):
        """
            Update labels and cover and handles widget visibility
            @param art_size as int
            @param font_size as int
        """
        if App().player.current_track.id is None:
            if self._infobox is not None:
                self._infobox.hide()
            self._cover.hide()
            return
        elif self._infobox is not None:
            self._infobox.show()
        self.update_labels(font_size)
        self.update_artwork(art_size, art_size, False)

    def update_labels(self, font_size):
        """
            Update labels
            @param font_size as int
        """
        if App().player.current_track.id == Type.RADIOS:
            artist_text = App().player.current_track.album_artists[0]
        else:
            artist_text = ", ".join(App().player.current_track.artists)
        if font_size is None:
            self._artist_label.set_text(artist_text)
        else:
            self._artist_label.set_markup(
                "<span font='%s'>%s</span>" %
                (font_size - 2,
                 GLib.markup_escape_text(artist_text)))
        self._artist_label.show()

        title_text = App().player.current_track.title
        if font_size is None:
            self._title_label.set_text(title_text)
        else:
            self._title_label.set_markup(
                "<span font='%s'>%s</span>" %
                                        (font_size,
                                         GLib.markup_escape_text(title_text)))
        self._title_label.show()

    def update_artwork(self, width, height, enable_blur):
        """
            Update artwork
            @param width as int
            @param height as int
            @param enable_blur as bool
        """
        if width < 1 or height < 1:
            return
        artwork = None
        if App().player.current_track.id == Type.RADIOS:
            artwork = App().art.get_radio_artwork(
                App().player.current_track.album_artists[0],
                width,
                self.get_scale_factor())
        elif App().player.current_track.id == Type.EXTERNALS:
            artwork = App().art.get_album_artwork2(
                App().player.current_track.uri,
                width,
                self.get_scale_factor())
        elif App().player.current_track.id is not None:
            artwork = App().art.get_album_artwork(
                App().player.current_track.album,
                width,
                self.get_scale_factor())
        if artwork is not None:
            if enable_blur:
                from lollypop.utils import blur
                blur(artwork, self._cover, width, height)
            else:
                self._cover.set_from_surface(artwork)
            self._cover.set_tooltip_text(App().player.current_track.album.name)
            self._cover.show()
        else:
            self._cover.hide()

    def set_artsize(self, artsize):
        """
            Set a new artsize for controller
            @param artsize as int
        """
        self.__artsize = artsize

    @property
    def artsize(self):
        """
            Art size as int
        """
        return self.__artsize
