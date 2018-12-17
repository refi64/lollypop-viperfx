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

from gi.repository import Gtk, GObject, GLib, Pango

from gettext import gettext as _

from lollypop.widgets_rating import RatingWidget
from lollypop.widgets_loved import LovedWidget
from lollypop.widgets_album import AlbumWidget
from lollypop.helper_overlay import OverlayAlbumHelper
from lollypop.widgets_context import ContextWidget
from lollypop.define import Sizing
from lollypop.view_tracks import TracksView
from lollypop.define import App, ArtSize, RowListType


class AlbumDetailedWidget(Gtk.Bin, AlbumWidget,
                          OverlayAlbumHelper, TracksView):
    """
        Widget with cover and tracks
    """
    __gsignals__ = {
        "populated": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "left-loaded": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "overlayed": (GObject.SignalFlags.RUN_FIRST, None, (bool,))
    }

    def __init__(self, album, genre_ids, artist_ids, show_cover):
        """
            Init detailed album widget
            @param album as Album
            @param label_height as int
            @param genre ids as [int]
            @param artist ids as [int]
            @param show_cover as bool
        """
        Gtk.Bin.__init__(self)
        AlbumWidget.__init__(self, album, genre_ids, artist_ids)
        TracksView.__init__(self, RowListType.TWO_COLUMNS)
        self._widget = None
        self.__show_cover = show_cover
        self.__width_allocation = 0
        self.connect("size-allocate", self.__on_size_allocate)

    def populate(self):
        """
            Populate widget content
        """
        if self._widget is None:
            OverlayAlbumHelper.__init__(self)
            self.__context = None
            grid = Gtk.Grid()
            grid.set_margin_start(5)
            grid.set_margin_end(5)
            grid.set_row_spacing(1)
            grid.set_vexpand(True)
            grid.show()
            self.__title_label = Gtk.Label()
            self.__title_label.set_margin_end(10)
            self.__title_label.set_ellipsize(Pango.EllipsizeMode.END)
            self.__title_label.get_style_context().add_class("dim-label")
            self.__title_label.set_property("has-tooltip", True)
            self.__title_label.connect("query-tooltip",
                                       self.__on_query_tooltip)
            self.__title_label.show()
            self.__artist_label = Gtk.Label()
            self.__artist_label.set_margin_end(10)
            self.__artist_label.set_ellipsize(Pango.EllipsizeMode.END)
            self.__artist_label.set_property("has-tooltip", True)
            self.__artist_label.connect("query-tooltip",
                                        self.__on_query_tooltip)
            self.__artist_label.show()
            self.__year_label = Gtk.Label()
            self.__year_label.set_margin_end(10)
            self.__year_label.get_style_context().add_class("dim-label")
            self.__year_label.show()
            self.__duration_label = Gtk.Label()
            self.__duration_label.get_style_context().add_class("dim-label")
            self.__duration_label.show()
            self.__context_button = Gtk.Button.new_from_icon_name(
                "go-next-symbolic", Gtk.IconSize.BUTTON)
            self.__context_button.set_relief(Gtk.ReliefStyle.NONE)
            self.__context_button.connect("clicked", self.__on_context_clicked)
            self.__context_button.get_style_context().add_class("menu-button")
            self.__context_button.get_style_context().add_class(
                                                          "album-menu-button")
            self.__context_button.show()
            self._widget = Gtk.Grid()
            self._widget.set_orientation(Gtk.Orientation.VERTICAL)
            self._widget.set_row_spacing(2)
            self._widget.show()
            self.__header = Gtk.Grid()
            self.__header.add(self.__artist_label)
            self.__header.add(self.__title_label)
            self.__header.add(self.__year_label)
            self.__header.add(self.__context_button)
            self.__header.show()
            self._widget.add(self.__header)
            separator = Gtk.Separator.new(Gtk.Orientation.HORIZONTAL)
            separator.show()
            self._widget.add(separator)

            loved = LovedWidget(self._album)
            loved.set_property("valign", Gtk.Align.CENTER)
            loved.set_margin_end(10)
            loved.show()

            rating = RatingWidget(self._album)
            rating.set_property("valign", Gtk.Align.CENTER)
            rating.set_property("halign", Gtk.Align.END)
            rating.set_margin_end(10)
            rating.show()

            if self.__show_cover:
                self.__header.add(self.__duration_label)
                self.__duration_label.set_hexpand(True)
                self.__duration_label.set_property("halign", Gtk.Align.END)
                eventbox = Gtk.EventBox()
                eventbox.connect("enter-notify-event", self._on_enter_notify)
                eventbox.connect("leave-notify-event", self._on_leave_notify)
                eventbox.connect("button-press-event", self._on_button_press)
                eventbox.show()
                self.set_property("valign", Gtk.Align.CENTER)
                self._artwork = App().art_helper.get_image(ArtSize.BIG,
                                                           ArtSize.BIG,
                                                           "cover-frame")
                self._artwork.show()
                eventbox.add(self._artwork)
                self.__duration_label.set_hexpand(True)
                self._overlay = Gtk.Overlay.new()
                self._overlay.add(eventbox)
                self._overlay.show()
                self.__coverbox = Gtk.Grid()
                self.__coverbox.set_row_spacing(2)
                self.__coverbox.set_margin_end(10)
                self.__coverbox.set_orientation(Gtk.Orientation.VERTICAL)
                self.__coverbox.show()
                self.__coverbox.attach(self._overlay, 0, 0, 2, 1)
                loved.set_property("halign", Gtk.Align.START)
                self.__coverbox.attach(rating, 0, 1, 1, 1)
                self.__coverbox.attach_next_to(loved,
                                               rating,
                                               Gtk.PositionType.RIGHT,
                                               1,
                                               1)
                if App().window.container.stack.get_allocation().width <\
                        Sizing.MEDIUM:
                    self.__coverbox.hide()
                if len(self._artist_ids) > 1:
                    self.__artist_label.set_text(
                        ", ".join(self._album.artists))
                    self.__artist_label.show()
            else:
                self._artwork = None
                loved.set_property("halign", Gtk.Align.END)
                self.__header.add(rating)
                self.__header.add(loved)
                rating.set_hexpand(True)
                self.__header.add(self.__duration_label)
                self.__artist_label.set_text(", ".join(self._album.artists))
                self.__artist_label.show()
            self.__set_duration()
            album_name = GLib.markup_escape_text(self._album.name)
            artist_name = GLib.markup_escape_text(
                ", ".join(self._album.artists))
            self.__title_label.set_markup("<b>%s</b>" % album_name)
            self.__artist_label.set_markup("<b>%s</b>" % artist_name)
            if self._album.year is not None:
                self.__year_label.set_label(str(self._album.year))
                self.__year_label.show()
            self.set_selection()
            if self._artwork is None:
                TracksView.populate(self)
                self._widget.add(self._responsive_widget)
                self._responsive_widget.show()
            else:
                grid.add(self.__coverbox)
                self.set_artwork()
            grid.add(self._widget)
            self.add(grid)
        else:
            TracksView.populate(self)

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

    def set_playing_indicator(self):
        """
            Update playing indicator
        """
        TracksView.set_playing_indicator(self)

    @property
    def requested_height(self):
        """
            Requested height: Internal tracks or at least cover
            @return (minimal: int, maximal: int)
        """
        from lollypop.widgets_row_track import TrackRow
        track_height = TrackRow.get_best_height(self)
        minimal_height = maximal_height = track_height + 20
        count = self._album.tracks_count
        mid_tracks = int(0.5 + count / 2)
        left_height = track_height * mid_tracks
        right_height = track_height * (count - mid_tracks)
        if left_height > right_height:
            minimal_height += left_height
        else:
            minimal_height += right_height
        maximal_height += left_height + right_height
        # Add height for disc label
        if len(self._album.discs) > 1:
            minimal_height += track_height
            maximal_height += track_height
        # 26 is for loved and rating
        cover_height = ArtSize.BIG + 26
        if minimal_height < cover_height:
            return (cover_height, cover_height)
        else:
            return (minimal_height, maximal_height)

