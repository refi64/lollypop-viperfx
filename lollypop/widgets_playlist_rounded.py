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

from random import sample, choice
from gettext import gettext as _

from lollypop.define import App, Shuffle, Type, ArtSize
from lollypop.objects import Track, Album, Disc
from lollypop.widgets_utils import Popover
from lollypop.widgets_albums_rounded import RoundedAlbumsWidget
from lollypop.helper_overlay import OverlayHelper


class PlayListPopover(Popover):
    """
        Edit a playlist
    """

    def __init__(self, playlist_id, obj):
        """
            @param playlist_id as int
            @param obj as Object
        """
        Popover.__init__(self)
        self.__playlist_id = playlist_id
        self.__obj = obj
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
        App().playlists.remove(self.__playlist_id)
        self.popdown()


class PlaylistRoundedWidget(RoundedAlbumsWidget, OverlayHelper):
    """
        Playlist widget showing cover for 9 albums
    """
    _pixel_size = ArtSize.ROUNDED / 10

    def __init__(self, playlist_id, obj):
        """
            Init widget
            @param playlist_id as playlist_id
            @param obj as Track/Album
        """
        OverlayHelper.__init__(self)
        name = sortname = App().playlists.get_name(playlist_id)
        RoundedAlbumsWidget.__init__(self, playlist_id, name, sortname)
        self.__track_ids = []
        self.__obj = obj
        if obj is not None:
            if isinstance(obj, Album) or\
                    isinstance(obj, Disc):
                self.__add = not App().playlists.exists_album(
                    playlist_id,
                    obj)
            else:
                self.__add = not App().playlists.exists_track(
                    playlist_id,
                    obj.uri)

    def populate(self):
        """
            Populate widget content
        """

        RoundedAlbumsWidget.populate(self)
        self._widget.connect("enter-notify-event", self._on_enter_notify)
        self._widget.connect("leave-notify-event", self._on_leave_notify)

    @property
    def playlist_id(self):
        """
            Get playlist id
            @return int
        """
        return self._data

    @property
    def track_ids(self):
        """
            Get current track ids
            @return [int]
        """
        return self.__track_ids

