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

from gi.repository import Gtk, GLib, Gio

from gettext import gettext as _
from threading import Thread

from lollypop.define import Lp, Type
from lollypop.widgets_artist import ArtistContent


class InfosPopover(Gtk.Popover):
    """
        Popover with artist informations
    """

    def should_be_shown():
        """
            True if we can show popover
        """
        return Lp.lastfm is not None or\
            ArtistInfos.Wikipedia is not None or\
            ArtistInfos.WebView is not None

    def __init__(self, artist=None):
        """
            Init popover
            @param artist as string
        """
        Gtk.Popover.__init__(self)
        self._infos = ArtistInfos(artist)
        self._infos.show()
        self.add(self._infos)

    def do_show(self):
        """
            Resize popover and set signals callback
        """
        size_setting = Lp.settings.get_value('window-size')
        if isinstance(size_setting[1], int):
            self.set_size_request(700, size_setting[1]*0.7)
        else:
            self.set_size_request(700, 400)
        Gtk.Popover.do_show(self)

    def do_get_preferred_width(self):
        """
            Preferred width
        """
        return (700, 700)


class ArtistInfos(Gtk.Bin):
    """
        Artist informations from lastfm
    """

    try:
        from lollypop.wikipedia import Wikipedia
    except Exception as e:
        print(e)
        print(_("Advanced artist informations disabled"))
        print("$ sudo pip3 install wikipedia")
        Wikipedia = None

    try:
        from lollypop.widgets_web import WebView
    except Exception as e:
        print(e)
        print(_("WebKit support disabled"))
        WebView = None

    def __init__(self, artist):
        """
            Init artist infos
            @param artist as string
        """
        Gtk.Bin.__init__(self)
        self._artist = artist

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/ArtistInfos.ui')
        builder.connect_signals(self)

        self._stack = builder.get_object('stack')
        self._stack.set_visible_child_name(
            Lp.settings.get_value('infoswitch').get_string())
        self.add(builder.get_object('widget'))

        if self.Wikipedia is None:
            builder.get_object('wikipedia').destroy()
        if Lp.lastfm is None:
            builder.get_object('lastfm').destroy()
        if self.WebView is None or artist is not None:
            builder.get_object('wikia').destroy()
        if self.WebView is None:
            builder.get_object('duck').destroy()

#######################
# PRIVATE             #
#######################
    def _on_map_lastfm(self, widget):
        """
            Load on map
        """
        Lp.settings.set_value('infoswitch',
                              GLib.Variant('s', 'lastfm'))
        content_widget = ArtistContent()
        content_widget.show()
        child = widget.get_child()
        if child is not None:
            child.destroy()
        widget.add(content_widget)
        t = Thread(target=self._populate_lastfm, args=(content_widget,))
        t.daemon = True
        t.start()

    def _populate_lastfm(self, widget):
        """
            Populate content with lastfm informations
            @param widget as Gtk.ScrolledWindow
            @thread safe
        """
        url = None
        image_url = None
        content = None
        if self._artist is None:
            artist = self._get_current_artist()
        else:
            artist = self._artist
        (url, image_url, content) = Lp.lastfm.get_artist_infos(artist)
        self._populate(url, image_url, content, widget)

    def _on_map_wikipedia(self, widget):
        """
            Load on map
        """
        Lp.settings.set_value('infoswitch',
                              GLib.Variant('s', 'wikipedia'))
        content_widget = ArtistContent()
        content_widget.show()
        child = widget.get_child()
        if child is not None:
            child.destroy()
        widget.add(content_widget)
        t = Thread(target=self._populate_wikipedia, args=(content_widget,))
        t.daemon = True
        t.start()

    def _populate_wikipedia(self, widget):
        """
            Populate content with wikipedia informations
            @param widget as Gtk.ScrolledWindow
            @thread safe
        """
        url = None
        image_url = None
        content = None
        if self._artist is None:
            artist = self._get_current_artist()
        else:
            artist = self._artist
        (url, image_url, content) = self.Wikipedia().get_artist_infos(artist)
        self._populate(url, image_url, content, widget)

    def _on_map_wikia(self, widget):
        """
            Load on map
            @param widget as Gtk.ScrolledWindow
        """
        child = widget.get_child()
        if child is not None:
            child.destroy()
        Lp.settings.set_value('infoswitch',
                              GLib.Variant('s', 'wikia'))
        artist = self._get_current_artist().replace(' ', '_')
        title = Lp.player.current_track.title.replace(' ', '_')
        url = "http://lyrics.wikia.com/wiki/%s:%s" % (artist, title)
        # Delayed load due to WebKit memory loading
        GLib.timeout_add(250, self._load_web, widget, url, True)

    def _on_map_duck(self, widget):
        """
            Load on map
            @param widget as Gtk.ScrolledWindow
        """
        child = widget.get_child()
        if child is not None:
            child.destroy()
        Lp.settings.set_value('infoswitch',
                              GLib.Variant('s', 'duck'))
        title = Lp.player.current_track.title
        if self._artist is None:
            search = "%s+%s" % (self._get_current_artist(), title)
        else:
            search = self._artist
        url = "https://duckduckgo.com/?q=%s&kl=%s&kd=-1&k5=2&kp=1&ks=l"\
              % (search, Gtk.get_default_language().to_string())
        # Delayed load due to WebKit memory loading
        GLib.timeout_add(250, self._load_web, widget, url, False)

    def _load_web(self, widget, url, mobile):
        """
            Load url in widget
            @param widget as Gtk.ScrolledWindow
        """
        web = self.WebView(url, mobile)
        web.show()
        widget.add(web)

    def _populate(self, url, image_url, content, widget):
        """
            populate widget with content
            @param url as string
            @param image url as string
            @param content as string
            @param widget as Gtk.ScrolledWindow
            @thread safe
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
        GLib.idle_add(self._set_content, content, url, stream, widget)

    def _set_content(self, content, url, stream, widget):
        """
            Set content on view
            @param content as str
            @param url as str
            @param stream as Gio.MemoryInputStream
            @param widget as Gtk.ScrolledWindow
        """
        widget.set_content(content, stream)

    def _get_current_artist(self):
        """
            Get current artist
            @return artist as string
        """
        artist_id = Lp.player.current_track.album_artist_id
        if artist_id == Type.COMPILATIONS:
            artist = Lp.player.current_track.artist
        else:
            artist = Lp.player.current_track.album_artist
        return artist
