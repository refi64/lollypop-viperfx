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

from gi.repository import Gtk, Pango, GLib, Gst, Gdk

from lollypop.define import App, RowListType
from lollypop.widgets_indicator import IndicatorWidget
from lollypop.widgets_context import ContextWidget
from lollypop.utils import seconds_to_string


class Row(Gtk.ListBoxRow):
    """
        A row
    """

    def __init__(self, track, list_type):
        """
            Init row widgets
            @param track as Track
            @param list_type as RowListType
        """
        # We do not use Gtk.Builder for speed reasons
        Gtk.ListBoxRow.__init__(self)
        self._list_type = list_type
        self._artists_label = None
        self._track = track
        self.__preview_timeout_id = None
        self.__context_timeout_id = None
        self.__context = None
        self._indicator = IndicatorWidget(self, list_type)
        # We do not use set_indicator() here, we do not want widget to be
        # populated
        if App().player.current_track.id == self._track.id:
            self._indicator.play()
        elif self._track.loved:
            self._indicator.loved(self._track.loved)
        self._row_widget = Gtk.EventBox()
        self._row_widget.connect("destroy", self._on_destroy)
        self._row_widget.connect("button-release-event",
                                 self.__on_button_release_event)
        self._row_widget.connect("enter-notify-event",
                                 self.__on_enter_notify_event)
        self._row_widget.connect("leave-notify-event",
                                 self.__on_leave_notify_event)
        self._grid = Gtk.Grid()
        self._grid.set_column_spacing(5)
        self._row_widget.add(self._grid)
        self._title_label = Gtk.Label.new(self._track.name)
        self._title_label.set_property("has-tooltip", True)
        self._title_label.connect("query-tooltip",
                                  self.__on_query_tooltip)
        self._title_label.set_property("hexpand", True)
        self._title_label.set_property("halign", Gtk.Align.START)
        self._title_label.set_property("xalign", 0)
        self._title_label.set_ellipsize(Pango.EllipsizeMode.END)
        featuring_artist_ids = track.featuring_artist_ids
        if featuring_artist_ids:
            artists = []
            for artist_id in featuring_artist_ids:
                artists.append(App().artists.get_name(artist_id))
            self._artists_label = Gtk.Label.new(GLib.markup_escape_text(
                ", ".join(artists)))
            self._artists_label.set_use_markup(True)
            self._artists_label.set_property("has-tooltip", True)
            self._artists_label.connect("query-tooltip",
                                        self.__on_query_tooltip)
            self._artists_label.set_property("hexpand", True)
            self._artists_label.set_property("halign", Gtk.Align.END)
            self._artists_label.set_ellipsize(Pango.EllipsizeMode.END)
            self._artists_label.set_opacity(0.3)
            self._artists_label.set_margin_end(5)
            self._artists_label.show()
        self._duration_label = Gtk.Label.new(
            seconds_to_string(self._track.duration))
        self._duration_label.get_style_context().add_class("dim-label")
        self._num_label = Gtk.Label()
        self._num_label.set_ellipsize(Pango.EllipsizeMode.END)
        self._num_label.set_property("valign", Gtk.Align.CENTER)
        self._num_label.set_width_chars(4)
        self._num_label.get_style_context().add_class("dim-label")
        self.update_number_label()
        self.__menu_button = Gtk.Button.new()
        self.__menu_button.set_relief(Gtk.ReliefStyle.NONE)
        self.__menu_button.get_style_context().add_class("menu-button")
        self.__menu_button.get_style_context().add_class("track-menu-button")
        if list_type & (RowListType.READ_ONLY | RowListType.POPOVER):
            self.__menu_button.set_opacity(0)
            self.__menu_button.set_sensitive(False)
        self._grid.add(self._num_label)
        self._grid.add(self._title_label)
        if self._artists_label is not None:
            self._grid.add(self._artists_label)
        self._grid.add(self._duration_label)
        self._grid.add(self.__menu_button)
        self.add(self._row_widget)
        self.get_style_context().add_class("trackrow")

    def set_indicator(self, playing, loved):
        """
            Show indicator
            @param widget name as str
            @param playing as bool
            @param loved as bool
        """
        self._indicator.clear()
        if playing:
            self.get_style_context().remove_class("trackrow")
            self.get_style_context().add_class("trackrowplaying")
            if loved == 1:
                self._indicator.play_loved()
            else:
                self._indicator.play()
        else:
            self.get_style_context().remove_class("trackrowplaying")
            self.get_style_context().add_class("trackrow")
            if loved != 0 and self.__context is None:
                self._indicator.loved(loved)
            else:
                self._indicator.button()

    def update_number_label(self):
        """
            Update position label for row
        """
        if App().player.track_in_queue(self._track):
            self._num_label.get_style_context().add_class("queued")
            pos = App().player.get_track_position(self._track.id)
            self._num_label.set_text(str(pos))
        elif self._track.number > 0:
            self._num_label.get_style_context().remove_class("queued")
            self._num_label.set_text(str(self._track.number))
        else:
            self._num_label.get_style_context().remove_class("queued")
            self._num_label.set_text("")

    @property
    def row_widget(self):
        """
            Get row main widget
            @return Gtk.Widget
        """
        return self._row_widget

    @property
    def track(self):
        """
            Get row track
            @return Track
        """
        return self._track

