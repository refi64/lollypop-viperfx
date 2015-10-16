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
from threading import Thread

from lollypop.define import Lp, NextContext
from lollypop.objects import Track
from lollypop import utils


class BaseMenu(Gio.Menu):
    """
        Base menu for all menus
    """

    def __init__(self, object_id, genre_id, is_album):
        """
            Init variable
            @param object id as int
            @param genre id as int
            @param is album as bool
        """
        Gio.Menu.__init__(self)
        self._genre_id = genre_id
        self._object_id = object_id
        self._is_album = is_album
        self._app = Gio.Application.get_default()


class PlaybackMenu(BaseMenu):
    """
        Contextual menu for playback
    """

    def __init__(self):
        """
            Init playback menu
        """
        BaseMenu.__init__(self, None, None, None)
        self._set_playback_actions()

#######################
# PRIVATE             #
#######################
    def _set_playback_actions(self):
        """
            Set playback actions
        """
        if Lp.player.context.next != NextContext.NONE:
            continue_play_action = Gio.SimpleAction(
                name="continue_play_action")
            self._app.add_action(continue_play_action)
            continue_play_action.connect('activate', self._continue_playback)
            self.append(_("Continue playback"), 'app.continue_play_action')
        if Lp.player.context.next != NextContext.STOP_TRACK:
            stop_track_action = Gio.SimpleAction(name="stop_track_action")
            self._app.add_action(stop_track_action)
            stop_track_action.connect('activate', self._stop_track)
            self.append(_("Stop after this track"), 'app.stop_track_action')
        if Lp.player.context.next != NextContext.STOP_ALBUM:
            stop_album_action = Gio.SimpleAction(name="stop_album_action")
            self._app.add_action(stop_album_action)
            stop_album_action.connect('activate', self._stop_album)
            self.append(_("Stop after this album"), 'app.stop_album_action')
        if Lp.player.context.next != NextContext.STOP_ARTIST:
            stop_artist_action = Gio.SimpleAction(name="stop_artist_action")
            self._app.add_action(stop_artist_action)
            stop_artist_action.connect('activate', self._stop_artist)
            self.append(_("Stop after this artist"), 'app.stop_artist_action')

    def _continue_playback(self, action, variant):
        """
            Tell player to continue playback
            @param SimpleAction
            @param GVariant
            @param album id as int
        """
        Lp.player.context.next = NextContext.NONE

    def _stop_track(self, action, variant):
        """
            Tell player to stop after current track
            @param SimpleAction
            @param GVariant
        """
        Lp.player.context.next = NextContext.STOP_TRACK

    def _stop_album(self, action, variant):
        """
            Tell player to stop after current album
            @param SimpleAction
            @param GVariant
        """
        Lp.player.context.next = NextContext.STOP_ALBUM

    def _stop_artist(self, action, variant):
        """
            Tell player to stop after current artist
            @param SimpleAction
            @param GVariant
        """
        Lp.player.context.next = NextContext.STOP_ARTIST


class QueueMenu(BaseMenu):
    """
        Contextual menu for queue
    """

    def __init__(self, object_id, genre_id, is_album):
        """
            Init playlists menu
            @param object id as int
            @param genre id as int
            @param is album as bool
        """
        BaseMenu.__init__(self, object_id, genre_id, is_album)
        self._set_queue_actions()

