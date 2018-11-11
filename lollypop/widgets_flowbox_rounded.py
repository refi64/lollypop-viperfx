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
from lollypop.utils import draw_rounded_image


class RoundedFlowBoxWidget(Gtk.FlowBoxChild):
    """
        Rounded flowbox child widget
    """

    __gsignals__ = {
        "overlayed": (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
        "populated": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, data, art_size=ArtSize.ROUNDED):
        """
            Init widget
            @param data as object
        """
        # We do not use Gtk.Builder for speed reasons
        Gtk.FlowBoxChild.__init__(self)
        self._art_size = art_size
        self._data = data
        self._scale_factor = self.get_scale_factor()
        self.set_size_request(art_size, art_size)
        self.get_style_context().add_class("loading-rounded")

    def populate(self, text):
        """
            Populate widget content
            @param text as str
        """
        self.get_style_context().remove_class("loading-rounded")
        grid = Gtk.Grid()
        grid.set_orientation(Gtk.Orientation.VERTICAL)
        label = Gtk.Label()
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_property("halign", Gtk.Align.CENTER)
        label.set_markup("<b>" + GLib.markup_escape_text(text) + "</b>")
        self._artwork = Gtk.Image.new()
        self._artwork.connect("draw", self.__on_artwork_draw)
        self._artwork.set_size_request(self._art_size, self._art_size)
        self._artwork.show()
        self._set_artwork()
        self._overlay = Gtk.Overlay()
        self._overlay.add(self._artwork)
        grid.add(self._overlay)
        grid.add(label)
        self._widget = Gtk.EventBox()
        self._widget.set_property("has-tooltip", True)
        self._widget.add(grid)
        self._widget.set_property("halign", Gtk.Align.CENTER)
        self._widget.set_property("valign", Gtk.Align.CENTER)
        self.add(self._widget)
        self.show_all()

    def do_get_preferred_width(self):
        """
            Return preferred width
            @return (int, int)
        """
        width = Gtk.FlowBoxChild.do_get_preferred_width(self)[0]
        return (width, width)

    @property
    def data(self):
        """
            Get associated data
            @return object
        """
        return self._data

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
    def __on_artwork_draw(self, image, ctx):
        """
            Draw rounded image
            @param image as Gtk.Image
            @param ctx as cairo.Context
        """
        if image.props.surface is None:
            return
        # Update image if scale factor changed
        if self._scale_factor != image.get_scale_factor():
            self._scale_factor = image.get_scale_factor()
            self._set_artwork()
        draw_rounded_image(image, ctx)
        return True
