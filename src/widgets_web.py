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

from gi.repository import Gtk, WebKit2, GLib

from urllib.parse import urlsplit


class WebView(Gtk.Stack):
    """
        Webkit view with loading scrobbler
    """

    def __init__(self, url, mobile=True, private=True):
        """
            Init view
            @param url as string
            @param mobile as bool
        """
        Gtk.Stack.__init__(self)
        self.set_transition_duration(500)
        self.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._current = urlsplit(url)[1]
        builder = Gtk.Builder()
        # Use ressource from ArtistContent
        builder.add_from_resource('/org/gnome/Lollypop/ArtistContent.ui')
        self._view = WebKit2.WebView()
        self.add_named(builder.get_object('spinner'), 'spinner')
        self.set_visible_child_name('spinner')
        self.add_named(self._view, 'view')
        self._view.connect('load-changed', self._on_load_changed)
        settings = self._view.get_settings()
        # Private browsing make duckduckgo fail to switch translations
        if private:
            settings.set_property('enable-private-browsing', True)
        settings.set_property('enable-plugins', False)
        if mobile:
            settings.set_property('user-agent',
                                  "Mozilla/5.0 (Linux; Ubuntu 14.04;"
                                  " BlackBerry) AppleWebKit2/537.36 Chromium"
                                  "/35.0.1870.2 Mobile Safari/537.36")
        self._view.set_settings(settings)
        # FIXME TLS is broken in WebKit2, don't know how to fix this
        self._view.get_context().set_tls_errors_policy(
                                                WebKit2.TLSErrorsPolicy.IGNORE)
        self._view.connect('decide_policy', self._on_decide_policy)
        self._view.set_property('hexpand', True)
        self._view.set_property('vexpand', True)
        self._view.show()
        self._view.grab_focus()
        self._view.load_uri(url)

    def do_unmap(self):
        """
            Destroy webkit view to stop any audio playback
        """
        self._view.stop_loading()
        self._view.destroy()
        Gtk.Stack.do_unmap(self)

#######################
# PRIVATE             #
#######################
    def _on_load_changed(self, view, event):
        """
            Show view if finished
            @param view as WebKit2.View
            @param event as WebKit2.LoadEvent
        """
        if event == WebKit2.LoadEvent.STARTED:
            self.set_visible_child_name('spinner')
        elif event == WebKit2.LoadEvent.FINISHED:
            self.set_visible_child_name('view')

    def _on_decide_policy(self, view, decision, decision_type):
        """
            Disallow navigation, launch in external browser
            @param view as WebKit2.WebView
            @param decision as WebKit2.NavigationPolicyDecision
            @param decision_type as WebKit2.PolicyDecisionType
            @return bool
        """
        if decision_type == WebKit2.PolicyDecisionType.NAVIGATION_ACTION:
            if decision.get_navigation_action().get_navigation_type() ==\
               WebKit2.NavigationType.LINK_CLICKED or (self._current not
               in decision.get_navigation_action().get_request().get_uri() and
               decision.get_navigation_action().get_request().get_uri() !=
               'about:blank'):
                decision.ignore()
                GLib.spawn_command_line_async("xdg-open \"%s\"" %
                                              decision.get_request().get_uri())
            return True
        decision.use()
        return False
