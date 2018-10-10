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

from gi.repository import Gtk, Pango, GObject

from gettext import gettext as _

from lollypop.define import App, ArtSize, Type
from lollypop.objects import Track
from lollypop.widgets_album import AlbumBaseWidget
from lollypop.pop_radio import RadioPopover


class RadioWidget(Gtk.FlowBoxChild, AlbumBaseWidget):
    """
        Widget with radio cover and title
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

    def __init__(self, radio_id, radios):
        """
            Init radio widget
            @param radio_id as int
            @param label_height as int
            @param radios as Radios
        """
        Gtk.FlowBoxChild.__init__(self)
        AlbumBaseWidget.__init__(self)
        self.set_size_request(ArtSize.BIG, ArtSize.BIG + self.LABEL_HEIGHT)
        self.get_style_context().add_class("loading")
        self.__radio_id = radio_id
        self.__name = radios.get_name(radio_id)
        self.__radios = radios

    def populate(self):
        """
            Init widget content
        """
        self.get_style_context().remove_class("loading")
        self._widget = Gtk.EventBox()
        self._widget.set_property("has-tooltip", True)
        self._widget.connect("query-tooltip", self._on_query_tooltip)
        grid = Gtk.Grid()
        grid.set_orientation(Gtk.Orientation.VERTICAL)
        self._artwork = Gtk.Image()
        self._artwork.set_property("halign", Gtk.Align.CENTER)
        self._artwork.set_size_request(ArtSize.BIG, ArtSize.BIG)
        self._artwork.get_style_context().add_class("cover-frame")
        self.__label = Gtk.Label()
        self.__label.set_justify(Gtk.Justification.CENTER)
        self.__label.set_ellipsize(Pango.EllipsizeMode.END)
        self.__label.set_text(self.__name)
        self._widget.add(grid)
        self.__overlay = Gtk.Overlay.new()
        self.__overlay.add(self._artwork)
        grid.add(self.__overlay)
        grid.add(self.__label)
        self.add(self._widget)
        self.set_artwork()
        self.set_selection()
        self.set_property("halign", Gtk.Align.CENTER)
        self.set_property("valign", Gtk.Align.CENTER)
        self.show_all()
        self._widget.connect("enter-notify-event", self._on_enter_notify)
        self._widget.connect("leave-notify-event", self._on_leave_notify)
        self._lock_overlay = False

    def set_sensitive(self, b):
        """
            Ignore set sensitive
        """
        pass

    def do_get_preferred_width(self):
        """
            Return preferred width
            @return (int, int)
        """
        if self._widget is None:
            return (0, 0)
        width = Gtk.FlowBoxChild.do_get_preferred_width(self)[0]
        return (width, width)

    def set_name(self, name):
        """
            Set radio name
            @param name as string
        """
        self.__name = name
        self.__title_label.set_label(name)

    def set_artwork(self, name=None):
        """
            Set artwork for radio matching name
        """
        if self._artwork is None or\
                (name is not None and name != self.__name):
            return
        surface = App().art.get_radio_artwork(
            self.__name,
            ArtSize.BIG,
            self._artwork.get_scale_factor())
        self._artwork.set_from_surface(surface)
        self.emit("populated")

    def set_selection(self):
        """
            Mark widget as selected if currently playing
        """
        if self._artwork is None:
            return
        selected = App().player.current_track.id == Type.RADIOS and\
            self.__name == App().player.current_track.album_artists[0]
        style_context = self._artwork.get_style_context()
        if selected:
            style_context.add_class("cover-frame-selected")
        else:
            style_context.remove_class("cover-frame-selected")

    @property
    def id(self):
        """
            Return widget id (same value for all radio widgets)
        """
        return Type.RADIOS

    @property
    def filter(self):
        """
            @Return filter as str
        """
        return self.__name

    @property
    def title(self):
        """
            @Return title as str
        """
        return self.__name

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
            self._play_event.set_margin_start(6)
            self._play_event.set_margin_bottom(6)
            self._play_event.set_property("has-tooltip", True)
            self._play_event.set_tooltip_text(_("Play"))
            self._play_event.set_hexpand(True)
            self._play_event.set_property("valign", Gtk.Align.END)
            self._play_event.set_property("halign", Gtk.Align.START)
            self._play_event.connect("realize", self._on_eventbox_realize)
            self._play_event.connect("button-press-event",
                                     self._on_play_press_event)
            self._play_button = Gtk.Image.new_from_icon_name(
                "media-playback-start-symbolic",
                Gtk.IconSize.DND)
            self._play_button.set_opacity(0)
            # Edit button
            self._action2_event = Gtk.EventBox()
            self._action2_event.set_margin_bottom(6)
            self._action2_event.set_margin_end(6)
            self._action2_event.set_property("has-tooltip", True)
            self._action2_event.set_tooltip_text(_("Modify radio"))
            self._action2_event.connect("realize", self._on_eventbox_realize)
            self._action2_event.connect("button-press-event",
                                        self._on_edit_press_event)
            self._action2_event.set_property("valign", Gtk.Align.END)
            self._action2_event.set_property("halign", Gtk.Align.END)
            self._action2_button = Gtk.Image.new_from_icon_name(
                "document-properties-symbolic",
                Gtk.IconSize.BUTTON)
            self._action2_button.set_opacity(0)
            self._play_event.add(self._play_button)
            self._action2_event.add(self._action2_button)
            self.__overlay.add_overlay(self._play_event)
            self.__overlay.add_overlay(self._action2_event)
            self.__overlay.show_all()
            AlbumBaseWidget._show_overlay_func(self, True)
        else:
            AlbumBaseWidget._show_overlay_func(self, False)
            self._play_event.destroy()
            self._play_event = None
            self._play_button.destroy()
            self._play_button = None
            self._action2_event.destroy()
            self._action2_event = None
            self._action2_button.destroy()
            self._action2_button = None

#######################
# PRIVATE             #
#######################
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

    def _on_play_press_event(self, widget, event):
        """
            Play radio
            @param: widget as Gtk.EventBox
            @param: event as Gdk.Event
        """
        if App().player.is_locked:
            return True
        url = self.__radios.get_url(self.__name)
        if url:
            track = Track()
            track.set_radio(self.__name, url)
            App().player.load(track)

    def _on_edit_press_event(self, widget, event):
        """
            Edit radio
            @param: widget as Gtk.EventBox
            @param: event as Gdk.Event
        """
        popover = RadioPopover(self.__name, self.__radios)
        popover.set_relative_to(widget)
        popover.connect("closed", self._on_popover_closed)
        self._lock_overlay = True
        popover.popup()
