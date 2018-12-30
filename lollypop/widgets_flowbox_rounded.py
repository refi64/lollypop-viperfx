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

from gi.repository import GLib, Gtk, Pango, GObject

from lollypop.define import ArtSize


class RoundedFlowBoxWidget(Gtk.FlowBoxChild):
    """
        Rounded flowbox child widget
    """

    __gsignals__ = {
        "overlayed": (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
        "populated": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, data, name, sortname, art_size=ArtSize.ROUNDED):
        """
            Init widget
            @param data as object
            @param name as str
            @param sortname as str
            @param art_size as int
        """
        # We do not use Gtk.Builder for speed reasons
        Gtk.FlowBoxChild.__init__(self)
        self._artwork = None
        self._art_size = art_size
        self._data = data
        self.__name = name
        self.__sortname = sortname
        self.__filtered = False
        self._scale_factor = self.get_scale_factor()
        self.set_size_request(art_size, art_size)
        self.set_property("halign", Gtk.Align.CENTER)
        self.set_property("valign", Gtk.Align.CENTER)

    def populate(self):
        """
            Populate widget content
        """
        grid = Gtk.Grid()
        grid.set_orientation(Gtk.Orientation.VERTICAL)
        self.__label = Gtk.Label()
        self.__label.set_ellipsize(Pango.EllipsizeMode.END)
        self.__label.set_property("halign", Gtk.Align.CENTER)
        self.__label.set_property("has-tooltip", True)
        self.__label.connect("query-tooltip", self.__on_query_tooltip)
        self.__label.set_markup(
            "<b>" + GLib.markup_escape_text(self.__name) + "</b>")
        self._artwork = Gtk.Image.new()
        self._artwork.set_size_request(self._art_size, self._art_size)
        self._artwork.show()
        self._set_artwork()
        self._overlay = Gtk.Overlay()
        self._overlay.add(self._artwork)
        grid.add(self._overlay)
        grid.add(self.__label)
        self._widget = Gtk.EventBox()
        self._widget.set_property("has-tooltip", True)
        self._widget.add(grid)
        self.add(self._widget)
        self.show_all()

    def do_get_preferred_width(self):
        """
            Return preferred width
            @return (int, int)
        """
        width = Gtk.FlowBoxChild.do_get_preferred_width(self)[0]
        return (width, width)

    def rename(self, name):
        """
            Rename widget
            @param name as str
        """
        self.__label.set_markup("<b>" + GLib.markup_escape_text(name) + "</b>")

    def set_filtered(self, b):
        """
            Set widget filtered
        """
        self.__filtered = b

    @property
    def name(self):
        """
            Get name
            @return str
        """
        return self.__name

    @property
    def sortname(self):
        """
            Get sortname
            @return str
        """
        return self.__sortname

    @property
    def data(self):
        """
            Get associated data
            @return object
        """
        return self._data

    @property
    def filter(self):
        """
            Current filter
            @return str
        """
        return self.name.lower()

    @property
    def filtered(self):
        """
            True if filtered by parent
        """
        return self.__filtered

    @property
    def is_populated(self):
        """
            True if album populated
        """
        return True

#######################
# PROTECTED           #
#######################
    def _set_artwork(self):
        """
            Set artwork
        """
        pass

    def _get_album_ids(self):
        """
            Get ids for widget
            @return [int]
        """
        return []

#######################
# PRIVATE             #
#######################
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
