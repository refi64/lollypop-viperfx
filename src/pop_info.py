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

from gi.repository import Gtk, GLib

from gettext import gettext as _
from threading import Thread

from lollypop.define import Lp, OpenLink
from lollypop.objects import Track
from lollypop.widgets_info import WikipediaContent, LastfmContent
from lollypop.cache import InfoCache
from lollypop.view_artist_albums import CurrentArtistAlbumsView


class InfoPopover(Gtk.Popover):
    """
        Popover with artist informations
        @Warning: Auto destroy on hide if artist id is not None
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

    def should_be_shown():
        """
            True if we can show popover
        """
        return Lp().lastfm is not None or\
            InfoPopover.Wikipedia is not None or\
            InfoPopover.WebView is not None

    def __init__(self, artist_ids=[], show_albums=True):
        """
            Init artist infos
            @param artist id as int
            @param show albums as bool
        """
        Gtk.Popover.__init__(self)
        self.set_position(Gtk.PositionType.BOTTOM)
        self.connect('map', self._on_map)
        self.connect('unmap', self._on_unmap)
        self._artist_ids = artist_ids
        self._current_track = Track()
        self._timeout_id = None
        self._signal_id = None

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/ArtistInfo.ui')
        builder.connect_signals(self)
        self._lyrics_label = builder.get_object('lyrics_label')
        self._jump_button = builder.get_object('jump-button')
        self._stack = builder.get_object('stack')
        self.add(builder.get_object('widget'))
        if Lp().settings.get_value('inforeload'):
            builder.get_object('reload').get_style_context().add_class(
                                                                    'selected')
        if show_albums:
            self._stack.get_child_by_name('albums').show()
        if InfoPopover.Wikipedia is not None:
            self._stack.get_child_by_name('wikipedia').show()
        if Lp().lastfm is not None:
            self._stack.get_child_by_name('lastfm').show()
        if InfoPopover.WebView is not None:
            self._stack.get_child_by_name('duck').show()
            if not artist_ids:
                self._stack.get_child_by_name('lyrics').show()
        self._stack.set_visible_child_name(
            Lp().settings.get_value('infoswitch').get_string())

#######################
# PRIVATE             #
#######################
    def _set_autoload(self, widget):
        """
            Mark as autoload
            @param widget as Gtk.Widget
        """
        self._timeout_id = None
        if self._signal_id is None:
            Lp().settings.set_value('inforeload', GLib.Variant('b', True))
            self._signal_id = Lp().player.connect("current-changed",
                                                  self._on_current_changed)
            widget.get_style_context().add_class('selected')
        else:
            Lp().player.disconnect(self._signal_id)
            self._signal_id = None
            Lp().settings.set_value('inforeload',
                                    GLib.Variant('b', False))
            widget.get_style_context().remove_class('selected')

    def _on_current_changed(self, player):
        """
            Update content on track changed
            @param player as Player
        """
        if self._artist_ids:
            return
        self._current_track = Lp().player.current_track
        name = self._stack.get_visible_child_name()
        if name == "albums":
            # stack -> grid
            visible = self._stack.get_visible_child()
        else:
            # stack -> scrolled -> viewport -> grid
            visible = self._stack.get_visible_child().get_child().get_child()
        getattr(self, '_on_map_%s' % name)(visible)

    def _on_btn_press(self, widget, event):
        """
            Start a timer to set autoload
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        self._timeout_id = GLib.timeout_add(500, self._set_autoload, widget)

    def _on_btn_release(self, widget, event):
        """
            Reload current view if autoload unchanged
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        if self._timeout_id is not None:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = None
            visible_name = self._stack.get_visible_child_name()
            # Clear cache if needed
            if visible_name in ['lastfm', 'wikipedia']:
                for artist in self._current_track.artists:
                    InfoCache.uncache(artist, visible_name)
                # stack -> scrolled -> viewport -> grid
                self._on_child_unmap(
                       self._stack.get_visible_child().get_child().get_child())
            self._on_current_changed(Lp().player)

    def _on_jump_button_clicked(self, widget):
        """
            Go to current album
        """
        try:
            self._stack.get_visible_child().get_child_at(
                                                        0, 0).jump_to_current()
        except Exception as e:
            print(e)

    def _on_map(self, widget):
        """
            Connect signals and resize
            @param widget as Gtk.Widget
        """
        size = Lp().window.get_size()
        self.set_size_request(size[0]*0.6,
                              size[1]*0.7)
        if Lp().settings.get_value('inforeload'):
            self._signal_id = Lp().player.connect("current-changed",
                                                  self._on_current_changed)

    def _on_unmap(self, widget):
        """
            Destroy self if needed and disconnect signals
            @param widget as Gtk.Widget
        """
        self._current_track = Track()
        if self._signal_id is not None:
            Lp().player.disconnect(self._signal_id)
            self._signal_id = None

    def _on_child_unmap(self, widget):
        """
            Destroy child children
            @param widget as Gtk.Widget
        """
        for child in widget.get_children():
            child.stop()
            child.destroy()

    def _on_map_albums(self, widget):
        """
            Load on map
            @param widget as Gtk.Grid
        """
        self._jump_button.show()
        if self._current_track.id is None:
            self._current_track = Lp().player.current_track
        Lp().settings.set_value('infoswitch',
                                GLib.Variant('s', 'albums'))
        view = widget.get_child_at(0, 0)
        if view is None:
            view = CurrentArtistAlbumsView()
            view.set_property('expand', True)
            view.show()
            widget.add(view)
        t = Thread(target=view.populate, args=(self._current_track,))
        t.daemon = True
        t.start()

    def _on_map_lastfm(self, widget):
        """
            Load on map
            @param widget as Gtk.Viewport
        """
        if self._current_track.id is None:
            self._current_track = Lp().player.current_track
        # Check if update is needed
        widgets_artists = []
        for child in widget.get_children():
            widgets_artists.append(child.artist)
        if widgets_artists == self._current_track.artists:
            return
        self._on_child_unmap(widget)
        self._jump_button.hide()
        Lp().settings.set_value('infoswitch',
                                GLib.Variant('s', 'lastfm'))
        if self._artist_ids:
            artists = []
            for artist_id in self._artist_ids:
                artists.append(Lp().artists.get_name(artist_id))
        else:
            artists = self._current_track.artists
        for artist in artists:
            content = LastfmContent()
            content.show()
            widget.add(content)
            t = Thread(target=content.populate, args=(artist, ))
            t.daemon = True
            t.start()

    def _on_map_wikipedia(self, widget):
        """
            Load on map
            @param widget as Gtk.Viewport
        """
        if self._current_track.id is None:
            self._current_track = Lp().player.current_track
        # Check if update is needed
        widgets_artists = []
        for child in widget.get_children():
            widgets_artists.append(child.artist)
        if widgets_artists == self._current_track.artists:
            return
        self._on_child_unmap(widget)
        self._jump_button.hide()
        Lp().settings.set_value('infoswitch',
                                GLib.Variant('s', 'wikipedia'))
        if self._artist_ids:
            artists = []
            for artist_id in self._artist_ids:
                artists.append(Lp().artists.get_name(artist_id))
        else:
            artists = self._current_track.artists
        for artist in artists:
            content = WikipediaContent()
            content.show()
            widget.add(content)
            t = Thread(target=content.populate,
                       args=(artist, self._current_track.album.name))
            t.daemon = True
            t.start()

    def _on_map_lyrics(self, widget):
        """
            Load on map
            @param widget as Gtk.Viewport
        """
        Lp().settings.set_value('infoswitch',
                                GLib.Variant('s', 'lyrics'))
        self._jump_button.hide()
        if self._current_track.id is None:
            self._current_track = Lp().player.current_track
        artists = ", ".join(Lp().player.current_track.artists)
        title = self._current_track.name
        # If already searching in genius, search with duckduckgo
        # Vice versa
        duckurl = "https://duckduckgo.com/?q=%s&kl=%s&kd=-1&k5=2&kp=1&k1=-1"\
            % (artists+"+"+title+" lyrics",
               Gtk.get_default_language().to_string())
        geniusurl = url = "http://genius.com/search?q=%s" % artists+" "+title
        children = widget.get_children()
        # First time genius
        if not children:
            url = geniusurl
        elif children[0].url == duckurl:
            url = geniusurl
        elif children[0].url == geniusurl:
            url = duckurl
        else:
            url = geniusurl
        self._on_child_unmap(widget)
        # Delayed load due to WebKit memory loading and Gtk animation
        web = self.WebView(True, True)
        web.add_word('search')
        web.add_word('lyrics')
        web.show()
        widget.add(web)
        GLib.timeout_add(250, web.load, url, OpenLink.OPEN)

    def _on_map_duck(self, widget):
        """
            Load on map
            @param widget as Gtk.Viewport
        """
        self._on_child_unmap(widget)
        self._jump_button.hide()
        if self._current_track.id is None:
            self._current_track = Lp().player.current_track
        Lp().settings.set_value('infoswitch',
                                GLib.Variant('s', 'duck'))
        if self._artist_ids:
            artists = []
            for artist_id in self._artist_ids:
                artists.append(Lp().artists.get_name(artist_id))
            search = ", ".join(artists)
        else:
            title = self._current_track.name
            artists = ", ".join(Lp().player.current_track.artists)
            search = "%s+%s" % (artists, title)
        url = "https://duckduckgo.com/?q=%s&kl=%s&kd=-1&k5=2&kp=1&k1=-1"\
              % (search, Gtk.get_default_language().to_string())
        # Delayed load due to WebKit memory loading and Gtk animation
        web = self.WebView(False, True)
        web.show()
        widget.add(web)
        GLib.timeout_add(250, web.load, url, OpenLink.NEW)
