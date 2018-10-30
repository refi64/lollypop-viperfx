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

    def __init__(self, obj=None):
        """
            Init decade view
            @param obj as Track/Album
        """
        self.__obj = obj
        grid = Gtk.Grid()
        grid.set_margin_top(5)
        grid.set_margin_start(5)
        grid.set_margin_bottom(5)
        grid.show()
        if obj is not None:
            back_button = Gtk.Button.new_from_icon_name("go-previous-symbolic",
                                                        Gtk.IconSize.BUTTON)
            back_button.connect("clicked",
                                lambda x: App().window.container.reload_view())
            back_button.set_property("halign", Gtk.Align.START)
            back_button.set_relief(Gtk.ReliefStyle.NONE)
            back_button.show()
            grid.add(back_button)
        new_playlist_button = Gtk.Button(_("New playlist"))
        new_playlist_button.connect("clicked", self.__on_new_button_clicked)
        new_playlist_button.set_property("halign", Gtk.Align.CENTER)
        new_playlist_button.set_hexpand(True)
        new_playlist_button.show()
        grid.add(new_playlist_button)
        FlowBoxView.__init__(self)
        self.insert_row(0)
        self.attach(grid, 0, 0, 1, 1)
        self._widget_class = PlaylistRoundedWidget

    def populate(self, items):
        """
            Populate items
            @param items
        """
        if self.__obj is not None:
            new_items = []
            for item in items:
                if not App().playlists.get_smart(item):
                    new_items.append(item)
            items = new_items
        else:
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
# PROTECTED           #
#######################
    def _add_items(self, playlist_ids, *args):
        """
            Add albums to the view
            Start lazy loading
            @param playlist ids as [int]
        """
        widget = FlowBoxView._add_items(self, playlist_ids, self.__obj)
        if widget is not None:
            widget.connect("overlayed", self.on_overlayed)

#######################
# PRIVATE             #
#######################
    def __on_new_button_clicked(self, button):
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
        if self.__obj is None:
            App().window.container.reload_view()
        else:
            App().window.container.show_playlist_manager(self.__obj)
