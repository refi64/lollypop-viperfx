# Copyright (c) 2014-2019 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import Gio

from gettext import gettext as _

from lollypop.define import App, ViewType
from lollypop.menu_playlists import PlaylistsMenu
from lollypop.menu_artist import ArtistMenu


class ToolbarMenu(Gio.Menu):
    """
        Contextual menu for toolbar
    """

    def __init__(self, track):
        """
            Init menu
            @param track as Track
        """
        Gio.Menu.__init__(self)
        lyrics_menu = Gio.Menu()
        action = Gio.SimpleAction(name="lyrics_action")
        App().add_action(action)
        action.connect("activate", self.__show_lyrics)
        lyrics_menu.append(_("Show lyrics"), "app.lyrics_action")
        self.insert_section(0, _("Lyrics"), lyrics_menu)
        if track.id >= 0:
            playlist_menu = PlaylistsMenu(track)
            self.insert_section(1, _("Playlists"), playlist_menu)
        self.insert_section(2, _("Artist"),
                            ArtistMenu(track, ViewType.ALBUM))

#######################
# PRIVATE             #
#######################
    def __show_lyrics(self, action, variant):
        """
            Show lyrics on main window
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        App().window.container.show_lyrics()
