# Copyright (c) 2014-2017 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from lollypop.define import Lp, OpenLink, Type
from lollypop.objects import Track
from lollypop.utils import get_network_available
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

    def __init__(self, artist_ids=[], view_type=Type.ALBUMS):
        """
            Init artist infos
            @param artist_ids as int
            @param view_type as Type
        """
        Gtk.Popover.__init__(self)
        self.set_position(Gtk.PositionType.BOTTOM)
        self.connect("map", self.__on_map)
        self.connect("unmap", self.__on_unmap)
        self.__artist_ids = artist_ids
        self.__current_track = Track()
        self.__timeout_id = None
        self.__signal_id = None

        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/ArtistInfo.ui")
        builder.connect_signals(self)
        self.__lyrics_label = builder.get_object("lyrics_label")
        self.__jump_button = builder.get_object("jump-button")
        self.__stack = builder.get_object("stack")
        self.add(builder.get_object("widget"))
        if Lp().settings.get_value("inforeload"):
            builder.get_object("reload").get_style_context().add_class(
                                                                    "selected")

    def set_view_type(self, view_type):
        """
            Set current view type
            @param view_type as Type
        """
        if view_type == Type.ALBUMS:
            self.__stack.get_child_by_name("albums").show()
        else:
            self.__stack.get_child_by_name("albums").hide()
        show_bio = view_type != Type.RADIOS
        if InfoPopover.Wikipedia is not None and show_bio:
            self.__stack.get_child_by_name("wikipedia").hide()
        else:
            self.__stack.get_child_by_name("wikipedia").show()
        if Lp().lastfm is not None and\
                not Lp().settings.get_value("use-librefm") and show_bio:
            self.__stack.get_child_by_name("lastfm").show()
        else:
            self.__stack.get_child_by_name("lastfm").hide()
        if InfoPopover.WebView is not None and get_network_available():
            self.__stack.get_child_by_name("duck").show()
        else:
            self.__stack.get_child_by_name("duck").hide()
        if not self.__artist_ids:
            self.__stack.get_child_by_name("lyrics").show()
        else:
            self.__stack.get_child_by_name("lyrics").hide()
        self.__stack.set_visible_child_name(
            Lp().settings.get_value("infoswitch").get_string())

