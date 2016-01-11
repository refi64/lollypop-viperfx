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

from gi.repository import Gtk, Gio

from lollypop.pop_next import NextPopover
from lollypop.pop_queue import QueueWidget
from lollypop.pop_search import SearchPopover
from lollypop.define import Lp, Shuffle


class ToolbarEnd(Gtk.Bin):
    """
        Toolbar end
    """

    def __init__(self, app):
        """
            Init toolbar
            @param app as Gtk.Application
        """
        Gtk.Bin.__init__(self)
        self._pop_next = NextPopover()
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/ToolbarEnd.ui')
        builder.connect_signals(self)

        self.add(builder.get_object('end'))

        self._shuffle_btn = builder.get_object('shuffle-button')
        self._shuffle_btn_image = builder.get_object('shuffle-button-image')
        Lp().settings.connect('changed::shuffle', self._shuffle_btn_aspect)

        self._party_btn = builder.get_object('party-button')
        party_action = Gio.SimpleAction.new('party', None)
        party_action.connect('activate', self._activate_party_button)
        app.add_action(party_action)
        app.set_accels_for_action("app.party", ["<Control>p"])

        search_button = builder.get_object('search-button')
        self._search = SearchPopover(self)
        self._search.set_relative_to(search_button)
        searchAction = Gio.SimpleAction.new('search', None)
        searchAction.connect('activate', self._on_search_btn_clicked)
        app.add_action(searchAction)
        app.set_accels_for_action("app.search", ["<Control>f"])

        self._queue_button = builder.get_object('queue-button')

        self._settings_button = builder.get_object('settings-button')

        Lp().player.connect('party-changed', self._on_party_changed)

    def setup_menu_btn(self, menu):
        """
            Add an application menu to menu button
            @parma: menu as Gio.Menu
        """
        self._settings_button.show()
        self._settings_button.set_menu_model(menu)

    def on_status_changed(self, player):
        """
            Update buttons on status changed
            @param player as Player
        """
        if player.is_playing():
            # Party mode can be activated
            # via Fullscreen class, so check button state
            self._party_btn.set_active(player.is_party())

    def do_realize(self):
        """
            Show popover if needed
        """
        Gtk.Bin.do_realize(self)
        self._set_shuffle_icon()

    def on_next_changed(self, player):
        """
            Update buttons on current changed
            @param player as Player
        """
        # Do not show next popover non internal tracks as
        # tags will be readed on the fly
        if player.next_track.id is not None and\
           player.next_track.id >= 0 and\
           player.is_playing() and\
            (player.is_party() or
             Lp().settings.get_enum('shuffle') == Shuffle.TRACKS):
            self._pop_next.update()
            self._pop_next.set_relative_to(self)
            self._pop_next.show()
        else:
            self._pop_next.hide()

#######################
# PRIVATE             #
#######################
    def _set_shuffle_icon(self):
        """
            Set shuffle icon
        """
        shuffle = Lp().settings.get_enum('shuffle')
        if shuffle == Shuffle.NONE:
            self._shuffle_btn_image.get_style_context().remove_class(
                                                                    'selected')
            self._shuffle_btn_image.set_from_icon_name(
                "media-playlist-consecutive-symbolic",
                Gtk.IconSize.SMALL_TOOLBAR)
        else:
            self._shuffle_btn_image.set_from_icon_name(
                "media-playlist-shuffle-symbolic",
                Gtk.IconSize.SMALL_TOOLBAR)
            if shuffle in [Shuffle.TRACKS, Shuffle.TRACKS_ARTIST]:
                self._shuffle_btn_image.get_style_context().add_class(
                                                                    'selected')
            else:
                self._shuffle_btn_image.get_style_context().remove_class(
                                                                    'selected')
        if shuffle == Shuffle.TRACKS:
            if Lp().player.next_track.id is not None and\
               not self._pop_next.is_visible():
                self._pop_next.set_relative_to(self)
                self._pop_next.update()
                self._pop_next.show()
        elif Lp().player.is_playing():
            self._pop_next.set_relative_to(None)
            self._pop_next.hide()

    def _shuffle_btn_aspect(self, settings, value):
        """
            Mark shuffle button as active when shuffle active
            @param settings as Gio.Settings, value as str
        """
        self._set_shuffle_icon()

    def _activate_party_button(self, action=None, param=None):
        """
            Activate party button
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
        """
        self._party_btn.set_active(not self._party_btn.get_active())

    def _on_search_btn_clicked(self, obj, param=None):
        """
            Show search widget on search button clicked
            @param obj as Gtk.Button or Gtk.Action
        """
        self._search.show()

    def _on_queue_btn_clicked(self, button):
        """
            Show queue widget on queue button clicked
            @param button as Gtk.Button
        """
        queue = QueueWidget()
        queue.set_relative_to(self._queue_button)
        queue.populate()
        queue.show()

    def _on_party_btn_toggled(self, button):
        """
            Set party mode on if party button active
            @param obj as Gtk.button
        """
        active = self._party_btn.get_active()
        self._shuffle_btn.set_sensitive(not active)
        if not Lp().settings.get_value('dark-ui'):
            settings = Gtk.Settings.get_default()
            settings.set_property("gtk-application-prefer-dark-theme", active)
        is_playing = Lp().player.is_playing()
        Lp().player.set_party(active)
        if not active:
            self._pop_next.set_relative_to(None)
            self._pop_next.hide()
        elif is_playing and not self._pop_next.is_visible():
            self._pop_next.set_relative_to(self)
            self._pop_next.update()
            self._pop_next.show()

    def _on_party_changed(self, player, is_party):
        """
            On party change, sync toolbar
            @param player as Player
            @param is party as bool
        """
        if self._party_btn.get_active() != is_party:
            self._activate_party_button()
