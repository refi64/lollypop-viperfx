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

from lollypop.player_bin import BinPlayer
from lollypop.player_queue import QueuePlayer
from lollypop.player_linear import LinearPlayer
from lollypop.player_shuffle import ShufflePlayer
from lollypop.player_radio import RadioPlayer
from lollypop.player_externals import ExternalsPlayer
from lollypop.player_userplaylist import UserPlaylistPlayer
from lollypop.objects import Track
from lollypop.define import Lp, Type


class Player(BinPlayer, QueuePlayer, UserPlaylistPlayer, RadioPlayer,
             LinearPlayer, ShufflePlayer, ExternalsPlayer):
    """
        Player object used to manage playback and playlists
    """

    def __init__(self):
        """
            Init player
        """
        BinPlayer.__init__(self)
        QueuePlayer.__init__(self)
        LinearPlayer.__init__(self)
        ShufflePlayer.__init__(self)
        UserPlaylistPlayer.__init__(self)
        RadioPlayer.__init__(self)
        ExternalsPlayer.__init__(self)
        self.update_crossfading()

    def prev(self):
        """
            Play previous track
        """
        if self.prev_track.id is not None:
            self.load(self.prev_track, False)

    def next(self):
        """
            Play next track
        """
        if self.next_track.id is not None:
            self.load(self.next_track, False)

    def load(self, track, notify=True):
        """
            Stop current track, load track id and play it
            @param track as Track
            @param notify as bool
        """
        if track.id == Type.RADIOS:
            if not Lp().scanner.is_locked():
                Lp().window.pulse(False)
                Lp().window.pulse(True)
            RadioPlayer.load(self, track)
        else:
            BinPlayer.load(self, track, notify)

    def play_album(self, album):
        """
            Play album
            @param album as Album
        """
        # Empty user playlist
        self._user_playlist = []
        Lp().player.load(album.tracks[0])
        if not Lp().player.is_party():
            self._albums = [album.id]
            self.context.genre_ids = []

    def set_albums(self, track_id, artist_ids, genre_ids):
        """
            Set album list (for next/prev)
            @param track id as int
            @param artist id as int
            @param genre id as int
        """
        # Invalid track
        if track_id is None:
            return
        album = Track(track_id).album
        self._albums = []
        ShufflePlayer.reset_history(self)

        # We are not playing a user playlist anymore
        self._user_playlist = []
        self._user_playlist_id = None
        # We are in all artists
        if (genre_ids and genre_ids[0] == Type.ALL) or\
           (artist_ids and artist_ids[0] == Type.ALL):
            if artist_ids and artist_ids[0] != Type.ALL:
                self._albums += Lp().albums.get_ids(artist_ids, None)
            else:
                if Lp().settings.get_value('show-compilations'):
                    self._albums = Lp().albums.get_compilations()
                self._albums += Lp().albums.get_ids()
        # We are in populars view, add popular albums
        elif genre_ids and genre_ids[0] == Type.POPULARS:
            self._albums = Lp().albums.get_populars()
        # We are in recents view, add recent albums
        elif genre_ids and genre_ids[0] == Type.RECENTS:
            self._albums = Lp().albums.get_recents()
        # We are in randoms view, add random albums
        elif genre_ids and genre_ids[0] == Type.RANDOMS:
            self._albums = Lp().albums.get_cached_randoms()
        # We are in compilation view without genre
        elif genre_ids and genre_ids[0] == Type.COMPILATIONS:
            self._albums = Lp().albums.get_compilations()
        # Add albums for artists/genres
        else:
            self._albums += Lp().albums.get_ids(artist_ids, genre_ids)

        album.set_genre(genre_ids)
        if track_id in album.tracks_ids:
            self.context.artist_ids = artist_ids
            self.context.genre_ids = genre_ids
            # Shuffle album list if needed
            self._shuffle_albums()
        else:  # Error
            self.stop()

    def clear_albums(self):
        """
            Clear all albums
        """
        self._albums = []

    def get_current_artist(self):
        """
            Get current artist
            @return artist as string
        """
        artist_id = self.current_track.album_artist_id
        if artist_id == Type.COMPILATIONS:
            artist = self.current_track.artist
        else:
            artist = self.current_track.album_artist
        return artist

    def restore_state(self):
        """
            Restore player state
        """
        track_id = Lp().settings.get_value('track-id').get_int32()
        if Lp().settings.get_value('save-state') and track_id > 0:
            path = Lp().tracks.get_path(track_id)
            if path != "":
                self._load_track(Track(track_id))
                self.set_albums(track_id, [Type.ALL], [Type.ALL])
                self.set_next()
                self.set_prev()
                self.emit('current-changed')
            else:
                print("Player::restore_state(): track missing")

    def set_party(self, party):
        """
            Set party mode on if party is True
            Play a new random track if not already playing
            @param party as bool
        """
        ShufflePlayer.set_party(self, party)
        self.set_next()
        self.set_prev()
        self.update_crossfading()

    def set_prev(self):
        """
            Set previous track
        """
        # Look at externals
        self.prev_track = ExternalsPlayer.prev(self)

        # Look at radio
        if self.prev_track.id is None:
            self.prev_track = RadioPlayer.prev(self)

        # Look at user playlist then
        if self.prev_track.id is None:
            self.prev_track = UserPlaylistPlayer.prev(self)

        # Look at shuffle
        if self.prev_track.id is None:
            self.prev_track = ShufflePlayer.prev(self)

        # Get a linear track then
        if self.prev_track.id is None:
            self.prev_track = LinearPlayer.prev(self)
        self.emit('prev-changed')

    def set_next(self):
        """
            Play next track
            @param sql as sqlite cursor
        """
        # Look at externals
        self.next_track = ExternalsPlayer.next(self)

        # Look at radio
        if self.next_track.id is None:
            self.next_track = RadioPlayer.next(self)

        # Look first at user queue
        if self.next_track.id is None:
            self.next_track = QueuePlayer.next(self)
            if self.next_track.id is not None:
                self.context.next_track = LinearPlayer.next(self)

        # Look at user playlist then
        if self.next_track.id is None:
            self.next_track = UserPlaylistPlayer.next(self)

        # Get a random album/track then
        if self.next_track.id is None:
            self.next_track = ShufflePlayer.next(self)

        # Get a linear track then
        if self.next_track.id is None:
            if self.context.next_track is not None:
                self.next_track = self.context.next_track
                self.context.next_track = None
            else:
                self.next_track = LinearPlayer.next(self)
        self.emit('next-changed')

    def update_crossfading(self):
        """
            Calculate if crossfading is needed
        """
        mix = Lp().settings.get_value('mix')
        party_mix = Lp().settings.get_value('party-mix')
        self._crossfading = (mix and not party_mix) or\
                            (party_mix and self._is_party)

#######################
# PRIVATE             #
#######################
    def _on_stream_start(self, bus, message):
        """
            On stream start, set next and previous track
        """
        if not Lp().scanner.is_locked():
            Lp().window.pulse(False)
        if self.current_track.id >= 0:
            ShufflePlayer._on_stream_start(self, bus, message)
        if self._queue and self.current_track.id == self._queue[0]:
            self._queue.pop(0)
            self.emit("queue-changed")
        self.set_next()
        self.set_prev()
        BinPlayer._on_stream_start(self, bus, message)
