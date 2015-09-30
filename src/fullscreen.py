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

from gi.repository import Gtk, Gdk, GLib

from cgi import escape
from gettext import gettext as _
from datetime import datetime

from lollypop.define import Lp, ArtSize, Type
from lollypop.utils import seconds_to_string
from lollypop.pop_slider import SliderPopover
from lollypop.pop_next import NextPopover


class FullScreen(Gtk.Window):
    """
        Show a fullscreen window showing current track context
    """

    def __init__(self, app, parent):
        """
            Init window and set transient for parent
            @param app as Gio.Application
            @param parent as Gtk.window
        """
        Gtk.Window.__init__(self)
        self.set_application(app)
        self._timeout1 = None
        self._timeout2 = None
        self._seeking = False
        self._signal1_id = None
        self._signal2_id = None
        self.set_decorated(False)
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/FullScreen.ui')
        builder.connect_signals(self)

        self._play_btn = builder.get_object('play_btn')
        self._next_btn = builder.get_object('next_btn')
        self._prev_btn = builder.get_object('prev_btn')
        self._next_popover = NextPopover()
        self._next_popover.set_position(Gtk.PositionType.BOTTOM)
        self._play_image = builder.get_object('play_image')
        self._pause_image = builder.get_object('pause_image')
        close_btn = builder.get_object('close_btn')
        close_btn.connect('clicked', self._destroy)
        self._cover = builder.get_object('cover')
        self._title = builder.get_object('title')
        self._artist = builder.get_object('artist')
        self._album = builder.get_object('album')

        self._datetime = builder.get_object('datetime')

        self._progress = builder.get_object('progress_scale')
        self._slider_popover = SliderPopover()
        self._slider_popover.set_relative_to(self._progress)
        self._slider_popover.set_position(Gtk.PositionType.BOTTOM)
        self._timelabel = builder.get_object('playback')
        self._total_time_label = builder.get_object('duration')
        self.connect('key-release-event', self._on_key_release_event)
        self.add(builder.get_object('widget'))

    def do_show(self):
        """
            Init signals, set color and go party mode if nothing is playing
        """
        is_playing = Lp.player.is_playing()
        self._signal1_id = Lp.player.connect('current-changed',
                                             self._on_current_changed)
        self._signal2_id = Lp.player.connect('status-changed',
                                             self._on_status_changed)
        if is_playing:
            self._change_play_btn_status(self._pause_image, _('Pause'))
            self._on_current_changed(Lp.player)
        else:
            Lp.player.set_party(True)
        if self._timeout1 is None:
            self._timeout1 = GLib.timeout_add(1000, self._update_position)
        Gtk.Window.do_show(self)
        now = datetime.now()
        self._datetime.set_label(now.strftime('%a %d %b, %X')[:-3])
        if self._timeout2 is None:
            second = datetime.now().second
            if 60 - second > 0:
                GLib.timeout_add((60-second)*1000, self._update_datetime)
            else:
                self._timeout2 = GLib.timeout_add(60000, self._update_datetime)
        self._update_position()
        self.fullscreen()
        self._next_popover.set_relative_to(self._album)
        if Lp.player.next_track.id != Type.RADIOS:
            self._next_popover.show()

    def do_hide(self):
        """
            Remove signals and unset color
        """
        Gtk.Window.do_hide(self)
        if self._signal1_id is not None:
            Lp.player.disconnect(self._signal1_id)
            self._signal1_id = None
        if self._signal2_id is not None:
            Lp.player.disconnect(self._signal2_id)
            self._signal2_id = None
        if self._timeout1 is not None:
            GLib.source_remove(self._timeout1)
            self._timeout1 = None
        if self._timeout2 is not None:
            GLib.source_remove(self._timeout2)
        self._next_popover.set_relative_to(None)
        self._next_popover.hide()

