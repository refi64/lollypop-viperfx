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

from gi.repository import Gtk, GLib

from gettext import gettext as _

from lollypop.define import Lp


class IndicatorWidget(Gtk.Stack):
    """
        Show play/loved indicator
    """

    def __init__(self):
        """
            Init indicator widget
        """
        Gtk.Stack.__init__(self)
        self._id = None
        self.connect('destroy', self._on_destroy)
        self._pass = 1
        self.set_transition_duration(500)
        self.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._timeout_id = None
        self._button = Gtk.Button.new()
        self._image = Gtk.Image.new()
        self._button.set_image(self._image)
        self._button.set_relief(Gtk.ReliefStyle.NONE)
        self._button.get_style_context().add_class('menu-button')
        self._button.get_style_context().add_class('track-menu-button')
        self._image.set_opacity(0.2)
        self._button.show()
        self._button.connect('clicked', self._on_button_clicked)
        play = Gtk.Image.new_from_icon_name('media-playback-start-symbolic',
                                            Gtk.IconSize.MENU)
        loved = Gtk.Image.new_from_icon_name('emblem-favorite-symbolic',
                                             Gtk.IconSize.MENU)
        self.add_named(self._button, 'button')
        self.add_named(play, 'play')
        self.add_named(loved, 'loved')
        self.show_all()
        Lp().player.connect('queue-changed', self._on_queue_changed)

    def set_id(self, id):
        """
            Store current object id
            @param id as int
        """
        self._id = id
        self._update_button()

    def empty(self):
        """
            Show no indicator
        """
        self.set_visible_child_name('button')

    def play(self):
        """
            Show play indicator
        """
        self.set_visible_child_name('play')

    def loved(self):
        """
            Show loved indicator
        """
        self.set_visible_child_name('loved')

    def play_loved(self):
        """
            Show play/loved indicator
        """
        self._pass = 1
        self.play()
        self._timeout_id = GLib.timeout_add(500, self._play_loved)

    def clear(self):
        """
            Clear timeout
        """
        if self._timeout_id is not None:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = None

#######################
# PRIVATE             #
#######################
    def _update_button(self):
        """
            Update button based on queue status
        """
        if self._id in Lp().player.get_queue():
            self._button.set_tooltip_text(_("Remove from queue"))
            self._image.set_from_icon_name('list-remove-symbolic',
                                           Gtk.IconSize.MENU)
        else:
            self._button.set_tooltip_text(_("Add to queue"))
            self._image.set_from_icon_name('list-add-symbolic',
                                           Gtk.IconSize.MENU)

    def _on_queue_changed(self, player):
        """
            Update button widget
            @param player as Player
            @param is party as bool
        """
        self._update_button()

    def _on_button_clicked(self, widget):
        """
            Popup menu for track relative to button
            @param widget as Gtk.Button
        """
        if self._id in Lp().player.get_queue():
            Lp().player.del_from_queue(self._id)
        else:
            Lp().player.append_to_queue(self._id)

    def _on_destroy(self, widget):
        """
            Clear timeout
            @param widget as Gtk.Widget
        """
        self.clear()

    def _play_loved(self):
        """
            Show play/loved indicator
        """
        if self._timeout_id is None:
            return False
        if self.get_visible_child_name() == 'play':
            if self._pass == 10:
                self._pass = 0
                self.loved()
        else:
            self.play()
        self._pass += 1
        return True
