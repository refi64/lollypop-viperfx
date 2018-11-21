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

from lollypop.define import App


class IndicatorWidget(Gtk.EventBox):
    """
        Show play/loved indicator
        If embedded in a Popover, will not affect playlists but only player
        playlists
    """

    def __init__(self, track):
        """
            Init indicator widget, ui will be set when needed
            @param track as Track
        """
        Gtk.EventBox.__init__(self)
        self.__track = track
        self.__playlist_ids = []
        self.__pass = 1
        self.__timeout_id = None
        self.__button = None
        self.__stack = None
        self.connect("destroy", self.__on_destroy)
        # min-width = 24px, borders = 2px, padding = 8px
        self.set_size_request(34, -1)

    def set_playlist_ids(self, playlist_ids):
        """
            Set playlist ids
            @param playlist_ids as [int]
        """
        self.__playlist_ids = playlist_ids

    def empty(self):
        """
            Show no indicator
        """
        if self.__button is not None:
            self.__stack.set_visible_child_name("button")

    def play(self):
        """
            Show play indicator
        """
        self.__init()
        self.__stack.set_visible_child_name("play")

    def loved(self, status):
        """
            Show loved indicator
            @param loved status
        """
        self.__init()
        if status == 1:
            self.__loved.set_from_icon_name("emblem-favorite-symbolic",
                                            Gtk.IconSize.MENU)
        elif status == -1:
            self.__loved.set_from_icon_name("media-skip-forward-symbolic",
                                            Gtk.IconSize.MENU)
        if status != 0:
            self.__stack.set_visible_child_name("loved")

    def play_loved(self):
        """
            Show play/loved indicator
        """
        self.__init()
        self.__pass = 1
        self.play()
        self.__timeout_id = GLib.timeout_add(1000, self.__play_loved)

    def clear(self):
        """
            Clear timeout
        """
        if self.__timeout_id is not None:
            GLib.source_remove(self.__timeout_id)
            self.__timeout_id = None

    def update_button(self):
        """
            Update button based on queue status
        """
        self.__init()
        if len(self.__playlist_ids) < 2:
            self.__button.set_tooltip_text(_("Remove from playlist"))
            self.__image.set_from_icon_name("list-remove-symbolic",
                                            Gtk.IconSize.MENU)
        elif self.__is_in_current_playlist():
            self.__button.set_tooltip_text(
                _("Remove from current playlist"))
            self.__image.set_from_icon_name("list-remove-symbolic",
                                            Gtk.IconSize.MENU)
        else:
            self.__button.set_tooltip_text(_("Add to current playlist"))
            self.__image.set_from_icon_name("list-add-symbolic",
                                            Gtk.IconSize.MENU)

#######################
# PRIVATE             #
#######################
    def __is_in_current_playlist(self):
        """
            Check if track in Player current playlist
            @return bool
        """
        if App().player.albums:
            for album in App().player.albums:
                if self.__track.album.id == album.id:
                    if self.__track.id in album.track_ids:
                        return True
        elif App().player.playlist_ids:
            if self.__track.id in App().player.playlist_track_ids:
                return True
        return False

    def __remove_from_player_albums(self):
        """
            Remove track from player albums
        """
        albums = [album
                  for album in App().player.albums
                  if album.id == self.__track.album.id]
        for album in albums:
            for track in album.tracks:
                if track.id == self.__track.id:
                    count = len(album.tracks)
                    album.remove_track(track)
                    # Album is now empty
                    if count == 1:
                        App().player.remove_album(album)
                        App().player.stop()
                    elif App().player.next_track.id == track.id:
                        App().player.set_next()
                    break

    def __remove_from_player_playlists(self):
        """
            Remove track from player playlists
        """
        App().player.remove_track(self.__track.id)
        App().playlists.remove_uri(self.__playlist_ids[0],
                                   self.__track.uri)

    def __init(self):
        """
            Init widget content if needed
        """
        if self.__button is not None:
            return
        self.__stack = Gtk.Stack()
        self.__stack.set_transition_duration(500)
        self.__stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.__button = Gtk.Button.new()
        self.__image = Gtk.Image.new()
        self.__button.set_image(self.__image)
        self.__button.set_relief(Gtk.ReliefStyle.NONE)
        self.__button.get_style_context().add_class("menu-button")
        self.__button.get_style_context().add_class("track-menu-button")
        if len(self.__playlist_ids) < 2:
            self.__button.show()
        self.__button.connect("button-release-event",
                              self.__on_button_release_event)
        play = Gtk.Image.new_from_icon_name("media-playback-start-symbolic",
                                            Gtk.IconSize.MENU)
        self.__loved = Gtk.Image()
        self.__stack.add_named(self.__button, "button")
        self.__stack.add_named(play, "play")
        self.__stack.add_named(self.__loved, "loved")
        self.add(self.__stack)
        self.connect("enter-notify-event", self.__on_enter_notify)
        self.connect("leave-notify-event", self.__on_leave_notify)
        self.show_all()

    def __on_enter_notify(self, widget, event):
        """
            Show queue button
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        self.empty()

    def __on_leave_notify(self, widget, event):
        """
            Show love button or play button again
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        if self.__track.id == App().player.current_track.id:
            self.play()
        else:
            self.loved(self.__track.loved)

    def __on_button_release_event(self, widget, event):
        """
            Add or remove track to player
            @param widget as Gtk.Widget
            @param event as Gdk.EventButton
        """
        if self.__image.get_icon_name()[0] == "list-remove-symbolic":
            if len(self.__playlist_ids) == 1:
                self.__remove_from_player_playlists()
            else:
                self.__remove_from_player_albums()
            # Destroy parent Gtk.ListBoxRow
            if len(self.__playlist_ids) == 1:
                ancestor = self.get_ancestor(Gtk.ListBoxRow)
                if ancestor is not None:
                    ancestor.destroy()
        else:
            albums = App().player.albums
            # If album last in list, merge
            if albums and albums[-1].id == self.__track.album.id:
                albums[-1].insert_track(self.__track)
                App().player.set_next()
            # Add album with only one track
            else:
                # We do not want to share same album with multiple user add
                # If needed, previous merge will do the job
                album = self.__track.album.clone(True)
                album.set_tracks([self.__track])
                if App().player.is_playing:
                    App().player.add_album(album)
                else:
                    App().player.play_album(album)
        self.update_button()
        return True

    def __on_destroy(self, widget):
        """
            Clear timeout
            @param widget as Gtk.Widget
        """
        self.clear()

    def __play_loved(self):
        """
            Show play/loved indicator
        """
        if self.__timeout_id is None:
            return False
        if self.__stack.get_visible_child_name() == "play":
            if self.__pass == 5:
                self.__pass = 0
                self.loved(1)
        else:
            self.play()
        self.__pass += 1
        return True
