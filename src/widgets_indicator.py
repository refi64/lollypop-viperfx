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
from lollypop.utils import is_loved


class IndicatorWidget(Gtk.EventBox):
    """
        Show play/loved indicator
    """

    def __init__(self, track_id):
        """
            Init indicator widget
            @param track id as int
        """
        Gtk.EventBox.__init__(self)
        self._id = track_id
        self._pass = 1
        self._timeout_id = None
        self._signal_id = Lp().player.connect('queue-changed',
                                              self._on_queue_changed)
        self.connect('destroy', self._on_destroy)
        self.connect('enter-notify-event', self._on_enter_notify)
        self.connect('leave-notify-event', self._on_leave_notify)
        self._stack = Gtk.Stack()
        self._stack.set_transition_duration(500)
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._button = Gtk.Button.new()
        self._image = Gtk.Image.new()
        self._button.set_image(self._image)
        # Here a hack to make old Gtk version support min-height css attribute
        # min-height = 24px, borders = 2px
        self._button.set_property('height-request', 26)
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
        self._stack.add_named(self._button, 'button')
        self._stack.add_named(play, 'play')
        self._stack.add_named(loved, 'loved')
        self.add(self._stack)
        self.show_all()

    def empty(self):
        """
            Show no indicator
        """
        self._stack.set_visible_child_name('button')

    def play(self):
        """
            Show play indicator
        """
        self._stack.set_visible_child_name('play')

    def loved(self):
        """
            Show loved indicator
        """
        self._stack.set_visible_child_name('loved')

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

    def update_button(self):
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

#######################
# PRIVATE             #
#######################
    def _on_enter_notify(self, widget, event):
        """
            Show queue button
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        self.empty()

    def _on_leave_notify(self, widget, event):
        """
            Show love button or play button again
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        if self._id == Lp().player.current_track.id:
            self.play()
        elif is_loved(self._id):
            self.loved()

    def _on_queue_changed(self, unused):
        """
            Update button widget
        """
        self.update_button()

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
        if self._signal_id is not None:
            Lp().player.disconnect(self._signal_id)
        self.clear()

    def _play_loved(self):
        """
            Show play/loved indicator
        """
        if self._timeout_id is None:
            return False
        if self._stack.get_visible_child_name() == 'play':
            if self._pass == 10:
                self._pass = 0
                self.loved()
        else:
            self.play()
        self._pass += 1
        return True
