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

from gi.repository import Gtk

from gettext import gettext as _

from lollypop.view_flowbox import FlowBoxView
from lollypop.define import App
from lollypop.widgets_playlist_rounded import PlaylistRoundedWidget
from lollypop.shown import ShownPlaylists


class PlaylistsManagerView(FlowBoxView):
    """
        Show playlists in a FlowBox
    """

    def __init__(self):
        """
            Init decade view
        """
        button = Gtk.Button(_("New playlist"))
        button.connect("clicked", self.__on_button_clicked)
        button.set_property("halign", Gtk.Align.CENTER)
        button.set_margin_top(5)
        button.set_margin_bottom(5)
        button.show()
        FlowBoxView.__init__(self)
        self._box.connect("child-activated", self.__on_album_activated)
        self.insert_row(0)
        self.attach(button, 0, 0, 1, 1)
        self._widget_class = PlaylistRoundedWidget

    def populate(self, items):
        """
            Populate items
            @param items
        """
        items = [i[0] for i in ShownPlaylists.get()] + items
        FlowBoxView.populate(self, items)

    def get_track_ids_for_playlist_id(self, playlist_id):
        """
            Get track_ids for current playlist id (even random)
            @return [int]
        """
        for child in self._box.get_children():
            if child.playlist_id == playlist_id:
                return child.track_ids
        return []

#######################
# PRIVATE             #
#######################
    def _add_items(self, playlist_ids, *args):
        """
            Add albums to the view
            Start lazy loading
            @param playlist ids as [int]
        """
        widget = FlowBoxView._add_items(self, playlist_ids)
        if widget is not None:
            widget.connect("overlayed", self._on_overlayed)

    def __on_button_clicked(self, button):
        """
            Add a new playlist
            @param button as Gtk.Button
        """
        existing_playlists = []
        for (playlist_id, name) in App().playlists.get():
            existing_playlists.append(name)

        # Search for an available name
        count = 1
        name = _("New playlist ") + str(count)
        while name in existing_playlists:
            count += 1
            name = _("New playlist ") + str(count)
        App().playlists.add(name)
        App().window.container.reload_view()

    def __on_album_activated(self, flowbox, widget):
        """
            Show overlay
            @param flowbox as Gtk.Flowbox
            @param widget as PlaylistRoundedWidget
        """
        # Here some code for touch screens
        # If mouse pointer activate Gtk.FlowBoxChild, overlay is on,
        # as enter notify event enabled it
        # Else, we are in touch screen, show overlay
        if not widget.is_overlay:
            widget.show_overlay(True)
            return
