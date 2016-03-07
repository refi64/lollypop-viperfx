# Copyright (c) 2014-2016 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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
from cgi import escape
from threading import Thread

from lollypop.view import View
from lollypop.widgets_playlist import PlaylistsWidget, PlaylistEditWidget
from lollypop.widgets_playlist import PlaylistsManagerWidget
from lollypop.define import Lp, Type


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
        View.__init__(self)
        self._tracks = []
        self._playlist_ids = playlist_ids
        self._populated = False
        self._signal_id = Lp().playlists.connect('playlist-changed',
                                                 self._update)

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/PlaylistView.ui')
        builder.connect_signals(self)

        name = ""
        for playlist_id in playlist_ids:
            if playlist_id == Type.POPULARS:
                name += _("Popular tracks")+", "
            elif playlist_id == Type.RECENTS:
                name += _("Recently played")+", "
            elif playlist_id == Type.NEVER:
                name += _("Never played")+", "
            elif playlist_id == Type.RANDOMS:
                name += _("Random tracks")+", "
            elif playlist_id == Type.SEARCH:
                name += _("Search")+", "
            else:
                name += Lp().playlists.get_name(playlist_id)+", "
        builder.get_object('title').set_label(name[:-2])

        self._edit_button = builder.get_object('edit-button')
        self._jump_button = builder.get_object('jump-button')

        if len(playlist_ids) > 1 or (
           playlist_ids[0] < 0 and playlist_ids[0] != Type.LOVED) or\
                not editable:
            self._edit_button.hide()
        self._title = builder.get_object('title')

        self._playlists_widget = PlaylistsWidget(playlist_ids)
        self._playlists_widget.connect('populated', self._on_populated)
        self._playlists_widget.show()

        self.add(builder.get_object('widget'))
        self._viewport.add(self._playlists_widget)
        self._scrolled.set_property('expand', True)
        self.add(self._scrolled)

    def populate(self, tracks):
        """
            Populate view with tracks from playlist
            Thread safe
        """
        self._tracks = tracks
        mid_tracks = int(0.5+len(tracks)/2)
        self._playlists_widget.populate_list_left(tracks[:mid_tracks],
                                                  1)
        self._playlists_widget.populate_list_right(tracks[mid_tracks:],
                                                   mid_tracks + 1)

    def get_ids(self):
        """
            Return playlist ids
            @return id as [int]
        """
        return self._playlist_ids

    def stop(self):
        """
            Stop populating
        """
        self._playlists_widget.stop()

#######################
# PRIVATE             #
#######################
    def _get_children(self):
        """
            Return view children
        """
        return [self._playlists_widget]

    def _update(self, manager, playlist_id):
        """
            Update tracks widgets
            @param manager as PlaylistsManager
            @param playlist id as int
        """
        if playlist_id in self._playlist_ids:
            self._playlists_widget.clear()
            t = Thread(target=self._update_view)
            t.daemon = True
            t.start()

    def _update_view(self):
        """
            Update tracks widgets
        """
        tracks = []
        for playlist_id in self._playlist_ids:
            tracks = Lp().playlists.get_tracks_ids(playlist_id)
        self.populate(tracks)

    def _update_jump_button(self):
        """
            Update jump button status
        """
        if Lp().player.current_track.id in self._tracks:
            self._jump_button.set_sensitive(True)
            self._jump_button.set_tooltip_markup(
             "<b>%s</b>\n%s" % (escape(Lp().player.current_track.artist_names),
                                escape(Lp().player.current_track.name)))
        else:
            self._jump_button.set_sensitive(False)
            self._jump_button.set_tooltip_text('')

    def _on_populated(self, widget):
        """
            Show current track
            @param widget as Gtk.Widget
        """
        # Ignore first list
        if not self._populated:
            self._populated = True
            return
        self._update_jump_button()

    def _on_destroy(self, widget):
        """
            Disconnect signals
            @param widget as Gtk.Widget
        """
        View._on_destroy(self, widget)
        if self._signal_id:
            Lp().playlists.disconnect(self._signal_id)
            self._signal_id = None

    def _on_jump_button_clicked(self, button):
        """
            Scroll to current track
            @param button as Gtk.Button
        """
        y = self._playlists_widget.get_current_ordinate()
        if y is not None:
            self._scrolled.get_vadjustment().set_value(y)

    def _on_edit_button_clicked(self, button):
        """
            Edit playlist
            @param button as Gtk.Button
        """
        Lp().window.show_playlist_editor(self._playlist_ids[0])

    def _on_current_changed(self, player):
        """
            Current song changed, update playing button
            @param player as Player
        """
        View._on_current_changed(self, player)
        self._update_jump_button()


class PlaylistsManageView(View):
    """
        Playlist view used to manage playlists
    """

    def __init__(self, object_id, genre_id, is_album):
        """
            Init View
            @param object id as int
            @param genre id as int
            @param is album as bool
            @param width as int
        """
        View.__init__(self)
        builder = Gtk.Builder()
        builder.add_from_resource(
            '/org/gnome/Lollypop/PlaylistsManagerView.ui')
        if object_id != Type.NONE:
            builder.get_object('back_btn').show()
        builder.connect_signals(self)
        self._manage_widget = PlaylistsManagerWidget(object_id,
                                                     genre_id,
                                                     is_album)
        self._manage_widget.show()
        self._viewport.add(self._manage_widget)
        self.add(builder.get_object('widget'))
        self.add(self._scrolled)

    def populate(self):
        """
            Populate the view
        """
        self._manage_widget.populate()

#######################
# PRIVATE             #
#######################
    def _on_new_clicked(self, widget):
        """
            Add new playlist
            @param widget as Gtk.Button
        """
        self._manage_widget.add_new_playlist()

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
        builder.add_from_resource('/org/gnome/Lollypop/PlaylistEditView.ui')
        builder.get_object('title').set_label(
                                          Lp().playlists.get_name(playlist_id))
        builder.connect_signals(self)
        grid = builder.get_object('widget')
        self.add(grid)
        self._edit_widget = PlaylistEditWidget(playlist_id)
        self._edit_widget.show()
        self._viewport.add(self._edit_widget)
        self.add(self._scrolled)

    def populate(self):
        """
            Populate view
        """
        self._edit_widget.populate()

#######################
# PRIVATE             #
#######################
    def _on_back_btn_clicked(self, button):
        """
            Restore previous view
            @param button as Gtk.Button
        """
        Lp().window.destroy_current_view()
