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
            Init indicator widget, ui will be set when needed
            @param track id as int
        """
        Gtk.EventBox.__init__(self)
        self.__id = track_id
        self.__pass = 1
        self.__timeout_id = None
        self.__button = None
        self.__stack = None
        self.__signal_id = Lp().player.connect("queue-changed",
                                               self.__on_queue_changed)
        self.connect("destroy", self.__on_destroy)
        # Here a hack to make old Gtk version support min-height css attribute
        # min-height = 24px, borders = 2px, we set directly on stack
        # min-width = 24px, borders = 2px, padding = 8px
        self.set_size_request(34, 26)

    def show_spinner(self):
        """
            Show spinner
        """
        self.__init()
        spinner = self.__stack.get_child_by_name("spinner")
        if spinner is None:
            spinner = Gtk.Spinner()
            spinner.set_property("halign", Gtk.Align.CENTER)
            spinner.set_property("valign", Gtk.Align.CENTER)
            spinner.show()
            self.__stack.add_named(spinner, "spinner")
        spinner.start()
        self.__stack.set_visible_child_name("spinner")

    def empty(self):
        """
            Show no indicator
        """
        if self.__button is not None:
            self.__stack.set_visible_child_name("button")

    def play(self):
        """
            Show play indicator
        """
        self.__init()
        self.__clear_spinner()
        self.__stack.set_visible_child_name("play")

    def loved(self):
        """
            Show loved indicator
        """
        self.__init()
        self.__clear_spinner()
        self.__stack.set_visible_child_name("loved")

    def play_loved(self):
        """
            Show play/loved indicator
        """
        self.__init()
        self.__clear_spinner()
        self.__pass = 1
        self.play()
        self.__timeout_id = GLib.timeout_add(500, self.__play_loved)

    def clear(self):
        """
            Clear timeout
        """
        if self.__timeout_id is not None:
            GLib.source_remove(self.__timeout_id)
            self.__timeout_id = None

    def update_button(self):
        """
            Update button based on queue status
        """
        self.__init()
        if self.__id in Lp().player.queue:
            self.__button.set_tooltip_text(_("Remove from queue"))
            self.__image.set_from_icon_name("list-remove-symbolic",
                                            Gtk.IconSize.MENU)
        else:
            self.__button.set_tooltip_text(_("Add to queue"))
            self.__image.set_from_icon_name("list-add-symbolic",
                                            Gtk.IconSize.MENU)

#######################
# PRIVATE             #
#######################
    def __clear_spinner(self):
        """
            Clear spinner
        """
        spinner = self.__stack.get_child_by_name("spinner")
        if spinner is not None:
            spinner.stop()

    def __init(self):
        """
            Init widget content if needed
        """
        if self.__button is not None:
            return
        self.__stack = Gtk.Stack()
        self.__stack.set_transition_duration(500)
        self.__stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.__button = Gtk.Button.new()
        self.__image = Gtk.Image.new()
        self.__button.set_image(self.__image)
        self.__button.set_relief(Gtk.ReliefStyle.NONE)
        self.__button.get_style_context().add_class("menu-button")
        self.__button.get_style_context().add_class("track-menu-button")
        self.__image.set_opacity(0.2)
        self.__button.show()
        self.__button.connect("clicked", self.__on_button_clicked)
        play = Gtk.Image.new_from_icon_name("media-playback-start-symbolic",
                                            Gtk.IconSize.MENU)
        loved = Gtk.Image.new_from_icon_name("emblem-favorite-symbolic",
                                             Gtk.IconSize.MENU)
        self.__stack.add_named(self.__button, "button")
        self.__stack.add_named(play, "play")
        self.__stack.add_named(loved, "loved")
        self.add(self.__stack)
        self.connect("enter-notify-event", self.__on_enter_notify)
        self.connect("leave-notify-event", self.__on_leave_notify)
        self.show_all()

    def __on_enter_notify(self, widget, event):
        """
            Show queue button
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        self.empty()

    def __on_leave_notify(self, widget, event):
        """
            Show love button or play button again
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        if self.__id == Lp().player.current_track.id:
            self.play()
        elif is_loved(self.__id):
            self.loved()

    def __on_queue_changed(self, unused):
        """
            Update button widget
        """
        self.update_button()

    def __on_button_clicked(self, widget):
        """
            Popup menu for track relative to button
            @param widget as Gtk.Button
        """
        if self.__id in Lp().player.queue:
            Lp().player.del_from_queue(self.__id)
        else:
            Lp().player.append_to_queue(self.__id)

    def __on_destroy(self, widget):
        """
            Clear timeout
            @param widget as Gtk.Widget
        """
        if self.__signal_id is not None:
            Lp().player.disconnect(self.__signal_id)
        self.clear()

    def __play_loved(self):
        """
            Show play/loved indicator
        """
        if self.__timeout_id is None:
            return False
        if self.__stack.get_visible_child_name() == "play":
            if self.__pass == 10:
                self.__pass = 0
                self.loved()
        else:
            self.play()
        self.__pass += 1
        return True
