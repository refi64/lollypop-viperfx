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

from gi.repository import Gtk, GLib

from gettext import gettext as _
from threading import Thread

from lollypop.define import Lp
from lollypop.widgets_artist import WikipediaContent, LastfmContent
from lollypop.view_artist_albums import CurrentArtistAlbumsView


class InfosPopover(Gtk.Popover):
    """
        Popover with artist informations
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
        return Lp.lastfm is not None or\
            InfosPopover.Wikipedia is not None or\
            InfosPopover.WebView is not None

    def __init__(self, artist_id=None, show_albums=True):
        """
            Init artist infos
            @param artist as int
            @param show albums as bool
        """
        Gtk.Bin.__init__(self)
        self._artist = None
        self._artist_id = artist_id
        self._timeout_id = None
        if self._artist_id is not None:
            self._artist = Lp.artists.get_name(artist_id)

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/ArtistInfos.ui')
        builder.connect_signals(self)

        if Lp.settings.get_value('infosreload'):
            builder.get_object('reload').get_style_context().add_class(
                                                                  'selected')
            self._signal_id = Lp.player.connect("current-changed",
                                                self._update_content)
        else:
            self._signal_id = None

        self._stack = builder.get_object('stack')
        self.add(builder.get_object('widget'))
        if not show_albums:
            self._stack.get_child_by_name('albums').destroy()
        if InfosPopover.Wikipedia is None:
            self._stack.get_child_by_name('wikipedia').destroy()
        if Lp.lastfm is None:
            self._stack.get_child_by_name('lastfm').destroy()
        if InfosPopover.WebView is None or artist_id is not None:
            self._stack.get_child_by_name('wikia').destroy()
        if InfosPopover.WebView is None:
            self._stack.get_child_by_name('duck').destroy()

        size_setting = Lp.settings.get_value('window-size')
        if isinstance(size_setting[1], int):
            self.set_size_request(size_setting[0]*0.6,
                                  size_setting[1]*0.8)
        else:
            self.set_size_request(700, 600)
        self._stack.set_visible_child_name(
            Lp.settings.get_value('infoswitch').get_string())

    def do_get_preferred_width(self):
        """
            Preferred width
        """
        return (700, 700)

#######################
# PRIVATE             #
#######################
    def _update_content(self, player=None, force=False):
        """
            Update content
        """
        name = self._stack.get_visible_child_name()
        if name == "albums":
            visible = self._stack.get_visible_child()
        else:
            visible = self._stack.get_visible_child().get_child()
        getattr(self, '_on_map_%s' % name)(visible, force)

    def _set_autoload(self, widget):
        """
            Mark as autoload
            @param widget as Gtk.Widget
        """
        self._timeout_id = None
        if self._signal_id is None:
            widget.get_style_context().add_class('selected')
        else:
            widget.get_style_context().remove_class('selected')

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
        if self._timeout_id is None:
            if self._signal_id is None:
                Lp.settings.set_value('infosreload', GLib.Variant('b', True))
                self._signal_id = Lp.player.connect("current-changed",
                                                    self._update_content)
            else:
                Lp.player.disconnect(self._signal_id)
                self._signal_id = None
                Lp.settings.set_value('infosreload', GLib.Variant('b', False))
        else:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = None
            self._update_content(None, True)

    def _on_unmap(self, widget):
        """
            Destroy child
            @param widget as Gtk.Widget
        """
        for child in widget.get_children():
            child.destroy()

    def _on_map_albums(self, widget, force=False):
        """
            Load on map
            @param widget as Gtk.Bin
            @param force as bool
        """
        if not self.is_visible():
            return
        Lp.settings.set_value('infoswitch',
                              GLib.Variant('s', 'albums'))
        view = widget.get_child_at(0, 0)
        if view is None:
            view = CurrentArtistAlbumsView(self._artist_id)
            view.set_property('expand', True)
            view.show()
            widget.add(view)
        t = Thread(target=view.populate)
        t.daemon = True
        t.start()

    def _on_map_lastfm(self, widget, force=False):
        """
            Load on map
            @param widget as Gtk.Viewport
            @param force as bool
        """
        if not self.is_visible():
            return
        Lp.settings.set_value('infoswitch',
                              GLib.Variant('s', 'lastfm'))
        content_widget = widget.get_child()
        if content_widget is None:
            content_widget = LastfmContent()
            content_widget.show()
            widget.add(content_widget)
        if force:
            content_widget.uncache(self._artist)
        if content_widget.get_artist() != self._artist:
            content_widget.clear()
            t = Thread(target=content_widget.populate, args=(self._artist,))
            t.daemon = True
            t.start()

    def _on_map_wikipedia(self, widget, force=False):
        """
            Load on map
            @param widget as Gtk.Viewport
            @param force as bool
        """
        if not self.is_visible():
            return
        Lp.settings.set_value('infoswitch',
                              GLib.Variant('s', 'wikipedia'))
        content_widget = widget.get_child()
        if content_widget is None:
            content_widget = WikipediaContent()
            content_widget.show()
            widget.add(content_widget)
        if force:
            content_widget.uncache(self._artist)
        if content_widget.get_artist() != self._artist:
            content_widget.clear()
            t = Thread(target=content_widget.populate, args=(self._artist,))
            t.daemon = True
            t.start()

    def _on_map_wikia(self, widget, force=False):
        """
            Load on map
            @param widget as Gtk.Viewport
            @param force as bool
        """
        if not self.is_visible():
            return
        Lp.settings.set_value('infoswitch',
                              GLib.Variant('s', 'wikia'))
        artist = Lp.player.get_current_artist().replace(' ', '_')
        title = Lp.player.current_track.title.replace(' ', '_')
        url = "http://lyrics.wikia.com/wiki/%s:%s" % (artist, title)
        # Delayed load due to WebKit memory loading
        GLib.timeout_add(250, self._load_web, widget, url, True, True)

    def _on_map_duck(self, widget, force=False):
        """
            Load on map
            @param widget as Gtk.Viewport
        """
        if not self.is_visible():
            return
        Lp.settings.set_value('infoswitch',
                              GLib.Variant('s', 'duck'))
        title = Lp.player.current_track.title
        if self._artist is None:
            search = "%s+%s" % (Lp.player.get_current_artist(), title)
        else:
            search = self._artist
        url = "https://duckduckgo.com/?q=%s&kl=%s&kd=-1&k5=2&kp=1&k1=-1"\
              % (search, Gtk.get_default_language().to_string())
        # Delayed load due to WebKit memory loading
        GLib.timeout_add(250, self._load_web, widget, url, False, False)

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
