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

from gi.repository import GObject, Pango

from lollypop.define import ResponsiveType
from lollypop.widgets_row import Row
from lollypop.widgets_row_dnd import DNDRow


class TrackRow(Row, DNDRow):
    """
        A track row
    """

    __gsignals__ = {
        "insert-track": (
            GObject.SignalFlags.RUN_FIRST, None, (int, bool)),
        "remove-track": (
            GObject.SignalFlags.RUN_FIRST, None, ()),
        "insert-album": (
            GObject.SignalFlags.RUN_FIRST, None, (
                int, GObject.TYPE_PYOBJECT, bool)),
    }

    def get_best_height(widget):
        """
            Calculate widget height
            @param widget as Gtk.Widget
        """
        ctx = widget.get_pango_context()
        layout = Pango.Layout.new(ctx)
        layout.set_text("a", 1)
        font_height = int(layout.get_pixel_size()[1])
        # Button min height + borders (application.css)
        menu_height = 24 + 2
        if font_height > menu_height:
            height = font_height
        else:
            height = menu_height
        return height

    def __init__(self, track, responsive_type):
        """
            Init row widget and show it
            @param track as Track
            @param responsive_type as ResponsiveType
        """
        Row.__init__(self, track, responsive_type)
        self.__parent_filter = False
        self._grid.insert_column(0)
        self._grid.attach(self._indicator, 0, 0, 1, 1)
        self.show_all()
        if responsive_type == ResponsiveType.DND:
            DNDRow.__init__(self)

    @property
    def filter(self):
        """
            @return str
        """
        return self._track.name

    def set_filtered(self, b):
        """
            Set widget filtered
        """
        self.__parent_filter = b

    @property
    def filtered(self):
        """
            True if filtered by parent
        """
        return self.__parent_filter

#######################
# PRIVATE             #
#######################