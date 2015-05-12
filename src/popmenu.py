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

from gi.repository import Gio, GLib

from shutil import which
from gettext import gettext as _
from _thread import start_new_thread

from lollypop.define import Objects, NextContext


# Base menu class
class BaseMenu(Gio.Menu):
    """
        Init variable
        @param object id as int
        @param genre id as int
        @param is album as bool
    """
    def __init__(self, object_id, genre_id, is_album):
        Gio.Menu.__init__(self)
        self._genre_id = genre_id
        self._object_id = object_id
        self._is_album = is_album
        self._app = Gio.Application.get_default()


# Contextual menu for playback
class PlaybackMenu(BaseMenu):
    """
        Init playback menu
    """
    def __init__(self):
        BaseMenu.__init__(self, None, None, None)
        self._set_playback_actions()

#######################
# PRIVATE             #
#######################
    """
        Set playback actions
    """
    def _set_playback_actions(self):
        if Objects.player.context.next != NextContext.NONE:
            continue_play_action = Gio.SimpleAction(
                                                name="continue_play_action")
            self._app.add_action(continue_play_action)
            continue_play_action.connect('activate', self._continue_playback)
            self.append(_("Continue playback"), 'app.continue_play_action')
        if Objects.player.context.next != NextContext.STOP_TRACK:
            stop_track_action = Gio.SimpleAction(name="stop_track_action")
            self._app.add_action(stop_track_action)
            stop_track_action.connect('activate', self._stop_track)
            self.append(_("Stop after this track"), 'app.stop_track_action')
        if Objects.player.context.next != NextContext.STOP_ALBUM:
            stop_album_action = Gio.SimpleAction(name="stop_album_action")
            self._app.add_action(stop_album_action)
            stop_album_action.connect('activate', self._stop_album)
            self.append(_("Stop after this album"), 'app.stop_album_action')
        if Objects.player.context.next != NextContext.STOP_ARTIST:
            stop_artist_action = Gio.SimpleAction(name="stop_artist_action")
            self._app.add_action(stop_artist_action)
            stop_artist_action.connect('activate', self._stop_artist)
            self.append(_("Stop after this artist"), 'app.stop_artist_action')

    """
        Tell player to continue playback
        @param SimpleAction
        @param GVariant
        @param album id as int
    """
    def _continue_playback(self, action, variant):
        Objects.player.context.next = NextContext.NONE

    """
        Tell player to stop after current track
        @param SimpleAction
        @param GVariant
    """
    def _stop_track(self, action, variant):
        Objects.player.context.next = NextContext.STOP_TRACK

    """
        Tell player to stop after current album
        @param SimpleAction
        @param GVariant
    """
    def _stop_album(self, action, variant):
        Objects.player.context.next = NextContext.STOP_ALBUM

    """
        Tell player to stop after current artist
        @param SimpleAction
        @param GVariant
    """
    def _stop_artist(self, action, variant):
        Objects.player.context.next = NextContext.STOP_ARTIST


# Contextual menu for queue
# Subclass for BaseMenu
class QueueMenu(BaseMenu):
    """
        Init playlists menu
        @param object id as int
        @param genre id as int
        @param is album as bool
    """
    def __init__(self, object_id, genre_id, is_album):
        BaseMenu.__init__(self, object_id, genre_id, is_album)
        self._set_queue_actions()

#######################
# PRIVATE             #
#######################
    """
        Set queue actions
    """
    def _set_queue_actions(self):
        queue = Objects.player.get_queue()
        append = True
        prepend = True
        delete = True
        if not queue:
            append = False
        if not self._is_album:
            if self._object_id in queue:
                if queue and queue[0] == self._object_id:
                    prepend = False
                append = False
            else:
                delete = False
        else:

            tracks = Objects.albums.get_tracks(self._object_id,
                                               self._genre_id)
            union = set(queue) & set(tracks)
            if len(union) == len(tracks):
                append = False
                prepend = False
            elif not bool(union):
                delete = False

        append_queue_action = Gio.SimpleAction(name="append_queue_action")
        self._app.add_action(append_queue_action)
        prepend_queue_action = Gio.SimpleAction(name="prepend_queue_action")
        self._app.add_action(prepend_queue_action)
        del_queue_action = Gio.SimpleAction(name="del_queue_action")
        self._app.add_action(del_queue_action)
        if append:
            append_queue_action.connect('activate',
                                        self._append_to_queue)
            self.append(_("Add to queue"), 'app.append_queue_action')
        if prepend:
            prepend_queue_action.connect('activate',
                                         self._prepend_to_queue)
            if self._is_album:
                self.append(_("Next tracks"), 'app.prepend_queue_action')
            else:
                self.append(_("Next track"), 'app.prepend_queue_action')
        if delete:
            del_queue_action.connect('activate',
                                     self._del_from_queue)
            self.append(_("Remove from queue"), 'app.del_queue_action')

    """
        Append track to queue
        @param SimpleAction
        @param GVariant
    """
    def _append_to_queue(self, action, variant):
        if self._is_album:
            for track_id in Objects.albums.get_tracks(self._object_id,
                                                      self._genre_id):
                Objects.player.append_to_queue(track_id)
        else:
            Objects.player.append_to_queue(self._object_id)

    """
        Prepend track id to queue
        @param SimpleAction
        @param GVariant
    """
    def _prepend_to_queue(self, action, variant):
        if self._is_album:
            for track_id in reversed(Objects.albums.get_tracks(
                                                    self._object_id,
                                                    self._genre_id)):
                Objects.player.prepend_to_queue(track_id)
        else:
            Objects.player.prepend_to_queue(self._object_id)

    """
        Delete track id from queue
        @param SimpleAction
        @param GVariant
    """
    def _del_from_queue(self, action, variant):
        if self._is_album:
            for track_id in Objects.albums.get_tracks(self._object_id,
                                                      self._genre_id):
                Objects.player.del_from_queue(track_id)
        else:
            Objects.player.del_from_queue(self._object_id)


