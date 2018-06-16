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

from gi.repository import Gtk, GObject

from gettext import gettext as _

from lollypop.widgets_rating import RatingWidget
from lollypop.widgets_loved import LovedWidget
from lollypop.widgets_album import AlbumWidget
from lollypop.pop_menu import AlbumMenu
from lollypop.widgets_context import ContextWidget
from lollypop.define import WindowSize
from lollypop.view_tracks import TracksView
from lollypop.define import App, ArtSize, ResponsiveType


class AlbumDetailedWidget(Gtk.Bin, AlbumWidget, TracksView):
    """
        Widget with cover and tracks
    """
    __gsignals__ = {
        "populated": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "overlayed": (GObject.SignalFlags.RUN_FIRST, None, (bool,))
    }

    def __init__(self, album, genre_ids, artist_ids, art_size):
        """
            Init detailed album widget
            @param album as Album
            @param genre ids as [int]
            @param artist ids as [int]
            @param lazy as LazyLoadingView
            @param art size as ArtSize
        """
        Gtk.Bin.__init__(self)
        AlbumWidget.__init__(self, album, genre_ids, artist_ids, art_size)
        TracksView.__init__(self, ResponsiveType.FIXED)
        self._rounded_class = "rounded-icon-small"
        self.__context = None
        # Cover + rating + spacing
        self.__height = ArtSize.BIG + 26
        self.set_property("height-request", self.__height)
        self.connect("size-allocate", self._on_size_allocate)
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/AlbumDetailedWidget.ui")
        builder.connect_signals(self)
        self._widget = builder.get_object("widget")
        album_info = builder.get_object("albuminfo")
        self.__title_label = builder.get_object("title")
        self.__title_label.set_property("has-tooltip", True)
        self.__artist_label = builder.get_object("artist")
        self.__artist_label.set_property("has-tooltip", True)
        self.__year_label = builder.get_object("year")
        self.__header = builder.get_object("header")
        self.__overlay = builder.get_object("overlay")
        self.__duration_label = builder.get_object("duration")
        self.__context_button = builder.get_object("context")

        if art_size == ArtSize.NONE:
            self._cover = None
            rating = RatingWidget(self._album)
            rating.set_hexpand(True)
            rating.set_property("halign", Gtk.Align.END)
            rating.set_property("valign", Gtk.Align.CENTER)
            rating.set_margin_end(10)
            rating.show()
            self.__header.attach(rating, 4, 0, 1, 1)
            loved = LovedWidget(self._album)
            loved.set_property("halign", Gtk.Align.END)
            loved.set_property("valign", Gtk.Align.CENTER)
            loved.set_margin_end(10)
            loved.show()
            self.__header.attach(loved, 5, 0, 1, 1)

            self.__artist_label.set_text(", ".join(self._album.artists))
            self.__artist_label.show()
            if self._album.year is not None:
                self.__year_label.set_label(str(self._album.year))
                self.__year_label.show()
        else:
            self.__duration_label.set_hexpand(True)
            builder = Gtk.Builder()
            builder.add_from_resource("/org/gnome/Lollypop/CoverBox.ui")
            builder.connect_signals(self)
            self._play_button = builder.get_object("play-button")
            self._action_button = builder.get_object("action-button")
            self._action_event = builder.get_object("action-event")
            self._cover = builder.get_object("cover")
            self.__coverbox = builder.get_object("coverbox")
            # 6 for 2*3px (application.css)
            self.__coverbox.set_property("width-request", art_size + 6)
            if art_size == ArtSize.BIG:
                self._cover.get_style_context().add_class("cover-frame")
                self._artwork_button = builder.get_object("artwork-button")
                if self._album.year is not None:
                    self.__year_label.set_label(str(self._album.year))
                    self.__year_label.show()
                grid = Gtk.Grid()
                grid.set_column_spacing(10)
                grid.set_property("halign", Gtk.Align.CENTER)
                grid.show()
                rating = RatingWidget(self._album)
                loved = LovedWidget(self._album)
                rating.show()
                loved.show()
                grid.add(rating)
                grid.add(loved)
                self.__coverbox.add(grid)
                self._widget.attach(self.__coverbox, 0, 0, 1, 1)
                if App().window.container.get_view_width() < WindowSize.MEDIUM:
                    self.__coverbox.hide()
                if len(artist_ids) > 1:
                    self.__artist_label.set_text(
                        ", ".join(self._album.artists))
                    self.__artist_label.show()
            elif art_size == ArtSize.HEADER:
                # Here we are working around default CoverBox ui
                # Do we really need to have another ui file?
                # So just hack values on the fly
                self._cover.get_style_context().add_class("small-cover-frame")
                overlay_grid = builder.get_object("overlay-grid")
                overlay_grid.set_margin_bottom(2)
                overlay_grid.set_margin_end(2)
                overlay_grid.set_column_spacing(0)
                play_event = builder.get_object("play-event")
                play_event.set_margin_start(2)
                play_event.set_margin_bottom(2)
                album_info.attach(self.__coverbox, 0, 0, 1, 1)
                self.__artist_label.set_text(", ".join(self._album.artists))
                self.__artist_label.show()

        self.__set_duration()

        album_info.add(self._responsive_widget)

        self.set_cover()
        self.update_state()

        self.__title_label.set_label(self._album.name)

        self.add(self._widget)

        self._lock_overlay = False

    def get_current_ordinate(self, parent):
        """
            If current track in widget, return it ordinate,
            @param parent widget as Gtk.Widget
            @return y as int
        """
        for dic in [self._tracks_widget_left, self._tracks_widget_right]:
            for widget in dic.values():
                for child in widget.get_children():
                    if child.track.id == App().player.current_track.id:
                        return child.translate_coordinates(parent, 0, 0)[1]
        return None

    def set_filter_func(self, func):
        """
            Set filter function
        """
        for widget in self._tracks_widget_left.values():
            widget.set_filter_func(func)
        for widget in self._tracks_widget_right.values():
            widget.set_filter_func(func)

    def update_playing_indicator(self):
        """
            Update playing indicator
        """
        TracksView.update_playing_indicator(self)

    def hide_header_labels(self):
        """
            Hide header labels
        """
        self.__title_label.hide()
        self.__artist_label.hide()
        self.__year_label.hide()

    @property
    def requested_height(self):
        """
            Requested height: Internal tracks or at least cover
        """
        if self.height < self.__height:
            return self.__height
        else:
            return self.height

