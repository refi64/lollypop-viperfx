# Copyright (c) 2014-2016 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import Gtk, Gdk

from lollypop.define import Lp, ArtSize, Type
from lollypop.widgets_album import AlbumWidget
from lollypop.pop_radio import RadioPopover


class RadioWidget(Gtk.Bin, AlbumWidget):
    """
        Widget with radio cover and title
    """

    def __init__(self, name, radios_manager):
        """
            Init radio widget
            @param name as string
            @param radios_manager as RadiosManager
        """
        Gtk.Bin.__init__(self)
        AlbumWidget.__init__(self, None)
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/RadioWidget.ui')
        builder.connect_signals(self)
        self._cover = builder.get_object('cover')
        self._color = builder.get_object('color')
        self._name = name
        self._radios_manager = radios_manager
        self._popover = None
        self._title = builder.get_object('title')
        self._title.set_label(name)
        self.update_state()
        self.add(builder.get_object('widget'))
        self.set_cover()
        self.set_property('halign', Gtk.Align.START)

    def set_sensitive(self, b):
        """
            Ignore set sensitive
        """
        pass

    def get_id(self):
        """
            Return widget id (same value for all radio widgets)
        """
        return Type.RADIOS

    def do_get_preferred_width(self):
        """
            Set maximum width
        """
        widths = self._cover.get_preferred_width()
        return (widths[0] + 8, widths[1] + 8)

    def set_name(self, name):
        """
            Set radio name
            @param name as string
        """
        self._name = name
        self._title.set_label(name)

    def get_name(self):
        """
            Return radio name
            @return name as string
        """
        return self._name

    def set_cover(self):
        """
            Set cover for album if state changed
        """
        if self._cover is None:
            return
        surface = Lp().art.get_radio_artwork(
                    self._name,
                    ArtSize.BIG*self._cover.get_scale_factor())
        self._cover.set_from_surface(surface)
        del surface

    def update_cover(self):
        """
            Update cover for radio
        """
        if self._cover is None:
            return
        surface = Lp().art.get_radio_artwork(
                    self._name,
                    ArtSize.BIG*self._cover.get_scale_factor())
        self._cover.set_from_surface(surface)
        del surface

    def update_state(self):
        """
            Update widget state
        """
        selected = Lp().player.current_track.id == Type.RADIOS and\
            self._name == Lp().player.current_track.album_artist
        if selected:
            self._color.get_style_context().add_class(
                                                    'cover-frame-selected')
        else:
            self._color.get_style_context().remove_class(
                                                    'cover-frame-selected')

    def edit(self, widget):
        """
            Edit radio
            @param widget as Gtk.Widget
        """
        self._popover = RadioPopover(self._name, self._radios_manager)
        self._popover.set_relative_to(widget)
        self._popover.show()

#######################
# PRIVATE             #
#######################
    def _on_title_press(self, widget, event):
        """
            Edit radio
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        self.edit(widget)

    def _on_cover_press(self, widget, event):
        """
            Edit radio on right click
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        if event.button != 1:
            self.edit(widget)

    def _on_eventbox_realize1(self, eventbox):
        """
            Change cursor over cover eventbox
            @param eventbox as Gdk.Eventbox
        """
        eventbox.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND1))

    def _on_eventbox_realize2(self, eventbox):
        """
            Change cursor over title eventbox
            @param eventbox as Gdk.Eventbox
        """
        eventbox.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.PENCIL))
