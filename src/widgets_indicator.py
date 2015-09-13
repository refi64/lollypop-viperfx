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

from gi.repository import GObject, Gtk, GLib


class IndicatorWidget(Gtk.Stack):
    """
        Show play/loved indicator
    """
    
    def __init__(self):
        """
            Init indicator widget
        """
        Gtk.Stack.__init__(self)
        self.set_transition_duration(1000)
        self.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._timeout_id = None
        play = Gtk.Image.new_from_icon_name('media-playback-start-symbolic',
                                            Gtk.IconSize.MENU)
        loved = Gtk.Image.new_from_icon_name('emblem-favorite-symbolic',
                                             Gtk.IconSize.MENU)
        loved.set_opacity(0.6)
        self.add_named(play, 'play')
        self.add_named(loved, 'loved')
        self.set_opacity(0)
        self.show_all()
        
    def play(self):
        """
            Show play indicator
        """
        self.set_visible_child_name('play')
        self.set_opacity(1)

    def loved(self):
        """
            Show loved indicator
        """
        self.set_visible_child_name('loved')
        self.set_opacity(1)

    def play_loved(self):
        """
            Show play/loved indicator 
        """
        self.play()
        self._timeout_id = GLib.timeout_add(2000, self._play_loved)

    def clear(self):
        """
            Show nothing
        """
        if self._timeout_id is not None:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = None
        self.set_opacity(0)

#######################
# PRIVATE             #
#######################
    def _play_loved(self):
        """
            Show play/loved indicator 
        """
        if self._timeout_id is None:
            return False
        if self.get_visible_child_name() == 'play':
            self.loved()
        else:
            self.play()
        return True
