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

from gi.repository import GLib, GObject

import os
from gettext import gettext as _
from stat import S_ISREG, ST_MTIME, ST_MODE

from lollypop.define import Lp


# A cached playlist
class Playlist:

    def __init__(self, index):
        """
            Init playlist
            @param index as int
        """
        self._cache = []
        self._index = index

    def get_index(self):
        """
            Get playlist index
            @return index as int
        """
        return self._index

    def add_track(self, track):
        """
            Add track to playlist
            @param track as str
        """
        self._cache.append(track)

    def remove_track(self, track):
        """
            Remove track from playlist
            @param track as str
        """
        self._cache.remove(track)

    def set_tracks(self, tracks):
        """
            Set playlist's tracks
            @param array of str
        """
        self._cache = tracks

    def get_tracks(self):
        """
            Return playlist's tracks
            @return array of str
        """
        return self._cache

    def reset_tracks(self):
        """
            Set playlist tracks
        """
        self._cache = []


# Manager user playlists
class PlaylistsManager(GObject.GObject):
    """
        Playlists manager
    """
    _PLAYLISTS_PATH = os.path.expanduser("~") +\
        "/.local/share/lollypop/playlists"
    __gsignals__ = {
        # Add or remove a playlist
        'playlists-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        # Objects added/removed to/from playlist
        'playlist-changed': (GObject.SignalFlags.RUN_FIRST, None, (str,))
    }

    def __init__(self):
        """
            Init playlists manager
        """
        GObject.GObject.__init__(self)
        self._LOVED = _("Loved tracks")
        self._index = 0
        self._playlists = {}
        # Create playlists directory if missing
        if not os.path.exists(self._PLAYLISTS_PATH):
            try:
                os.mkdir(self._PLAYLISTS_PATH)
            except Exception as e:
                print("Lollypop::PlaylistsManager::init: %s" % e)
        self._init_playlists()

    def add(self, playlist_name):
        """
            Add a playlist, erase current
            @param playlist name as str
            @thread safe
        """
        filename = self._PLAYLISTS_PATH + "/" + playlist_name + ".m3u"
        try:
            if not os.path.exists(filename):
                f = open(filename, "w")
                f.write("#EXTM3U\n")
                f.close()
                self._index += 1
                self._playlists[playlist_name] = Playlist(self._index)
                GLib.idle_add(self.emit, 'playlists-changed')
        except Exception as e:
            print("PlaylistsManager::add: %s" % e)

    def exists(self, playlist_name):
        """
            Return True if playlist exist
            @param playlist name as string
            @param exist as bool
        """
        return playlist_name in self._playlists

    def rename(self, new_name, old_name):
        """
            Rename playlist (Thread safe)
            @param new playlist name as str
            @param old playlist name as str
        """
        try:
            os.rename(self._PLAYLISTS_PATH+"/"+old_name+".m3u",
                      self._PLAYLISTS_PATH+"/"+new_name+".m3u")
            self._playlists[new_name] = self._playlists[old_name]
            del self._playlists[old_name]
            GLib.idle_add(self.emit, "playlists-changed")
        except Exception as e:
            print("PlaylistsManager::rename: %s" % e)

    def delete(self, playlist_name):
        """
            delete playlist (Thread safe)
            @param playlist name as str
        """
        try:
            os.remove(self._PLAYLISTS_PATH+"/"+playlist_name+".m3u")
            del self._playlists[playlist_name]
            GLib.idle_add(self.emit, "playlists-changed")
        except Exception as e:
            print("PlaylistsManager::delete: %s" % e)

    def get(self):
        """
            Return availables playlists
            @return array of (id, string)
        """
        playlists = []
        for item in sorted(self._playlists.items()):
            playlists.append((item[1].get_index(), item[0]))
        return playlists

    def get_last(self):
        """
            Return 6 last modified playlist
            @return [string]
        """
        playlists = []
        try:
            index = 0
            entries = []
            for filename in os.listdir(self._PLAYLISTS_PATH):
                stat = os.stat(self._PLAYLISTS_PATH+"/"+filename)
                if S_ISREG(stat[ST_MODE]):
                    entries.append((stat[ST_MTIME], filename))
            for cdate, filename in sorted(entries, reverse=True):
                if filename.endswith(".m3u") and\
                   filename != self._LOVED+".m3u":
                    playlists.append(filename[:-4])
                    index += 1
                    # Break if 6 playlists is reached
                    if index >= 6:
                        break
        except Exception as e:
            print("Lollypop::PlaylistManager::get_last: %s" % e)
        return playlists

    def get_tracks(self, playlist_name):
        """
            Return availables tracks for playlist
            @param playlist playlist_name as str
            @return array of track filepath as str
        """
        try:
            tracks = self._playlists[playlist_name].get_tracks()
            if tracks:
                return tracks

            f = open(self._PLAYLISTS_PATH+"/"+playlist_name+".m3u", "r")
            for filepath in f:
                if filepath[0] not in ["#", "\n"]:
                    tracks.append(filepath[:-1])
            f.close()
        except Exception as e:
            print("PlaylistsManager::get_tracks: %s" % e)
        self._playlists[playlist_name].set_tracks(tracks)
        return tracks

    def set_tracks(self, playlist_name, tracks_path):
        """
            Set playlist tracks (Thread safe)
            @param playlist name as str
            @param tracks path as [str]
        """
        f = open(self._PLAYLISTS_PATH+"/"+playlist_name+".m3u", "w")
        f.write("#EXTM3U\n")
        self._playlists[playlist_name].reset_tracks()
        for filepath in tracks_path:
            self._add_track(f, playlist_name, filepath)
        GLib.timeout_add(1000, self.emit, "playlist-changed", playlist_name)
        try:
            f.close()
        except Exception as e:
            print("PlaylistsManager::set_tracks: %s" % e)

    def get_tracks_id(self, playlist_name, sql=None):
        """
            Return availables tracks id for playlist
            Thread safe if you pass an sql cursor
            @param playlist name as str
            @return array of track id as int
        """
        tracks_id = []
        for filepath in self.get_tracks(playlist_name):
            tracks_id.append(Lp.tracks.get_id_by_path(filepath, sql))
        return tracks_id

    def add_track(self, playlist_name, filepath):
        """
            Add track to playlist if not already present
            @param playlist name as str
            @param track filepath as str
        """
        try:
            f = open(self._PLAYLISTS_PATH+"/"+playlist_name+".m3u", "a")
            self._add_track(f, playlist_name, filepath)
            GLib.idle_add(self.emit, "playlist-changed", playlist_name)
            f.close()
        except Exception as e:
            print("PlaylistsManager::add_track: %s" % e)

    def add_tracks(self, playlist_name, tracks_path):
        """
            Add tracks to playlist if not already present
            @param playlist name as str
            @param tracks filepath as [str]
        """
        try:
            f = open(self._PLAYLISTS_PATH+"/"+playlist_name+".m3u", "a")
            for filepath in tracks_path:
                self._add_track(f, playlist_name, filepath)
            GLib.idle_add(self.emit, "playlist-changed", playlist_name)
            f.close()
        except Exception as e:
            print("PlaylistsManager::add_tracks: %s" % e)

    def remove_tracks(self, playlist_name, tracks_to_remove):
        """
            Remove tracks from playlist
            @param playlist name as str
            @param tracks to remove as [str]
        """
        playlist_tracks = self.get_tracks(playlist_name)
        self._remove_tracks(playlist_name, playlist_tracks, tracks_to_remove)
        GLib.idle_add(self.emit, "playlist-changed", playlist_name)

    def is_present(self, playlist_name, object_id,
                   genre_id, is_album, sql=None):
        """
            Return True if object_id is already present in playlist
            @param playlist name as str
            @param object id as int
            @param genre id as int
            @param is an album as bool
            @param sql as sqlite cursor
            @return bool
        """
        playlist_paths = self.get_tracks(playlist_name)
        if is_album:
            tracks_path = Lp.albums.get_tracks_path(object_id,
                                                    genre_id,
                                                    sql)
        else:
            tracks_path = [Lp.tracks.get_path(object_id, sql)]

        found = 0
        len_tracks = len(tracks_path)
        for filepath in tracks_path:
            if filepath in playlist_paths:
                found += 1
                if found >= len_tracks:
                    break
        if found == len_tracks:
            return True
        else:
            return False

