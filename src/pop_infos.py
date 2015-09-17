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

from gi.repository import Gtk, GLib, Gio, GdkPixbuf

from gettext import gettext as _
from locale import getdefaultlocale
from threading import Thread
from cgi import escape

from lollypop.define import Lp, Type


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
            ArtistInfos.WebKit2 is not None

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


class ArtistContent(Gtk.Stack):
    """
        Widget showing artist image and bio
    """

    def __init__(self):
        """
            Init artist content
        """
        Gtk.Stack.__init__(self)
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/ArtistContent.ui')
        self._content = builder.get_object('content')
        self._image = builder.get_object('image')
        self.add_named(builder.get_object('widget'), 'widget')
        self.add_named(builder.get_object('notfound'), 'notfound')
        self.add_named(builder.get_object('spinner'), 'spinner')
        self.set_visible_child_name('spinner')

    def set_content(self, content, stream):
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
                self._image.set_from_pixbuf(pixbuf)
                del pixbuf
            self.set_visible_child_name('widget')
        else:
            self.set_visible_child_name('notfound')


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
        from gi.repository import WebKit2
    except Exception as e:
        print(e)
        print(_("Wikia support disabled"))
        WebKit2 = None

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
        if self.WebKit2 is None or artist is not None:
            builder.get_object('wikia').destroy()
        if self.WebKit2 is None:
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
        Lp.settings.set_value('infoswitch',
                              GLib.Variant('s', 'wikia'))
        artist = self._get_current_artist().replace(' ', '_')
        title = Lp.player.current_track.title.replace(' ', '_')
        self._load_web(widget, "http://lyrics.wikia.com/wiki/%s:%s" % (artist,
                                                                       title))
        self._stack.set_visible_child_name('wikia')

    def _on_map_duck(self, widget):
        """
            Load on map
            @param widget as Gtk.ScrolledWindow
        """
        Lp.settings.set_value('infoswitch',
                              GLib.Variant('s', 'duck'))
        if self._artist is None:
            artist = self._get_current_artist()
        else:
            artist = self._artist
        title = Lp.player.current_track.title
        self._load_web(widget, "https://duckduckgo.com/?q=%s+%s" % (artist,
                                                                    title))
        self._stack.set_visible_child_name('duck')

    def _load_web(self, widget, url):
        """
            Load url with two replacement
            @param url as string
            @param widget as Gtk.ScrolledWindow
        """
        child = widget.get_child()
        if child is not None:
            child.destroy()

        settings = self.WebKit2.Settings()
        settings.set_property('enable-private-browsing', True)
        settings.set_property('enable-plugins', False)
        settings.set_property('user-agent',
                              "Mozilla/5.0 (Linux; Ubuntu 14.04;"
                              " BlackBerry) AppleWebKit2/537.36 Chromium"
                              "/35.0.1870.2 Mobile Safari/537.36")
        view = self.WebKit2.WebView()
        view.set_settings(settings)
        view.show()
        # TLS is broken in WebKit2, don't know how to fix this so disable
        # auth/forms
        view.get_context().set_tls_errors_policy(
                                        self.WebKit2.TLSErrorsPolicy.IGNORE)
        view.connect('authenticate', self._on_authenticate)
        view.connect('decide_policy', self._on_decide_policy)
        view.connect('submit-form', self._on_submit_form)
        widget.add(view)
        view.set_property('hexpand', True)
        view.set_property('vexpand', True)
        view.grab_focus()
        view.load_uri(url)

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

    def _on_authenticate(self, view, request):
        """
            Disable web auth
            @param view as WebKit2.WebView
            @param request as WebKit2.AuthenticationRequest
            @return bool
        """
        return True

    def _on_decide_policy(self, view, decision, decision_type):
        """
            Disallow navigation, launch in external browser
            @param view as WebKit2.WebView
            @param decision as WebKit2.NavigationPolicyDecision
            @param decision_type as WebKit2.PolicyDecisionType
            @return bool
        """
        if decision_type == self.WebKit2.PolicyDecisionType.NAVIGATION_ACTION:
            if decision.get_navigation_action().get_navigation_type() ==\
               self.WebKit2.NavigationType.LINK_CLICKED:
                decision.ignore()
                GLib.spawn_command_line_async("xdg-open \"%s\"" %
                                              decision.get_request().get_uri())
            return True
        decision.use()
        return False

    def _on_submit_form(self, view, request):
        """
            Ignore request
            @param view as WebKit2.WebView
            @param request as WebKit2.FormSubmissionRequest
        """
        if request.get_text_fields() is not None:
            view.stop_loading()
