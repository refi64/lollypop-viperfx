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
from lollypop.view_artist_albums import ArtistAlbumsView


class AlbumView(ArtistAlbumsView):
    """
        Show artist albums and tracks
    """

    def __init__(self, artist_ids, genre_ids):
        """
            Init ArtistView
            @param artist id as int (Current if None)
            @param genre id as int
        """
        view_type = ViewType.TWO_COLUMNS | ViewType.MULTIPLE
        ArtistAlbumsView.__init__(self, artist_ids, genre_ids, view_type)
        genre_ids = remove_static_genres(genre_ids)
        if artist_ids and artist_ids[0] == Type.COMPILATIONS:
            self.__album_ids = App().albums.get_compilation_ids(genre_ids)
        else:
            self.__album_ids = App().albums.get_ids(artist_ids, genre_ids)
        self.__label = None
        self._album_box.set_margin_top(30)
        self._album_box.set_margin_start(10)
        self._album_box.set_margin_end(10)
        if len(self.__album_ids) == 1 or len(artist_ids) != 1:
            return
        artist = App().artists.get_name(artist_ids[0])
        self.__label = Gtk.Label()
        self.__label.set_markup(
                         '''<span size="large" alpha="40000"
                             weight="bold">%s %s</span>''' %
                         (_("Others albums from"), artist))
        self.__label.set_property("halign", Gtk.Align.START)
        self.__label.set_margin_top(30)
        self.__label.show()

    def populate(self, albums):
        """
            Populate the view with album
            @param albums as [Album]
        """
        # Remove album from artist albums
        if albums and albums[0].id in self.__album_ids:
            self.__album_ids.remove(albums[0].id)
        ArtistAlbumsView.populate(self, albums)

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
                                 GLib.Variant("ai", self._genre_ids))
        App().settings.set_value("state-two-ids",
                                 GLib.Variant("ai", self._artist_ids))

    def _on_populated(self, widget):
        """
            Add another album/disc
            @param widget as AlbumWidget/TracksView
        """
        ArtistAlbumsView._on_populated(self, widget)
        if widget.is_populated:
            from lollypop.view_albums_box import AlbumsBoxView
            if self.__label is not None:
                self._album_box.add(self.__label)
            others_box = AlbumsBoxView(self._genre_ids,
                                       self._artist_ids,
                                       ViewType.SMALL)
            others_box.show()
            self._album_box.add(others_box)
            others_box.populate([Album(id) for id in self.__album_ids])

#######################
# PRIVATE             #
#######################
