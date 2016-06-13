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

from gi.repository import GLib, Gst

from cgi import escape
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
        # Can add a \n in markup
        # GTK bug => https://bugzilla.gnome.org/show_bug.cgi?id=749965
        if player.prev_track.id == Type.RADIOS:
            self._prev_btn.set_tooltip_text(
                                    ", ".join(player.prev_track.album_artists))
        elif player.prev_track.id is not None:
            prev_artists = escape(", ".join(player.prev_track.artists))
            prev_title = escape(player.prev_track.title)
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
            next_artists = escape(", ".join(player.next_track.artists))
            next_title = escape(player.next_track.title)
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
        if player.is_playing():
            self._change_play_btn_status(self._pause_image, _("Pause"))
        else:
            self._change_play_btn_status(self._play_image, _("Play"))

#######################
# PRIVATE             #
#######################
    def _change_play_btn_status(self, image, status):
        """
            Update play button with image and status as tooltip
            @param image as Gtk.Image
            @param status as str
        """
        self._play_btn.set_image(image)
        self._play_btn.set_tooltip_text(status)

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
        if Lp().player.is_playing():
            Lp().player.pause()
            self._change_play_btn_status(self._play_image, _("Play"))
        else:
            Lp().player.play()
            self._change_play_btn_status(self._pause_image, _("Pause"))

    def _on_next_btn_clicked(self, button):
        """
            Next track on next button clicked
            @param button as Gtk.Button
        """
        Lp().player.next()


class ProgressController:
    """
        Progress controller (for toolbars)
    """

    def __init__(self):
        """
            Init progress controller (for toolbars)
        """
        # Prevent updating progress while seeking
        self._seeking = False
        # Update pogress position
        self._timeout_id = None

    def on_current_changed(self, player):
        """
            Update scale on current changed
            @param player as Player
        """
        self._progress.clear_marks()
        if player.current_track.id != Type.RADIOS:
            self._progress.set_sensitive(player.current_track.id is not None)
        self._progress.set_value(0.0)
        self._timelabel.set_text("0:00")
        if player.current_track.id == Type.RADIOS:
            self._progress.set_sensitive(False)
            self._total_time_label.set_text('')
            self._progress.set_range(0.0, 0.0)
        else:
            self._progress.set_range(0.0, player.current_track.duration * 60)
            self._total_time_label.set_text(
                seconds_to_string(player.current_track.duration))

    def on_status_changed(self, player):
        """
            Update buttons and progress bar
            @param player as Player
        """
        if player.is_playing():
            if self._timeout_id is None:
                self._timeout_id = GLib.timeout_add(1000,
                                                    self._update_position)
        else:
            self._update_position()
            if self._timeout_id is not None:
                GLib.source_remove(self._timeout_id)
                self._timeout_id = None

#######################
# PRIVATE             #
#######################
    def _update_position(self, value=None):
        """
            Update progress bar position
            @param value as int
        """
        if not self._seeking:
            if value is None and Lp().player.get_status() != Gst.State.PAUSED:
                value = Lp().player.position/1000000
            if value is not None:
                self._progress.set_value(value)
                self._timelabel.set_text(seconds_to_string(value/60))
        return True

    def _on_progress_press_button(self, scale, event):
        """
            On press, mark player as seeking
            @param scale as Gtk.Scale
            @param event as Gdk.Event
        """
        if Lp().player.locked:
            return True
        self._seeking = True

    def _on_progress_release_button(self, scale, event):
        """
            Callback for scale release button
            Seek player to scale value
            @param scale as Gtk.Scale
            @param event as Gdk.Event
        """
        value = scale.get_value()
        Lp().player.seek(value/60)
        self._seeking = False
        self._update_position(value)

    def _on_scroll_event(self, scale, event):
        """
            Seek forward or backward
            @param scale as Gtk.Scale
            @param event as Gdk.Event
        """
        (smooth, x, y) = event.get_scroll_deltas()
        if smooth and Lp().player.is_playing():
            position = Lp().player.position
            if y > 0:
                seek = position/1000000/60-5
            else:
                seek = position/1000000/60+5
            if seek < 0:
                seek = 0
            if seek > Lp().player.current_track.duration:
                seek = Lp().player.current_track.duration - 2
            Lp().player.seek(seek)
            self._update_position(seek*60)


class InfosController:
    """
        Infos controller (for toolbars)
    """

    def __init__(self, artsize):
        """
            Init controller
        """
        self._infobox = None
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

        self._artist_label.set_text(", ".join(player.current_track.artists))
        self._title_label.set_text(player.current_track.title)

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
