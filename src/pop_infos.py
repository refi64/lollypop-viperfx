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
from cgi import escape

from lollypop.define import Lp, Type
from lollypop.widgets_artist import WikipediaContent, LastfmContent
from lollypop.view_artist_albums import CurrentArtistAlbumsView


class InfosPopover(Gtk.Popover):
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
            InfosPopover.Wikipedia is not None or\
            InfosPopover.WebView is not None

    def __init__(self, artist_id=None, show_albums=True):
        """
            Init artist infos
            @param artist id as int
            @param show albums as bool
        """
        Gtk.Popover.__init__(self)
        self.set_position(Gtk.PositionType.BOTTOM)
        self.connect('map', self._on_self_map)
        self.connect('unmap', self._on_self_unmap)
        self._artist_id = artist_id
        self._current = None
        self._timeout_id = None
        self._signal_id = None

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/ArtistInfos.ui')
        builder.connect_signals(self)
        self._menu = builder.get_object('menu')
        self._jump_button = builder.get_object('jump-button')
        self._stack = builder.get_object('stack')
        self.add(builder.get_object('widget'))
        if Lp().settings.get_value('infosreload'):
            builder.get_object('reload').get_style_context().add_class(
                                                                    'selected')
        if not show_albums:
            self._stack.get_child_by_name('albums').destroy()
        if InfosPopover.Wikipedia is None:
            self._stack.get_child_by_name('wikipedia').destroy()
        if Lp().lastfm is None:
            self._stack.get_child_by_name('lastfm').destroy()
        if InfosPopover.WebView is None or artist_id is not None:
            self._stack.get_child_by_name('wikia').destroy()
        if InfosPopover.WebView is None:
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

    def do_get_preferred_width(self):
        """
            Preferred width
        """
        return (700, 700)

