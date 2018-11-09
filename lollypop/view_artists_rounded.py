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

from lollypop.view_flowbox import FlowBoxView
from lollypop.define import App, Type
from lollypop.widgets_artist_rounded import RoundedArtistWidget


class RoundedArtistsView(FlowBoxView):
    """
        Show artists in a FlowBox
    """

    def __init__(self):
        """
            Init decade view
        """
        FlowBoxView.__init__(self)
        self._widget_class = RoundedArtistWidget

#######################
# PROTECTED           #
#######################
    def _add_items(self, item_ids, *args):
        """
            Add artists to the view
            Start lazy loading
            @param item ids as [int]
        """
        if Type.ALL in item_ids:
            item_ids.remove(Type.ALL)
        art_size = App().settings.get_value("cover-size").get_int32()
        FlowBoxView._add_items(self, item_ids, art_size)
        # if widget is not None:
        #    widget.connect("overlayed", self.on_overlayed)

    def _on_item_activated(self, flowbox, widget):
        """
            Show artist albums
            @param flowbox as Gtk.Flowbox
            @param widget as ArtistRoundedWidget
        """
        App().window.container.show_view(widget.data)