#######################
# PRIVATE             #
#######################
    def _init_playlists(self):
        """
            Create initial index
        """
        try:
            for filename in sorted(os.listdir(self._PLAYLISTS_PATH)):
                if filename.endswith(".m3u"):
                    self._playlists[filename[:-4]] = Playlist(self._index)
                    self._index += 1
        except Exception as e:
            print("Lollypop::PlaylistManager::get: %s" % e)

    def _add_track(self, f, playlist_name, filepath):
        """
            Add track to playlist if not already present
            @param f as file descriptor
            @param playlist name as str
            @param track filepath as str
        """
        tracks = self.get_tracks(playlist_name)
        # Do nothing if uri already present in playlist
        if filepath not in tracks:
            try:
                f.write(filepath+'\n')
                self._playlists[playlist_name].add_track(filepath)
            except Exception as e:
                print("PlaylistsManager::_add_track: %s" % e)

    def _remove_tracks(self, playlist_name, playlist_tracks, tracks_to_remove):
        """
            Remove track from playlist
            @param playlist name as str
            @param playlist tracks as [str]
            @param tracks to remove as [str]
        """
        try:
            f = open(self._PLAYLISTS_PATH+"/"+playlist_name+".m3u", "w")
            for path in playlist_tracks:
                if path not in tracks_to_remove:
                    f.write(path+'\n')
                    self._playlists[playlist_name].remove_track(path)
            f.close()
        except Exception as e:
            print("PlaylistsManager::remove_tracks: %s" % e)


class RadiosManager(PlaylistsManager):
    """
        Radios manager
    """
    _PLAYLISTS_PATH = os.path.expanduser("~") + "/.local/share/lollypop/radios"

    def __init__(self):
        """
            Init radio manager
        """
        PlaylistsManager.__init__(self)