#######################
# PROTECTED           #
#######################
    def _get_menu(self):
        """
            Return TrackMenu
        """
        from lollypop.pop_menu import TrackMenu
        return TrackMenu(self._track)

    def _on_destroy(self, widget):
        """
            We need to stop timeout idle to prevent
            __on_indicator_button_release_event() segfaulting
        """
        if self.__context_timeout_id is not None:
            GLib.source_remove(self.__context_timeout_id)
            self.__context_timeout_id = None

#######################
# PRIVATE             #
#######################
    def __play_preview(self):
        """
            Play track
            @param widget as Gtk.Widget
        """
        App().player.preview.set_property("uri", self._track.uri)
        App().player.preview.set_state(Gst.State.PLAYING)
        self.set_indicator(True, False)
        self.__preview_timeout_id = None

    def __popup_menu(self, eventbox, xcoordinate=None, ycoordinate=None):
        """
            Popup menu for track
            @param eventbox as Gtk.EventBox
            @param xcoordinate as int (or None)
            @param ycoordinate as int (or None)
        """
        from lollypop.pop_menu import TrackMenuPopover, RemoveMenuPopover
        if self.get_state_flags() & Gtk.StateFlags.SELECTED:
            # Get all selected rows
            rows = [self]
            r = self.previous_row
            while r is not None:
                if r.get_state_flags() & Gtk.StateFlags.SELECTED:
                    rows.append(r)
                r = r.previous_row
            r = self.next_row
            while r is not None:
                if r.get_state_flags() & Gtk.StateFlags.SELECTED:
                    rows.append(r)
                r = r.next_row
            popover = RemoveMenuPopover(rows)
        else:
            popover = TrackMenuPopover(self._track, self._get_menu())
        if xcoordinate is not None and ycoordinate is not None:
            rect = eventbox.get_allocation()
            rect.x = xcoordinate
            rect.y = ycoordinate
            rect.width = rect.height = 1
        popover.set_relative_to(eventbox)
        popover.set_pointing_to(rect)
        popover.connect("closed", self.__on_closed)
        self.get_style_context().add_class("track-menu-selected")
        popover.popup()

    def __on_artist_button_press(self, eventbox, event):
        """
            Go to artist page
            @param eventbox as Gtk.EventBox
            @param event as Gdk.EventButton
        """
        App().window.container.show_artists_albums(self._album.artist_ids)
        return True

    def __on_enter_notify_event(self, widget, event):
        """
            Set image on buttons now, speed reason
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        if self.__context_timeout_id is not None:
            GLib.source_remove(self.__context_timeout_id)
            self.__context_timeout_id = None
        if App().settings.get_value("preview-output").get_string() != "":
            self.__preview_timeout_id = GLib.timeout_add(500,
                                                         self.__play_preview)
        if self.__menu_button.get_image() is None:
            image = Gtk.Image.new_from_icon_name("go-previous-symbolic",
                                                 Gtk.IconSize.MENU)
            self.__menu_button.set_image(image)
            self.__menu_button.connect(
                "button-release-event",
                self.__on_indicator_button_release_event)
        self._indicator.button()

    def __on_leave_notify_event(self, widget, event):
        """
            Stop preview
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        def close_indicator():
            """
                Simulate a release event
            """
            self.__on_indicator_button_release_event(self.__menu_button,
                                                     event)
        allocation = widget.get_allocation()
        if event.x <= 0 or\
           event.x >= allocation.width or\
           event.y <= 0 or\
           event.y >= allocation.height:
            if self.__context is not None and\
                    self.__context_timeout_id is None:
                self.__context_timeout_id = GLib.timeout_add(
                    1000,
                    close_indicator)
            if App().settings.get_value("preview-output").get_string() != "":
                if self.__preview_timeout_id is not None:
                    GLib.source_remove(self.__preview_timeout_id)
                    self.__preview_timeout_id = None
                App().player.preview.set_state(Gst.State.NULL)
            self.set_indicator(App().player.current_track.id == self._track.id,
                               self._track.loved)

    def __on_button_release_event(self, widget, event):
        """
            Handle button press event:
                |_ 1 => activate
                |_ 2 => queue
                |_ 3 => menu
            @param widget as Gtk.Widget
            @param event as Gdk.EventButton
        """
        if event.state & Gdk.ModifierType.CONTROL_MASK and\
                self._list_type & RowListType.DND:
            if self.get_state_flags() & Gtk.StateFlags.SELECTED:
                self.set_state_flags(Gtk.StateFlags.NORMAL, True)
            else:
                self.set_state_flags(Gtk.StateFlags.SELECTED, True)
                self.grab_focus()
        elif event.state & Gdk.ModifierType.SHIFT_MASK and\
                self._list_type & RowListType.DND:
            self.emit("do-selection")
        elif event.button == 3:
            window = widget.get_window()
            if window == event.window:
                self.__popup_menu(widget, event.x, event.y)
            # Happens when pressing button over menu btn
            else:
                self.__on_indicator_button_release_event(self.__menu_button,
                                                         event)
        elif event.button == 2:
            if self._track.id in App().player.queue:
                App().player.remove_from_queue(self._track.id)
            else:
                App().player.append_to_queue(self._track.id)
        elif event.state & Gdk.ModifierType.MOD1_MASK:
            App().player.clear_albums()
            App().player.reset_history()
            App().player.load(self._track)
        else:
            self.activate()
        return True

    def __on_indicator_button_release_event(self, button, event):
        """
            Popup menu for track relative to button
            @param button as Gtk.Button
            @param event as Gdk.EventButton
        """
        def on_hide(widget):
            self.__on_indicator_button_release_event(button, event)
        self.__context_timeout_id = None
        image = self.__menu_button.get_image()
        if self.__context is None:
            image.set_from_icon_name("go-next-symbolic",
                                     Gtk.IconSize.MENU)
            self.__context = ContextWidget(self._track, button)
            self.__context.connect("hide", on_hide)
            self.__context.set_property("halign", Gtk.Align.END)
            self.__context.show()
            self._duration_label.hide()
            self._grid.insert_next_to(button, Gtk.PositionType.LEFT)
            self._grid.attach_next_to(self.__context, button,
                                      Gtk.PositionType.LEFT, 1, 1)
            self.set_indicator(App().player.current_track.id == self._track.id,
                               False)
        else:
            image.set_from_icon_name("go-previous-symbolic",
                                     Gtk.IconSize.MENU)
            self.__context.destroy()
            self._duration_label.show()
            self.__context = None
            self.set_indicator(App().player.current_track.id == self._track.id,
                               self._track.loved)
        return True

    def __on_closed(self, widget):
        """
            Remove selected style
            @param widget as Popover
        """
        self.get_style_context().remove_class("track-menu-selected")

    def __on_query_tooltip(self, widget, x, y, keyboard, tooltip):
        """
            Show tooltip if needed
            @param widget as Gtk.Widget
            @param x as int
            @param y as int
            @param keyboard as bool
            @param tooltip as Gtk.Tooltip
        """
        text = ""
        layout = widget.get_layout()
        label = widget.get_text()
        if layout.is_ellipsized():
            text = "%s" % (GLib.markup_escape_text(label))
        widget.set_tooltip_markup(text)
