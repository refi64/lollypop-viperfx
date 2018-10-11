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

from gi.repository import GLib, Gdk, Gtk, Pango, GObject

from gettext import gettext as _
from random import choice

from lollypop.widgets_album import AlbumWidget
from lollypop.art import AlbumArtHelper
from lollypop.pop_menu import AlbumMenu
from lollypop.define import App, ArtSize, Shuffle


class AlbumSimpleWidget(Gtk.FlowBoxChild, AlbumWidget, AlbumArtHelper):
    """
        Album widget showing cover, artist and title
    """
    __gsignals__ = {
        "populated": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "overlayed": (GObject.SignalFlags.RUN_FIRST, None, (bool,))
    }

    ctx = App().window.get_pango_context()
    layout = Pango.Layout.new(ctx)
    layout.set_text("a", 1)
    # * 2 => two labels
    LABEL_HEIGHT = int(layout.get_pixel_size()[1])

    def __init__(self, album, genre_ids, artist_ids):
        """
            Init simple album widget
            @param album as Album
            @param genre ids as [int]
            @param artist_ids as [int]
        """
        # We do not use Gtk.Builder for speed reasons
        Gtk.FlowBoxChild.__init__(self)
        self.set_size_request(ArtSize.BIG, ArtSize.BIG + self.LABEL_HEIGHT)
        self.get_style_context().add_class("loading")
        AlbumArtHelper.__init__(self)
        AlbumWidget.__init__(self, album, genre_ids, artist_ids)

    def populate(self):
        """
            Populate widget content
        """
        AlbumArtHelper.populate(self, ArtSize.BIG, "cover-frame")
        self.get_style_context().remove_class("loading")
        self._widget = Gtk.EventBox()
        grid = Gtk.Grid()
        grid.set_orientation(Gtk.Orientation.VERTICAL)
        self.__label = Gtk.Label()
        self.__label.set_justify(Gtk.Justification.CENTER)
        self.__label.set_ellipsize(Pango.EllipsizeMode.END)
        self.__label.set_property("halign", Gtk.Align.CENTER)
        album_name = GLib.markup_escape_text(self._album.name)
        artist_name = GLib.markup_escape_text(", ".join(self._album.artists))
        self.__label.set_markup("<b>%s</b>\n<span alpha='40000'>%s</span>" %
                                (album_name, artist_name))
        eventbox = Gtk.EventBox()
        eventbox.add(self.__label)
        eventbox.set_property("has-tooltip", True)
        eventbox.connect("query-tooltip", self._on_query_tooltip)
        eventbox.connect("realize", self._on_eventbox_realize)
        eventbox.connect("button-press-event",
                         self.__on_artist_button_press)
        eventbox.show()
        self._widget.add(grid)
        self.__overlay = Gtk.Overlay.new()
        self.__overlay.add(self._artwork)
        self.__overlay_grid = None
        grid.add(self.__overlay)
        grid.add(eventbox)
        self.add(self._widget)
        AlbumArtHelper.set_artwork(self)
        self.set_selection()
        self._widget.connect("enter-notify-event", self._on_enter_notify)
        self._widget.connect("leave-notify-event", self._on_leave_notify)
        self._widget.connect("button-press-event", self.__on_button_press)
        self._lock_overlay = False

    def set_artwork(self, album_id):
        """
            Set cover for album id
            @param album_id as int
        """
        if self._artwork is None or\
                (album_id is not None and album_id != self._album.id):
            return
        AlbumArtHelper.set_artwork(self)

    def do_get_preferred_width(self):
        """
            Return preferred width
            @return (int, int)
        """
        if self._widget is None:
            return (0, 0)
        width = Gtk.FlowBoxChild.do_get_preferred_width(self)[0]
        return (width, width)

    @property
    def is_populated(self):
        """
            True if album populated
        """
        return True