#######################
# PROTECTED           #
#######################
    def _on_button_press(self, widget, event):
        """
            Start a timer to set autoload
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        self.__timeout_id = GLib.timeout_add(500, self.__set_autoload, widget)

    def _on_button_release(self, widget, event):
        """
            Reload current view if autoload unchanged
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        if self.__timeout_id is not None:
            GLib.source_remove(self.__timeout_id)
            self.__timeout_id = None
            visible_name = self.__stack.get_visible_child_name()
            # Clear cache if needed
            if visible_name in ["lastfm", "wikipedia"]:
                for artist in self.__current_track.artists:
                    InfoCache.remove(artist, visible_name)
                # stack -> scrolled -> viewport -> grid
                self._on_child_unmap(
                      self.__stack.get_visible_child().get_child().get_child())
            self.__on_current_changed(Lp().player)

    def _on_jump_button_clicked(self, widget):
        """
            Go to current album
        """
        try:
            self.__stack.get_visible_child().get_child_at(
                                                        0, 0).jump_to_current()
        except Exception as e:
            print(e)

    def _on_map_albums(self, widget):
        """
            Load on map
            @param widget as Gtk.Grid
        """
        self.__jump_button.show()
        if self.__current_track.id is None:
            self.__current_track = Lp().player.current_track
        Lp().settings.set_value("infoswitch",
                                GLib.Variant("s", "albums"))
        view = widget.get_child_at(0, 0)
        if view is None:
            view = CurrentArtistAlbumsView()
            view.set_property("expand", True)
            view.show()
            widget.add(view)
        t = Thread(target=view.populate, args=(self.__current_track,))
        t.daemon = True
        t.start()

    def _on_map_lastfm(self, widget):
        """
            Load on map
            @param widget as Gtk.Viewport
        """
        if self.__current_track.id is None:
            self.__current_track = Lp().player.current_track
        # Check if update is needed
        widgets_artists = []
        for child in widget.get_children():
            widgets_artists.append(child.artist)
        if widgets_artists == self.__current_track.artists:
            return
        self._on_child_unmap(widget)
        self.__jump_button.hide()
        Lp().settings.set_value("infoswitch",
                                GLib.Variant("s", "lastfm"))
        if self.__artist_ids:
            artists = []
            for artist_id in self.__artist_ids:
                artists.append(Lp().artists.get_name(artist_id))
        else:
            artists = self.__current_track.artists
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
        if self.__current_track.id is None:
            self.__current_track = Lp().player.current_track
        # Check if update is needed
        widgets_artists = []
        for child in widget.get_children():
            widgets_artists.append(child.artist)
        if widgets_artists == self.__current_track.artists:
            return
        self._on_child_unmap(widget)
        self.__jump_button.hide()
        Lp().settings.set_value("infoswitch",
                                GLib.Variant("s", "wikipedia"))
        if self.__artist_ids:
            artists = []
            for artist_id in self.__artist_ids:
                artists.append(Lp().artists.get_name(artist_id))
        else:
            artists = self.__current_track.artists
        for artist in artists:
            content = WikipediaContent()
            content.show()
            widget.add(content)
            t = Thread(target=content.populate,
                       args=(artist, self.__current_track.album.name))
            t.daemon = True
            t.start()

    def _on_map_lyrics(self, widget):
        """
            Load on map
            @param widget as Gtk.Viewport
        """
        Lp().settings.set_value("infoswitch",
                                GLib.Variant("s", "lyrics"))
        self.__jump_button.hide()
        if self.__current_track.id is None:
            self.__current_track = Lp().player.current_track
        # First try to get lyrics from tags
        from lollypop.tagreader import TagReader
        reader = TagReader()
        try:
            info = reader.get_info(self.__current_track.uri)
        except:
            info = None
        lyrics = ""
        if info is not None:
            tags = info.get_tags()
            lyrics = reader.get_lyrics(tags)
        if lyrics or InfoPopover.WebView is None\
                or not get_network_available():
            # Destroy previous widgets
            self._on_child_unmap(widget)
            label = Gtk.Label()
            label.set_vexpand(True)
            label.set_hexpand(True)
            label.set_margin_top(10)
            label.set_margin_end(10)
            label.show()
            widget.add(label)
            if lyrics:
                label.set_label(lyrics)
            elif not get_network_available():
                string = GLib.markup_escape_text(_("Network access disabled"))
                label.get_style_context().add_class("dim-label")
                label.set_markup(
                       '<span font_weight="bold" size="xx-large">' +
                       string +
                       "</span>")
            else:
                string = GLib.markup_escape_text(
                       _("No lyrics found, please install gir1.2-webkit2-4.0"))
                label.get_style_context().add_class("dim-label")
                label.set_markup(
                       '<span font_weight="bold" size="xx-large">' +
                       string +
                       "</span>")
        elif get_network_available():
            title = self.__current_track.name
            if self.__current_track.id == Type.RADIOS:
                search = GLib.uri_escape_string(title, None, True)
            else:
                artists = ", ".join(Lp().player.current_track.artists)
                search = GLib.uri_escape_string(artists + " " + title,
                                                None, True)
            url = "http://genius.com/search?q=%s" % search
            # If we do not have a webview in children, create a new one
            # Else load url
            children = widget.get_children()
            if not children or not isinstance(children[0], self.WebView):
                # Destroy previous widgets
                self._on_child_unmap(widget)
                web = self.WebView(True, True)
                web.add_word("search")
                web.add_word("lyrics")
                web.show()
                widget.add(web)
                # Delayed load due to WebKit memory loading and Gtk animation
                GLib.timeout_add(250, web.load, url, OpenLink.NEW)
            elif url != children[0].url:
                children[0].load(url, OpenLink.NEW)

    def _on_map_duck(self, widget):
        """
            Load on map
            @param widget as Gtk.Viewport
        """
        self._on_child_unmap(widget)
        self.__jump_button.hide()
        if self.__current_track.id is None:
            self.__current_track = Lp().player.current_track
        Lp().settings.set_value("infoswitch",
                                GLib.Variant("s", "duck"))
        if self.__artist_ids:
            artists = []
            for artist_id in self.__artist_ids:
                artists.append(Lp().artists.get_name(artist_id))
            search = ", ".join(artists)
        else:
            if self.__current_track.id == Type.RADIOS:
                search = self.__current_track.name
            else:
                title = self.__current_track.name
                artists = ", ".join(Lp().player.current_track.artists)
                search = "%s+%s" % (artists, title)
        url = "https://duckduckgo.com/?q=%s&kl=%s&kd=-1&k5=2&kp=1&k1=-1"\
              % (search, Gtk.get_default_language().to_string())
        # If we do not have a webview in children, create a new one
        # Else load url
        children = widget.get_children()
        if not children or not isinstance(children[0], self.WebView):
            # Destroy previous widgets
            self._on_child_unmap(widget)
            web = self.WebView(False, True)
            web.show()
            widget.add(web)
            # Delayed load due to WebKit memory loading and Gtk animation
            GLib.timeout_add(250, web.load, url, OpenLink.NEW)
        elif url != children[0].url:
            children[0].load(url, OpenLink.NEW)

    def _on_child_unmap(self, widget):
        """
            Destroy child children
            @param widget as Gtk.Widget
        """
        for child in widget.get_children():
            if not isinstance(child, Gtk.Label):
                child.stop()
            child.destroy()

#######################
# PRIVATE             #
#######################
    def __set_autoload(self, widget):
        """
            Mark as autoload
            @param widget as Gtk.Widget
        """
        self.__timeout_id = None
        if self.__signal_id is None:
            Lp().settings.set_value("inforeload", GLib.Variant("b", True))
            self.__signal_id = Lp().player.connect("current-changed",
                                                   self.__on_current_changed)
            widget.get_style_context().add_class("selected")
        else:
            Lp().player.disconnect(self.__signal_id)
            self.__signal_id = None
            Lp().settings.set_value("inforeload",
                                    GLib.Variant("b", False))
            widget.get_style_context().remove_class("selected")

    def __on_current_changed(self, player):
        """
            Update content on track changed
            @param player as Player
        """
        if self.__artist_ids:
            return
        self.__current_track = Lp().player.current_track
        name = self.__stack.get_visible_child_name()
        if name == "albums":
            # stack -> grid
            visible = self.__stack.get_visible_child()
        else:
            # stack -> scrolled -> viewport -> grid
            visible = self.__stack.get_visible_child().get_child().get_child()
        getattr(self, "_on_map_%s" % name)(visible)

    def __on_map(self, widget):
        """
            Connect signals and resize
            @param widget as Gtk.Widget
        """
        size = Lp().window.get_size()
        self.set_size_request(size[0]*0.6,
                              size[1]*0.7)
        if Lp().settings.get_value("inforeload"):
            self.__signal_id = Lp().player.connect("current-changed",
                                                   self.__on_current_changed)

    def __on_unmap(self, widget):
        """
            Destroy self if needed and disconnect signals
            @param widget as Gtk.Widget
        """
        self.__current_track = Track()
        if self.__signal_id is not None:
            Lp().player.disconnect(self.__signal_id)
            self.__signal_id = None