#######################
# PRIVATE             #
#######################
    def _get_current(self):
        """
            Update current track
        """
        album_id = Type.NONE
        track_id = Type.NONE
        if self._artist_id is None:
            if Lp().player.current_track.album_artist_id == Type.COMPILATIONS:
                album_id = Lp().player.current_track.album_id
                artist_id = Lp().player.current_track.artist_id
            else:
                artist_id = Lp().player.current_track.album_artist_id
            track_id = Lp().player.current_track.id
        else:
            artist_id = self._artist_id
        return (artist_id, album_id, track_id)

    def _set_autoload(self, widget):
        """
            Mark as autoload
            @param widget as Gtk.Widget
        """
        self._timeout_id = None
        if self._signal_id is None:
            Lp().settings.set_value('infosreload', GLib.Variant('b', True))
            self._signal_id = Lp().player.connect("current-changed",
                                                  self._on_current_changed)
            widget.get_style_context().add_class('selected')
        else:
            Lp().player.disconnect(self._signal_id)
            self._signal_id = None
            Lp().settings.set_value('infosreload',
                                    GLib.Variant('b', False))
            widget.get_style_context().remove_class('selected')

    def _load_web(self, widget, url, mobile, private):
        """
            Load url in widget
            @param widget as Gtk.Viewport
        """
        web = widget.get_child()
        if web is None:
            web = self.WebView(mobile, private)
            web.show()
            widget.add(web)
        web.load(url)

    def _on_current_changed(self, player, force=False):
        """
            Update content on track changed
            @param player as Player
            @param force as bool
        """
        self._current = self._get_current()
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

    def _on_self_map(self, widget):
        """
            Connect signals
            @param widget as Gtk.Widget
        """
        if Lp().settings.get_value('infosreload') and self._artist_id is None:
            self._signal_id = Lp().player.connect("current-changed",
                                                  self._on_current_changed)

    def _on_self_unmap(self, widget):
        """
            Destroy self if needed and disconnect signals
            @param widget as Gtk.Widget
        """
        self._current = None
        if self._signal_id is not None:
            Lp().player.disconnect(self._signal_id)
            self._signal_id = None
        if self._artist_id is not None:
            GLib.idle_add(self.destroy)

    def _on_unmap(self, widget):
        """
            Destroy child
            @param widget as Gtk.Widget
        """
        for child in widget.get_children():
            if hasattr(child, 'clear_artist'):
                child.clear_artist()
            child.destroy()

    def _on_map_albums(self, widget, force=False):
        """
            Load on map
            @param widget as Gtk.Grid
            @param force as bool
        """
        self._menu.hide()
        self._jump_button.show()
        self._jump_button.set_tooltip_markup(
                                      "<b>%s</b> - " %
                                      escape(
                                        Lp().player.current_track.artist_names
                                        ) +
                                      Lp().player.current_track.name)
        if self._current is None:
            self._current = self._get_current()
        Lp().settings.set_value('infoswitch',
                                GLib.Variant('s', 'albums'))
        view = widget.get_child_at(0, 0)
        if view is None:
            view = CurrentArtistAlbumsView()
            view.set_property('expand', True)
            view.show()
            widget.add(view)
        t = Thread(target=view.populate,
                   args=(self._current[0], self._current[1]))
        t.daemon = True
        t.start()

    def _on_map_lastfm(self, widget, force=False):
        """
            Load on map
            @param widget as Gtk.Viewport
            @param force as bool
        """
        self._menu.hide()
        self._jump_button.hide()
        if self._current is None:
            self._current = self._get_current()
        artist = Lp().artists.get_name(self._current[0])
        Lp().settings.set_value('infoswitch',
                                GLib.Variant('s', 'lastfm'))
        content_widget = widget.get_child()
        if content_widget is None:
            content_widget = LastfmContent()
            content_widget.show()
            widget.add(content_widget)
        if force:
            content_widget.uncache(artist)
        if content_widget.should_update(artist) or force:
            content_widget.clear()
            t = Thread(target=content_widget.populate, args=(artist,))
            t.daemon = True
            t.start()

    def _on_map_wikipedia(self, widget, force=False):
        """
            Load on map
            @param widget as Gtk.Viewport
            @param force as bool
        """
        self._jump_button.hide()
        if self._current is None:
            self._current = self._get_current()
        artist = Lp().artists.get_name(self._current[0])
        # Get one album from artist
        if self._current[1] == Type.NONE:
            ids = Lp().artists.get_albums(self._current[0])
            if ids:
                album = Lp().albums.get_name(ids[0])
        else:
            album = Lp().albums.get_name(self._current[1])
        Lp().settings.set_value('infoswitch',
                                GLib.Variant('s', 'wikipedia'))
        content_widget = widget.get_child()
        if content_widget is None:
            content_widget = WikipediaContent(self._menu)
            content_widget.show()
            widget.add(content_widget)
        if force:
            content_widget.uncache(artist)
        if content_widget.should_update(artist) or force:
            content_widget.clear()
            t = Thread(target=content_widget.populate, args=(artist, album))
            t.daemon = True
            t.start()

    def _on_map_wikia(self, widget, force=False):
        """
            Load on map
            @param widget as Gtk.Viewport
            @param force as bool
        """
        self._jump_button.hide()
        self._menu.hide()
        if self._current is None:
            self._current = self._get_current()
        artist = Lp().artists.get_name(self._current[0])
        title = Lp().tracks.get_name(self._current[2])
        Lp().settings.set_value('infoswitch',
                                GLib.Variant('s', 'wikia'))
        url = "http://lyrics.wikia.com/wiki/%s:%s" % (artist.replace(' ', '_'),
                                                      title.replace(' ', '_'))
        # Delayed load due to WebKit memory loading
        GLib.timeout_add(250, self._load_web, widget, url, True, True)

    def _on_map_duck(self, widget, force=False):
        """
            Load on map
            @param widget as Gtk.Viewport
        """
        self._jump_button.hide()
        self._menu.hide()
        if self._current is None:
            self._current = self._get_current()
        artist = Lp().artists.get_name(self._current[0])
        Lp().settings.set_value('infoswitch',
                                GLib.Variant('s', 'duck'))
        if self._current[2] == Type.NONE:
            search = artist
        else:
            title = Lp().tracks.get_name(self._current[2])
            search = "%s+%s" % (artist, title)
        url = "https://duckduckgo.com/?q=%s&kl=%s&kd=-1&k5=2&kp=1&k1=-1"\
              % (search, Gtk.get_default_language().to_string())
        # Delayed load due to WebKit memory loading
        GLib.timeout_add(250, self._load_web, widget, url, False, False)