# Contextual menu for playlists
# Subclass for BaseMenu
class PlaylistsMenu(BaseMenu):
    """
        Init playlist menu
        @param object id as int
        @param genre id as int
        @param is album as bool
    """
    def __init__(self, object_id, genre_id, is_album):
        BaseMenu.__init__(self, object_id, genre_id, is_album)
        self._set_playlist_actions()

#######################
# PRIVATE             #
#######################
    """
        Set playlist actions
    """
    def _set_playlist_actions(self):
        playlist_action = Gio.SimpleAction(name="playlist_action")
        self._app.add_action(playlist_action)
        playlist_action.connect('activate',
                                self._add_to_playlists)
        self.append(_("Add to others"), 'app.playlist_action')

        i = 0
        for playlist in Objects.playlists.get_last():
            action = Gio.SimpleAction(name="playlist%s" % i)
            self._app.add_action(action)
            if Objects.playlists.is_present(playlist,
                                            self._object_id,
                                            self._genre_id,
                                            self._is_album):
                action.connect('activate',
                               self._del_from_playlist,
                               playlist)
                self.append(_("Remove from \"%s\"") % playlist,
                            "app.playlist%s" % i)
            else:
                action.connect('activate',
                               self._add_to_playlist,
                               playlist)
                self.append(_("Add to \"%s\"") % playlist,
                            "app.playlist%s" % i)
            i += 1

    """
        Add to playlists
        @param SimpleAction
        @param GVariant
    """
    def _add_to_playlists(self, action, variant):
        Objects.window.show_playlist_manager(self._object_id,
                                             self._genre_id,
                                             self._is_album)

    """
        Add to playlist
        @param SimpleAction
        @param GVariant
        @param playlist name as str
    """
    def _add_to_playlist(self, action, variant, playlist_name):
        if self._is_album:
            tracks_path = Objects.albums.get_tracks_path(self._object_id,
                                                         self._genre_id)
        else:
            tracks_path = [Objects.tracks.get_path(self._object_id)]

        start_new_thread(Objects.playlists.add_tracks,
                         (playlist_name, tracks_path))

    """
        Del from playlist
        @param SimpleAction
        @param GVariant
        @param object id as int
        @param is album as bool
        @param playlist name as str
    """
    def _del_from_playlist(self, action, variant, playlist_name):
        if self._is_album:
            tracks_path = Objects.albums.get_tracks_path(self._object_id,
                                                         self._genre_id)
        else:
            tracks_path = [Objects.tracks.get_path(self._object_id)]

        start_new_thread(Objects.playlists.remove_tracks,
                         (playlist_name, tracks_path))



# Contextual menu for toolbar
class PopToolbarMenu(Gio.Menu):
    """
        Init menu model
        @param object id as int
        @param genre id as int
    """
    def __init__(self, object_id, genre_id):
        Gio.Menu.__init__(self)
        if not Objects.player.is_party():
            self.insert_section(0, _("Playback"),
                                PlaybackMenu())
        self.insert_section(1, _("Playlists"),
                            PlaylistsMenu(object_id, genre_id, False))


# Edition menu for album
# Subclass for BaseMenu
class EditMenu(BaseMenu):
    _TAG_EDITORS = ['exfalso', 'easytag', 'picard', 'puddletag', 'kid3-qt']
    """
        Init playlist menu
        @param object id as int
        @param genre id as int
        @param is album as bool
    """
    def __init__(self, object_id, genre_id, is_album):
        BaseMenu.__init__(self, object_id, genre_id, is_album)

        if is_album:
            favorite = Objects.settings.get_value(
                                                     'tag-editor').get_string()
            for editor in [favorite] + self._TAG_EDITORS:
                if which(editor) is not None:
                    self._tag_editor = editor
                    self._set_edit_actions()
                    break

    """
        Set edit actions
    """
    def _set_edit_actions(self):
        edit_tag_action = Gio.SimpleAction(name="edit_tag_action")
        self._app.add_action(edit_tag_action)
        edit_tag_action.connect('activate',
                                self._edit_tag)
        self.append(_("Modify informations"), 'app.edit_tag_action')

    """
        Run tag editor
    """
    def _edit_tag(self, action, variant):
        album_path = Objects.albums.get_path(self._object_id)
        GLib.spawn_command_line_async("%s \"%s\"" % (self._tag_editor,
                                                     album_path))


# Contextual menu for album
class PopAlbumMenu(Gio.Menu):
    """
        Init menu model
        @param object id as int
        @param genre id as int
    """
    def __init__(self, object_id, genre_id):
        Gio.Menu.__init__(self)
        self.insert_section(0, _("Playback"),
                            QueueMenu(object_id, genre_id, True))
        self.insert_section(1, _("Playlists"),
                            PlaylistsMenu(object_id, genre_id, True))
        self.insert_section(2, _("Edit"),
                            EditMenu(object_id, genre_id, True))
        

# Contextual menu for track
class PopTrackMenu(Gio.Menu):
    """
        Init menu model
        @param object id as int
        @param genre id as int
    """
    def __init__(self, object_id, genre_id):
        Gio.Menu.__init__(self)
        self.insert_section(0, _("Playback"),
                            QueueMenu(object_id, genre_id, False))
        self.insert_section(1, _("Playlists"),
                            PlaylistsMenu(object_id, genre_id, False))

