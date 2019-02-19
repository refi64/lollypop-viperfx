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

from lollypop.helper_art import ArtHelperEffect
from lollypop.define import App, ArtSize, MARGIN, Type, ViewType
from lollypop.widgets_rating import RatingWidget
from lollypop.widgets_loved import LovedWidget
from lollypop.widgets_cover import CoverWidget
from lollypop.utils import get_human_duration, on_query_tooltip, on_realize


class AlbumBannerWidget(Gtk.Bin):
    """
        Banner for album
    """

    def __init__(self, album, view_type=ViewType.DEFAULT):
        """
            Init cover widget
            @param album
            @param view_type as ViewType
        """
        Gtk.Bin.__init__(self)
        self.__width = 0
        self.__padding = 0
        self.__allocation_timeout_id = None
        self.__album = album
        self.__view_type = view_type
        self.__height = self.default_height
        self.set_property("valign", Gtk.Align.START)
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/AlbumBannerWidget.ui")
        builder.connect_signals(self)
        self.__title_label = builder.get_object("name_label")
        self.__year_label = builder.get_object("year_label")
        if view_type & ViewType.SMALL:
            self.__title_label.get_style_context().add_class(
                "text-x-large")
            self.__year_label.get_style_context().add_class(
                "text-large")
        else:
            self.__title_label.get_style_context().add_class(
                "text-xx-large")
            self.__year_label.get_style_context().add_class(
                "text-x-large")
        self.__duration_label = builder.get_object("duration_label")
        self.__title_label.set_text(album.name)
        self.__title_label.connect("query-tooltip", on_query_tooltip)
        self.__title_label.set_property("has-tooltip", True)
        self.__year_label.set_text(str(album.year))
        self.__year_label.set_margin_end(MARGIN)
        year_eventbox = builder.get_object("year_eventbox")
        year_eventbox.connect("realize", on_realize)
        year_eventbox.connect("button-release-event",
                              self.__on_year_button_release_event)
        duration = App().albums.get_duration(self.__album.id,
                                             self.__album.genre_ids)
        self.__duration_label.set_text(get_human_duration(duration))
        self.__artwork = builder.get_object("artwork")
        self.__grid = builder.get_object("grid")
        if view_type & ViewType.SMALL:
            self.__grid.get_style_context().add_class("white")
            self.__artwork.get_style_context().add_class("white")
            self.__widget = Gtk.Grid()
            self.__widget.show()
            self.__widget.get_style_context().add_class("cover-frame")
            self.__widget.add(builder.get_object("widget"))
            # See application.css: cover-frame
            self.__padding = 8
            self.__cover_widget = CoverWidget(True, ArtSize.LARGE)
        else:
            self.__grid.get_style_context().add_class("black")
            self.__artwork.get_style_context().add_class("black")
            self.__cover_widget = CoverWidget(True)
            self.__widget = builder.get_object("widget")
        self.__cover_widget.update(album)
        self.__cover_widget.set_margin_start(MARGIN)
        self.__cover_widget.set_vexpand(True)
        self.__cover_widget.show()
        self.__grid.attach(self.__cover_widget, 0, 0, 1, 3)
        self.__rating_grid = builder.get_object("rating_grid")
        rating = RatingWidget(album)
        rating.set_property("halign", Gtk.Align.START)
        rating.set_property("valign", Gtk.Align.CENTER)
        rating.show()
        self.__rating_grid.attach(rating, 0, 0, 1, 1)
        loved = LovedWidget(album)
        loved.set_property("halign", Gtk.Align.START)
        loved.set_property("valign", Gtk.Align.CENTER)
        loved.show()
        self.__rating_grid.attach(loved, 1, 0, 1, 1)
        self.add(self.__widget)
        self.connect("size-allocate", self.__on_size_allocate)
        self.connect("destroy", self.__on_destroy)
        self.__art_signal_id = App().art.connect(
                                               "album-artwork-changed",
                                               self.__on_album_artwork_changed)

    def set_height(self, height):
        """
            Set height
            @param height as int
        """
        self.__height = height
        if height < self.default_height:
            # Make grid cover artwork
            # No idea why...
            self.__grid.set_size_request(-1, height + 1)
            self.__cover_widget.hide()
            self.__duration_label.hide()
            self.__rating_grid.hide()
            self.__year_label.set_vexpand(True)
            self.__title_label.get_style_context().remove_class(
                "text-xx-large")
            self.__title_label.get_style_context().add_class(
                "text-x-large")
            self.__year_label.get_style_context().remove_class(
                "text-x-large")
            self.__year_label.get_style_context().add_class(
                "text-large")
        else:
            # Make grid cover artwork
            # No idea why...
            self.__grid.set_size_request(-1, height + 1)
            self.__cover_widget.show()
            self.__duration_label.show()
            self.__rating_grid.show()
            self.__year_label.set_vexpand(False)
            if App().window.is_adaptive:
                self.__title_label.get_style_context().add_class(
                    "text-x-large")
                self.__year_label.get_style_context().add_class(
                    "text-large")
            else:
                self.__title_label.get_style_context().add_class(
                    "text-xx-large")
                self.__year_label.get_style_context().add_class(
                    "text-x-large")

    def do_get_preferred_width(self):
        """
            Force preferred width
        """
        return (0, 0)

    def do_get_preferred_height(self):
        """
            Force preferred height
        """
        return (self.__height, self.__height)

    @property
    def height(self):
        """
            Get height
            @return int
        """
        return self.__height

    @property
    def default_height(self):
        """
            Get default height
        """
        if self.__view_type & ViewType.SMALL:
            return ArtSize.LARGE + 20
        else:
            return ArtSize.BANNER + 40