#######################
# PRIVATE             #
#######################
    def _update_datetime(self):
        """
            Update datetime in headerbar
        """
        now = datetime.now()
        self._datetime.set_label(now.strftime('%a %d %b, %X')[:-3])
        if self._timeout2 is None:
            self._timeout2 = GLib.timeout_add(60000, self._update_datetime)
            return False
        return True

    def _change_play_btn_status(self, image, status):
        """
            Update play button with image and status as tooltip
            @param image as Gtk.Image
            @param status as str
        """
        self._play_btn.set_image(image)
        self._play_btn.set_tooltip_text(status)

    def _update_position(self, value=None):
        """
            Update progress bar position
            @param value as int
        """
        if not self._seeking and self._progress.is_visible():
            if value is None:
                value = Lp.player.get_position_in_track()/1000000
            self._progress.set_value(value)
            self._timelabel.set_text(seconds_to_string(value/60))
        return True

    def _destroy(self, widget):
        """
            Destroy self
            @param widget as Gtk.Button
        """
        self.destroy()

    def _on_progress_motion_notify(self, eventbox, event):
        """
            Show progress popover
            @param eventbox as Gtk.EventBox
            @param event as Gdk.Event
        """
        slider_width = self._progress.style_get_property('slider-width') / 2
        rect = self._progress.get_range_rect()
        if event.x < slider_width or\
           event.x > rect.width - slider_width:
            return

        current = (event.x - slider_width) *\
            self._progress.get_adjustment().get_upper() /\
            (rect.width - slider_width * 2)
        self._slider_popover.set(seconds_to_string(current/60))
        r = Gdk.Rectangle()
        r.x = event.x
        r.y = rect.height
        r.width = 1
        r.height = 1
        self._slider_popover.set_pointing_to(r)
        self._slider_popover.show()

    def _on_progress_leave_notify(self, eventbox, event):
        """
            Show progress popover
            @param eventbox as Gtk.EventBox
            @param event as Gdk.Event
        """
        self._slider_popover.delayed_hide()

    def _on_current_changed(self, player):
        """
            Update View for current track
                - Cover
                - artist/title
                - reset progress bar
                - update time/total labels
            @param player as Player
        """
        if player.current_track.id is not None:
            if Lp.player.current_track.id == Type.RADIOS:
                self._timelabel.hide()
                self._total_time_label.hide()
                self._progress.hide()
                surface = Lp.art.get_radio(
                    player.current_track.artist,
                    ArtSize.MONSTER*self.get_scale_factor())
            else:
                self._timelabel.show()
                self._total_time_label.show()
                self._progress.show()
                surface = Lp.art.get_album(
                    player.current_track.album,
                    ArtSize.MONSTER*self.get_scale_factor())
            self._cover.set_from_surface(surface)
            del surface

            album_name = player.current_track.album.name
            if player.current_track.year != '':
                album_name += " (%s)" % player.current_track.year
            self._title.set_text(player.current_track.title)
            self._artist.set_text(player.current_track.artist)
            self._album.set_text(album_name)
            self._progress.set_value(1.0)
            self._progress.set_range(0.0, player.current_track.duration * 60)
            self._total_time_label.set_text(
                seconds_to_string(player.current_track.duration))
            self._timelabel.set_text("0:00")

            # Can add a \n in markup
            # GTK bug => https://bugzilla.gnome.org/show_bug.cgi?id=749965
            prev_artist = escape(player.prev_track.artist)
            prev_title = escape(player.prev_track.title)
            next_artist = escape(player.next_track.artist)
            next_title = escape(player.next_track.title)
            self._next_btn.set_tooltip_markup("<b>%s</b> - %s" %
                                              (next_artist,
                                               next_title))
            self._prev_btn.set_tooltip_markup("<b>%s</b> - %s" %
                                              (prev_artist,
                                               prev_title))

            # Do not show next popover non internal tracks as
            # tags will be readed on the fly
            if player.next_track.id >= 0:
                self._next_popover.update()
                self._next_popover.show()
            else:
                self._next_popover.hide()

    def _on_key_release_event(self, widget, event):
        """
            Destroy window if Esc
            @param widget as Gtk.Widget
            @param event as Gdk.event
        """
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()

    def _on_prev_btn_clicked(self, widget):
        """
            Go to prev track
            @param widget as Gtk.Button
        """
        Lp.player.prev()

    def _on_play_btn_clicked(self, widget):
        """
            Play/pause
            @param widget as Gtk.Button
        """
        if Lp.player.is_playing():
            Lp.player.pause()
            widget.set_image(self._play_image)
        else:
            Lp.player.play()
            widget.set_image(self._pause_image)

    def _on_next_btn_clicked(self, widget):
        """
            Go to next track
            @param widget as Gtk.Button
        """
        Lp.player.next()

    def _on_status_changed(self, obj):
        """
            Update buttons and progress bar
            @param obj as unused
        """
        is_playing = Lp.player.is_playing()
        if Lp.player.current_track.id != Type.RADIOS:
            self._progress.set_sensitive(is_playing)
        if is_playing and not self._timeout1:
            self._timeout1 = GLib.timeout_add(1000, self._update_position)
            self._change_play_btn_status(self._pause_image, _("Pause"))
        elif not is_playing and self._timeout1:
            GLib.source_remove(self._timeout1)
            self._timeout1 = None
            self._change_play_btn_status(self._play_image, _("Play"))

    def _on_progress_press_btn(self, scale, data):
        """
            On press, mark player as seeking
            @param unused
        """
        self._seeking = True

    def _on_progress_release_btn(self, scale, data):
        """
            Callback for scale release button
            Seek player to scale value
            @param scale as Gtk.Scale, data as unused
        """
        value = scale.get_value()
        self._seeking = False
        self._update_position(value)
        Lp.player.seek(value/60)
