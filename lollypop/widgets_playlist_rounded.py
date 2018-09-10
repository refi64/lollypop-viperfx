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

from gi.repository import Gtk, Gdk

from random import shuffle
from gettext import gettext as _

from lollypop.define import App
from lollypop.objects import Track
from lollypop.widgets_flowbox_rounded import RoundedFlowBoxWidget
from lollypop.widgets_album import AlbumBaseWidget


class PlayListPopover(Gtk.Popover):
    """
        Edit a playlist
    """

    def __init__(self, playlist_id):
        """
            @param playlist_id as int
        """
        Gtk.Popover.__init__(self)
        self.__playlist_id = playlist_id
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/PlaylistPopover.ui")
        builder.connect_signals(self)
        self.__name_entry = builder.get_object("name")
        self.__name_entry.set_text(App().playlists.get_name(playlist_id))
        self.add(builder.get_object("widget"))

#######################
# PROTECTED           #
#######################
    def _on_save_button_clicked(self, button):
        """
            Save playlist
            @param button as Gtk.Button
        """
        old_name = App().playlists.get_name(self.__playlist_id)
        new_name = self.__name_entry.get_text()
        App().playlists.rename(old_name, new_name)
        App().window.container.reload_view()
        self.destroy()

    def _on_delete_button_clicked(self, button):
        """
            Delete playlist
            @param button as Gtk.Button
        """
        name = App().playlists.get_name(self.__playlist_id)
        App().playlists.delete(name)
        App().window.container.reload_view()
        self.destroy()


class PlaylistRoundedWidget(RoundedFlowBoxWidget, AlbumBaseWidget):
    """
        Playlist widget showing cover for 9 albums
    """

    def __init__(self, playlist_id):
        """
            Init widget
            @param playlist_id as playlist_id
        """
        AlbumBaseWidget.__init__(self)
        RoundedFlowBoxWidget.__init__(self, playlist_id)

    def populate(self):
        """
            Populate widget content
        """
        text = App().playlists.get_name(self._data)
        RoundedFlowBoxWidget.populate(self, text)
        self._widget.connect("enter-notify-event", self._on_enter_notify)
        self._widget.connect("leave-notify-event", self._on_leave_notify)
        self._lock_overlay = False

#######################
# PROTECTED           #
#######################
    def _get_album_ids(self):
        """
            Get ids for widget
            @return [int]
        """
        album_ids = []
        track_ids = App().playlists.get_track_ids(self._data)
        shuffle(track_ids)
        for track_id in track_ids:
            track = Track(track_id)
            if track.album.id not in album_ids:
                album_ids.append(track.album.id)
            if len(album_ids) == self._ALBUMS_COUNT:
                break
        return album_ids

    def _show_overlay_func(self, set):
        """
            Set overlay
            @param set as bool
        """
        if self._lock_overlay or\
           self._show_overlay == set:
            return
        if set:
            # Play button
            self._play_event = Gtk.EventBox()
            self._play_event.set_property("has-tooltip", True)
            self._play_event.set_tooltip_text(_("Play"))
            self._play_event.set_hexpand(True)
            self._play_event.set_property("valign", Gtk.Align.CENTER)
            self._play_event.set_property("halign", Gtk.Align.CENTER)
            self._play_event.connect("realize", self.__on_eventbox_realize)
            self._play_event.connect("button-press-event",
                                     self._on_play_press_event)
            self._play_button = Gtk.Image.new_from_icon_name(
                "media-playback-start-symbolic",
                Gtk.IconSize.DND)
            self._play_button.set_opacity(0)
            # Edit button
            self._artwork_event = Gtk.EventBox()
            self._artwork_event.set_property("has-tooltip", True)
            self._artwork_event.set_tooltip_text(_("Modify playlist"))
            self._artwork_event.set_property("halign", Gtk.Align.END)
            self._artwork_event.connect("realize", self.__on_eventbox_realize)
            self._artwork_event.connect("button-press-event",
                                        self._on_edit_press_event)
            self._artwork_event.set_property("valign", Gtk.Align.END)
            self._artwork_event.set_margin_bottom(5)
            self._artwork_event.set_property("halign", Gtk.Align.CENTER)
            self._artwork_button = Gtk.Image.new_from_icon_name(
                "document-properties-symbolic",
                Gtk.IconSize.BUTTON)
            self._artwork_button.set_opacity(0)
            self._play_event.add(self._play_button)
            self._artwork_event.add(self._artwork_button)
            self._overlay.add_overlay(self._play_event)
            self._overlay.add_overlay(self._artwork_event)
            self._overlay.show_all()
            AlbumBaseWidget._show_overlay_func(self, True)
        else:
            AlbumBaseWidget._show_overlay_func(self, False)
            self._play_event.destroy()
            self._play_event = None
            self._play_button.destroy()
            self._play_button = None
            self._artwork_event.destroy()
            self._artwork_event = None
            self._artwork_button.destroy()
            self._artwork_button = None

#######################
# PRIVATE             #
#######################
    def _on_play_press_event(self, widget, event):
        """
            Play radio
            @param: widget as Gtk.EventBox
            @param: event as Gdk.Event
        """
        if App().player.locked:
            return True
        track_ids = App().playlists.get_track_ids(self._data)
        if track_ids:
            App().player.populate_playlist_by_track_ids(track_ids,
                                                        [self._data])
            App().player.load(Track(track_ids[0]))

    def _on_edit_press_event(self, widget, event):
        """
            Edit radio
            @param: widget as Gtk.EventBox
            @param: event as Gdk.Event
        """
        popover = PlayListPopover(self._data)
        popover.set_relative_to(widget)
        popover.connect("closed", self._on_pop_artwork_closed)
        self._lock_overlay = True
        popover.show()

    def __on_eventbox_realize(self, eventbox):
        """
            Change cursor over eventbox
            @param eventbox as Gdk.Eventbox
        """
        window = eventbox.get_window()
        if window is not None:
            window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))
