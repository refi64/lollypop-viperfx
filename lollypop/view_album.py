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
        self._album = album
        self.__genre_ids = genre_ids
        self.__artist_ids = artist_ids
        self.__grid = Gtk.Grid()
        self.__grid.set_property("vexpand", True)
        self.__grid.set_row_spacing(10)
        self.__grid.set_orientation(Gtk.Orientation.VERTICAL)
        self.__grid.show()
        self.__genre_ids = remove_static_genres(genre_ids)

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
        self._responsive_widget.set_margin_start(15)
        self._responsive_widget.set_margin_end(15)
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
            for artist_id in self.__artist_ids:
                artist = App().artists.get_name(artist_id)
                label = Gtk.Label()
                label.set_markup(
                                 '''<span size="large" alpha="40000"
                                     weight="bold">%s %s</span>''' %
                                 (_("Others albums from"), artist))
                label.set_property("halign", Gtk.Align.START)
                label.set_margin_top(30)
                label.set_margin_start(20)
                label.show()
                self.__grid.add(label)
                others_box = AlbumsBoxView([],
                                           [artist_id],
                                           ViewType.SMALL)
                others_box.show()
                others_box.set_margin_start(30)
                others_box.set_margin_end(30)
                self.__grid.add(others_box)
                if artist_id == Type.COMPILATIONS:
                    album_ids = App().albums.get_compilation_ids(
                        self.__genre_ids)
                else:
                    album_ids = App().albums.get_ids(
                        [artist_id], [])
                if self._album.id in album_ids:
                    album_ids.remove(self._album.id)
                others_box.populate([Album(id) for id in album_ids])
        else:
            TracksView.populate(self)

#######################
# PRIVATE             #
#######################
