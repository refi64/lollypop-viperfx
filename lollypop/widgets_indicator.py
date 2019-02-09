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

from gi.repository import Gtk, GLib


class IndicatorWidget(Gtk.EventBox):
    """
        Show play/loved indicator
        If embedded in a Popover, will not affect playlists but only player
        playlists
    """

    def __init__(self, row, view_type):
        """
            Init indicator widget, ui will be set when needed
            @param row as Row
            @param view_type as ViewType
        """
        Gtk.EventBox.__init__(self)
        self.__row = row
        self.__view_type = view_type
        self.__pass = 1
        self.__timeout_id = None
        self.__stack = None
        self.connect("destroy", self.__on_destroy)
        # min-width = 24px, borders = 2px, padding = 8px
        self.set_size_request(34, -1)

    def play(self):
        """
            Show play indicator
        """
        self.__init()
        self.__stack.set_visible_child_name("play")

    def loved(self, status):
        """
            Show loved indicator
            @param loved status
        """
        self.__init()
        if status == 1:
            self.__loved.set_from_icon_name("emblem-favorite-symbolic",
                                            Gtk.IconSize.MENU)
        elif status == -1:
            self.__loved.set_from_icon_name("media-skip-forward-symbolic",
                                            Gtk.IconSize.MENU)
        if status != 0:
            self.__stack.set_visible_child_name("loved")

    def play_loved(self):
        """
            Show play/loved indicator
        """
        self.__init()
        self.__pass = 1
        self.play()
        self.__timeout_id = GLib.timeout_add(1000, self.__play_loved)

    def clear(self):
        """
            Clear timeout
        """
        if self.__timeout_id is not None:
            GLib.source_remove(self.__timeout_id)
            self.__timeout_id = None

#######################
# PRIVATE             #
#######################
    def __init(self):
        """
            Init widget content if needed
        """
        if self.__stack is not None:
            return
        self.__stack = Gtk.Stack()
        self.__stack.set_transition_duration(500)
        self.__stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        play = Gtk.Image.new_from_icon_name("media-playback-start-symbolic",
                                            Gtk.IconSize.MENU)
        self.__loved = Gtk.Image()
        self.__stack.add_named(play, "play")
        self.__stack.add_named(self.__loved, "loved")
        self.add(self.__stack)
        self.show_all()

    def __on_destroy(self, widget):
        """
            Clear timeout
            @param widget as Gtk.Widget
        """
        self.clear()

    def __play_loved(self):
        """
            Show play/loved indicator
        """
        if self.__timeout_id is None:
            return False
        if self.__stack.get_visible_child_name() == "play":
            if self.__pass == 5:
                self.__pass = 0
                self.loved(1)
        else:
            self.play()
        self.__pass += 1
        return True
