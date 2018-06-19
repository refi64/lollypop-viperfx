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

from gi.repository import Gtk, GLib

from gettext import gettext as _

from lollypop.helper_task import TaskHelper
from lollypop.view_albums_list import AlbumsListView
from lollypop.define import App, ResponsiveType


class AlbumsPopover(Gtk.Popover):
    """
        Popover showing Albums View
    """

    def __init__(self):
        """
            Init popover
        """
        Gtk.Popover.__init__(self)
        self.__clear_button = Gtk.Button.new_from_icon_name(
            "edit-clear-all-symbolic",
            Gtk.IconSize.MENU)
        self.__clear_button.set_relief(Gtk.ReliefStyle.NONE)
        self.__clear_button.set_tooltip_text(_("Clear albums"))
        self.__clear_button.set_sensitive(App().player.albums)
        self.__clear_button.connect("clicked", self.__on_clear_clicked)
        self.__save_button = Gtk.Button.new_from_icon_name(
            "document-new-symbolic",
            Gtk.IconSize.MENU)
        self.__save_button.set_relief(Gtk.ReliefStyle.NONE)
        self.__save_button.set_tooltip_text(_("Create a new playlist"))
        self.__save_button.set_sensitive(App().player.albums)
        self.__save_button.connect("clicked", self.__on_save_clicked)
        self.__jump_button = Gtk.Button.new_from_icon_name(
            "go-jump-symbolic",
            Gtk.IconSize.MENU)
        self.__jump_button.set_relief(Gtk.ReliefStyle.NONE)
        self.__jump_button.connect("clicked", self.__on_jump_clicked)
        self.__jump_button.set_tooltip_text(_("Go to current track"))
        self.__jump_button.set_sensitive(App().player.albums)
        label = Gtk.Label.new("<b>" + _("Playing albums") + "</b>")
        label.set_use_markup(True)
        label.set_hexpand(True)
        label.set_margin_start(2)
        label.get_style_context().add_class("dim-label")
        label.set_property("halign", Gtk.Align.START)
        self.__view = AlbumsListView(ResponsiveType.DND)
        self.__view.populate(App().player.albums)
        self.__view.show()
        grid = Gtk.Grid()
        grid.set_column_spacing(5)
        grid.set_row_spacing(2)
        grid.add(label)
        grid.add(self.__jump_button)
        grid.add(self.__save_button)
        grid.add(self.__clear_button)
        grid.attach(self.__view, 0, 1, 4, 1)
        grid.show_all()

        self.set_position(Gtk.PositionType.BOTTOM)
        self.connect("map", self.__on_map)
        self.connect("unmap", self.__on_unmap)
        self.add(grid)

#######################
# PRIVATE             #
#######################
    def __albums_to_playlist(self):
        """
            Create a new playlist based on search
        """
        tracks = []
        for child in self.__view.children:
            tracks += child.album.tracks
        if tracks:
            import datetime
            now = datetime.datetime.now()
            date_string = now.strftime("%Y-%m-%d-%H:%M:%S")
            App().playlists.add(date_string)
            playlist_id = App().playlists.get_id(date_string)
            App().playlists.add_tracks(playlist_id, tracks)

    def __on_jump_clicked(self, button):
        """
            Scroll to album
            @param button as Gtk.Button
        """
        self.__view.jump_to_current()

    def __on_save_clicked(self, button):
        """
            Save to playlist
            @param button as Gtk.Button
        """
        button.set_sensitive(False)
        helper = TaskHelper()
        helper.run(self.__albums_to_playlist)

    def __on_clear_clicked(self, button):
        """
            Clear albums
            @param button as Gtk.Button
        """
        self._stop = True
        GLib.idle_add(self.__view.clear, True)
        self.__clear_button.set_sensitive(False)
        self.__jump_button.set_sensitive(False)
        self.__save_button.set_sensitive(False)

    def __on_map(self, widget):
        """
            Resize
            @param widget as Gtk.Widget
        """
        window_size = App().window.get_size()
        height = window_size[1]
        width = min(500, window_size[0])
        self.set_size_request(width, height * 0.7)

    def __on_unmap(self, widget):
        """
            Stop view
            @param widget as Gtk.Widget
        """
        self.__view.stop()
