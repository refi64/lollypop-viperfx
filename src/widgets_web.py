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

import gi
gi.require_version('WebKit2', '4.0')
from gi.repository import Gtk, WebKit2, GLib

from urllib.parse import urlsplit

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
        self.connect('destroy', self._on_destroy)
        self.set_transition_duration(500)
        self.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._current_domain = ''
        self._url = ''
        self._allowed_words = []
        self._open_links = OpenLink.NEW
        builder = Gtk.Builder()
        # Use ressource from ArtistContent
        builder.add_from_resource('/org/gnome/Lollypop/InfoContent.ui')
        self._view = WebKit2.WebView()
        self._spinner = builder.get_object('spinner')
        self.add_named(self._spinner, 'spinner')
        self.set_visible_child_name('spinner')
        self.add_named(self._view, 'view')
        self._view.connect('load-changed', self._on_load_changed)
        settings = self._view.get_settings()
        # Private browsing make duckduckgo fail to switch translations
        if private:
            settings.set_property('enable-private-browsing', True)
            settings.set_property('print-backgrounds', False)
        settings.set_property('enable-smooth-scrolling', True)
        settings.set_property('enable-plugins', False)
        settings.set_property('enable-fullscreen', False)
        settings.set_property('enable-html5-database', False)
        settings.set_property('enable-html5-local-storage', False)
        settings.set_property('enable-media-stream', False)
        settings.set_property('enable-mediasource', False)
        settings.set_property('enable-offline-web-application-cache', False)
        settings.set_property('enable-page-cache', False)
        settings.set_property('enable-webaudio', False)
        settings.set_property('enable-webgl', False)
        if mobile:
            settings.set_property('user-agent',
                                  "Mozilla/5.0 (Linux; Ubuntu 14.04;"
                                  " BlackBerry) AppleWebKit2/537.36 Chromium"
                                  "/35.0.1870.2 Mobile Safari/537.36")
        self._view.set_settings(settings)
        # FIXME TLS is broken in WebKit2, don't know how to fix this
        self._view.get_context().set_tls_errors_policy(
                                                WebKit2.TLSErrorsPolicy.IGNORE)
        self._view.connect('decide-policy', self._on_decide_policy)
        self._view.connect('context-menu', self._on_context_menu)
        self._view.set_property('hexpand', True)
        self._view.set_property('vexpand', True)
        self._view.show()

    @property
    def url(self):
        """
            domain as str
        """
        return self._url

    def add_word(self, word):
        """
            Add a word to allowed urls, only urls with this word will
            get a navigation token
        """
        self._allowed_words.append(word)

    def load(self, url, open_link):
        """
            Load url
            @param url as string
            @param open link as OpenLink
        """
        self._open_link = open_link
        self._url = url
        self._current_domain = self._get_domain(url)
        self._view.grab_focus()
        self._view.load_uri(url)

    def stop(self):
        """
            Stop loading
        """
        self._view.stop_loading()

#######################
# PRIVATE             #
#######################
    def _get_domain(self, url):
        """
            Return domain for url
            @param url as str
        """
        hostname = urlsplit(url)[1]
        split = hostname.split('.')
        return split[-2] + "." + split[-1]

    def _on_destroy(self, widget):
        """
            Destroy webkit view to stop any audio playback
            @param widget as Gtk.Widget
        """
        self._view.stop_loading()
        self._view.destroy()

    def _on_load_changed(self, view, event):
        """
            Show view if finished
            @param view as WebKit2.View
            @param event as WebKit2.LoadEvent
        """
        if event == WebKit2.LoadEvent.STARTED:
            self.set_transition_type(Gtk.StackTransitionType.NONE)
            self.set_visible_child_name('spinner')
            self._spinner.start()
            self.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        elif event == WebKit2.LoadEvent.FINISHED:
            self.set_visible_child_name('view')
            self._spinner.stop()

    def _on_decide_policy(self, view, decision, decision_type):
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
        for word in self._allowed_words:
            if word in url:
                found = True
                break
        if self._allowed_words and not found:
            decision.ignore()
            return True

        # On clicked, if external wanted, launch user browser and stop
        # If navigation not allowed, stop
        if self._open_link == OpenLink.NEW and\
                self._get_domain(url) != self._current_domain:
            GLib.spawn_command_line_async("xdg-open \"%s\"" % url)
            decision.ignore()
            return True
        elif self._open_link == OpenLink.NONE:
            decision.ignore()
            return True
        # Use click, load page
        elif decision.get_navigation_action().get_navigation_type() ==\
                WebKit2.NavigationType.LINK_CLICKED:
            decision.use()
            return False
        # If external domain, do not load
        elif self._get_domain(url) != self._current_domain:
            decision.ignore()
            return True
        self._current_domain = self._get_domain(url)
        decision.use()
        return False

    def _on_context_menu(self, view, menu, event, hit):
        """
            No menu
            @param view as WebKit2.WebView
            @param menu as WebKit2.ContextMenu
            @param event as Gdk.Event
            @param hit as WebKit2.HitTestResult
        """
        return True
