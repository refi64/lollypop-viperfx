#!/usr/bin/python
# Copyright (c) 2014-2015 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from _thread import start_new_thread

from lollypop.view import View
from lollypop.widgets_playlist import PlaylistWidget, PlaylistEditWidget
from lollypop.widgets_playlist import PlaylistsManagerWidget
from lollypop.define import Lp, Type


# Playlist view is a vertical grid with album's covers
class PlaylistsView(View):
    """
        Init PlaylistsView ui with a scrolled grid of PlaylistWidgets
        @parma playlist id as int
        @param playlist name as str
    """
    def __init__(self, playlist_id, playlist_name, parent):
        View.__init__(self)
        self._playlist_name = playlist_name
        self._signal_id = None

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/PlaylistsView.ui')
        builder.get_object('title').set_label(playlist_name)
        builder.connect_signals(self)

        self._edit_btn = builder.get_object('edit_btn')
        if playlist_id <= 0 and playlist_id != Type.LOVED:
            self._edit_btn.hide()
        self._back_btn = builder.get_object('back_btn')
        self._title = builder.get_object('title')

        self._playlist_widget = PlaylistWidget(playlist_id, playlist_name)
        self._playlist_widget.show()

        self.add(builder.get_object('widget'))
        self._viewport.add(self._playlist_widget)
        self._scrolledWindow.set_property('expand', True)
        self.add(self._scrolledWindow)

    """
        Populate view with tracks from playlist
        Thread safe
    """
    def populate(self):
        sql = Lp.db.get_cursor()
        tracks = Lp.playlists.get_tracks_id(self._playlist_name, sql)
        mid_tracks = int(0.5+len(tracks)/2)
        self._playlist_widget.populate_list_one(tracks[:mid_tracks],
                                                1)
        self._playlist_widget.populate_list_two(tracks[mid_tracks:],
                                                mid_tracks + 1)
        sql.close()

    """
        Populate view with tracks
        @param tracks as [int]
    """
    def populate_tracks(self, tracks):
        mid_tracks = int(0.5+len(tracks)/2)
        self._playlist_widget.populate_list_one(tracks[:mid_tracks],
                                                1)
        self._playlist_widget.populate_list_two(tracks[mid_tracks:],
                                                mid_tracks + 1)

    """
        Return playlist name
        @return name as str
    """
    def get_name(self):
        return self._playlist_name

    """
        Do show, connect signals
    """
    def do_show(self):
        self._signal_id = Lp.playlists.connect('playlist-changed',
                                               self._update_view)
        View.do_show(self)

    """
        Do hide, disconnect signals
    """
    def do_hide(self):
        if self._signal_id:
            Lp.playlists.disconnect(self._signal_id)
            self._signal_id = None
        View.do_hide(self)

    """
        Stop populating
    """
    def stop(self):
        self._playlist_widget.stop()

#######################
# PRIVATE             #
#######################
    """
        Update tracks widgets
        @param manager as PlaylistsManager
        @param playlist name as str
    """
    def _update_view(self, manager, playlist_name):
        if playlist_name == self._playlist_name:
            self._playlist_widget.clear()
            start_new_thread(self.populate, ())

    """
        Edit playlist
        @param button as Gtk.Button
        @param playlist name as str
    """
    def _on_edit_btn_clicked(self, button):
        Lp.window.show_playlist_editor(self._playlist_name)

    """
        Current song changed
        @param player as Player
    """
    def _on_current_changed(self, player):
        self._playlist_widget.update_playing_indicator()


# Playlist view used to manage playlists
class PlaylistsManageView(View):
    """
         @param object id as int
         @param genre id as int
         @param is album as bool
         @param width as int
    """
    def __init__(self, object_id, genre_id, is_album, width):
        View.__init__(self)
        builder = Gtk.Builder()
        builder.add_from_resource(
            '/org/gnome/Lollypop/PlaylistsManagerView.ui')
        if object_id != -1:
            builder.get_object('back_btn').show()
        builder.connect_signals(self)
        self._manage_widget = PlaylistsManagerWidget(object_id,
                                                     genre_id,
                                                     is_album)
        self._manage_widget.show()
        self._scrolledWindow.set_property('halign', Gtk.Align.CENTER)
        self._scrolledWindow.set_property('width-request', width)
        self._viewport.add(self._manage_widget)
        self.add(builder.get_object('widget'))
        self.add(self._scrolledWindow)

    def populate(self):
        self._manage_widget.populate()

#######################
# PRIVATE             #
#######################
    """
        Add new playlist
        @param widget as Gtk.Button
    """
    def _on_new_clicked(self, widget):
        self._manage_widget.add_new_playlist()

    """
        Restore previous view
        @param button as Gtk.Button
    """
    def _on_back_btn_clicked(self, button):
        Lp.window.destroy_current_view()


# Playlist view used to edit playlists
class PlaylistEditView(View):
    """
         @param playlist name as str
         @param width as int
    """
    def __init__(self, playlist_name, width):
        View.__init__(self)
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/PlaylistEditView.ui')
        builder.get_object('title').set_label(playlist_name)
        builder.connect_signals(self)
        grid = builder.get_object('widget')
        self.add(grid)
        self._edit_widget = PlaylistEditWidget(playlist_name)
        self._edit_widget.show()
        self._scrolledWindow.set_property('halign', Gtk.Align.CENTER)
        self._scrolledWindow.set_property('width-request', width)
        self._viewport.add(self._edit_widget)
        self.add(self._scrolledWindow)

    def populate(self):
        self._edit_widget.populate()

#######################
# PRIVATE             #
#######################
    """
        Restore previous view
        @param button as Gtk.Button
    """
    def _on_back_btn_clicked(self, button):
        Lp.window.destroy_current_view()
