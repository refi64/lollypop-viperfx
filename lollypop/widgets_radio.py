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
from lollypop.helper_overlay import OverlayHelper


class RadioWidget(Gtk.FlowBoxChild, OverlayHelper):
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
        OverlayHelper.__init__(self)
        self._widget = None
        self.__art_size = 110\
            if App().window.is_adaptive\
            else ArtSize.BIG
        self.set_size_request(self.__art_size,
                              self.__art_size + self.LABEL_HEIGHT)
        self.get_style_context().add_class("loading")
        self.__radio_id = radio_id
        self.__radios = radios

    def populate(self):
        """
            Init widget content
        """
        name = self.__radios.get_name(self.__radio_id)
        self.get_style_context().remove_class("loading")
        self._widget = Gtk.EventBox()
        self._widget.set_property("has-tooltip", True)
        self._widget.connect("query-tooltip", self.__on_query_tooltip)
        grid = Gtk.Grid()
        grid.set_orientation(Gtk.Orientation.VERTICAL)
        self._artwork = App().art_helper.get_image(self.__art_size,
                                                   self.__art_size,
                                                   "cover-frame")
        self.__label = Gtk.Label()
        self.__label.set_justify(Gtk.Justification.CENTER)
        self.__label.set_ellipsize(Pango.EllipsizeMode.END)
        self.__label.set_text(name)
        self._widget.add(grid)
        self.__overlay = Gtk.Overlay.new()
        self.__overlay.add(self._artwork)
        grid.add(self.__overlay)
        grid.add(self.__label)
        self.add(self._widget)
        self.set_artwork()
        self.set_selection()
        self.show_all()
        self._lock_overlay = False
        self.set_property("halign", Gtk.Align.CENTER)
        self.set_property("valign", Gtk.Align.CENTER)
        self._widget.connect("enter-notify-event", self._on_enter_notify)
        self._widget.connect("leave-notify-event", self._on_leave_notify)

    def set_artwork(self):
        """
            Set album artwork
        """
        if self._widget is None:
            return
        name = self.__radios.get_name(self.__radio_id)
        App().art_helper.set_radio_artwork(name,
                                           self.__art_size,
                                           self.__art_size,
                                           self._artwork.get_scale_factor(),
                                           self.__on_radio_artwork)

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

    def rename(self, name):
        """
            Set radio name
            @param name as str
        """
        self.__label.set_label(name)

    def set_selection(self):
        """
            Mark widget as selected if currently playing
        """
        if self._artwork is None:
            return
        name = self.__radios.get_name(self.__radio_id)
        selected = App().player.current_track.id == Type.RADIOS and\
            name == App().player.current_track.radio_name
        if selected:
            self._artwork.set_state(Gtk.StateType.SELECTED)
        else:
            self._artwork.set_state(Gtk.StateType.NORMAL)

    @property
    def is_populated(self):
        """
            True if album populated
            @return bool
        """
        return True

    @property
    def id(self):
        """
            @return int
        """
        return self.__radio_id

    @property
    def filter(self):
        """
            @return filter as str
        """
        return self.name.lower()

    @property
    def name(self):
        """
            @return name as str
        """
        return self.__radios.get_name(self.__radio_id)

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
        OverlayHelper._show_overlay_func(self, set)
        if set:
            # Play button
            self.__play_event = Gtk.EventBox()
            self.__play_event.set_margin_start(6)
            self.__play_event.set_margin_bottom(6)
            self.__play_event.set_property("has-tooltip", True)
            self.__play_event.set_tooltip_text(_("Play"))
            self.__play_event.set_hexpand(True)
            self.__play_event.set_property("valign", Gtk.Align.END)
            self.__play_event.set_property("halign", Gtk.Align.START)
            self.__play_event.connect("realize", self._on_eventbox_realize)
            self.__play_event.connect("button-press-event",
                                      self.__on_play_press_event)
            self.__play_button = Gtk.Image.new_from_icon_name(
                "media-playback-start-symbolic",
                Gtk.IconSize.DND)
            # Edit button
            self.__artwork_event = Gtk.EventBox()
            self.__artwork_event.set_margin_bottom(6)
            self.__artwork_event.set_margin_end(6)
            self.__artwork_event.set_property("has-tooltip", True)
            self.__artwork_event.set_tooltip_text(_("Modify radio"))
            self.__artwork_event.connect("realize", self._on_eventbox_realize)
            self.__artwork_event.connect("button-press-event",
                                         self.__on_edit_press_event)
            self.__artwork_event.set_property("valign", Gtk.Align.END)
            self.__artwork_event.set_property("halign", Gtk.Align.END)
            self.__artwork_button = Gtk.Image.new_from_icon_name(
                "document-properties-symbolic",
                Gtk.IconSize.BUTTON)
            self.__play_event.add(self.__play_button)
            self.__artwork_event.add(self.__artwork_button)
            self.__overlay.add_overlay(self.__play_event)
            self.__overlay.add_overlay(self.__artwork_event)
            self.__overlay.show_all()
            self.__play_button.get_style_context().add_class(
                "rounded-icon")
            self.__artwork_button.get_style_context().add_class(
                "squared-icon-small")
        else:
            self.__play_event.destroy()
            self.__play_event = None
            self.__play_button.destroy()
            self.__play_button = None
            self.__artwork_event.destroy()
            self.__artwork_event = None
            self.__artwork_button.destroy()
            self.__artwork_button = None

#######################
# PRIVATE             #
#######################
    def __on_play_press_event(self, widget, event):
        """
            Play radio
            @param: widget as Gtk.EventBox
            @param: event as Gdk.Event
        """
        if App().player.is_locked:
            return True
        track = Track()
        track.set_radio_id(self.__radio_id)
        App().player.load(track)

    def __on_edit_press_event(self, widget, event):
        """
            Edit radio
            @param: widget as Gtk.EventBox
            @param: event as Gdk.Event
        """
        from lollypop.pop_radio import RadioPopover
        popover = RadioPopover(self.__radio_id, self.__radios)
        popover.set_relative_to(widget)
        popover.connect("closed", self._on_popover_closed)
        self._lock_overlay = True
        popover.popup()

    def __on_query_tooltip(self, eventbox, x, y, keyboard, tooltip):
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

    def __on_radio_artwork(self, surface):
        """
            Set radio artwork
            @param surface as str
        """
        if surface is None:
            self._artwork.set_from_icon_name("audio-input-microphone-symbolic",
                                             Gtk.IconSize.DIALOG)
        else:
            self._artwork.set_from_surface(surface)
        self.show_all()
        self.emit("populated")
