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

from gi.repository import Gio

from lollypop.objects import Album
from lollypop.define import App, Repeat

from random import shuffle


class SimilarsPlayer:
    """
        Manage playback when going to end
    """

    def __init__(self):
        """
            Init player
        """
        self.__cancellable = Gio.Cancellable()
        self.connect("next-changed", self.__on_next_changed)

#######################
# PRIVATE             #
#######################
    def __on_next_changed(self, player):
        """
            Add a new album if playback finished and wanted by user
        """
        # Check if we need to add a new album
        if App().settings.get_enum("repeat") == Repeat.AUTO and\
                player.next_track.id is None and\
                Gio.NetworkMonitor.get_default().get_network_available() and\
                player.current_track.artist_ids:
            artist_id = player.current_track.artist_ids[0]
            artist_name = App().artists.get_name(artist_id)
            App().spotify.get_artist_id(artist_name,
                                        self.__on_get_artist_id)

    def __on_get_artist_id(self, artist_id):
        """
            Get similars
            @param artist_id as str
        """
        if artist_id is None:
            return
        App().task_helper.run(App().spotify.get_similar_artists,
                              artist_id, self.__cancellable,
                              callback=(self.__on_similar_artists,))

    def __on_similar_artists(self, artists):
        """
            Add one album
            @param artists as [str]
        """
        shuffle(artists)
        for artist in artists:
            artist_id = App().artists.get_id(artist)
            # Get an album
            if artist_id is not None:
                album_ids = App().albums.get_ids([artist_id], [])
                if album_ids:
                    shuffle(album_ids)
                    self.add_album(Album(album_ids[0]))
                    break
