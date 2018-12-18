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
from lollypop.define import App, Type, RowListType
from lollypop.controller_view import ViewController, ViewControllerType


class PlaylistsView(View, ViewController):
    """
        Show playlist tracks
    """

    def __init__(self, playlist_ids, list_type, editable=True):
        """
            Init PlaylistView
            @parma playlist ids as [int]
            @param list_type as RowListType
            @param editable as bool
        """
        View.__init__(self, True)
        ViewController.__init__(self, ViewControllerType.ALBUM)
        self.__list_type = list_type
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
        self.__play_button = builder.get_object("play_button")
        self.__shuffle_button = builder.get_object("shuffle_button")
        if App().player.is_locked:
            self.__play_button.set_sensitive(False)
            self.__shuffle_button.set_sensitive(False)
        self.__duration_label = builder.get_object("duration")
        builder.get_object("title").set_label(
            ", ".join(App().playlists.get_names(playlist_ids)))

        self.__jump_button = builder.get_object("jump_button")
        self.__split_button = builder.get_object("split_button")
        smart_button = builder.get_object("smart_button")

        if editable:
            self.__split_button.set_active(not App().settings.get_value(
                "split-view"))
        else:
            self.__jump_button.set_hexpand(True)
            self.__split_button.hide()
            self.__play_button.hide()
            self.__shuffle_button.hide()
        if not editable or len(playlist_ids) > 1 or playlist_ids[0] < 0:
            smart_button.hide()

        self.__playlists_widget = PlaylistsWidget(playlist_ids, list_type)
        self.__playlists_widget.set_filter_func(self._filter_func)
        self.__playlists_widget.connect("populated", self.__on_populated)
        self.__playlists_widget.show()
        self.add(builder.get_object("widget"))
        self._viewport.add(self.__playlists_widget)
        self._scrolled.set_property("expand", True)
        self.add(self._scrolled)
        # Connect signals after ui init
        # "split-button" will emit a signal otherwise
        builder.connect_signals(self)

        # In DB duration calculation
        if playlist_ids[0] > 0:
            duration = 0
            for playlist_id in self.__playlist_ids:
                duration += App().playlists.get_duration(playlist_id)
            self.__set_duration(duration)
        # Ask widget after populated
        else:
            self.__playlists_widget.connect("populated",
                                            self.__on_playlist_populated)
        self.__playlists_widget.connect("orientation-changed",
                                        self.__on_orientation_changed)

    def populate(self, tracks):
        """
            Populate view with tracks from playlist
            @param tracks as [track]
        """
        self.__playlists_widget.populate(tracks)
        self.__update_jump_button()

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
    def __set_duration(self, duration):
        """
            Set playlist duration
            @param duration as int (seconds)
        """
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
        track_ids = [child.track.id
                     for child in self.__playlists_widget.children]
        if App().player.current_track.id in track_ids:
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

    def __on_populated(self, playlists_widget):
        """
            Update jump button on populated
            @param playlists_widget as PlaylistsWidget
        """
        self.__update_jump_button()

    def __on_playlist_track_added(self, playlists, playlist_id, uri, pos):
        """
            Update tracks widgets
            @param playlists as Playlists
            @param playlist id as int
            @param uri as str
            @param pos as int
        """
        if len(self.__playlist_ids) == 1 and\
                playlist_id in self.__playlist_ids:
            track_id = App().tracks.get_id_by_uri(uri)
            self.__playlists_widget.append(track_id)

    def __on_playlist_track_removed(self, playlists, playlist_id, uri, pos):
        """
            Update tracks widgets
            @param playlists as Playlists
            @param playlist id as int
            @param uri as str
            @param pos as int
        """
        if len(self.__playlist_ids) == 1 and\
                playlist_id in self.__playlist_ids:
            track_id = App().tracks.get_id_by_uri(uri)
            self.__playlists_widget.remove(track_id, pos)

    def __on_playlist_populated(self, widget):
        """
            Set duration on populated
            @param widget as PlaylistsWidget
        """
        self.__set_duration(widget.duration)

    def __on_orientation_changed(self, widget, orientation):
        """
            Show/Hide split button
            @param widget as Gtk.Widget
            @param orientation as Gtk.Orientation
        """
        if orientation == Gtk.Orientation.VERTICAL and (
                App().window.is_adaptive or
                self.__list_type & RowListType.POPOVER):
            self.__split_button.hide()
        else:
            self.__split_button.show()
