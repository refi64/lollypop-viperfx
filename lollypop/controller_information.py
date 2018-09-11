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
        self.__tooltip = tooltip

    def on_current_changed(self, art_size, font_size):
        """
            Update labels and cover and handles widget visibility
            @param art_size as int
            @param font_size as int
        """
        if App().player.current_track.id is None:
            if self._infobox is not None:
                self._infobox.hide()
            self._cover.hide()
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
        artwork = None
        if App().player.current_track.id == Type.RADIOS:
            artwork = App().art.get_radio_artwork(
                App().player.current_track.album_artists[0],
                width,
                self.get_scale_factor())
        elif App().player.current_track.id is not None:
            artwork = App().art.get_album_artwork(
                App().player.current_track.album,
                width,
                self.get_scale_factor(),
                App().settings.get_value("allow-per-track-cover"))
        if artwork is not None:
            if enable_blur:
                from lollypop.utils import blur
                blur(artwork, self._cover, width, height)
            else:
                self._cover.set_from_surface(artwork)
            if self.__tooltip:
                self._cover.set_tooltip_text(
                    App().player.current_track.album.name)
            self._cover.show()
        else:
            self._cover.hide()

    def set_artsize(self, artsize):
        """
            Set a new artsize for controller
            @param artsize as int
        """
        self.__artsize = artsize

    @property
    def artsize(self):
        """
            Art size as int
        """
        return self.__artsize