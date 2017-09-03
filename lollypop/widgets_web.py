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

import gi
gi.require_version("WebKit2", "4.0")
from gi.repository import Gtk, WebKit2, GLib

from urllib.parse import urlparse

from lollypop.define import OpenLink


class WebView(Gtk.Stack):
    """
        Webkit view with loading scrobbler
        Webkit destroyed on unmap
    """

    def __init__(self, mobile=True, private=True):
        """
            Init view
            @param mobile as bool
            @param private as bool
        """
        Gtk.Stack.__init__(self)
        self.connect("destroy", self.__on_destroy)
        self.set_transition_duration(500)
        self.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.__current_domain = ""
        self.__url = ""
        self.__allowed_words = []
        self.__open_links = OpenLink.NEW
        builder = Gtk.Builder()
        # Use ressource from ArtistContent
        builder.add_from_resource("/org/gnome/Lollypop/InfoContent.ui")
        self.__view = WebKit2.WebView()
        self.__spinner = builder.get_object("spinner")
        self.add_named(self.__spinner, "spinner")
        self.set_visible_child_name("spinner")
        self.add_named(self.__view, "view")
        self.__view.connect("load-changed", self.__on_load_changed)
        settings = self.__view.get_settings()
        # Private browsing make duckduckgo fail to switch translations
        if private:
            settings.set_property("enable-private-browsing", True)
            settings.set_property("print-backgrounds", False)
        settings.set_property("enable-smooth-scrolling", True)
        settings.set_property("enable-plugins", False)
        settings.set_property("enable-fullscreen", False)
        settings.set_property("enable-html5-database", False)
        settings.set_property("enable-html5-local-storage", True)
        settings.set_property("enable-media-stream", False)
        settings.set_property("enable-mediasource", False)
        settings.set_property("enable-offline-web-application-cache", False)
        settings.set_property("enable-page-cache", True)
        settings.set_property("enable-webaudio", False)
        settings.set_property("enable-webgl", False)
        if mobile:
            settings.set_property("user-agent",
                                  "Mozilla/5.0 (Linux; Ubuntu 14.04;"
                                  " BlackBerry) AppleWebKit2/537.36 Chromium"
                                  "/35.0.1870.2 Mobile Safari/537.36")
        self.__view.set_settings(settings)
        self.__view.connect("decide-policy", self.__on_decide_policy)
        self.__view.connect("context-menu", self.__on_context_menu)
        self.__view.set_property("hexpand", True)
        self.__view.set_property("vexpand", True)
        self.__view.show()

    @property
    def url(self):
        """
            domain as str
        """
        return self.__url

    def add_word(self, word):
        """
            Add a word to allowed urls, only urls with this words will
            get a navigation token
        """
        self.__allowed_words.append(word)

    def load(self, url, open_link):
        """
            Load url
            @param url as string
            @param open link as OpenLink
        """
        self.__open_link = open_link
        self.__url = url
        self.__current_domain = self.__get_domain(url)
        self.__view.load_uri(url)

    def stop(self):
        """
            Stop loading
        """
        self.__view.stop_loading()

#######################
# PRIVATE             #
#######################
    def __get_domain(self, url):
        """
            Return domain for url
            @param url as str
        """
        parsed = urlparse(url)
        return parsed.netloc

    def __on_destroy(self, widget):
        """
            Destroy webkit view to stop any audio playback
            @param widget as Gtk.Widget
        """
        self.__view.stop_loading()
        self.__view.destroy()

    def __on_load_changed(self, view, event):
        """
            Show view if finished
            @param view as WebKit2.View
            @param event as WebKit2.LoadEvent
        """
        if event == WebKit2.LoadEvent.STARTED:
            self.set_transition_type(Gtk.StackTransitionType.NONE)
            self.set_visible_child_name("spinner")
            self.__spinner.start()
            self.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        elif event == WebKit2.LoadEvent.COMMITTED:
            self.set_visible_child_name("view")
            self.__spinner.stop()

    def __on_decide_policy(self, view, decision, decision_type):
        """
            Navigation policy
            @param view as WebKit2.WebView
            @param decision as WebKit2.NavigationPolicyDecision
            @param decision_type as WebKit2.PolicyDecisionType
            @return bool
        """
        # Always accept response
        if decision_type == WebKit2.PolicyDecisionType.RESPONSE:
            decision.use()
            return False

        url = decision.get_navigation_action().get_request().get_uri()
        # WTF is this?
        if url == "about:blank":
            decision.ignore()
            return True

        # Refused non allowed words
        found = False
        for word in self.__allowed_words:
            if word in url:
                found = True
                break
        if self.__allowed_words and not found:
            decision.ignore()
            return True

        # On clicked, if external wanted, launch user browser and stop
        # If navigation not allowed, stop
        if self.__open_link == OpenLink.NEW and\
                self.__get_domain(url) != self.__current_domain:
            GLib.spawn_command_line_async("xdg-open \"%s\"" % url)
            decision.ignore()
            return True
        elif self.__open_link == OpenLink.NONE:
            decision.ignore()
            return True
        # Use click, load page
        elif decision.get_navigation_action().get_navigation_type() ==\
                WebKit2.NavigationType.LINK_CLICKED:
            decision.use()
            return False
        # If external domain, do not load
        elif self.__get_domain(url) != self.__current_domain:
            decision.ignore()
            return True
        self.__current_domain = self.__get_domain(url)
        decision.use()
        return False

    def __on_context_menu(self, view, menu, event, hit):
        """
            No menu
            @param view as WebKit2.WebView
            @param menu as WebKit2.ContextMenu
            @param event as Gdk.Event
            @param hit as WebKit2.HitTestResult
        """
        return True
