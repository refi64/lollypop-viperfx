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

from gi.repository import Gtk, GLib, Gio

from gettext import gettext as _
from random import shuffle

from lollypop.view import View
from lollypop.widgets_playlist import PlaylistsWidget
from lollypop.define import App, Type
from lollypop.objects import Track
from lollypop.controller_view import ViewController


class PlaylistsView(View, ViewController):
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
        ViewController.__init__(self)
        self.__track_ids = []
        self.__playlist_ids = playlist_ids
        self.__signal_id1 = App().playlists.connect(
                                            "playlist-track-added",
                                            self.__on_playlist_track_added)
        self.__signal_id2 = App().playlists.connect(
                                            "playlist-track-removed",
                                            self.__on_playlist_track_removed)

        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/PlaylistView.ui")
        self.__header = builder.get_object("header")
        if App().player.is_locked:
            builder.get_object("play_button").set_sensitive(False)
            builder.get_object("shuffle_button").set_sensitive(False)
        self.__duration_label = builder.get_object("duration")
        builder.get_object("title").set_label(
            ", ".join(App().playlists.get_names(playlist_ids)))

        self.__jump_button = builder.get_object("jump_button")
        split_button = builder.get_object("split_button")
        smart_button = builder.get_object("smart_button")

        if editable:
            split_button.set_active(not App().settings.get_value("split-view"))
        else:
            split_button.hide()

        if not editable or len(playlist_ids) > 1 or playlist_ids[0] < 0:
            smart_button.hide()

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
        self.connect_current_changed_signal()

        # No duration for non user playlists
        # FIXME
        if playlist_ids[0] > 0:
            self.__set_duration()

    def populate(self, track_ids):
        """
            Populate view with tracks from playlist
            @param track_ids as [int]
        """
        # We are looking for middle
        # Ponderate with this:
        # Tracks with cover == 2
        # Tracks without cover == 1
        prev_album_id = None
        heights = {}
        total = 0
        idx = 0
        for track_id in track_ids:
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
        self.__track_ids = track_ids
        self.__update_jump_button()
        self.__playlists_widget.populate_list_left(track_ids[:mid_tracks],
                                                   1)
        self.__playlists_widget.populate_list_right(track_ids[mid_tracks:],
                                                    mid_tracks + 1)

    def stop(self):
        """
            Stop populating
        """
        self.__playlists_widget.stop()

    @property
    def playlist_ids(self):
        """
            Return playlist ids
            @return id as [int]
        """
        return self.__playlist_ids

#######################
# PROTECTED           #
#######################
    def _on_current_changed(self, player):
        """
            Update children state
            @param player as Player
        """
        self.__update_jump_button()
        self.__playlists_widget.set_playing_indicator()

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
            App().playlists.disconnect(self.__signal_id1)
            self.__signal_id1 = None
        if self.__signal_id2:
            App().playlists.disconnect(self.__signal_id2)
            self.__signal_id2 = None

    def _on_split_button_toggled(self, button):
        """
            Split/Unsplit view
        """
        App().settings.set_value("split-view",
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

    def _on_save_button_clicked(self, button):
        """
            Save playlist as file
            @param button as Gtk.Button
        """
        filechooser = Gtk.FileChooserNative.new(_("Save playlist"),
                                                App().window,
                                                Gtk.FileChooserAction.SAVE,
                                                _("Save"),
                                                _("Cancel"))
        filter = Gtk.FileFilter.new()
        filter.set_name("audio/x-mpegurl")
        filter.add_mime_type("audio/x-mpegurl")
        filechooser.add_filter(filter)
        filechooser.set_do_overwrite_confirmation(True)
        name = ", ".join(App().playlists.get_names(self.__playlist_ids))
        filechooser.set_current_name("%s.m3u" % name)
        filechooser.connect("response", self.__on_save_response)
        filechooser.run()

    def _on_play_button_clicked(self, button):
        """
            Play playlist
            @param button as Gtk.Button
        """
        tracks = []
        for child in self.__playlists_widget.children:
            tracks.append(child.track)
        if tracks:
            App().player.load(tracks[0])
            App().player.populate_playlist_by_tracks(tracks,
                                                     self.__playlist_ids)

    def _on_shuffle_button_clicked(self, button):
        """
            Play playlist shuffled
            @param button as Gtk.Button
        """
        tracks = []
        for child in self.__playlists_widget.children:
            tracks.append(child.track)
        if tracks:
            shuffle(tracks)
            App().player.load(tracks[0])
            App().player.populate_playlist_by_tracks(tracks,
                                                     self.__playlist_ids)

    def _on_smart_button_clicked(self, button):
        """
            Edit smart playlist
            @param button as Gtk.Button
        """
        App().window.container.show_smart_playlist_editor(
            self.__playlist_ids[0])

    def _on_map(self, widget):
        """
            Set active ids
        """
        App().settings.set_value("state-one-ids",
                                 GLib.Variant("ai", [Type.PLAYLISTS]))
        App().settings.set_value("state-two-ids",
                                 GLib.Variant("ai", self.__playlist_ids))

#######################
# PRIVATE             #
#######################
    def __set_duration(self):
        """
            Set playlist duration
        """
        duration = 0
        for playlist_id in self.__playlist_ids:
            duration += App().playlists.get_duration(playlist_id)

        hours = int(duration / 3600)
        mins = int(duration / 60)
        if hours > 0:
            mins -= hours * 60
            if mins > 0:
                # Duration hour minute
                self.__duration_label.set_text(_("%s h  %s m") % (hours, mins))
            else:
                # Duration hour minute
                self.__duration_label.set_text(_("%s h") % hours)
        else:
            # Duration hour minute
            self.__duration_label.set_text(_("%s m") % mins)

    def __update_jump_button(self):
        """
            Update jump button status
        """
        if App().player.current_track.id in self.__track_ids:
            self.__jump_button.set_sensitive(True)
        else:
            self.__jump_button.set_sensitive(False)

    def __on_save_response(self, dialog, response_id):
        """
            Save playlist
            @param dialog as Gtk.NativeDialog
            @param response_id as int
        """
        try:
            if response_id == Gtk.ResponseType.ACCEPT:
                uris = []
                for box in self.__playlists_widget.boxes:
                    for child in box.get_children():
                        uris.append(child.track.uri)
                stream = dialog.get_file().replace(
                    None,
                    False,
                    Gio.FileCreateFlags.REPLACE_DESTINATION,
                    None)
                stream.write("#EXTM3U\n".encode("utf-8"))
                for uri in uris:
                    string = "%s\n" % uri
                    stream.write(string.encode("utf-8"))
                stream.close()
        except:
            pass

    def __on_playlist_track_added(self, playlists, playlist_id, uri):
        """
            Update tracks widgets
            @param playlists as Playlists
            @param playlist id as int
            @param uri as str
        """
        if len(self.__playlist_ids) == 1 and\
                playlist_id in self.__playlist_ids:
            track_id = App().tracks.get_id_by_uri(uri)
            self.__playlists_widget.insert(track_id)

    def __on_playlist_track_removed(self, playlists, playlist_id, uri):
        """
            Update tracks widgets
            @param playlists as Playlists
            @param playlist id as int
            @param uri as str
        """
        if len(self.__playlist_ids) == 1 and\
                playlist_id in self.__playlist_ids:
            track_id = App().tracks.get_id_by_uri(uri)
            self.__playlists_widget.remove(track_id)