#######################
# PROTECTED           #
#######################
    def _on_menu_button_clicked(self, button):
        """
            Show album menu
            @param button as Gtk.Button
        """
        from lollypop.pop_menu import AlbumMenu
        menu = AlbumMenu(self.__album, True)
        popover = Gtk.Popover.new_from_model(button, menu)
        popover.popup()

#######################
# PRIVATE             #
#######################
    def __handle_size_allocate(self, allocation):
        """
            Change box max/min children
            @param allocation as Gtk.Allocation
        """
        self.__allocation_timeout_id = None
        if allocation.width == 1 or self.__width == allocation.width:
            return
        self.__width = allocation.width
        App().art_helper.set_album_artwork(
                self.__album,
                allocation.width - self.__padding,
                allocation.height - self.__padding,
                self.__artwork.get_scale_factor(),
                self.__on_album_artwork,
                ArtHelperEffect.RESIZE | ArtHelperEffect.BLUR_HARD)

    def __on_destroy(self, widget):
        """
            Disconnect signal
            @param widget as Gtk.Widget
        """
        if self.__art_signal_id is not None:
            App().art.disconnect(self.__art_signal_id)

    def __on_album_artwork_changed(self, art, album_id):
        """
            Update cover for album_id
            @param art as Art
            @param album id as int
        """
        if album_id == self.__album.id:
            App().art_helper.set_album_artwork(
                            self.__album,
                            self.get_allocated_width() - self.__padding,
                            self.get_allocated_height() - self.__padding,
                            self.__artwork.get_scale_factor(),
                            self.__on_album_artwork,
                            ArtHelperEffect.RESIZE | ArtHelperEffect.BLUR_HARD)

    def __on_album_artwork(self, surface):
        """
            Set album artwork
            @param surface as str
        """
        self.__artwork.set_from_surface(surface)

    def __on_year_button_release_event(self, widget, event):
        """
            Show year view
            @param widget as Gtk.Widget
            @param event as Gdk.event
        """
        App().window.container.show_view(Type.YEARS, [self.__album.year])

    def __on_size_allocate(self, widget, allocation):
        """
            Change box max/min children
            @param widget as Gtk.Widget
            @param allocation as Gtk.Allocation
        """
        if self.__allocation_timeout_id is not None:
            GLib.source_remove(self.__allocation_timeout_id)
        self.__allocation_timeout_id = GLib.idle_add(
            self.__handle_size_allocate, allocation)
