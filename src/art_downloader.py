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

from gi.repository import GLib, Gio, GdkPixbuf

from _thread import start_new_thread

from lollypop.define import Lp, ArtSize

class ArtDownloader:

    def __init__(self):
        self._albums_queue = []
        self._in_albums_download = False
    
    def download_album_art(self, album_id):
        """
            Download album artwork
            @param album id as int
        """
        if Gio.NetworkMonitor.get_default().get_network_available():
            album = Lp.albums.get_name(album_id)
            artist = Lp.albums.get_artist_name(album_id)
            self._albums_queue.append((artist, album))
            if not self._in_albums_download:
                start_new_thread(self._download_albums_art, ())

#######################
# PRIVATE             #
#######################

    def _download_albums_art(self):
        """
            Download albums artwork (from queue)
            @thread safe
        """
        self._in_albums_download = True
        sql = Lp.db.get_cursor()
        while self._albums_queue:
            (artist, album) = self._albums_queue.pop()
            pixbuf = self._get_album_art_itunes(artist, album)
            if pixbuf is None:
                pixbuf = self._get_album_art_lastfm(artist, album)
            if pixbuf is None:
                continue
            try:
                artist_id = Lp.artists.get_id(artist, sql)
                album_id = Lp.albums.get_id(album, artist_id, sql)
                # Compilation or album without album artist
                if album_id is None:
                    album_id = Lp.albums.get_compilation_id(album, sql)
                if album_id is not None:
                    Lp.art.save_album_art(pixbuf, album_id, sql)
                    Lp.art.clean_album_cache(album_id, sql)
                    GLib.idle_add(Lp.art.announce_cover_update, album_id)
            except Exception as e:
                print("ArtDownloader::_download_albums_art: %s" % e)
        self._in_albums_download = False
        sql.close()

    def _get_album_art_itunes(self, artist, album):
        """
            Get album artwork from itunes
            @param artist as string
            @param album as string
            @return pixbuf as GdkPixbuf.Pixbuf
            @tread safe
        """
        return None

    def _get_album_art_lastfm(self, artist, album):
        """
            Get album artwork from lastfm
            @param artist as string
            @param album as string
            @return pixbuf as GdkPixbuf.Pixbuf
            @tread safe
        """
        pixbuf = None
        if Lp.lastfm is not None:
            try:
                last_album = Lp.lastfm.get_album(artist, album)
                url = last_album.get_cover_image(4)
                if url is not None:
                    s = Gio.File.new_for_uri(url)
                    (status, data, tag) = s.load_contents()
                    if status:
                        stream = Gio.MemoryInputStream.new_from_data(data,
                                                                     None)
                        pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(
                                    stream, ArtSize.MONSTER,
                                    ArtSize.MONSTER,
                                    False,
                                    None)
            except Exception as e:
                print("ArtDownloader::_get_album_art_lasfm: %s" % e)
        return pixbuf