#######################
# PRIVATE             #
#######################
    def _set_queue_actions(self):
        """
            Set queue actions
        """
        queue = Lp.player.get_queue()
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

            tracks = Lp.albums.get_tracks(self._object_id,
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

    def _append_to_queue(self, action, variant):
        """
            Append track to queue
            @param SimpleAction
            @param GVariant
        """
        if self._is_album:
            for track_id in Lp.albums.get_tracks(self._object_id,
                                                 self._genre_id):
                Lp.player.append_to_queue(track_id)
        else:
            Lp.player.append_to_queue(self._object_id)

    def _prepend_to_queue(self, action, variant):
        """
            Prepend track id to queue
            @param SimpleAction
            @param GVariant
        """
        if self._is_album:
            for track_id in reversed(Lp.albums.get_tracks(self._object_id,
                                                          self._genre_id)):
                Lp.player.prepend_to_queue(track_id)
        else:
            Lp.player.prepend_to_queue(self._object_id)

    def _del_from_queue(self, action, variant):
        """
            Delete track id from queue
            @param SimpleAction
            @param GVariant
        """
        if self._is_album:
            for track_id in Lp.albums.get_tracks(self._object_id,
                                                 self._genre_id):
                Lp.player.del_from_queue(track_id)
        else:
            Lp.player.del_from_queue(self._object_id)


class PlaylistsMenu(BaseMenu):
    """
        Contextual menu for playlists
    """

    def __init__(self, object_id, genre_id, is_album):
        """
            Init playlist menu
            @param object id as int
            @param genre id as int
            @param is album as bool
        """
        BaseMenu.__init__(self, object_id, genre_id, is_album)
        self._set_playlist_actions()

#######################
# PRIVATE             #
#######################
    def _set_playlist_actions(self):
        """
            Set playlist actions
        """
        playlist_action = Gio.SimpleAction(name="playlist_action")
        self._app.add_action(playlist_action)
        playlist_action.connect('activate',
                                self._add_to_playlists)
        self.append(_("Add to others"), 'app.playlist_action')

        i = 0
        for playlist in Lp.playlists.get_last():
            action = Gio.SimpleAction(name="playlist%s" % i)
            self._app.add_action(action)
            if self._is_album:
                exists = Lp.playlists.exists_album(playlist[0],
                                                   self._object_id,
                                                   self._genre_id)
            else:
                exists = Lp.playlists.exists_track(playlist[0],
                                                   self._object_id)
            if exists:
                action.connect('activate',
                               self._remove_from_playlist,
                               playlist[0])
                self.append(_("Remove from \"%s\"") % playlist[1],
                            "app.playlist%s" % i)
            else:
                action.connect('activate',
                               self._add_to_playlist,
                               playlist[0])
                self.append(_("Add to \"%s\"") % playlist[1],
                            "app.playlist%s" % i)
            i += 1

    def _add_to_playlists(self, action, variant):
        """
            Add to playlists
            @param SimpleAction
            @param GVariant
        """
        Lp.window.show_playlist_manager(self._object_id,
                                        self._genre_id,
                                        self._is_album)

    def _add_to_playlist(self, action, variant, playlist_id):
        """
            Add to playlist
            @param SimpleAction
            @param GVariant
            @param playlist id as int
        """
        def add(playlist_id):
            tracks = []
            if self._is_album:
                tracks_ids = Lp.albums.get_tracks(self._object_id,
                                                  self._genre_id)
                for track_id in tracks_ids:
                    tracks.append(Track(track_id))
            else:
                tracks = [Track(self._object_id)]
            Lp.playlists.add_tracks(playlist_id, tracks)
        t = Thread(target=add, args=(playlist_id,))
        t.daemon = True
        t.start()

    def _remove_from_playlist(self, action, variant, playlist_id):
        """
            Del from playlist
            @param SimpleAction
            @param GVariant
            @param object id as int
            @param is album as bool
            @param playlist id as int
        """
        def remove(playlist_id):
            tracks = []
            if self._is_album:
                tracks_ids = Lp.albums.get_tracks(self._object_id,
                                                  self._genre_id)
                for track_id in tracks_ids:
                    tracks.append(Track(track_id))
            else:
                tracks = [Track(self._object_id)]
            Lp.playlists.remove_tracks(playlist_id, tracks)
        t = Thread(target=remove, args=(playlist_id,))
        t.daemon = True
        t.start()

    def _add_to_loved(self, action, variant):
        """
            Add to loved
            @param SimpleAction
            @param GVariant
            @param playlist name as str
        """
        utils.set_loved(self._object_id, True)

    def _del_from_loved(self, action, variant):
        """
            Remove from loved
            @param SimpleAction
            @param GVariant
            @param playlist name as str
        """
        utils.set_loved(self._object_id, False)


class PopToolbarMenu(Gio.Menu):
    """
        Contextual menu for toolbar
    """

    def __init__(self, object_id, genre_id):
        """
            Init menu model
            @param object id as int
            @param genre id as int
        """
        Gio.Menu.__init__(self)
        if not Lp.player.is_party():
            self.insert_section(0, _("Playback"),
                                PlaybackMenu())
        self.insert_section(1, _("Playlists"),
                            PlaylistsMenu(object_id, genre_id, False))


class EditMenu(BaseMenu):
    """
        Edition menu for album
    """
    _TAG_EDITORS = ['exfalso', 'easytag', 'picard', 'puddletag', 'kid3-qt']

    def __init__(self, object_id, genre_id, is_album):
        """
            Init edit menu
            @param object id as int
            @param genre id as int
            @param is album as bool
        """
        BaseMenu.__init__(self, object_id, genre_id, is_album)

        if is_album:
            favorite = Lp.settings.get_value('tag-editor').get_string()
            for editor in [favorite] + self._TAG_EDITORS:
                if which(editor) is not None:
                    self._tag_editor = editor
                    self._set_edit_actions()
                    break

    def _set_edit_actions(self):
        """
            Set edit actions
        """
        edit_tag_action = Gio.SimpleAction(name="edit_tag_action")
        self._app.add_action(edit_tag_action)
        edit_tag_action.connect('activate',
                                self._edit_tag)
        self.append(_("Modify informations"), 'app.edit_tag_action')

    def _edit_tag(self, action, variant):
        """
            Run tag editor
            @param SimpleAction
            @param GVariant
        """
        album_path = Lp.albums.get_path(self._object_id)
        argv = [self._tag_editor, album_path, None]
        (s, pid, i, o, e) = GLib.spawn_async_with_pipes(
                                None, argv, None,
                                GLib.SpawnFlags.SEARCH_PATH |
                                GLib.SpawnFlags.DO_NOT_REAP_CHILD, None)
        GLib.child_watch_add(GLib.PRIORITY_DEFAULT_IDLE,
                             pid,
                             self._on_exit)

    def _on_exit(self, pid, status):
        """
            Update database
            @param pid as int
            @param status as int
        """
        if status == 0:
            Lp.window.update_db()


class AlbumMenu(Gio.Menu):
    """
        Contextual menu for album
    """

    def __init__(self, object_id, genre_id):
        """
            Init menu model
            @param object id as int
            @param genre id as int
        """
        Gio.Menu.__init__(self)
        self.insert_section(0, _("Queue"),
                            QueueMenu(object_id, genre_id, True))
        self.insert_section(1, _("Playlists"),
                            PlaylistsMenu(object_id, genre_id, True))
        self.insert_section(2, _("Edit"),
                            EditMenu(object_id, genre_id, True))


class TrackMenu(Gio.Menu):
    """
        Contextual menu for track
    """

    def __init__(self, object_id, genre_id):
        """
            Init menu model
            @param object id as int
            @param genre id as int
        """
        Gio.Menu.__init__(self)
        self.insert_section(0, _("Queue"),
                            QueueMenu(object_id, genre_id, False))
        self.insert_section(1, _("Playlists"),
                            PlaylistsMenu(object_id, genre_id, False))