#######################
# PROTECTED           #
#######################
    def _show_overlay_func(self, set):
        """
            Set overlay
            @param set as bool
        """
        if self._lock_overlay or\
           self._show_overlay == set:
            return
        if set:
            # Play button
            self._play_event = Gtk.EventBox()
            self._play_event.set_property("has-tooltip", True)
            self._play_event.set_tooltip_text(_("Play"))
            self._play_event.connect("realize", self._on_eventbox_realize)
            self._play_event.connect("button-press-event",
                                     self._on_play_press_event)
            self._play_button = Gtk.Image.new_from_icon_name(
                "media-playback-start-symbolic",
                Gtk.IconSize.DND)
            self._play_button.set_opacity(0)
            # Play all button
            self._play_all_event = Gtk.EventBox()
            self._play_all_event.set_property("has-tooltip", True)
            self._play_all_event.set_tooltip_text(_("Play albums"))
            self._play_all_event.set_property("halign", Gtk.Align.END)
            self._play_all_event.set_property("valign", Gtk.Align.END)
            self._play_all_event.connect("realize", self._on_eventbox_realize)
            self._play_all_event.connect("button-press-event",
                                         self.__on_play_all_press_event)
            self._play_all_button = Gtk.Image.new()
            self._play_all_button.set_opacity(0)
            # Artwork button
            self._action2_event = Gtk.EventBox()
            self._action2_event.set_property("has-tooltip", True)
            self._action2_event.set_tooltip_text(_("Change artwork"))
            self._action2_event.set_property("halign", Gtk.Align.END)
            self._action2_event.set_property("valign", Gtk.Align.END)
            self._action2_event.connect("realize", self._on_eventbox_realize)
            self._action2_event.connect("button-press-event",
                                        self._on_artwork_press_event)
            self._action2_button = Gtk.Image.new_from_icon_name(
                "image-x-generic-symbolic",
                Gtk.IconSize.BUTTON)
            self._action2_button.set_opacity(0)
            # Action button
            self._action1_event = Gtk.EventBox()
            self._action1_event.set_property("has-tooltip", True)
            self._action1_event.set_property("halign", Gtk.Align.END)
            self._action1_event.set_property("valign", Gtk.Align.END)
            self._action1_event.connect("realize", self._on_eventbox_realize)
            self._action1_event.connect("button-press-event",
                                        self._on_action_press_event)
            self._action1_button = Gtk.Image.new()
            self._action1_button.set_opacity(0)
            self._play_event.set_hexpand(True)
            self._play_event.set_vexpand(False)
            self._play_event.set_property("halign", Gtk.Align.START)
            self._play_event.set_property("valign", Gtk.Align.END)
            self._play_event.add(self._play_button)
            self._play_all_event.add(self._play_all_button)
            self._action2_event.add(self._action2_button)
            self._action1_event.add(self._action1_button)
            if self.__overlay_grid is None:
                self.__overlay_grid = Gtk.Grid()
                self.__overlay_grid.set_row_spacing(6)
                self.__overlay_grid.set_margin_top(6)
                self.__overlay_grid.set_margin_bottom(6)
                self.__overlay_grid.set_margin_start(6)
                self.__overlay_grid.set_margin_end(6)
                self.__overlay_grid.set_property("halign", Gtk.Align.FILL)
                self.__overlay_grid.set_property("valign", Gtk.Align.END)
                self.__overlay.add_overlay(self.__overlay_grid)
            self.__overlay_grid.add(self._play_event)
            self.__overlay_grid.add(self._play_all_event)
            self.__overlay_grid.add(self._action1_event)
            self.__overlay_grid.add(self._action2_event)
            self.__overlay_grid.show_all()
            AlbumWidget._show_overlay_func(self, True)
        else:
            AlbumWidget._show_overlay_func(self, False)
            self._play_event.destroy()
            self._play_event = None
            self._play_button.destroy()
            self._play_button = None
            self._play_all_event.destroy()
            self._play_all_event = None
            self._play_all_button.destroy()
            self._play_all_button = None
            self._action1_event.destroy()
            self._action1_event = None
            self._action1_button.destroy()
            self._action1_button = None
            self._action2_event.destroy()
            self._action2_event = None
            self._action2_button.destroy()
            self._action2_button = None

    def _on_album_updated(self, scanner, album_id, destroy):
        """
            On album modified, disable it
            @param scanner as CollectionScanner
            @param album id as int
            @param deleted as bool
            @param destroy as bool
        """
        if self._album.id == album_id and destroy:
            self.destroy()

#######################
# PRIVATE             #
#######################
    def __on_play_all_press_event(self, widget, event):
        """
            Play album with context
            @param: widget as Gtk.EventBox
            @param: event as Gdk.Event
        """
        if App().player.is_locked:
            return True
        self._show_append(False)
        if App().player.is_party:
            App().lookup_action("party").change_state(GLib.Variant("b", False))
        if App().settings.get_enum("shuffle") == Shuffle.TRACKS:
            track = choice(self._album.tracks)
        else:
            track = self._album.tracks[0]
        App().player.clear_albums()
        for child in self.get_parent().get_children():
            if not child.filtered:
                App().player.add_album(child.album)
        App().player.load(track)
        return True

    def _on_query_tooltip(self, eventbox, x, y, keyboard, tooltip):
        """
            Show tooltip if needed
            @param eventbox as Gtk.EventBox
            @param x as int
            @param y as int
            @param keyboard as bool
            @param tooltip as Gtk.Tooltip
        """
        layout = self.__label.get_layout()
        if layout.is_ellipsized():
            markup = self.__label.get_label()
            tooltip.set_markup(markup)
            return True

    def __on_button_press(self, eventbox, event):
        """
            Handle album mouse click
            @param eventbox as Gtk.EventBox
            @param event as Gdk.EventButton
        """
        if event.button != 1:
            popover = Gtk.Popover.new_from_model(self._artwork,
                                                 AlbumMenu(self._album,
                                                           True))
            popover.set_position(Gtk.PositionType.BOTTOM)
            rect = Gdk.Rectangle()
            rect.x = event.x
            rect.y = event.y
            rect.width = rect.height = 1
            popover.set_pointing_to(rect)
            popover.connect("closed", self.__on_album_popover_closed)
            popover.popup()

    def __on_artist_button_press(self, eventbox, event):
        """
            Go to artist page
            @param eventbox as Gtk.EventBox
            @param event as Gdk.EventButton
        """
        App().window.container.show_artists_albums(self._album.artist_ids)
        return True

    def __on_album_popover_closed(self, popover):
        """
            Remove overlay and restore opacity
            @param popover as Gtk.Popover
            @param album_widget as AlbumWidget
        """
        self.lock_overlay(False)
        self.get_artwork().set_opacity(1)
