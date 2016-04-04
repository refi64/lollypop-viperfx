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

from lollypop.define import Lp
from lollypop.objects import Track
from lollypop.widgets_info import WikipediaContent, LastfmContent
from lollypop.widgets_web import OpenLink
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
        if not show_albums:
            self._stack.get_child_by_name('albums').destroy()
        if InfoPopover.Wikipedia is None:
            self._stack.get_child_by_name('wikipedia').destroy()
        if Lp().lastfm is None:
            self._stack.get_child_by_name('lastfm').destroy()
        if artist_ids:
            self._stack.get_child_by_name('lyrics').destroy()
        if InfoPopover.WebView is None:
            self._stack.get_child_by_name('duck').destroy()
        self._stack.set_visible_child_name(
            Lp().settings.get_value('infoswitch').get_string())

    def do_show(self):
        """
            Set widget size
        """
        size = Lp().window.get_size()
        self.set_size_request(size[0]*0.6,
                              size[1]*0.7)
        Gtk.Popover.do_show(self)

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

    def _load_web(self, widget, url, mobile, private, open_link):
        """
            Load url in widget
            @param widget as Gtk.Viewport
        """
        web = self.WebView(mobile, private)
        web.show()
        widget.add(web)
        web.load(url, open_link)

    def _on_current_changed(self, player, force=False):
        """
            Update content on track changed
            @param player as Player
            @param force as bool
        """
        self._current_track = Lp().player.current_track
        name = self._stack.get_visible_child_name()
        if name == "albums":
            visible = self._stack.get_visible_child()
        else:
            visible = self._stack.get_visible_child().get_child()
        getattr(self, '_on_map_%s' % name)(visible, force)

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
            self._on_current_changed(Lp().player, True)

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
            Connect signals
            @param widget as Gtk.Widget
        """
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
            child.destroy()

    def _on_map_albums(self, widget, force=False):
        """
            Load on map
            @param widget as Gtk.Grid
            @param force as bool
        """
        self._jump_button.show()
        self._jump_button.set_tooltip_text(_("Go to current track"))
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

    def _on_map_lastfm(self, widget, force=False):
        """
            Load on map
            @param widget as Gtk.Viewport
            @param force as bool
        """
        self._on_child_unmap(widget)
        self._jump_button.hide()
        if self._current_track.id is None:
            self._current_track = Lp().player.current_track
        Lp().settings.set_value('infoswitch',
                                GLib.Variant('s', 'lastfm'))
        for artist in self._current_track.artists:
            content = LastfmContent()
            content.show()
            widget.add(content)
            if force:
                InfoCache.uncache(artist, 'lastfm')
            t = Thread(target=content.populate, args=(artist, ))
            t.daemon = True
            t.start()

    def _on_map_wikipedia(self, widget, force=False):
        """
            Load on map
            @param widget as Gtk.Viewport
            @param force as bool
        """
        self._on_child_unmap(widget)
        self._jump_button.hide()
        if self._current_track.id is None:
            self._current_track = Lp().player.current_track
        Lp().settings.set_value('infoswitch',
                                GLib.Variant('s', 'wikipedia'))
        for artist in self._current_track.artists:
            content = WikipediaContent()
            content.show()
            widget.add(content)
            if force:
                InfoCache.uncache(artist, 'wikipedia')
            t = Thread(target=content.populate,
                       args=(artist, self._current_track.album.name))
            t.daemon = True
            t.start()

    def _on_map_lyrics(self, widget, force=False):
        """
            Load on map
            @param widget as Gtk.Viewport
        """
        self._on_child_unmap(widget)
        self._jump_button.hide()
        if self._current_track.id is None:
            self._current_track = Lp().player.current_track
        artists = ", ".join(Lp().player.current_track.artists)
        Lp().settings.set_value('infoswitch',
                                GLib.Variant('s', 'lyrics'))
        title = self._current_track.name
        url = "https://duckduckgo.com/?q=%s&kl=%s&kd=-1&k5=2&kp=1&k1=-1"\
            % (artists+"+"+title+" lyrics",
               Gtk.get_default_language().to_string())
        # Delayed load due to WebKit memory loading
        GLib.timeout_add(250, self._load_web, widget,
                         url, True, True, OpenLink.OPEN)

    def _on_map_duck(self, widget, force=False):
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
        # Delayed load due to WebKit memory loading
        GLib.timeout_add(250, self._load_web, widget, url,
                         False, False, OpenLink.NEW)
