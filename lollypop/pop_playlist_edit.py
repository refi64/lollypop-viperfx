# Copyright (c) 2014-2019 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from lollypop.define import App
from lollypop.widgets_utils import Popover


class PlaylistEditPopover(Popover):
    """
        Edit a playlist
    """

    def __init__(self, playlist_id):
        """
            @param playlist_id as int
        """
        Popover.__init__(self)
        self.__playlist_id = playlist_id
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/PlaylistPopover.ui")
        builder.connect_signals(self)
        widget = builder.get_object("widget")
        self.__name_entry = builder.get_object("name")
        if playlist_id < 0:
            widget.set_sensitive(False)
        self.__name_entry.set_text(App().playlists.get_name(playlist_id))
        self.add(widget)

#######################
# PROTECTED           #
#######################
    def _on_save_button_clicked(self, button):
        """
            Save playlist
            @param button as Gtk.Button
        """
        new_name = self.__name_entry.get_text()
        App().playlists.rename(self.__playlist_id, new_name)
        self.popdown()

    def _on_delete_button_clicked(self, button):
        """
            Delete playlist
            @param button as Gtk.Button
        """
        def remove_playlist():
            App().playlists.remove(self.__playlist_id)
        from lollypop.app_notification import AppNotification
        notification = AppNotification(_("Remove this playlist?"),
                                       [_("Confirm")],
                                       [remove_playlist])
        notification.show()
        App().window.container.add_overlay(notification)
        notification.set_reveal_child(True)
        self.popdown()
