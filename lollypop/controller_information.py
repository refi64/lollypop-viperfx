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

from gi.repository import GLib

from lollypop.helper_art import ArtHelper
from lollypop.define import Type, App


class InformationController:
    """
        Information controller (title, artist, album, cover)
    """

    def __init__(self, tooltip=True):
        """
            Init controller
            @param tooltip as bool => Show album name over cover
        """
        self._infobox = None
        self.__art_helper = ArtHelper()
        self.__art_helper.connect("artwork-set", self.__on_artwork_set)
        self.__tooltip = tooltip
        self.__per_track_cover = App().settings.get_value(
            "allow-per-track-cover")

    def on_current_changed(self, art_size, font_size):
        """
            Update labels and cover and handles widget visibility
            @param art_size as int
            @param font_size as int
        """
        if App().player.current_track.id is None:
            if self._infobox is not None:
                self._infobox.hide()
            self._artwork.hide()
            return
        elif self._infobox is not None:
            self._infobox.show()
        self.update_labels(font_size)
        self.update_artwork(art_size, art_size, False)

    def update_labels(self, font_size):
        """
            Update labels
            @param font_size as int
        """
        if App().player.current_track.id == Type.RADIOS:
            artist_text = App().player.current_track.album_artists[0]
        else:
            artist_text = ", ".join(App().player.current_track.artists)
        if font_size is None:
            self._artist_label.set_text(artist_text)
        else:
            self._artist_label.set_markup(
                "<span font='%s'>%s</span>" %
                (font_size - 2,
                 GLib.markup_escape_text(artist_text)))
        self._artist_label.show()

        title_text = App().player.current_track.title
        if font_size is None:
            self._title_label.set_text(title_text)
        else:
            self._title_label.set_markup(
                "<span font='%s'>%s</span>" %
                                        (font_size,
                                         GLib.markup_escape_text(title_text)))
        self._title_label.show()

    def update_artwork(self, width, height, enable_blur):
        """
            Update artwork
            @param width as int
            @param height as int
            @param enable_blur as bool
        """
        if width < 1 or height < 1:
            return
        if App().player.current_track.id == Type.RADIOS:
            self.__art_helper.set_album_radio(
                self._artwork,
                App().player.current_track.album_artists[0],
                width,
                height,
                self.get_scale_factor())

        elif App().player.current_track.id is not None:
            self.__art_helper.set_album_artwork(
                self._artwork,
                App().player.current_track.album,
                width,
                height,
                self.get_scale_factor(),
                enable_blur)
            if self.__tooltip:
                self._artwork.set_tooltip_text(
                    App().player.current_track.album.name)

    def set_art_size(self, art_size):
        """
            Set a new art_size for controller
            @param art_size as int
        """
        self.__art_size = art_size

    @property
    def art_size(self):
        """
            Art size as int
        """
        return self.__art_size

#######################
# PRIVATE             #
#######################
    def __on_artwork_set(self, helper):
        """
            Show artwork
            @param helper as ArtHelper
        """
        pass
