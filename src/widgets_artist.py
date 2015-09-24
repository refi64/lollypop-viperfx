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

from gi.repository import Gtk, GdkPixbuf, GLib, Gio

from cgi import escape

from lollypop.wikipedia import Wikipedia
from lollypop.define import Lp, Type


class ArtistContent(Gtk.Stack):
    """
        Widget showing artist image and bio
    """

    def __init__(self):
        """
            Init artist content
        """
        Gtk.Stack.__init__(self)
        self.set_transition_duration(500)
        self.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/ArtistContent.ui')
        self._content = builder.get_object('content')
        self._image = builder.get_object('image')
        self.add_named(builder.get_object('widget'), 'widget')
        self.add_named(builder.get_object('notfound'), 'notfound')
        self.add_named(builder.get_object('spinner'), 'spinner')

    def clear(self):
        """
            Clear content
        """
        self._content.set_text('')
        self._image.clear()
        self.set_visible_child_name('spinner')

    def populate(self, content, image_url):
        """
            populate widget with content
            @param content as string
            @param image url as string
        """
        stream = None
        try:
            if image_url is not None:
                f = Gio.File.new_for_uri(image_url)
                (status, data, tag) = f.load_contents()
                if status:
                    stream = Gio.MemoryInputStream.new_from_data(data,
                                                                 None)
        except Exception as e:
            print("PopArtistInfos::_populate: %s" % e)
        self._set_content(content, stream)

#######################
# PRIVATE             #
#######################
    def _set_content(self, content, stream):
        """
            Set content
            @param content as string
            @param stream as Gio.MemoryInputStream
        """
        if content:
            self._content.set_markup(escape(content))
            if stream is not None:
                pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(stream,
                                                                   200,
                                                                   -1,
                                                                   True,
                                                                   None)
                self._image.set_from_surface(Lp.art.make_icon_frame(pixbuf,
                                                                    False))
                del pixbuf
            self.set_visible_child_name('widget')
        else:
            self.set_visible_child_name('notfound')

    def _get_current_artist(self):
        """
            Get current artist
            @return artist as string
        """
        # TODO: This code is duplicated
        artist_id = Lp.player.current_track.album_artist_id
        if artist_id == Type.COMPILATIONS:
            artist = Lp.player.current_track.artist
        else:
            artist = Lp.player.current_track.album_artist
        return artist


class WikipediaContent(ArtistContent):
    """
        Show wikipedia content
    """
    def __init__(self):
        """
            Init widget
        """
        ArtistContent.__init__(self)

    def populate(self, artist):
        """
            Populate content
            @param artist as string
            @thread safe
        """
        url = None
        image_url = None
        content = None
        if artist is None:
            artist = self._get_current_artist()
        (url, image_url, content) = Wikipedia().get_artist_infos(artist)
        GLib.idle_add(ArtistContent.populate, self, content, image_url)


class LastfmContent(ArtistContent):
    """
        Show lastfm content
    """
    def __init__(self):
        """
            Init widget
        """
        ArtistContent.__init__(self)

    def populate(self, artist):
        """
            Populate content
            @param artist as string
            @thread safe
        """
        url = None
        image_url = None
        content = None
        if artist is None:
            artist = self._get_current_artist()
        (url, image_url, content) = Lp.lastfm.get_artist_infos(artist)
        GLib.idle_add(ArtistContent.populate, self, content, image_url)
