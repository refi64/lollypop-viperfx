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

from gi.repository import GLib, Gst

import socketserver
import threading
from time import sleep
from datetime import datetime
import re

from lollypop.define import Lp, Type
from lollypop.objects import Track, Album
from lollypop.database_mpd import MpdDatabase
from lollypop.utils import translate_artist_name, format_artist_name


class MpdHandler(socketserver.BaseRequestHandler):
    idle = None

    def handle(self):
        """
            One function to handle them all
        """
        self._mpddb = MpdDatabase()
        self._playlist_version = 0
        self._idle_strings = []
        self._current_song = None
        self._signal1 = Lp().player.connect('current-changed',
                                            self._on_player_changed)
        self._signal2 = Lp().player.connect('status-changed',
                                            self._on_player_changed)
        self._signal3 = Lp().player.connect('seeked',
                                            self._on_player_changed)
        self._signal4 = Lp().playlists.connect('playlist-changed',
                                               self._on_playlist_changed)
        self.request.send("OK MPD 0.19.0\n".encode('utf-8'))
        try:
            while self.server.running:
                data = self.request.recv(4096).decode('utf-8')
                # We check if we need to wait for a command_list_end
                list_begin = data.startswith('command_list_begin') or\
                    data.startswith('command_list_ok_begin')
                list_ok = data.startswith('command_list_ok_begin')
                # Check for list_ok
                list_end = data.endswith('command_list_end\n')
                if list_end:
                    data = data.replace('command_list_end\n', '')
                    list_begin = False
                while list_begin:
                    data += self.request.recv(1024).decode('utf-8')
                    if data.endswith('command_list_end\n'):
                        list_begin = False
                if data == '':
                    raise IOError
                else:
                    data = data.replace('command_list_begin\n', '')
                    data = data.replace('command_list_ok_begin\n', '')
                    data = data.replace('command_list_end\n', '')
                    cmds = data.split('\n')
                    print(cmds)
                    if cmds and self.server.running:
                        try:
                            # Group commands
                            cmd_dict = {}
                            for cmd in cmds:
                                if cmd != '':
                                    command = cmd.split(' ')[0]
                                    size = len(command) + 1
                                    if command not in cmd_dict:
                                        cmd_dict[command] = []
                                    cmd_dict[command].append(cmd[size:])
                            for key in cmd_dict.keys():
                                if key.find("idle") == -1:
                                    self._noidle(None, None)
                                call = getattr(self, '_%s' % key)
                                call(cmd_dict[key], list_ok)
                            if list_ok:
                                self._send_msg('', False)
                        except Exception as e:
                            print("MpdHandler::handle(): ", command, e)
                            self._send_msg('', list_ok)
        except:
            self._noidle(None, None)
        Lp().player.disconnect(self._signal1)
        Lp().player.disconnect(self._signal2)
        Lp().player.disconnect(self._signal3)
        Lp().playlists.disconnect(self._signal4)

    def _add(self, args_array, list_ok):
        """
            Add track to mpd playlist
            @param args as [str]
            @param add list_OK as bool
        """
        tracks = []
        for args in args_array:
            arg = self._get_args(args)
            track_id = Lp().tracks.get_id_by_path(arg[0])
            if track_id is None:
                splited = arg[0].split("/")
                print(splited)
                # Genre and artist
                if len(splited) < 3:
                    genre_id = Lp().genres.get_id(splited[0])
                    try:
                        artist_id = Lp().artists.get_id(splited[1])
                    except:
                        artist_id = None
                    print(artist_id, genre_id)
                    for album_id in Lp().albums.get_ids(artist_id, genre_id):
                        for track_id in Lp().albums.get_tracks(album_id,
                                                               genre_id):
                            tracks.append(Track(track_id))
                # Album or track
                else:
                    genre_id = Lp().genres.get_id(splited[0])
                    artist_id = Lp().artists.get_id(splited[1])
                    # Get year
                    try:
                        date = re.search('\([0-9]*\)', splited[2]).group(0)
                        name = splited[2].replace(' '+date, '', 1)
                    except:
                        date = ''
                        name = splited[2]
                    try:
                        year = int(date[1:-1])
                    except:
                        year = None
                    album_id = Lp().albums.get_id(name, artist_id, year)
                    if len(splited) == 4:
                        track_id = Lp().tracks.get_id_by(splited[3], album_id)
                        tracks.append(Track(track_id))
                    else:
                        for track_id in Lp().albums.get_tracks(album_id,
                                                               genre_id):
                            tracks.append(Track(track_id))
            else:
                tracks.append(Track(track_id))
        Lp().playlists.add_tracks(Type.MPD, tracks)
        self._send_msg('', list_ok)

    def _clear(self, args_array, list_ok):
        """
            Clear mpd playlist
            @param args as [str]
            @param add list_OK as bool
        """
        Lp().playlists.clear(Type.MPD, True)
        self._send_msg('', list_ok)

    def _channels(self, args_array, list_ok):
        self._send_msg('', list_ok)

    def _commands(self, args_array, list_ok):
        """
            Send available commands
            @param args as [str]
            @param add list_OK as bool
        """
        msg = "command: add\ncommand: clear\ncommand: channels\ncommand: count\
\ncommand: currentsong\ncommand: delete\ncommand: idle\ncommand: noidle\
\ncommand: list\ncommand: listallinfo\ncommand: listplaylists\ncommand: lsinfo\
\ncommand: next\ncommand: outputs\ncommand: pause\ncommand: play\
\ncommand: playid\ncommand: playlistinfo\ncommand: plchanges\
\ncommand: plchangesposid\ncommand: prev\ncommand: replay_gain_status\
\ncommand: repeat\ncommand: seek\ncommand: seekid\ncommand: search\
\ncommand: setvol\ncommand: stats\ncommand: status\ncommand: sticker\
\ncommand: stop\ncommand: tagtypes\ncommand: update\ncommand: urlhandlers\n"
        self._send_msg(msg, list_ok)

    def _count(self, args_array, list_ok):
        """
            Send lollypop current song
            @param args as [str]
            @param add list_OK as bool
        """
        args = self._get_args(args_array[0])
        # Search for filters
        i = 0
        artist = artist_id = year = album = genre = genre_id = None
        while i < len(args) - 1:
            if args[i].lower() == 'album':
                album = args[i+1]
            elif args[i].lower() == 'artist':
                artist = format_artist_name(args[i+1])
            elif args[i].lower() == 'genre':
                genre = args[i+1]
            elif args[i].lower() == 'date':
                date = args[i+1]
            i += 2

        # Artist have albums with different dates so
        # we do not want None in year
        if artist_id is not None or album is not None:
            try:
                year = int(date)
            except:
                year = None
        else:
            year = Type.NONE

        if genre is not None:
            genre_id = Lp().genres.get_id(genre)
        if artist is not None:
            artist_id = Lp().artists.get_id(artist)

        (songs, playtime) = self._mpddb.count(album, artist_id,
                                              genre_id, year)
        msg = "songs: %s\nplaytime: %s\n" % (songs, playtime)
        self._send_msg(msg, list_ok)

    def _currentsong(self, args_array, list_ok):
        """
            Send lollypop current song
            @param args as [str]
            @param add list_OK as bool
        """
        if self._current_song is None:
            self._current_song = self._string_for_track_id(
                                                  Lp().player.current_track.id)
        msg = self._current_song
        self._send_msg(msg, list_ok)

    def _delete(self, args_array, list_ok):
        """
            Delete track from playlist
            @param args as [str]
            @param add list_OK as bool
        """
        for args in args_array:
            tracks = []
            for track_id in Lp().playlists.get_tracks_ids(Type.MPD):
                tracks.append(Track(track_id))
            del tracks[self._get_args(args)[0]]
            Lp().playlists.clear(Type.MPD, False)
            Lp().playlists.add_tracks(Type.MPD, tracks)

    def _idle(self, args_array, list_ok):
        msg = ''
        self.request.settimeout(0)
        MpdHandler.idle = self
        while not self._idle_strings and\
                MpdHandler.idle == self and\
                self.server.running:
            print('IDLE', MpdHandler.idle, self, self._idle_strings)
            sleep(1)
        if MpdHandler.idle == self:
            for string in self._idle_strings:
                msg += "changed: %s\n" % string
            self._idle_strings = []
        self._send_msg(msg, list_ok)
        self.request.settimeout(10)

    def _noidle(self, args_array, list_ok):
        MpdHandler.idle = None

    def _list(self, args_array, list_ok):
        """
            List objects
            @param args as [str]
            @param add list_OK as bool
        """
        msg = ""
        args = self._get_args(args_array[0])

        # Search for filters
        i = 1
        artist = artist_id = None
        album = None
        genre = genre_id = None
        date = ''
        while i < len(args) - 1:
            if args[i].lower() == 'album':
                album = args[i+1]
            elif args[i].lower() == 'artist':
                artist = format_artist_name(args[i+1])
            elif args[i].lower() == 'genre':
                genre = args[i+1]
            elif args[i].lower() == 'date':
                date = args[i+1]
            i += 2

        try:
            year = int(date)
        except:
            year = None
        if genre is not None:
            genre_id = Lp().genres.get_id(genre)
        if artist is not None:
            artist_id = Lp().artists.get_id(artist)

        if args[0].lower() == 'file':
            for path in self._mpddb.get_tracks_paths(album, artist_id,
                                                     genre_id, year):
                msg += "File: "+path+"\n"
        if args[0].lower() == 'album':
            for album in self._mpddb.get_albums_names(artist_id,
                                                      genre_id, year):
                msg += "Album: "+album+"\n"
        elif args[0].lower() == 'artist':
            for artist in self._mpddb.get_artists_names(genre_id):
                msg += "Artist: "+translate_artist_name(artist)+"\n"
        elif args[0].lower() == 'genre':
            results = Lp().genres.get_names()
            for name in results:
                msg += "Genre: "+name+"\n"
        elif args[0].lower() == 'date':
            for year in self._mpddb.get_albums_years(album, artist_id,
                                                     genre_id):
                msg += "Date: "+str(year)+"\n"
        self._send_msg(msg, list_ok)

    def _listall(self, args_array, list_ok):
        """
            List all tracks
            @param args as [str]
            @param add list_OK as bool
        """
        self._send_msg('', list_ok)

    def _listallinfo(self, args_array, list_ok):
        """
            List all tracks
            @param args as [str]
            @param add list_OK as bool
        """
        i = 0
        msg = ""
        for track_id in Lp().tracks.get_ids():
            msg += self._string_for_track_id(track_id)
            if i > 100:
                self.request.send(msg.encode("utf-8"))
                msg = ""
                i = 0
            else:
                i += 1
        self._send_msg(msg, list_ok)

    def _listplaylistinfo(self, args_array, list_ok):
        """
            List playlist informations
            @param args as [str]
            @param add list_OK as bool
        """
        arg = self._get_args(args_array[0])[0]
        playlist_id = Lp().playlists.get_id(arg)
        msg = ""
        for track_id in Lp().playlists.get_tracks_ids(playlist_id):
            msg += self._string_for_track_id(track_id)
        self._send_msg(msg, list_ok)

    def _listplaylists(self, args_array, list_ok):
        """
            Send available playlists
            @param args as [str]
            @param add list_OK as bool
        """
        dt = datetime.utcnow()
        dt = dt.replace(microsecond=0)
        msg = ""
        for (playlist_id, name) in Lp().playlists.get():
            msg += "playlist: %s\nLast-Modified: %s\n" % (
                                                      name,
                                                      '%sZ' % dt.isoformat())
        self._send_msg(msg, list_ok)

    def _load(self, args_array, list_ok):
        """
            Load playlist
            @param args as [str]
            @param add list_OK as bool
        """
        arg = self._get_args(args_array[0])[0]
        playlist_id = Lp().playlists.get_id(arg)
        tracks = []
        for track_id in Lp().playlists.get_tracks_ids(playlist_id):
            tracks.append(Track(track_id))
        Lp().playlists.add_tracks(Type.MPD, tracks)
        self._send_msg('', list_ok)

    def _lsinfo(self, args_array, list_ok):
        """
            List directories and files
            @param args as [str]
            @param add list_OK as bool
        """
        msg = ""
        args = self._get_args(args_array[0])

        if not args:
            arg = ""
        else:
            arg = args[0]
            if arg == "/":
                arg = ""
        directory = True
        if arg == "":
            results = Lp().genres.get()
        elif arg.count("/") == 0:
            genre_id = Lp().genres.get_id(arg)
            results = Lp().artists.get(genre_id)
        elif arg.count("/") == 1:
            splited = arg.split("/")
            genre_id = Lp().genres.get_id(splited[0])
            artist_id = Lp().artists.get_id(splited[1])
            results = []
            for album_id in Lp().albums.get_ids(artist_id, genre_id):
                album = Album(album_id)
                if album.year != '':
                    string = " (%s)" % album.year
                else:
                    string = ""
                results.append((album.id, album.name + string))
        elif arg.count("/") == 2:
            splited = arg.split("/")
            genre_id = Lp().genres.get_id(splited[0])
            artist_id = Lp().artists.get_id(splited[1])
            # Get year
            try:
                date = re.search('\([0-9]*\)', splited[2]).group(0)
            except:
                date = ''
            name = splited[2].replace(' '+date, '', 1)
            try:
                year = int(date[1:-1])
            except:
                year = None
            album_id = Lp().albums.get_id(name, artist_id, year)
            tracks_ids = Lp().albums.get_tracks(album_id, genre_id)
            directory = False

        i = 0
        if directory:
            for (rowid, item) in results:
                if arg:
                    msg += "directory: %s/%s\n" % (arg, item)
                else:
                    msg += "directory: %s\n" % item
                if i > 100:
                    self._send_msg(msg, list_ok)
                    msg = ""
                    i = 0
                i += 1
        else:
            for track_id in tracks_ids:
                track = Track(track_id)
                msg += "file: %s/%s\n" % (arg, track.title)
                if i > 100:
                    self._send_msg(msg, list_ok)
                    msg = ""
                    i = 0
                i += 1
        self._send_msg(msg, list_ok)

    def _next(self, args_array, list_ok):
        """
            Send output
            @param args as [str]
            @param add list_OK as bool
        """
        GLib.idle_add(Lp().player.next)
        self._send_msg('', list_ok)

    def _move(self, args_array, list_ok):
        """
            Move range in playlist
            @param args as [str]
            @param add list_OK as bool
        """
        # TODO implement range
        tracks_ids = Lp().playlists.get_tracks_ids(Type.MPD)
        for args in args_array:
            arg = self._get_args(args)
            orig = int(arg[0])
            dst = int(arg[1])
            track_id = tracks_ids[orig]
            del tracks_ids[orig]
            tracks_ids.insert(dst, track_id)

        Lp().playlists.clear(Type.MPD)
        tracks = []
        for track_id in tracks_ids:
            tracks.append(Track(track_id))
        Lp().playlists.add_tracks(Type.MPD, tracks)
        self._send_msg('', list_ok)

    def _moveid(self, args_array, list_ok):
        """
            Move id in playlist
            @param args as [str]
            @param add list_OK as bool
        """
        tracks_ids = Lp().playlists.get_tracks_ids(Type.MPD)
        for args in args_array:
            arg = self._get_args(args)
            track_id = int(arg[0])
            orig = tracks_ids.index(track_id)
            dst = int(arg[1])
            del tracks_ids[orig]
            tracks_ids.insert(dst, track_id)

        Lp().playlists.clear(Type.MPD)
        tracks = []
        for track_id in tracks_ids:
            tracks.append(Track(track_id))
        Lp().playlists.add_tracks(Type.MPD, tracks)
        self._send_msg('', list_ok)

    def _outputs(self, args_array, list_ok):
        """
            Send output
            @param args as [str]
            @param add list_OK as bool
        """
        msg = "outputid: 0\noutputname: null\noutputenabled: 1\n"
        self._send_msg(msg, list_ok)

    def _pause(self, args_array, list_ok):
        """
            Pause track
            @param args as [str]
            @param add list_OK as bool
        """
        try:
            args = self._get_args(args_array[0])
            if args[0] == "0":
                GLib.idle_add(Lp().player.play)
            else:
                GLib.idle_add(Lp().player.pause)
        except Exception as e:
            print("MpdHandler::_pause(): %s" % e)
        self._send_msg('', list_ok)

    def _play(self, args_array, list_ok):
        """
            Play track
            @param args as [str]
            @param add list_OK as bool
        """
        if Lp().player.get_user_playlist_id() != Type.MPD:
            Lp().player.set_user_playlist(Type.MPD)
        if self._get_status == 'stop':
            track_id = Lp().player.get_user_playlist()[0]
            GLib.idle_add(Lp().player.load_in_playlist, track_id)
        else:
            GLib.idle_add(Lp().player.play)
        self._send_msg('', list_ok)

    def _playid(self, args_array, list_ok):
        """
            Play track
            @param args as [str]
            @param add list_OK as bool
        """
        arg = int(self._get_args(args_array[0])[0])
        if Lp().player.get_user_playlist_id() != Type.MPD:
            Lp().player.set_user_playlist(Type.MPD)
        GLib.idle_add(Lp().player.load_in_playlist, arg)
        self._send_msg('', list_ok)

    def _playlistadd(self, args_array, list_ok):
        """
            Add a new playlist
        """
        args = self._get_args(args_array[0])
        playlist_id = Lp().playlists.get_id(args[0])
        tracks = []
        if not Lp().playlists.exists(playlist_id):
            Lp().playlists.add(args[0])
            playlist_id = Lp().playlists.get_id(args[0])
        for arg in args[1:]:
            track_id = Lp().tracks.get_id_by_path(arg)
            tracks.append(Track(track_id))
        if tracks:
            Lp().playlists.add_tracks(playlist_id, tracks)
        self._send_msg('', list_ok)

    def _playlistinfo(self, args_array, list_ok):
        """
            Send informations about playlists
            @param args as [str]
            @param add list_OK as bool
        """
        msg = ""
        tracks_ids = Lp().playlists.get_tracks_ids(Type.MPD)
        if Lp().player.is_playing() and\
           Lp().player.current_track.id not in tracks_ids:
            tracks_ids.insert(0, Lp().player.current_track.id)
        for track_id in tracks_ids:
            msg += self._string_for_track_id(track_id)
        self._send_msg(msg, list_ok)

    def _plchanges(self, args_array, list_ok):
        """
            Send informations about playlists
            @param args as [str]
            @param add list_OK as bool
        """
        i = 0
        msg = ""
        for track_id in Lp().playlists.get_tracks_ids(Type.MPD):
            msg += self._string_for_track_id(track_id)
            if i > 100:
                self.request.send(msg.encode("utf-8"))
                msg = ""
                i = 0
            else:
                i += 1
        self._send_msg(msg, list_ok)

    def _plchangesposid(self, args_array, list_ok):
        """
            Send informations about playlists
            @param args as [str]
            @param add list_OK as bool
        """
        self._send_msg('', list_ok)

    def _prev(self, args_array, list_ok):
        """
            Send output
            @param args as [str]
            @param add list_OK as bool
        """
        GLib.idle_add(Lp().player.prev)
        self._send_msg('', list_ok)

    def _replay_gain_status(self, args_array, list_ok):
        """
            Send output
            @param args as [str]
            @param add list_OK as bool
        """
        msg = "replay_gain_mode: off\n"
        self._send_msg(msg, list_ok)

    def _repeat(self, args_array, list_ok):
        """
            Ignore
            @param args as [str]
            @param add list_OK as bool
        """
        self._send_msg('', list_ok)

    def _seek(self, args_array, list_ok):
        """
           Seek current
           @param args as [str]
           @param add list_OK as bool
        """
        args = self._get_args(args_array[0])
        seek = int(args[1])
        GLib.idle_add(Lp().player.seek, seek)
        self._send_msg('', list_ok)

    def _seekid(self, args_array, list_ok):
        """
            Seek track id
            @param args as [str]
            @param add list_OK as bool
        """
        args = self._get_args(args_array[0])
        track_id = int(args[0])
        seek = int(args[1])
        if track_id == Lp().player.current_track.id:
            GLib.idle_add(Lp().player.seek, seek)
        self._send_msg('', list_ok)

    def _search(self, args_array, list_ok):
        """
            Send stats about db
            @param args as [str]
            @param add list_OK as bool
        """
        msg = ""
        args = self._get_args(args_array[0])
        # Search for filters
        i = 0
        artist = artist_id = None
        album = None
        genre = genre_id = None
        date = ''
        while i < len(args) - 1:
            if args[i].lower() == 'album':
                album = args[i+1]
            elif args[i].lower() == 'artist':
                artist = format_artist_name(args[i+1])
            elif args[i].lower() == 'genre':
                genre = args[i+1]
            elif args[i].lower() == 'date':
                date = args[i+1]
            i += 2

        try:
            year = int(date)
        except:
            year = None
        if genre is not None:
            genre_id = Lp().genres.get_id(genre)
        if artist is not None:
            artist_id = Lp().artists.get_id(artist)

        for track_id in self._mpddb.get_tracks_ids(album, artist_id,
                                                   genre_id, year):
            msg += self._string_for_track_id(track_id)
        self._send_msg(msg, list_ok)

    def _setvol(self, args_array, list_ok):
        """
            Send stats about db
            @param args as [str]
            @param add list_OK as bool
        """
        args = self._get_args(args_array[0])
        vol = float(args[0])
        Lp().player.set_volume(vol/100)
        self._send_msg('', list_ok)

    def _stats(self, args_array, list_ok):
        """
            Send stats about db
            @param args as [str]
            @param add list_OK as bool
        """
        artists = Lp().artists.count()
        albums = Lp().albums.count()
        tracks = Lp().tracks.count()
        msg = "artists: %s\nalbums: %s\nsongs: %s\nuptime: 0\
\nplaytime: 0\ndb_playtime: 0\ndb_update: 0\n" % \
            (artists, albums, tracks)
        self._send_msg(msg, list_ok)

    def _status(self, args_array, list_ok):
        """
            Send lollypop status
            @param args as [str]
            @param add list_OK as bool
        """
        if self._get_status() != 'stop':
            elapsed = Lp().player.get_position_in_track() / 1000000 / 60
            time = Lp().player.current_track.duration
            songid = Lp().player.current_track.id
        else:
            time = 0
            elapsed = 0
            songid = -1
        msg = "volume: %s\nrepeat: %s\nrandom: %s\
\nsingle: %s\nconsume: %s\nplaylist: %s\
\nplaylistlength: %s\nstate: %s\nsong: %s\
\nsongid: %s\ntime: %s:%s\nelapsed: %s\n" % (
           int(Lp().player.get_volume()*100),
           1,
           int(Lp().player.is_party()),
           1,
           1,
           self._playlist_version,
           len(Lp().playlists.get_tracks(Type.MPD)),
           self._get_status(),
           Lp().playlists.get_position(Type.MPD,
                                       Lp().player.current_track.id),
           songid,
           int(elapsed),
           time,
           elapsed)
        self._send_msg(msg, list_ok)

    def _sticker(self, args_array, list_ok):
        """
            Send stickers
            @param args as [str]
            @param add list_OK as bool
        """
        args = self._get_args(args_array[0])
        msg = ""
        if args[0].find("get song ") != -1 and\
                args[2].find("rating") != -1:
            track_id = Lp().tracks.get_id_by_path(args[1])
            track = Track(track_id)
            msg = "sticker: rating=%s\n" % int(track.get_popularity()*2)
        elif args[0].find("set song") != -1 and\
                args[2].find("rating") != -1:
            track_id = Lp().tracks.get_id_by_path(args[1])
            track = Track(track_id)
            track.set_popularity(int(args[3])/2)
        self._send_msg(msg, list_ok)

    def _stop(self, args_array, list_ok):
        """
            Stop player
            @param args as [str]
            @param add list_OK as bool
        """
        GLib.idle_add(Lp().player.stop)

    def _tagtypes(self, args_array, list_ok):
        """
            Send available tags
            @param args as [str]
            @param add list_OK as bool
        """
        msg = "tagtype: Artist\ntagtype: Album\ntagtype: Title\
\ntagtype: Track\ntagtype: Name\ntagtype: Genre\ntagtype: Date\
\ntagtype: Performer\ntagtype: Disc\n"
        self._send_msg(msg, list_ok)

    def _update(self, args_array, list_ok):
        """
            Update database
            @param args as [str]
            @param add list_OK as bool
        """
        Lp().window.update_db()
        self._send_msg('', list_ok)

    def _urlhandlers(self, args_array, list_ok):
        """
            Send url handlers
            @param args as [str]
            @param add list_OK as bool
        """
        msg = "handler: http\n"
        self._send_msg(msg, list_ok)

    def _string_for_track_id(self, track_id):
        """
            Get mpd protocol string for track id
            @param track id as int
            @return str
        """
        if track_id is None:
            msg = ""
        else:
            track = Track(track_id)
            msg = "file: %s\nArtist: %s\nAlbum: %s\nAlbumArtist: %s\
\nTitle: %s\nDate: %s\nGenre: %s\nTime: %s\nId: %s\nPos: %s\n" % (
                     track.path,
                     track.artist,
                     track.album.name,
                     track.album_artist,
                     track.name,
                     track.album.year,
                     track.genre,
                     track.duration,
                     track.id,
                     track.position)
        return msg

    def _get_status(self):
        """
            Player status
            @return str
        """
        state = Lp().player.get_status()
        if state == Gst.State.PLAYING:
            return 'play'
        elif state == Gst.State.PAUSED:
            return 'pause'
        else:
            return 'stop'

    def _get_args(self, args):
        """
            Get args from string
            @param args as str
            @return args as [str]
        """
        splited = args.split('"')
        ret = []
        for arg in splited:
            if len(arg.replace(' ', '')) == 0:
                continue
            ret.append(arg)
        return ret

    def _send_msg(self, msg, list_ok):
        """
            Send message to client
            @msg as string
            @param list ok as bool
        """
        if list_ok:
            msg += "list_OK\n"
        else:
            msg += "OK\n"
        self.request.send(msg.encode("utf-8"))
        print(msg.encode("utf-8"))

    def _on_player_changed(self, player, data=None):
        """
            Add player to idle
            @param player as Player
        """
        self._current_song = None
        self._idle_strings.append('player')

    def _on_playlist_changed(self, playlists, playlist_id):
        """
            Add playlist to idle if mpd
            @param playlists as Playlists
            @param playlist id as int
        """
        if playlist_id == Type.MPD:
            self._idle_strings.append('playlist')
            self._playlist_version += 1
        else:
            self._idle_strings.append('stored_playlist')


class MpdServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """
        Create a MPD server.
    """

    def __init__(self, port=6600):
        """
            Init server
        """
        socketserver.TCPServer.allow_reuse_address = True
        socketserver.TCPServer.__init__(self, ("", port), MpdHandler)

    def run(self):
        """
            Run MPD server in a blocking way.
        """
        self.serve_forever()


class MpdServerDaemon(MpdServer):
    """
        Create a deamonized MPD server
    """
    def __init__(self, port=6600):
        """
            Init daemon
        """
        MpdServer.__init__(self, port)
        self.running = True
        self.thread = threading.Thread(target=self.run)
        self.thread.setDaemon(True)
        self.thread.start()

    def quit(self):
        """
            Stop MPD server deamon
        """
        self.running = False
        self.shutdown()
        self.server_close()