#######################
# PROTECTED           #
#######################
    def _on_tracks_populated(self, disc_number):
        """
            Emit populated signal
            @param disc_number as int
        """
        self.emit("populated")

    def _on_album_updated(self, scanner, album_id, destroy):
        """
            On album modified, disable it
            @param scanner as CollectionScanner
            @param album id as int
            @param destroy as bool
        """
        TracksView._on_album_updated(self, scanner, album_id, destroy)
        AlbumWidget._on_album_updated(self, scanner, album_id, destroy)

    def _on_eventbox_button_press_event(self, widget, event):
        """
            Show overlay if not shown
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        # Here some code for touch screens
        # If mouse pointer activate Gtk.FlowBoxChild, overlay is on,
        # as enter notify event enabled it
        # Else, we are in touch screen, first time show overlay, next time
        # show popover
        if not self.is_overlay:
            self.show_overlay(True)
            return

    def _on_album_artwork(self, surface):
        """
            Set album artwork
            @param surface as str
        """
        if surface is None:
            self._artwork.set_from_icon_name("folder-music-symbolic",
                                             Gtk.IconSize.DIALOG)
        else:
            self._artwork.set_from_surface(surface)
        if self._responsive_widget is None:
            self._artwork.show()
            TracksView.populate(self)
            self._widget.add(self._responsive_widget)
            self._responsive_widget.show()

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

    def __on_query_tooltip(self, widget, x, y, keyboard, tooltip):
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

    def __on_context_clicked(self, button):
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

    def __on_size_allocate(self, widget, allocation):
        """
            Update internals
            @param widget as Gtk.Widget
            @param allocation as Gtk.Allocation
        """
        if self.__width_allocation == allocation.width:
            return
        self.__width_allocation = allocation.width
        (min_height, max_height) = self.requested_height
        if allocation.width < Sizing.MONSTER:
            self.set_size_request(-1, max_height)
        else:
            self.set_size_request(-1, min_height)
        if self._artwork is not None:
            # Use mainloop to let GTK get the event
            if allocation.width < Sizing.MEDIUM:
                GLib.idle_add(self.__coverbox.hide)
            else:
                GLib.idle_add(self.__coverbox.show)
