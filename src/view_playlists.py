# Copyright (c) 2014-2017 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from lollypop.view import View
from lollypop.widgets_playlist import PlaylistsWidget, PlaylistEditWidget
from lollypop.widgets_playlist import PlaylistsManagerWidget
from lollypop.define import Lp, Type
from lollypop.objects import Track


class PlaylistsView(View):
    """
        Show playlist tracks
    """

    def __init__(self, playlist_ids, editable=True):
        """
            Init PlaylistView
            @parma playlist ids as [int]
            @param editable as bool
        """
        View.__init__(self, True)
        self.__tracks = []
        self.__playlist_ids = playlist_ids
        self.__signal_id1 = Lp().playlists.connect("playlist-add",
                                                   self.__on_playlist_add)
        self.__signal_id2 = Lp().playlists.connect("playlist-del",
                                                   self.__on_playlist_del)

        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/PlaylistView.ui")
        self.__duration_label = builder.get_object("duration")
        builder.get_object("title").set_label(
                             ", ".join(Lp().playlists.get_names(playlist_ids)))

        self.__edit_button = builder.get_object("edit-button")
        self.__jump_button = builder.get_object("jump-button")
        split_button = builder.get_object("split-button")
        if editable:
            split_button.set_active(not Lp().settings.get_value("split-view"))
        else:
            split_button.hide()

        if len(playlist_ids) > 1 or (
           playlist_ids[0] < 0 and playlist_ids[0] not in [Type.LOVED,
                                                           Type.NOPARTY]) or\
                not editable:
            self.__edit_button.hide()

        self.__playlists_widget = PlaylistsWidget(playlist_ids)
        self.__playlists_widget.set_filter_func(self._filter_func)
        self.__playlists_widget.show()
        self.add(builder.get_object("widget"))
        self._viewport.add(self.__playlists_widget)
        self._scrolled.set_property("expand", True)
        self.add(self._scrolled)
        # Connect signals after ui init
        # "split-button" will emit a signal otherwise
        builder.connect_signals(self)
        self.__set_duration()

    def populate(self, tracks):
        """
            Populate view with tracks from playlist
            Thread safe
        """
        # We are looking for middle
        # Ponderate with this:
        # Tracks with cover == 2
        # Tracks without cover == 1
        prev_album_id = None
        heights = {}
        total = 0
        idx = 0
        for track_id in tracks:
            track = Track(track_id)
            if track.album_id != prev_album_id:
                heights[idx] = 2
                total += 2
            else:
                heights[idx] = 1
                total += 1
            prev_album_id = track.album_id
            idx += 1
        half = int(total / 2 + 0.5)
        mid_tracks = 1
        count = 0
        for height in heights.values():
            count += height
            if count >= half:
                break
            mid_tracks += 1
        self.__tracks = tracks
        self.__update_jump_button()
        self.__playlists_widget.populate_list_left(tracks[:mid_tracks],
                                                   1)
        self.__playlists_widget.populate_list_right(tracks[mid_tracks:],
                                                    mid_tracks + 1)

    def get_ids(self):
        """
            Return playlist ids
            @return id as [int]
        """
        return self.__playlist_ids

    def stop(self):
        """
            Stop populating
        """
        self.__playlists_widget.stop()

#######################
# PROTECTED           #
#######################
    def _get_children(self):
        """
            Return view children
        """
        return [self.__playlists_widget]

    def _on_search_changed(self, entry):
        """
            Update filter
            @param entry as Gtk.Entry
        """
        self._filter = entry.get_text()
        for box in self.__playlists_widget.boxes:
            box.invalidate_filter()

    def _on_destroy(self, widget):
        """
            Disconnect signals
            @param widget as Gtk.Widget
        """
        View._on_destroy(self, widget)
        if self.__signal_id1:
            Lp().playlists.disconnect(self.__signal_id1)
            self.__signal_id1 = None
        if self.__signal_id2:
            Lp().playlists.disconnect(self.__signal_id2)
            self.__signal_id2 = None

    def _on_split_button_toggled(self, button):
        """
            Split/Unsplit view
        """
        Lp().settings.set_value("split-view",
                                GLib.Variant("b", not button.get_active()))
        self.__playlists_widget.update_allocation()

    def _on_jump_button_clicked(self, button):
        """
            Scroll to current track
            @param button as Gtk.Button
        """
        y = self.__playlists_widget.get_current_ordinate()
        if y is not None:
            self._scrolled.get_vadjustment().set_value(y)

    def _on_edit_button_clicked(self, button):
        """
            Edit playlist
            @param button as Gtk.Button
        """
        Lp().window.show_playlist_editor(self.__playlist_ids[0])

    def _on_current_changed(self, player):
        """
            Current song changed, update playing button
            @param player as Player
        """
        View._on_current_changed(self, player)
        self.__update_jump_button()

