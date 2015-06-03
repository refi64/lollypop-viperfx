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

from lollypop.define import Lp
from lollypop.toolbar_playback import ToolbarPlayback
from lollypop.toolbar_infos import ToolbarInfos
from lollypop.toolbar_title import ToolbarTitle
from lollypop.toolbar_end import ToolbarEnd


# Toolbar as headerbar
# Get real widget with Toolbar.widget
class Toolbar(Gtk.HeaderBar):
    """
        Init toolbar/headerbar ui
        @param app as Gtk.Application
    """
    def __init__(self, app):
        Gtk.HeaderBar.__init__(self)

        self._toolbar_playback = ToolbarPlayback()
        self._toolbar_playback.show()
        self._toolbar_infos = ToolbarInfos()
        self._toolbar_infos.show()
        self._toolbar_title = ToolbarTitle()
        self._toolbar_title.show()
        self._toolbar_end = ToolbarEnd(app)
        self._toolbar_end.show()
        self.pack_start(self._toolbar_playback)
        self.pack_start(self._toolbar_infos)
        self.set_custom_title(self._toolbar_title)
        self.pack_end(self._toolbar_end)

        Lp.player.connect('status-changed', self._on_status_changed)
        Lp.player.connect('current-changed', self._on_current_changed)

    """
        Here, we calculate height based on left widget
        We want to ignore titlebox height, like in original Gtk+ code
        Simplified version here
    """
    def do_get_preferred_height(self):
        style = self.get_style_context()
        padding = style.get_padding(Gtk.StateFlags.NORMAL)
        toolbar_height = self._toolbar_playback.get_preferred_height()
        return (toolbar_height[0]+padding.top+padding.bottom,
                toolbar_height[1]+padding.top+padding.bottom)

    """
        Update progress bar position
        @param value as int
    """
    def update_position(self, value=None):
        self._toolbar_title.update_position(value)

    """
        Set Gtk.Scale progress width
        @param width as int
    """
    def set_progress_width(self, width):
        self._toolbar_title.set_progress_width(width)

    """
        Add an application menu to menu button
        @parma: menu as Gio.Menu
    """
    def setup_menu_btn(self, menu):
        self._toolbar_end.setup_menu_btn(menu)

#######################
# PRIVATE             #
#######################
    """
        Update toolbar
        @param player as Player
    """
    def _on_current_changed(self, player):
        self._toolbar_playback.on_current_changed(player)
        self._toolbar_infos.on_current_changed(player)
        self._toolbar_title.on_current_changed(player)
        self._toolbar_end.on_current_changed(player)

    """
        Update buttons and progress bar
        @param player as Player
    """
    def _on_status_changed(self, player):
        self._toolbar_playback.on_status_changed(player)
        self._toolbar_infos.on_status_changed(player)
        self._toolbar_title.on_status_changed(player)
        self._toolbar_end.on_status_changed(player)
