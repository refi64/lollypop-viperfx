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

from gi.repository import Gtk

from pickle import load

from lollypop.define import Lp, WindowSize, DataPath
from lollypop.toolbar_playback import ToolbarPlayback
from lollypop.toolbar_info import ToolbarInfo
from lollypop.toolbar_title import ToolbarTitle
from lollypop.toolbar_end import ToolbarEnd


class Toolbar(Gtk.HeaderBar):
    """
        Lollypop toolbar
    """

    def __init__(self, app):
        """
            Init toolbar
            @param app as Gtk.Application
        """
        Gtk.HeaderBar.__init__(self)
        self._width = WindowSize.SMALL
        self.set_title("Lollypop")
        self._toolbar_playback = ToolbarPlayback()
        self._toolbar_playback.show()
        self._toolbar_info = ToolbarInfo()
        self._toolbar_info.show()
        self._toolbar_title = ToolbarTitle()
        self._toolbar_title.show()
        self._toolbar_end = ToolbarEnd(app)
        self._toolbar_end.show()
        self.pack_start(self._toolbar_playback)
        self.pack_start(self._toolbar_info)
        self.set_custom_title(self._toolbar_title)
        self.pack_end(self._toolbar_end)

        Lp().player.connect('status-changed', self._on_status_changed)
        Lp().player.connect('current-changed', self._on_current_changed)
        Lp().player.connect('next-changed', self._on_next_changed)
        Lp().player.connect('prev-changed', self._on_prev_changed)

    def do_get_preferred_height(self):
        """
            Here, we calculate height based on:
            - playback toolbar if bigger
            - infos toolbar to adapt to font size then
        """
        style = self.get_style_context()
        padding = style.get_padding(style.get_state())
        info_height = self._toolbar_info.get_preferred_height()
        if info_height[0]+padding.top+padding.bottom > 47:
            height = info_height[0]+padding.top+padding.bottom
        else:
            height = 47
        return (height, height)

    def do_get_preferred_width(self):
        """
            Allow snapping for screen with width > 1400
            @return (int, int)
        """
        return (WindowSize.SMALL, self._width)

    def set_content_width(self, window_width):
        """
            Calculate infos/title width
            @param window width as int
        """
        width = self._toolbar_playback.get_preferred_width()[1]
        if window_width < WindowSize.MONSTER:
            self._toolbar_info.hide()
        else:
            self._toolbar_info.show()
        if window_width < WindowSize.BIG:
            self._toolbar_end.hide()
        else:
            width += self._toolbar_end.get_preferred_width()[1]
            self._toolbar_end.show()
        window = self.get_window()
        if window is not None:
            available = window.get_width() - width
            if available > 0:
                if window_width >= WindowSize.MONSTER:
                    title = available/2
                else:
                    title = available
                self._toolbar_title.set_width(title)
                if window_width >= WindowSize.MEDIUM:
                    self._toolbar_info.set_width((available-title)/2)
            self._width = window.get_width()

    def update_position(self, value=None):
        """
            Update progress bar position
            @param value as int
        """
        self._toolbar_title._update_position(value)

    def setup_menu(self, menu):
        """
            Add an application menu to menu button
            @parma: menu as Gio.Menu
        """
        self._toolbar_end.setup_menu(menu)

    def set_mark(self):
        """
            Mark toolbar with previously saved position
        """
        try:
            if Lp().settings.get_value('save-state'):
                position = load(open(DataPath + "/position.bin", "rb"))
                self._toolbar_title.add_mark(position/1000000)
        except Exception as e:
            print("Toolbar::restore_state():", e)

#######################
# PRIVATE             #
#######################
    def _on_current_changed(self, player):
        """
            Update toolbar
            @param player as Player
        """
        self._toolbar_playback.on_current_changed(player)
        self._toolbar_info.on_current_changed(player)
        self._toolbar_title.on_current_changed(player)

    def _on_prev_changed(self, player):
        """
            Update toolbar
            @param player as Player
        """
        self._toolbar_playback.on_prev_changed(player)

    def _on_next_changed(self, player):
        """
            Update toolbar
            @param player as Player
        """
        self._toolbar_playback.on_next_changed(player)
        self._toolbar_end.on_next_changed(player)

    def _on_status_changed(self, player):
        """
            Update buttons and progress bar
            @param player as Player
        """
        self._toolbar_playback.on_status_changed(player)
        self._toolbar_title.on_status_changed(player)
        self._toolbar_end.on_status_changed(player)
