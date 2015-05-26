#!/usr/bin/python
# Copyright (c) 2014-2015 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# Copyright (c) 2013 Vadim Rutkovsky <vrutkovs@redhat.com>
# Copyright (c) 2013 Arnel A. Borja <kyoushuu@yahoo.com>
# Copyright (c) 2013 Seif Lotfy <seif@lotfy.com>
# Copyright (c) 2013 Guillaume Quintard <guillaume.quintard@gmail.com>
# Copyright (c) 2013 Lubosz Sarnecki <lubosz@gmail.com>
# Copyright (c) 2013 Sai Suman Prayaga <suman.sai14@gmail.com>
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

from gi.repository import GLib, GdkPixbuf, Gio, Gst

import re
import os

from lollypop.art_base import BaseArt
from lollypop.define import Lp


# Manager album artwork
class AlbumArt(BaseArt):
    _MIMES = ["jpeg", "jpg", "png", "gif"]
    """
        Init radio art
    """
    def __init__(self):
        BaseArt.__init__(self)
        self._favorite = Lp.settings.get_value('favorite-cover').get_string()
        if not os.path.exists(self._CACHE_PATH):
            try:
                os.mkdir(self._CACHE_PATH)
            except:
                print("Can't create %s" % self._CACHE_PATH)

    """
        get cover cache path for album_id
        @param album id as int, size as int
        @return cover path as string or None if no cover
    """
    def get_album_cache_path(self, album_id, size):
        filename = ''
        try:
            filename = self._get_album_cache_name(album_id)
            cache_path_jpg = "%s/%s_%s.jpg" % (self._CACHE_PATH,
                                               filename,
                                               size)
            if os.path.exists(cache_path_jpg):
                return cache_path_jpg
            else:
                self.get_album(album_id, size)
                if os.path.exists(cache_path_jpg):
                    return cache_path_jpg
                else:
                    return None
        except Exception as e:
            print("Art::get_album_cache_path(): %s" % e, ascii(filename))
            return None

   
    """
        Look for covers in dir:
        - favorite from settings first
        - Artist_Album.jpg then
        - Any image else
        any supported image otherwise
        @param album id as int
        @return cover file path as string
    """
    def get_album_art_path(self, album_id, sql=None):
        if album_id is None:
            return None
        album_path = Lp.albums.get_path(album_id, sql)
        album_name = Lp.albums.get_name(album_id, sql)
        artist_name = Lp.albums.get_artist_name(album_id, sql)
        try:
            if os.path.exists(album_path + "/" + self._favorite):
                return album_path + "/" + self._favorite
            # Used when having muliple albums in same folder
            elif os.path.exists(album_path + "/" + artist_name +
                                "_" + album_name + ".jpg"):
                return album_path + "/" +\
                       artist_name + "_" + album_name + ".jpg"

            for file in os.listdir(album_path):
                lowername = file.lower()
                supported = False
                for mime in self._MIMES:
                    if lowername.endswith(mime):
                        supported = True
                        break
                if (supported):
                    return "%s/%s" % (album_path, file)

            return None
        except Exception as e:
            print("Art::get_album_art_path(): %s" % e)

    """
        Get locally available covers for album
        Ignore favorite cover
        @param album_id as int
        @return [uri]
    """
    def get_locally_available_covers(self, album_id, sql=None):
        album_path = Lp.albums.get_path(album_id, sql)
        files = []
        for file in os.listdir(album_path):
            lowername = file.lower()
            supported = False
            for mime in self._MIMES:
                if lowername.endswith(mime):
                    supported = True
                    break
            if (supported and file != self._favorite):
                files.append("%s/%s" % (album_path, file))
        return files

    """
        Return a pixbuf with borders for uri
        No cache usage
        @param uri as string
        @param size as int
        @param selected as bool
        @return Gdk.Pixbuf
    """
    def get_cover_for_uri(self, uri, size, selected):
        pixbuf = self._pixbuf_from_tags(GLib.filename_from_uri(uri)[0], size)
        if pixbuf is not None:
            return self._make_icon_frame(pixbuf, selected)
        else:
            return self._make_icon_frame(self._get_default_icon(
                                                    size,
                                                    'folder-music-symbolic'),
                                         selected)

    """
        Return a pixbuf for album_id, covers are cached as jpg.
        @param album id as int
        @param pixbuf size as int
        @param selected as bool
        return: Gdk.Pixbuf
    """
    def get_album(self, album_id, size, selected=False):
        filename = self._get_album_cache_name(album_id)
        cache_path_jpg = "%s/%s_%s.jpg" % (self._CACHE_PATH, filename, size)
        pixbuf = None

        try:
            # Look in cache
            if os.path.exists(cache_path_jpg):
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(cache_path_jpg,
                                                                size,
                                                                size)
            else:
                path = self.get_album_art_path(album_id)
                # Look in album folder
                if path is not None:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path,
                                                                     size,
                                                                     size,
                                                                     False)
                # Try to get from tags
                else:
                    try:
                        tracks = Lp.albums.get_tracks(album_id, None)
                        if tracks:
                            filepath = Lp.tracks.get_path(tracks[0])
                            pixbuf = self._pixbuf_from_tags(filepath, size)
                    except Exception as e:
                        print(e)
                        return self._make_icon_frame(
                                            self._get_default_icon(
                                                    size,
                                                    'folder-music-symbolic'),
                                            selected)
                # No cover, use default one
                if pixbuf is None:
                    if Lp.lastfm is not None:
                        Lp.lastfm.download_album_img(album_id)
                    pixbuf = self._get_default_icon(size,
                                                    'folder-music-symbolic')
                else:
                    # Gdk < 3.15 was missing save method
                    # > 3.15 is missing savev method
                    try:
                        pixbuf.save(cache_path_jpg, "jpeg",
                                    ["quality"], ["90"])
                    except:
                        pixbuf.savev(cache_path_jpg, "jpeg",
                                     ["quality"], ["90"])

            return self._make_icon_frame(pixbuf, selected)

        except Exception as e:
            print(e)
            return self._make_icon_frame(self._get_default_icon(
                                                    size,
                                                    'folder-music-symbolic'),
                                         selected)

    """
        Save pixbuf for album id
        @param pixbuf as Gdk.Pixbuf
        @param album id as int
    """
    def save_album_art(self, pixbuf, album_id):
        try:
            artpath = self.get_album_art_filepath(album_id)
            # Gdk < 3.15 was missing save method
            try:
                pixbuf.save(artpath, "jpeg", ["quality"], ["90"])
            # > 3.15 is missing savev method :(
            except:
                pixbuf.savev(artpath, "jpeg", ["quality"], ["90"])
        except Exception as e:
            print("Art::save_album_art(): %s" % e)

    """
        Get album art filepath
        @param album_id as int
        @param sql as sqlite cursor
        @thread safe
    """
    def get_album_art_filepath(self, album_id, sql=None):
        album_path = Lp.albums.get_path(album_id, sql)
        path_count = Lp.albums.get_path_count(album_path, sql)
        album_name = Lp.albums.get_name(album_id, sql)
        artist_name = Lp.albums.get_artist_name(album_id, sql)
        # Many albums with same path, suffix with artist_album name
        if path_count > 1:
            artpath = album_path + "/" +\
                      artist_name + "_" +\
                      album_name + ".jpg"
            if os.path.exists(album_path+"/"+self._favorite):
                os.remove(album_path+"/"+self._favorite)
        else:
            artpath = album_path + "/" + self._favorite
        return artpath

    """
        Announce album cover update
        @param album id as int
    """
    def announce_cover_update(self, album_id):
        self.emit('cover-changed', album_id)

    """
        Remove cover from cache for album id
        @param album id as int
        @param sql as sqlite cursor
    """
    def clean_album_cache(self, album_id, sql=None):
        filename = self._get_album_cache_name(album_id, sql)
        try:
            for f in os.listdir(self._CACHE_PATH):
                if re.search('%s_.*\.jpg' % re.escape(filename), f):
                    os.remove(os.path.join(self._CACHE_PATH, f))
        except Exception as e:
            print("Art::clean_album_cache(): ", e, filename)

#######################
# PRIVATE             #
#######################
    """
        Return cover from tags
        @param filepath as str
        @param size as int
    """
    def _pixbuf_from_tags(self, filepath, size):
        pixbuf = None
        infos = self.get_infos(filepath)
        exist = False
        if infos is not None:
            (exist, sample) = infos.get_tags().get_sample_index('image', 0)
        if exist:
            (exist, mapflags) = sample.get_buffer().map(Gst.MapFlags.READ)
        if exist:
            stream = Gio.MemoryInputStream.new_from_data(mapflags.data,
                                                         None)
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(stream,
                                                               size,
                                                               size,
                                                               False,
                                                               None)
        return pixbuf

    """
        Get a uniq string for album
        @param album id as int
        @param sql as sqlite cursor
    """
    def _get_album_cache_name(self, album_id, sql=None):
        path = Lp.albums.get_name(album_id, sql) + "_" + \
               Lp.albums.get_artist_name(album_id, sql)
        return path[0:240].replace("/", "_")