#######################
# PRIVATE             #
#######################
    def __set_duration(self):
        """
            Set playlist duration
        """
        duration = 0
        for playlist_id in self.__playlist_ids:
            duration += Lp().playlists.get_duration(playlist_id)

        hours = int(duration / 3600)
        mins = int(duration / 60)
        if hours > 0:
            mins -= hours * 60
            if mins > 0:
                self.__duration_label.set_text(_("%s h  %s m") % (hours, mins))
            else:
                self.__duration_label.set_text(_("%s h") % hours)
        else:
            self.__duration_label.set_text(_("%s m") % mins)

    def __update_jump_button(self):
        """
            Update jump button status
        """
        if Lp().player.current_track.id in self.__tracks:
            self.__jump_button.set_sensitive(True)
            artists = ", ".join(Lp().player.current_track.artists)
            self.__jump_button.set_tooltip_markup(
             "<b>%s</b>\n%s" % (GLib.markup_escape_text(artists),
                                GLib.markup_escape_text(
                                              Lp().player.current_track.name)))
        else:
            self.__jump_button.set_sensitive(False)
            self.__jump_button.set_tooltip_text("")

    def __on_playlist_add(self, manager, playlist_id, track_id, pos):
        """
            Update tracks widgets
            @param manager as PlaylistsManager
            @param playlist id as int
            @param track id as int
        """
        if playlist_id in self.__playlist_ids:
            self.__playlists_widget.insert(track_id, pos)

    def __on_playlist_del(self, manager, playlist_id, track_id):
        """
            Update tracks widgets
            @param manager as PlaylistsManager
            @param playlist id as int
            @param track id as int
        """
        if playlist_id in self.__playlist_ids:
            self.__playlists_widget.remove(track_id)


class PlaylistsManageView(View):
    """
        Playlist view used to manage playlists
    """

    def __init__(self, object_id, genre_ids, artist_ids, is_album):
        """
            Init View
            @param object id as int
            @param genre ids as [int]
            @param artist ids as [int]
            @param is album as bool
            @param width as int
        """
        View.__init__(self)
        builder = Gtk.Builder()
        builder.add_from_resource(
            "/org/gnome/Lollypop/PlaylistsManagerView.ui")
        if object_id != Type.NONE:
            builder.get_object("back_btn").show()
        builder.connect_signals(self)
        self.__manage_widget = PlaylistsManagerWidget(object_id,
                                                      genre_ids,
                                                      artist_ids,
                                                      is_album)
        self.__manage_widget.show()
        self._viewport.add(self.__manage_widget)
        self.add(builder.get_object("widget"))
        self.add(self._scrolled)

    def populate(self):
        """
            Populate the view
        """
        self.__manage_widget.populate()

#######################
# PROTECTED           #
#######################
    def _on_new_clicked(self, widget):
        """
            Add new playlist
            @param widget as Gtk.Button
        """
        self.__manage_widget.add_new_playlist()

    def _on_back_btn_clicked(self, button):
        """
            Restore previous view
            @param button as Gtk.Button
        """
        Lp().window.destroy_current_view()


class PlaylistEditView(View):
    """
        Playlist view used to edit playlists
    """

    def __init__(self, playlist_id):
        """
            Init view
            @param playlist id as int
            @param playlist name as int
            @param width as int
        """
        View.__init__(self)
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/PlaylistEditView.ui")
        builder.get_object("title").set_label(
                                          Lp().playlists.get_name(playlist_id))
        builder.connect_signals(self)
        grid = builder.get_object("widget")
        self.add(grid)
        self.__edit_widget = PlaylistEditWidget(playlist_id)
        self.__edit_widget.show()
        self._viewport.add(self.__edit_widget)
        self.add(self._scrolled)

    def populate(self):
        """
            Populate view
        """
        self.__edit_widget.populate()

#######################
# PROTECTED           #
#######################
    def _on_back_btn_clicked(self, button):
        """
            Restore previous view
            @param button as Gtk.Button
        """
        Lp().window.reload_view()
