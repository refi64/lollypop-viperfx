# Copyright (c) 2014-2017 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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
from lollypop.pop_menu import AlbumMenu
from lollypop.define import Lp, ArtSize, Shuffle


class AlbumSimpleWidget(Gtk.FlowBoxChild, AlbumWidget):
    """
        Album widget showing cover, artist and title
    """
    __gsignals__ = {
        "overlayed": (GObject.SignalFlags.RUN_FIRST, None, (bool,))
    }

    def __init__(self, album_id, genre_ids, artist_ids):
        """
            Init simple album widget
            @param album id as int
            @param genre ids as [int]
            @param artist_ids as [int]
        """
        # We do not use Gtk.Builder for speed reasons
        Gtk.FlowBoxChild.__init__(self)
        self.set_size_request(ArtSize.BIG, ArtSize.BIG)
        self.get_style_context().add_class("loading")
        AlbumWidget.__init__(self, album_id, genre_ids,
                             artist_ids, ArtSize.BIG)

    def populate(self):
        """
            Populate widget content
        """
        self.get_style_context().remove_class("loading")
        self._rounded_class = "rounded-icon-small"
        self._widget = Gtk.EventBox()
        grid = Gtk.Grid()
        grid.set_orientation(Gtk.Orientation.VERTICAL)
        self._cover = Gtk.Image()
        self._cover.set_property("halign", Gtk.Align.CENTER)
        self._cover.get_style_context().add_class("cover-frame")
        self.__title_label = Gtk.Label()
        self.__title_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.__title_label.set_property("halign", Gtk.Align.CENTER)
        self.__title_label.set_markup("<b>" +
                                      GLib.markup_escape_text(
                                                            self._album.name) +
                                      "</b>")
        self.__artist_label = Gtk.Label()
        self.__artist_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.__artist_label.set_property("halign", Gtk.Align.CENTER)
        self.__artist_label.set_text(", ".join(self._album.artists))
        self.__artist_label.get_style_context().add_class("dim-label")
        artist_eventbox = Gtk.EventBox()
        artist_eventbox.add(self.__artist_label)
        artist_eventbox.connect("realize", self._on_eventbox_realize)
        artist_eventbox.connect("button-press-event",
                                self.__on_artist_button_press)
        artist_eventbox.show()
        self._widget.set_property("has-tooltip", True)
        self._widget.connect("query-tooltip", self._on_query_tooltip)
        self._widget.add(grid)
        self.__overlay = Gtk.Overlay.new()
        self.__overlay.set_property("halign", Gtk.Align.CENTER)
        self.__overlay.set_property("valign", Gtk.Align.CENTER)
        self.__overlay_grid = Gtk.Grid()
        self.__overlay_grid.set_column_spacing(6)
        self.__overlay_grid.set_row_spacing(6)
        self.__overlay_grid.set_margin_top(6)
        self.__overlay_grid.set_margin_bottom(6)
        self.__overlay_grid.set_margin_start(6)
        self.__overlay_grid.set_margin_end(6)
        self.__overlay.add(self._cover)
        self.__overlay.add_overlay(self.__overlay_grid)
        color = Gtk.Grid()
        color.set_property("halign", Gtk.Align.CENTER)
        color.set_property("valign", Gtk.Align.CENTER)
        color.get_style_context().add_class("white")
        color.add(self.__overlay)
        grid.add(color)
        grid.add(self.__title_label)
        grid.add(artist_eventbox)
        self.add(self._widget)
        self.set_cover()
        self.update_state()
        self._widget.set_property("halign", Gtk.Align.CENTER)
        self._widget.set_property("valign", Gtk.Align.CENTER)
        self.show_all()
        self._widget.connect("enter-notify-event", self._on_enter_notify)
        self._widget.connect("leave-notify-event", self._on_leave_notify)
        self._widget.connect("button-press-event", self.__on_button_press)
        self._lock_overlay = False

    def do_get_preferred_width(self):
        """
            Return preferred width
            @return (int, int)
        """
        if self._widget is None:
            return (0, 0)
        width = Gtk.FlowBoxChild.do_get_preferred_width(self)[0]
        return (width, width)

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
                                               Gtk.IconSize.BUTTON)
            self._play_button.set_opacity(0)
            # Play all button
            self._play_all_event = Gtk.EventBox()
            self._play_all_event.set_property("has-tooltip", True)
            self._play_all_event.set_tooltip_text(_("Play albums"))
            self._play_all_event.set_property("halign", Gtk.Align.END)
            self._play_all_event.connect("realize", self._on_eventbox_realize)
            self._play_all_event.connect("button-press-event",
                                         self.__on_play_all_press_event)
            self._play_all_button = Gtk.Image.new()
            self._play_all_button.set_opacity(0)
            # Artwork button
            self._artwork_event = Gtk.EventBox()
            self._artwork_event.set_property("has-tooltip", True)
            self._artwork_event.set_tooltip_text(_("Change artwork"))
            self._artwork_event.set_property("halign", Gtk.Align.END)
            self._artwork_event.connect("realize", self._on_eventbox_realize)
            self._artwork_event.connect("button-press-event",
                                        self._on_artwork_press_event)
            self._artwork_button = Gtk.Image.new_from_icon_name(
                                               "image-x-generic-symbolic",
                                               Gtk.IconSize.BUTTON)
            self._artwork_button.set_opacity(0)
            # Action button
            self._action_event = Gtk.EventBox()
            self._action_event.set_property("has-tooltip", True)
            self._action_event.set_property("halign", Gtk.Align.END)
            self._action_event.connect("realize", self._on_eventbox_realize)
            self._action_event.connect("button-press-event",
                                       self._on_action_press_event)
            self._action_button = Gtk.Image.new()
            self._action_button.set_opacity(0)
            self.__overlay_grid.set_orientation(self._overlay_orientation)
            if self._overlay_orientation == Gtk.Orientation.VERTICAL:
                self._play_event.set_hexpand(False)
                self._play_event.set_vexpand(True)
                self._play_event.set_property("halign", Gtk.Align.END)
                self._play_event.set_property("valign", Gtk.Align.START)
                self.__overlay_grid.set_property("valign", Gtk.Align.FILL)
                self.__overlay_grid.set_property("halign", Gtk.Align.END)
            else:
                self._play_event.set_hexpand(True)
                self._play_event.set_vexpand(False)
                self._play_event.set_property("halign", Gtk.Align.START)
                self._play_event.set_property("valign", Gtk.Align.END)
                self.__overlay_grid.set_property("halign", Gtk.Align.FILL)
                self.__overlay_grid.set_property("valign", Gtk.Align.END)
            self._play_event.add(self._play_button)
            self._play_all_event.add(self._play_all_button)
            self._artwork_event.add(self._artwork_button)
            self._action_event.add(self._action_button)
            self.__overlay_grid.add(self._play_event)
            self.__overlay_grid.add(self._play_all_event)
            self.__overlay_grid.add(self._action_event)
            self.__overlay_grid.add(self._artwork_event)
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
            self._action_event.destroy()
            self._action_event = None
            self._action_button.destroy()
            self._action_button = None
            self._artwork_event.destroy()
            self._artwork_event = None
            self._artwork_button.destroy()
            self._artwork_button = None

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
        if Lp().player.locked:
            return True
        self._show_append(False)
        if Lp().player.is_party:
            Lp().player.set_party(False)
        Lp().player.clear_albums()
        if Lp().settings.get_enum("shuffle") == Shuffle.TRACKS:
            track = choice(self._album.tracks)
        else:
            track = self._album.tracks[0]
        if Lp().window.view.filtered:
            # Here we need to get ids from parent as view may be filtered
            for child in self.get_parent().get_children():
                if not child.filtered:
                    Lp().player.add_album(child.album)
        else:
            Lp().player.set_albums(track.id, self._artist_ids,
                                   self._album.genre_ids)
        Lp().player.load(track)
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
        eventbox.set_tooltip_text("")
        for widget in [self.__title_label, self.__artist_label]:
            layout = widget.get_layout()
            if layout.is_ellipsized():
                artist_text = self.__artist_label.get_text()
                if artist_text:
                    text = "<b>%s</b> - %s" % (
                        GLib.markup_escape_text(artist_text),
                        GLib.markup_escape_text(self.__title_label.get_text()))
                else:
                    text = GLib.markup_escape_text(
                                                 self.__title_label.get_text())
                eventbox.set_tooltip_markup(text)
                break

    def __on_button_press(self, eventbox, event):
        """
            Store pressed button
            @param eventbox as Gtk.EventBox
            @param event as Gdk.EventButton
        """
        if event.button != 1:
            popover = Gtk.Popover.new_from_model(self._cover,
                                                 AlbumMenu(self._album,
                                                           True))
            popover.set_position(Gtk.PositionType.BOTTOM)
            rect = Gdk.Rectangle()
            rect.x = event.x
            rect.y = event.y
            rect.width = rect.height = 1
            popover.set_pointing_to(rect)
            popover.connect("closed", self.__on_album_popover_closed)
            popover.show()

    def __on_artist_button_press(self, eventbox, event):
        """
            Go to artist page
            @param eventbox as Gtk.EventBox
            @param event as Gdk.EventButton
        """
        Lp().window.show_artists_albums(self._album.artist_ids)
        return True

    def __on_album_popover_closed(self, popover):
        """
            Remove overlay and restore opacity
            @param popover as Gtk.Popover
            @param album_widget as AlbumWidget
        """
        self.lock_overlay(False)
        self.get_cover().set_opacity(1)
