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

from gi.repository import Gtk, Gdk, GObject, GdkPixbuf, Gio, Gst
import cairo
import os
import re
import json
import urllib.request
import urllib.parse
from math import pi

from lollypop.tagreader import TagReader
from lollypop.define import Lp, ArtSize, GOOGLE_INC


# Manage album's arts
class Art(GObject.GObject, TagReader):

    _CACHE_PATH = os.path.expanduser("~") + "/.cache/lollypop"
    _RADIOS_PATH = os.path.expanduser("~") +\
                     "/.local/share/lollypop/radios"
    _mimes = ["jpeg", "jpg", "png", "gif"]
    __gsignals__ = {
        'cover-changed': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        'logo-changed' : (GObject.SignalFlags.RUN_FIRST, None, (str,))
    }
    """
        Create cache path
    """
    def __init__(self):
        GObject.GObject.__init__(self)
        TagReader.__init__(self)
        self._gtk_settings = Gtk.Settings.get_default()
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
            CACHE_PATH_JPG = "%s/%s_%s.jpg" % (self._CACHE_PATH,
                                               filename,
                                               size)
            if os.path.exists(CACHE_PATH_JPG):
                return CACHE_PATH_JPG
            else:
                self.get(album_id, size)
                if os.path.exists(CACHE_PATH_JPG):
                    return CACHE_PATH_JPG
                else:
                    return None
        except Exception as e:
            print("Art::get_album_cache_path(): %s" % e, ascii(filename))
            return None

    """
        get cover cache path for radio
        @param name as string
        @return cover path as string or None if no cover
    """
    def get_radio_cache_path(self, name, size):
        filename = ''
        try:
            filename = self._get_radio_cache_name(name)
            CACHE_PATH_JPG = "%s/%s_%s.png" % (self._CACHE_PATH,
                                               filename,
                                               size)
            if os.path.exists(CACHE_PATH_JPG):
                return CACHE_PATH_JPG
            else:
                self.get_radio(name, size)
                if os.path.exists(CACHE_PATH_JPG):
                    return CACHE_PATH_JPG
                else:
                    return None
        except Exception as e:
            print("Art::get_radio_cache_path(): %s" % e, ascii(filename))
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
                for mime in self._mimes:
                    if lowername.endswith(mime):
                        supported = True
                        break
                if (supported):
                    return "%s/%s" % (album_path, file)

            return None
        except Exception as e:
            print("Art::get_album_art_path(): %s" % e)

    """
        Return a pixbuf for radio name
        @param radio name as string
        @param pixbuf size as int
        @param selected as bool
    """
    def get_radio(self, name, size, selected=False):
        filename = self._get_radio_cache_name(name)
        CACHE_PATH_PNG = "%s/%s_%s.png" % (self._CACHE_PATH, filename, size)
        pixbuf = None

        try:
            # Look in cache
            if os.path.exists(CACHE_PATH_PNG):
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(CACHE_PATH_PNG,
                                                                size,
                                                                size)
            else:
                path = self._get_radio_art_path(name)
                if path is not None:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(path,
                                                                    size,
                                                                    size)
            if pixbuf is None:
                pixbuf = self._get_default_icon(
                                            size,
                                            'audio-input-microphone-symbolic')

            # Gdk < 3.15 was missing save method
            # > 3.15 is missing savev method
            try:
                pixbuf.save(CACHE_PATH_PNG, "png",
                            [None], [None])
            except:
                pixbuf.savev(CACHE_PATH_PNG, "png",
                             [None], [None])
            return self._make_icon_frame(pixbuf, selected)

        except Exception as e:
            print(e)
            return self._make_icon_frame(self._get_default_icon(
                                          size,
                                          'audio-input-microphone-symbolic'),
                                         selected)

    """
        Return a pixbuf for album_id, covers are cached as jpg.
        @param album id as int
        @param pixbuf size as int
        @param selected as bool
        return: pixbuf
    """
    def get_album(self, album_id, size, selected=False):
        filename = self._get_album_cache_name(album_id)
        CACHE_PATH_JPG = "%s/%s_%s.jpg" % (self._CACHE_PATH, filename, size)
        pixbuf = None

        try:
            # Look in cache
            if os.path.exists(CACHE_PATH_JPG):
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(CACHE_PATH_JPG,
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
                            pixbuf = self._pixbuf_from_tags(tracks[0], size)
                    except Exception as e:
                        print(e)
                        return self._make_icon_frame(
                                            self._get_default_icon(
                                                    size,
                                                    'folder-music-symbolic'),
                                            selected)
                # No cover, use default one
                if pixbuf is None:
                    Lp.lastfm.download_album_img(album_id)
                    pixbuf = self._get_default_icon(size,
                                                    'folder-music-symbolic')
                else:
                    # Gdk < 3.15 was missing save method
                    # > 3.15 is missing savev method
                    try:
                        pixbuf.save(CACHE_PATH_JPG, "jpeg",
                                    ["quality"], ["90"])
                    except:
                        pixbuf.savev(CACHE_PATH_JPG, "jpeg",
                                     ["quality"], ["90"])

            return self._make_icon_frame(pixbuf, selected)

        except Exception as e:
            print(e)
            return self._make_icon_frame(self._get_default_icon(
                                                    size,
                                                    'folder-music-symbolic'),
                                         selected)

    """
        Remove all covers from cache
    """
    def clean_all_cache(self):
        try:
            files = os.listdir(self._CACHE_PATH)
            for f in files:
                os.remove(os.path.join(self._CACHE_PATH, f))
        except Exception as e:
            print("Art::clean_all_cache(): ", e)

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

    """
        Remove logo from cache for radio
        @param radio name as string
    """
    def clean_radio_cache(self, name):
        filename = self._get_radio_cache_name(name)
        try:
            for f in os.listdir(self._CACHE_PATH):
                if re.search('%s_.*\.png' % re.escape(filename), f):
                    os.remove(os.path.join(self._CACHE_PATH, f))
        except Exception as e:
            print("Art::clean_radio_cache(): ", e, filename)

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
        Save pixbuf for radio
        @param pixbuf as Gdk.Pixbuf
        @param radio name as string
    """
    def save_radio_logo(self, pixbuf, radio):
        try:
            artpath = self._RADIOS_PATH + "/" + radio + ".png"

            # Gdk < 3.15 was missing save method
            try:
                pixbuf.save(artpath, "png", [None], [None])
            # > 3.15 is missing savev method :(
            except:
                pixbuf.savev(artpath, "png", [None], [None])
        except Exception as e:
            print("Art::save_radio_logo(): %s" % e)

    """
        Get arts on google image corresponding to search
        @param search words as string
        @param start page
        @return [urls as string]
    """
    def get_google_arts(self, search, start=0):
        try:
            response = urllib.request.urlopen("https://ajax.googleapis.com/"
                                              "ajax/services/search/images"
                                              "?&q=%s&v=1.0&start=%s&rsz=%s" %
                                              (urllib.parse.quote(search),
                                               start,
                                               GOOGLE_INC))
        except Exception as e:
            print(e)
            return None

        data = response.read()
        decode = json.loads(data.decode("utf-8"))
        urls = []
        if decode is None:
            return urls
        try:
            for item in decode['responseData']['results']:
                urls.append(item['url'])
        except:
            pass

        return urls

    """
        Announce album cover update
        @param album id as int
    """
    def announce_cover_update(self, album_id):
        self.emit('cover-changed', album_id)

    """
        Announce radio logo update
        @param radio name as string
    """
    def announce_logo_update(self, name):
        self.emit('logo-changed', name)

#######################
# PRIVATE             #
#######################
    """
        Look for radio covers
        @param radio name as string
        @return cover file path as string
    """
    def _get_radio_art_path(self, name):
        try:
            if os.path.exists(self._RADIOS_PATH + "/" + name + ".png"):
                return self._RADIOS_PATH + "/" + name + ".png"
            return None
        except Exception as e:
            print("Art::_get_radio_art_path(): %s" % e)

    """
        Return cover from tags
        @param track id as int
        @param size as int
    """
    def _pixbuf_from_tags(self, track_id, size):
        pixbuf = None
        filepath = Lp.tracks.get_path(track_id)
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

    """
        Get a uniq string for radio
        @param album id as int
        @param sql as sqlite cursor
    """
    def _get_radio_cache_name(self, name):
        return "@@"+name+"@@radio@@"

    """
        Draw an icon frame around pixbuf,
        code forked Gnome Music, see copyright header
        @param: pixbuf source as Gdk.Pixbuf
        @param selected as bool
    """
    def _make_icon_frame(self, pixbuf, selected):
        selected_color = Lp.window.get_selected_color()
        dark = self._gtk_settings.get_property(
                                           "gtk-application-prefer-dark-theme")
        degrees = pi / 180

        width = pixbuf.get_width()
        height = pixbuf.get_height()

        if width < ArtSize.BIG:
            radius = ArtSize.SMALL_RADIUS
            border = ArtSize.SMALL_BORDER
        else:
            radius = ArtSize.RADIUS
            border = ArtSize.BORDER

        surface_width = width + border * 2
        surface_height = height + border * 2
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                     surface_width, surface_height)
        ctx = cairo.Context(surface)
        ctx.new_sub_path()
        ctx.arc(surface_width - radius, radius,
                radius - 0.5, -90 * degrees, 0 * degrees)
        ctx.arc(surface_width - radius, surface_height - radius,
                radius - 0.5, 0 * degrees, 90 * degrees)
        ctx.arc(radius, surface_height - radius,
                radius - 0.5, 90 * degrees, 180 * degrees)
        ctx.arc(radius, radius, radius - 0.5, 180 * degrees, 270 * degrees)
        ctx.close_path()
        ctx.set_line_width(0.6)

        if selected:
            ctx.set_source_rgb(selected_color.red,
                               selected_color.green,
                               selected_color.blue)
        elif dark and width > ArtSize.MEDIUM:
            ctx.set_source_rgb(0.8, 0.8, 0.8)
        else:
            ctx.set_source_rgb(0.2, 0.2, 0.2)
        ctx.stroke_preserve()

        if selected:
            ctx.set_source_rgb(selected_color.red,
                               selected_color.green,
                               selected_color.blue)
        else:
            if width < ArtSize.BIG:
                ctx.set_source_rgb(0, 0, 0)
            elif dark:
                ctx.set_source_rgba(0, 0, 0, 0.5)
            else:
                ctx.set_source_rgb(1, 1, 1)
        ctx.fill()
        border_pixbuf = Gdk.pixbuf_get_from_surface(surface, 0, 0,
                                                    surface_width,
                                                    surface_height)

        pixbuf.copy_area(0, 0,
                         width,
                         height,
                         border_pixbuf,
                         border, border)
        return border_pixbuf

    """
        Construct an empty cover album,
        code forked Gnome Music, see copyright header
        @param size as int
        @param icon_name as str
        @return pixbuf as Gdk.Pixbuf
    """
    def _get_default_icon(self, size, icon_name):
        #First look in cache
        CACHE_PATH_JPG = "%s/%s_%s.jpg" % (self._CACHE_PATH, icon_name, size)
        if os.path.exists(CACHE_PATH_JPG):
            print('cache')
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(CACHE_PATH_JPG,
                                                             size,
                                                             size,
                                                             False)
            return pixbuf

        # get a small pixbuf with the given path
        icon_size = size / 4
        icon = Gtk.IconTheme.get_default().load_icon(icon_name,
                                                     icon_size, 0)
        # create an empty pixbuf with the requested size
        result = GdkPixbuf.Pixbuf.new(icon.get_colorspace(),
                                      True,
                                      icon.get_bits_per_sample(),
                                      size,
                                      size)
        result.fill(0xffffffff)
        icon.composite(result,
                       icon_size * 3 / 2,
                       icon_size * 3 / 2,
                       icon_size,
                       icon_size,
                       icon_size * 3 / 2,
                       icon_size * 3 / 2,
                       1, 1,
                       GdkPixbuf.InterpType.NEAREST, 255)
        # Gdk < 3.15 was missing save method
        # > 3.15 is missing savev method
        try:
            result.save(CACHE_PATH_JPG, "jpeg",
                        ["quality"], ["90"])
        except:
            result.savev(CACHE_PATH_JPG, "jpeg",
                         ["quality"], ["90"])
        return result
