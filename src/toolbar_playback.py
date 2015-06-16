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

from cgi import escape
from gettext import gettext as _

from lollypop.pop_infos import InfosPopover
from lollypop.define import Lp, Type


class ToolbarPlayback(Gtk.Bin):
    """
        Init playback toolbar
    """
    def __init__(self):
        Gtk.Bin.__init__(self)
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/ToolbarPlayback.ui')
        builder.connect_signals(self)

        self.add(builder.get_object('playback'))

        self._prev_btn = builder.get_object('previous_button')
        self._play_btn = builder.get_object('play_button')
        self._next_btn = builder.get_object('next_button')
        self._play_image = builder.get_object('play_image')
        self._pause_image = builder.get_object('pause_image')

        if Lp.lastfm is not None or Lp.wikipedia is not None:
            self._artist_infos_btn = builder.get_object('artist_infos_btn')
            self._artist_infos_btn.show()

    """
        Update buttons on current changed
        @param player as Player
    """
    def on_current_changed(self, player):
        if Lp.lastfm is not None or Lp.wikipedia is not None:
            if player.current_track.id != Type.RADIOS:
                self._artist_infos_btn.set_sensitive(True)
            else:
                self._artist_infos_btn.set_sensitive(False)
        self._play_btn.set_sensitive(True)
        self._prev_btn.set_sensitive(True)
        self._next_btn.set_sensitive(True)
        # Can add a \n in markup
        # GTK bug => https://bugzilla.gnome.org/show_bug.cgi?id=749965
        prev_artist = escape(player.prev_track.artist)
        prev_title = escape(player.prev_track.title)
        next_artist = escape(player.next_track.artist)
        next_title = escape(player.next_track.title)
        self._next_btn.set_tooltip_markup("<b>%s</b> - %s" %\
                                          (next_artist,
                                           next_title))
        self._prev_btn.set_tooltip_markup("<b>%s</b> - %s" %\
                                          (prev_artist,
                                           prev_title))

    """
        Update buttons on status changed
        @param player as Player
    """
    def on_status_changed(self, player):
        if player.is_playing():
            self._change_play_btn_status(self._pause_image, _("Pause"))
        else:
            self._change_play_btn_status(self._play_image, _("Play"))

#######################
# PRIVATE             #
#######################
    """
        Update play button with image and status as tooltip
        @param image as Gtk.Image
        @param status as str
    """
    def _change_play_btn_status(self, image, status):
        self._play_btn.set_image(image)
        self._play_btn.set_tooltip_text(status)

    """
        Previous track on prev button clicked
        @param button as Gtk.Button
    """
    def _on_prev_btn_clicked(self, button):
        Lp.player.prev()

    """
        Play/Pause on play button clicked
        @param button as Gtk.Button
    """
    def _on_play_btn_clicked(self, button):
        if Lp.player.is_playing():
            Lp.player.pause()
            self._change_play_btn_status(self._play_image, _("Play"))
        else:
            Lp.player.play()
            self._change_play_btn_status(self._pause_image, _("Pause"))

    """
        Next track on next button clicked
        @param button as Gtk.Button
    """
    def _on_next_btn_clicked(self, button):
        Lp.player.next()

    """
        Show current artist informations
        @param button as Gtk.Button
    """
    def _on_infos_btn_clicked(self, button):
        if Lp.lastfm is not None or Lp.wikipedia is not None:
            artist_id = Lp.player.current_track.aartist_id
            if artist_id == Type.COMPILATIONS:
                artist = Lp.player.current_track.artist
            else:
                artist = Lp.player.current_track.aartist
            popover = InfosPopover(artist, Lp.player.current_track.id)
            popover.set_relative_to(button)
            popover.populate()
            popover.show()