#######################
# PROTECTED           #
#######################
    def _on_populated(self):
        """
            Emit populated signal
        """
        TracksView._on_populated(self)
        self.emit("populated")

    def _on_query_tooltip(self, widget, x, y, keyboard, tooltip):
        """
            Show tooltip if needed
            @param widget as Gtk.Widget
            @param x as int
            @param y as int
            @param keyboard as bool
            @param tooltip as Gtk.Tooltip
        """
        layout = widget.get_layout()
        if layout.is_ellipsized():
            tooltip.set_text(widget.get_label())
        else:
            return False
        return True

    def _on_context_clicked(self, button):
        """
            Show context widget
            @param button as Gtk.Button
        """
        def on_hide(widget):
            button.emit("clicked")
        image = button.get_image()
        if self.__context is None:
            image.set_from_icon_name("go-previous-symbolic",
                                     Gtk.IconSize.MENU)
            self.__context = ContextWidget(self._album, button)
            self.__context.connect("hide", on_hide)
            self.__context.set_property("halign", Gtk.Align.START)
            self.__context.set_property("valign", Gtk.Align.CENTER)
            self.__context.show()
            self.__header.insert_next_to(button, Gtk.PositionType.RIGHT)
            self.__header.attach_next_to(self.__context, button,
                                         Gtk.PositionType.RIGHT, 1, 1)
        else:
            image.set_from_icon_name("go-next-symbolic",
                                     Gtk.IconSize.MENU)
            self.__context.destroy()
            self.__context = None

    def _on_album_updated(self, scanner, album_id, destroy):
        """
            On album modified, disable it
            @param scanner as CollectionScanner
            @param album id as int
            @param destroy as bool
        """
        TracksView._on_album_updated(self, scanner, album_id, destroy)
        AlbumWidget._on_album_updated(self, scanner, album_id, destroy)

    def _on_size_allocate(self, widget, allocation):
        """
            Change box max/min children
            @param widget as Gtk.Widget
            @param allocation as Gtk.Allocation
        """
        TracksView._on_size_allocate(self, widget, allocation)
        if self._art_size == ArtSize.BIG:
            if allocation.width < WindowSize.MEDIUM:
                self.__coverbox.hide()
            else:
                self.__coverbox.show()

#######################
# PRIVATE             #
#######################
    def __set_duration(self):
        """
            Set album duration
        """
        duration = App().albums.get_duration(self._album.id,
                                             self._album.genre_ids)
        hours = int(duration / 3600)
        mins = int(duration / 60)
        if hours > 0:
            mins -= hours * 60
            if mins > 0:
                self.__duration_label.set_text(_("%s h  %s m") % (hours, mins))
            else:
                self.__duration_label.set_text(_("%s h") % hours)
        else:
            self.__duration_label.set_text(_("%s m") % mins)

    def __pop_menu(self, widget):
        """
            Popup menu for album
            @param widget as Gtk.Button
            @param album id as int
        """
        ancestor = self.get_ancestor(Gtk.Popover)
        # Get album real genre ids (not contextual)
        popover = Gtk.Popover.new_from_model(widget,
                                             AlbumMenu(self._album,
                                                       ancestor is not None))
        if ancestor is not None:
            App().window.container.view.show_popover(popover)
        else:
            popover.connect("closed", self.__on_pop_menu_closed)
            self.get_style_context().add_class("album-menu-selected")
            popover.show()

    def __on_pop_menu_closed(self, widget):
        """
            Remove selected style
            @param widget as Gtk.Popover
        """
        self.get_style_context().remove_class("album-menu-selected")
