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

from lollypop.view import View
from lollypop.view_albums import ArtistView
from lollypop.view_container import ViewContainer
from lollypop.define import Lp, Type



class CurrentArtistView(ArtistView):
    """
        Show albums from current artist
    """

    def __init__(self, artist_id):
        """
            Init ArtistsView
            @param artist id as int
        """
        View.__init__(self)
        self._artist_id = artist_id
        self._genre_id = Type.ALL
        self._signal_id = None

        self._pop_allowed = False

        self._albumbox = Gtk.Grid()
        self._albumbox.set_row_spacing(20)
        self._albumbox.set_property("orientation", Gtk.Orientation.VERTICAL)
        self._albumbox.show()

        self._scrolledWindow.set_property('expand', True)
        self._viewport.set_property("valign", Gtk.Align.START)
        self._viewport.add(self._albumbox)
        self.add(self._scrolledWindow)


class AlbumsPopover(Gtk.Popover):
    """
        Popover => CurrentArtistView
    """

    def __init__(self):
        """
            Init popover
        """
        Gtk.Popover.__init__(self)
        self._stack = ViewContainer(1000)
        self._stack.show()

        self._on_screen_id = None
        self.add(self._stack)

        Lp.player.connect("current-changed", self._update_content)

    def populate(self):
        """
            Load content of the popover
        """
        if Lp.player.current_track.album_artist_id == Type.COMPILATIONS:
            new_id = Lp.player.current_track.album_id
        else:
            new_id = Lp.player.current_track.album_artist_id
        if self._on_screen_id != new_id:
            self._on_screen_id = new_id
            view = CurrentArtistView(Lp.player.current_track.album_artist_id)
            albums = self._get_albums(Lp.player.current_track.album_artist_id)
            view.populate(albums)
            view.show()
            self._stack.add(view)
            self._stack.set_visible_child(view)
            self._stack.clean_old_views(view)

    def do_show(self):
        """
            Resize popover
        """
        size_setting = Lp.settings.get_value('window-size')
        if isinstance(size_setting[0], int) and\
           isinstance(size_setting[1], int):
            self.set_size_request(size_setting[0]*0.65, size_setting[1]*0.8)
        else:
            self.set_size_request(600, 600)
        Gtk.Popover.do_show(self)

    def do_hide(self):
        """
            Remove view
        """
        Gtk.Popover.do_hide(self)
        child = self._stack.get_visible_child()
        if child is not None:
            child.stop()
        self._on_screen_id = None
        self._stack.clean_old_views(None)

#######################
# PRIVATE             #
#######################
    def _get_albums(self, artist_id):
        """
            Get albums
            @return album ids as [int]
        """
        sql = Lp.db.get_cursor()
        if artist_id == Type.COMPILATIONS:
            albums = [Lp.player.current_track.album_id]
        else:
            albums = Lp.artists.get_albums(artist_id, sql)
        sql.close()
        return albums

    def _update_content(self, player):
        """
            Update the content view
            @param player as Player
            @param track id as int
        """
        if self.is_visible():
            self.populate()

    def do_get_preferred_width(self):
        """
            Set 0 to force popover to not expand
        """
        return (0, 0)
