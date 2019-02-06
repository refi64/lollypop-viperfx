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

from gettext import gettext as _

from lollypop.define import App, ViewType, Type
from lollypop.objects import Album
from lollypop.utils import remove_static_genres
from lollypop.view_tracks import TracksView
from lollypop.widgets_album_banner import AlbumBannerWidget
from lollypop.view import View


class AlbumView(View, TracksView):
    """
        Show artist albums and tracks
    """

    def __init__(self, album, artist_ids, genre_ids):
        """
            Init ArtistView
            @param album as Album
            @param artist_ids as [int]
            @param genre_ids as [int]
        """
        view_type = ViewType.TWO_COLUMNS | ViewType.MULTIPLE
        View.__init__(self, view_type)
        TracksView.__init__(self, view_type)
        self.__grid = Gtk.Grid()
        self.__grid.set_property("vexpand", True)
        self.__grid.set_row_spacing(10)
        self.__grid.set_orientation(Gtk.Orientation.VERTICAL)
        self.__grid.show()
        self._album = album
        self.__artist_ids = artist_ids
        self.__genre_ids = remove_static_genres(genre_ids)
        if artist_ids and artist_ids[0] == Type.COMPILATIONS:
            self.__album_ids = App().albums.get_compilation_ids(genre_ids)
        else:
            self.__album_ids = App().albums.get_ids(artist_ids, genre_ids)
        self.__label = None
        if len(self.__album_ids) == 1 or len(artist_ids) != 1:
            return
        # Remove album from artist albums
        if self._album.id in self.__album_ids:
            self.__album_ids.remove(album.id)
        artist = App().artists.get_name(artist_ids[0])
        self.__label = Gtk.Label()
        self.__label.set_markup(
                         '''<span size="large" alpha="40000"
                             weight="bold">%s %s</span>''' %
                         (_("Others albums from"), artist))
        self.__label.set_property("halign", Gtk.Align.START)
        self.__label.set_margin_top(30)
        self.__label.show()

    def populate(self):
        """
            Populate the view with album
            @param albums as [Album]
        """
        banner = AlbumBannerWidget(self._album)
        banner.show()
        self.__grid.add(banner)
        TracksView.populate(self)
        self.__grid.add(self._responsive_widget)
        self._viewport.add(self.__grid)
        self.add(self._scrolled)
        self._responsive_widget.show()

#######################
# PROTECTED           #
#######################
    def _on_map(self, widget):
        """
            Connect signals and set active ids
            @param widget as Gtk.Widget
        """
        App().window.emit("show-can-go-back", True)
        App().window.emit("can-go-back-changed", True)
        App().settings.set_value("state-one-ids",
                                 GLib.Variant("ai", self.__genre_ids))
        App().settings.set_value("state-two-ids",
                                 GLib.Variant("ai", self.__artist_ids))

    def _on_tracks_populated(self, disc_number):
        """
            Emit populated signal
            @param disc_number as int
        """
        if TracksView.get_populated(self):
            from lollypop.view_albums_box import AlbumsBoxView
            if self.__label is not None:
                self.__grid.add(self.__label)
                others_box = AlbumsBoxView(self.__genre_ids,
                                           self.__artist_ids,
                                           ViewType.SMALL)
                others_box.show()
                self.__grid.add(others_box)
                others_box.populate([Album(id) for id in self.__album_ids])
        else:
            TracksView.populate(self)

#######################
# PRIVATE             #
#######################