#######################
# PROTECTED           #
#######################
    def _get_album_ids(self):
        """
            Get ids for widget
            @return [int]
        """
        album_ids = []
        if App().playlists.get_smart(self._data):
            request = App().playlists.get_smart_sql(self._data)
            if request is not None:
                self.__track_ids = App().db.execute(request)
        else:
            self.__track_ids = App().playlists.get_track_ids(self._data)
        sample(self.__track_ids, len(self.__track_ids))
        for track_id in self.__track_ids:
            track = Track(track_id)
            if track.album.id not in album_ids:
                album_ids.append(track.album.id)
            if len(album_ids) == self._ALBUMS_COUNT:
                break
        return album_ids

    def _show_overlay_func(self, show_overlay):
        """
            Set overlay
            @param show_overlay as bool
        """
        if self._lock_overlay or\
                self._show_overlay == show_overlay or\
                App().player.is_locked:
            return
        OverlayHelper._show_overlay_func(self, show_overlay)
        if show_overlay:
            # Play button
            if self.__obj is None:
                self.__play_button = Gtk.Button.new_from_icon_name(
                    "media-playback-start-symbolic",
                    Gtk.IconSize.INVALID)
                self.__play_button.set_tooltip_text(_("Play"))
            elif self.__add:
                # Special case, we are in add to playlist mode
                self.__play_button = Gtk.Button.new_from_icon_name(
                    "list-add-symbolic",
                    Gtk.IconSize.INVALID)
                self.__play_button.set_tooltip_text(_("Add"))
            else:
                # Special case, we are in remove from playlist mode
                self.__play_button = Gtk.Button.new_from_icon_name(
                    "list-remove-symbolic",
                    Gtk.IconSize.INVALID)
                self.__play_button.set_tooltip_text(_("Remove"))
            self.__play_button.set_property("has-tooltip", True)
            self.__play_button.set_hexpand(True)
            self.__play_button.set_relief(Gtk.ReliefStyle.NONE)
            self.__play_button.set_property("valign", Gtk.Align.CENTER)
            self.__play_button.set_property("halign", Gtk.Align.CENTER)
            self.__play_button.connect("realize", self._on_realize)
            self.__play_button.connect("clicked", self.__on_play_clicked)
            self.__play_button.get_image().set_pixel_size(
                PlaylistRoundedWidget._pixel_size + 20)
            # Open button
            self.__open_button = Gtk.Button.new_from_icon_name(
                "folder-open-symbolic",
                Gtk.IconSize.INVALID)
            self.__open_button.set_relief(Gtk.ReliefStyle.NONE)
            self.__open_button.set_property("has-tooltip", True)
            self.__open_button.set_tooltip_text(_("Open"))
            self.__open_button.connect("realize", self._on_realize)
            self.__open_button.connect("clicked", self.__on_open_clicked)
            self.__open_button.get_image().set_pixel_size(
                PlaylistRoundedWidget._pixel_size)
            # Edit button
            self.__edit_button = Gtk.Button.new_from_icon_name(
                "document-properties-symbolic",
                Gtk.IconSize.INVALID)
            self.__edit_button.set_relief(Gtk.ReliefStyle.NONE)
            self.__edit_button.set_property("has-tooltip", True)
            self.__edit_button.set_tooltip_text(_("Modify playlist"))
            self.__edit_button.connect("realize", self._on_realize)
            self.__edit_button.connect("clicked", self.__on_edit_clicked)
            self.__edit_button.get_image().set_pixel_size(
                PlaylistRoundedWidget._pixel_size)
            self._overlay.add_overlay(self.__play_button)
            self.__overlay_grid = Gtk.Grid()
            self.__overlay_grid.set_property("valign", Gtk.Align.END)
            self.__overlay_grid.set_margin_bottom(10)
            self.__overlay_grid.set_property("halign", Gtk.Align.CENTER)
            self.__overlay_grid.add(self.__open_button)
            self.__overlay_grid.add(self.__edit_button)
            self._overlay.add_overlay(self.__overlay_grid)
            self._overlay.show_all()
            self.__play_button.get_style_context().add_class("rounded-icon")
            self.__open_button.get_style_context().add_class("overlay-button")
            self.__edit_button.get_style_context().add_class("overlay-button")
            self.__overlay_grid.get_style_context().add_class(
                "squared-icon-small")
        else:
            self.__overlay_grid.destroy()
            self.__play_button.destroy()
            self.__play_button = None
            self.__open_button.destroy()
            self.__open_button = None
            self.__edit_button.destroy()
            self.__edit_button = None
            self.__overlay_grid.destroy()
            self.__overlay_grid = None

#######################
# PROTECTED           #
#######################

#######################
# PRIVATE             #
#######################
    def __on_play_clicked(self, button):
        """
            Play playlist
            @param button as Gtk.Button
        """
        if self.__obj is None:
            if App().player.is_locked:
                return True
            if self.__track_ids:
                if App().player.is_party:
                    App().lookup_action("party").change_state(
                        GLib.Variant("b", False))
                tracks = [Track(track_id) for track_id in self.__track_ids]
                App().player.populate_playlist_by_tracks(tracks, [self._data])
                if App().settings.get_enum("shuffle") == Shuffle.TRACKS:
                    track = choice(tracks)
                else:
                    track = tracks[0]
                App().player.load(track)
        else:
            if isinstance(self.__obj, Disc):
                tracks = self.__obj.tracks
            elif isinstance(self.__obj, Album):
                tracks = self.__obj.tracks
            else:
                tracks = [self.__obj]
            if self.__add:
                App().playlists.add_tracks(self.playlist_id, tracks)
            else:
                App().playlists.remove_tracks(self.playlist_id, tracks)
            App().window.container.reload_view()
        return True

    def __on_open_clicked(self, button):
        """
            Open playlist
            @param button as Gtk.Button
        """
        if App().settings.get_value("show-sidebar"):
            App().window.container.list_two.select_ids([self._data])
        else:
            App().window.container.show_view(Type.PLAYLISTS, [self._data])
        return True

    def __on_edit_clicked(self, button):
        """
            Edit playlist
            @param button as Gtk.Button
        """
        popover = PlayListPopover(self._data, self.__obj)
        popover.set_relative_to(button)
        popover.connect("closed", self._on_popover_closed)
        self._lock_overlay = True
        popover.popup()
        return True
