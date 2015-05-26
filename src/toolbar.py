#!/usr/bin/python
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

from gi.repository import Gtk, Gdk, GLib, Gio

from gettext import gettext as _
from cgi import escape

from lollypop.define import Lp, Shuffle, ArtSize, Type
from lollypop.search import SearchWidget
from lollypop.pop_artist_infos import PopArtistInfos
from lollypop.pop_menu import PopToolbarMenu
from lollypop.queue import QueueWidget
from lollypop.utils import seconds_to_string
from lollypop.pop_albums import PopAlbums


# Show next track to play
class NextPopover(Gtk.Popover):
    """
        Init popover
    """
    def __init__(self):
        Gtk.Popover.__init__(self)
        self.set_modal(False)
        self.get_style_context().add_class('osd-popover')
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/NextPopover.ui')
        self.add(builder.get_object('widget'))
        self._title_label = builder.get_object('title')
        self._artist_label = builder.get_object('artist')
        self._cover = builder.get_object('cover')
        Lp.player.connect('queue-changed', self.update)

    """
        Update widget with current track
    """
    def update(self, player=None):
        self._artist_label.set_text(Lp.player.next_track.artist)
        self._title_label.set_text(Lp.player.next_track.title)
        art = Lp.art.get_album(Lp.player.next_track.album_id,
                         ArtSize.MEDIUM)
        if art is not None:
            self._cover.set_from_pixbuf(art)
            del art
            self._cover.set_tooltip_text(Lp.player.next_track.album)
            self._cover.show()
        else:
            self._cover.hide()


# Toolbar as headerbar
# Get real widget with Toolbar.widget
class Toolbar(Gtk.HeaderBar):
    """
        Init toolbar/headerbar ui
        @param app as Gtk.Application
    """
    def __init__(self, app):
        Gtk.HeaderBar.__init__(self)
        # Prevent updating progress while seeking
        self._seeking = False
        # Update pogress position
        self._timeout = None
        self._next_popover = NextPopover()

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/Toolbar.ui')
        builder.connect_signals(self)

        self._leftbar = builder.get_object('leftbar')
        self.pack_start(self._leftbar)
        self.pack_start(builder.get_object('titlebar'))
        self.pack_end(builder.get_object('rightbar'))
        self.set_custom_title(builder.get_object('title-box'))

        self._prev_btn = builder.get_object('previous_button')
        self._play_btn = builder.get_object('play_button')
        self._next_btn = builder.get_object('next_button')
        self._play_image = builder.get_object('play_image')
        self._pause_image = builder.get_object('pause_image')

        self._progress = builder.get_object('progress_scale')
        self._progress.set_sensitive(False)

        self._timelabel = builder.get_object('playback')
        self._total_time_label = builder.get_object('duration')

        self._title_label = builder.get_object('title')
        self._artist_label = builder.get_object('artist')
        self._cover = builder.get_object('cover')
        self._infobox = builder.get_object('infobox')
        self._infobox.set_property('has-tooltip', True)
        self._pop_albums = PopAlbums()
        self._pop_albums.set_relative_to(self._infobox)

        Lp.player.connect('status-changed', self._on_status_changed)
        Lp.player.connect('current-changed', self._on_current_changed)
        Lp.player.connect('party-changed', self._on_party_changed)
        Lp.art.connect('cover-changed', self._update_cover)

        self._shuffle_btn = builder.get_object('shuffle-button')
        self._shuffle_btn_image = builder.get_object('shuffle-button-image')
        self._set_shuffle_icon()
        Lp.settings.connect('changed::shuffle', self._shuffle_btn_aspect)

        self._party_btn = builder.get_object('party-button')
        party_action = Gio.SimpleAction.new('party', None)
        party_action.connect('activate', self._activate_party_button)
        app.add_action(party_action)
        app.set_accels_for_action("app.party", ["<Control>p"])

        search_button = builder.get_object('search-button')
        self._search = SearchWidget(self)
        self._search.set_relative_to(search_button)
        searchAction = Gio.SimpleAction.new('search', None)
        searchAction.connect('activate', self._on_search_btn_clicked)
        app.add_action(searchAction)
        app.set_accels_for_action("app.search", ["<Control>f"])

        queue_button = builder.get_object('queue-button')
        self._queue = QueueWidget()
        self._queue.set_relative_to(queue_button)

        if Lp.lastfm is not None:
            self._lastfm_btn = builder.get_object('lastfm_button')
            self._lastfm_btn.show()
        self._settings_button = builder.get_object('settings-button')

    """
        Here, we calculate height based on left widget
        We want to ignore titlebox height, like in original Gtk+ code
        Simplified version here
    """
    def do_get_preferred_height(self):
        style = self.get_style_context()
        padding = style.get_padding(Gtk.StateFlags.NORMAL)
        leftbar_height = self._leftbar.get_preferred_height()
        return (leftbar_height[0]+padding.top+padding.bottom,
                leftbar_height[1]+padding.top+padding.bottom )

    """
        Add an application menu to menu button
        @parma: menu as Gio.Menu
    """
    def setup_menu_btn(self, menu):
        self._settings_button.show()
        self._settings_button.set_menu_model(menu)

    """
        Set Gtk.Scale progress width
        @param width as int
    """
    def set_progress_width(self, width):
        self._progress.set_property("width_request", width)

    """
        Update progress bar position
        @param value as int
    """
    def update_position(self, value=None):
        if not self._seeking:
            if value is None:
                value = Lp.player.get_position_in_track()/1000000
            self._progress.set_value(value)
            self._timelabel.set_text(seconds_to_string(value/60))
        return True
#######################
# PRIVATE             #
#######################
    """
        Set shuffle icon
    """
    def _set_shuffle_icon(self):
        shuffle = Lp.settings.get_enum('shuffle')
        if shuffle == Shuffle.NONE:
            self._shuffle_btn_image.set_from_icon_name(
                                    "media-playlist-consecutive-symbolic",
                                    Gtk.IconSize.SMALL_TOOLBAR)
        else:
            self._shuffle_btn_image.set_from_icon_name(
                                    "media-playlist-shuffle-symbolic",
                                    Gtk.IconSize.SMALL_TOOLBAR)

    """
        Mark shuffle button as active when shuffle active
        @param settings as Gio.Settings, value as str
    """
    def _shuffle_btn_aspect(self, settings, value):
        self._set_shuffle_icon()

    """
        Update cover for album_id
        @param obj as unused, album id as int
    """
    def _update_cover(self, obj, album_id):
        if Lp.player.current_track.album_id == album_id:
            pixbuf = Lp.art.get_album(album_id, ArtSize.SMALL)
            self._cover.set_from_pixbuf(pixbuf)
            del pixbuf

    """
        Show next popover
    """
    def _show_next_popover(self):
        # Do not show next popover for external tracks as 
        # tags will be readed on the fly
        if Lp.player.next_track.id == Type.EXTERNAL:
            self._next_popover.hide()
        elif Lp.player.is_party() or\
           Lp.settings.get_enum('shuffle') == Shuffle.TRACKS:
            self._next_popover.update()
            if Lp.player.is_party():
                self._next_popover.set_relative_to(self._party_btn)
            else:
                self._next_popover.set_relative_to(self._shuffle_btn)
            self._next_popover.show()
    
    """
        On press, mark player as seeking
        @param unused
    """
    def _on_progress_press_button(self, scale, data):
        self._seeking = True

    """
        Callback for scale release button
        Seek player to scale value
        @param scale as Gtk.Scale, data as unused
    """
    def _on_progress_release_button(self, scale, data):
        value = scale.get_value()
        self._seeking = False
        self.update_position(value)
        Lp.player.seek(value/60)

    """
        Update toolbar items with track_id informations:
            - Cover
            - artist/title
            - reset progress bar
            - update time/total labels
        @param player as Player
    """
    def _on_current_changed(self, player):
        art = None
        if Lp.lastfm is not None:
            if player.current_track.id != Type.RADIOS:
                self._lastfm_btn.set_sensitive(True)
            else:
                self._lastfm_btn.set_sensitive(False)
        self._play_btn.set_sensitive(True)
        self._prev_btn.set_sensitive(True)
        self._next_btn.set_sensitive(True)
        prev_artist = escape(player.prev_track.artist)
        prev_title = escape(player.prev_track.title)
        next_artist = escape(player.next_track.artist)
        next_title = escape(player.next_track.title)
        self._next_btn.set_tooltip_markup("<b>%s</b> - %s" %\
                                          (next_artist,
                                           next_title))
        self._prev_btn.set_tooltip_markup("<b>%s</b> - %s" %\
                                          (prev_artist,
                                           prev_title))
        self._artist_label.set_text(player.current_track.artist)
        self._title_label.set_text(player.current_track.title)

        # Hide controls if on radio
        if player.current_track.id == Type.RADIOS:
            self._progress.set_sensitive(False)
            self._total_time_label.hide()
            self._timelabel.hide()
            self._progress.set_value(0.0)
            self._progress.set_range(0.0, 0.0)

        # Setup buttons and art for radios
        if player.current_track.id == Type.RADIOS:
            self._infobox.get_window().set_cursor(
                                      Gdk.Cursor(Gdk.CursorType.LEFT_PTR))

            art = Lp.art.get_radio(player.current_track.artist,
                                   ArtSize.SMALL)
        # Setup buttons and art for local playback
        elif player.current_track.id is not None:
            self._progress.set_value(0.0)
            self._progress.set_range(0.0, player.current_track.duration * 60)
            self._total_time_label.set_text(
                            seconds_to_string(player.current_track.duration))
            self._total_time_label.show()
            self._timelabel.set_text("0:00")
            self._timelabel.show()
            self._infobox.get_window().set_cursor(
                                    Gdk.Cursor(Gdk.CursorType.HAND1))
            art = Lp.art.get_album(player.current_track.album_id,
                             ArtSize.SMALL)
            self._show_next_popover()

        if art is not None:
            self._cover.set_from_pixbuf(art)
            del art
            self._cover.set_tooltip_text(player.current_track.album)
            self._cover.show()
        else:
            self._cover.hide()

    """
        Update buttons and progress bar
        @param player as Player
    """
    def _on_status_changed(self, player):
        is_playing = player.is_playing()

        if player.current_track.id != Type.RADIOS:
            self._progress.set_sensitive(is_playing)

        if is_playing:
            # Party mode can be activated
            # via Fullscreen class, so check button state
            self._party_btn.set_active(Lp.player.is_party())
            self._change_play_btn_status(self._pause_image, _("Pause"))
            if player.current_track.id == Type.RADIOS and self._timeout:
                GLib.source_remove(self._timeout)
                self._timeout = None
            elif not self._timeout:
                self._timeout = GLib.timeout_add(1000, self.update_position)
        else:
            self._change_play_btn_status(self._play_image, _("Play"))
            self.update_position()
            if self._timeout:
                GLib.source_remove(self._timeout)
                self._timeout = None


    """
        Previous track on prev button clicked
        @param button as Gtk.Button
    """
    def _on_prev_btn_clicked(self, button):
        Lp.player.prev()

    """
        Play/Pause on play button clicked
        @param button as Gtk.Button
    """
    def _on_play_btn_clicked(self, button):
        if Lp.player.is_playing():
            Lp.player.pause()
            self._change_play_btn_status(self._play_image, _("Play"))
        else:
            Lp.player.play()
            self._change_play_btn_status(self._pause_image, _("Pause"))

    """
        Next track on next button clicked
        @param button as Gtk.Button
    """
    def _on_next_btn_clicked(self, button):
        Lp.player.next()

    """
        Show search widget on search button clicked
        @param obj as Gtk.Button or Gtk.Action
    """
    def _on_search_btn_clicked(self, obj, param=None):
        self._search.show()

    """
        Show queue widget on queue button clicked
        @param button as Gtk.Button
    """
    def _on_queue_btn_clicked(self, button):
        self._queue.show()

    """
        Show current artist informations
        @param button as Gtk.Button
    """
    def _on_lastfm_btn_clicked(self, button):
        if Lp.lastfm is not None:
            if Lp.player.current_track.aartist_id == Type.COMPILATIONS:
                artist = Lp.player.current_track.artist
            else:
                artist = Lp.player.current_track.aartist
            popover = PopArtistInfos(artist, Lp.player.current_track.title)
            popover.set_relative_to(self._lastfm_btn)
            popover.populate()
            popover.show()

    """
        Pop albums from current artistleft click
        Show playlist menu on right
        @param widget as Gtk.EventBox
        @param event as Gdk.Event
    """
    def _on_infobox_clicked(self, widget, event):
        if Lp.player.current_track.id is not None and\
           Lp.player.current_track.id != Type.RADIOS:
            if event.button == 1:
                self._pop_albums.populate()
                self._pop_albums.show()
            else:
                menu = PopToolbarMenu(Lp.player.current_track.id, None)
                popover = Gtk.Popover.new_from_model(self._infobox, menu)
                popover.show()
            return True

    """
        Update play button with image and status as tooltip
        @param image as Gtk.Image
        @param status as str
    """
    def _change_play_btn_status(self, image, status):
        self._play_btn.set_image(image)
        self._play_btn.set_tooltip_text(status)

    """
        Activate party button
        @param action as Gio.SimpleAction
        @param param as GLib.Variant
    """
    def _activate_party_button(self, action=None, param=None):
        self._party_btn.set_active(not self._party_btn.get_active())

    """
        Set party mode on if party button active
        @param obj as Gtk.button
    """
    def _on_party_btn_toggled(self, button):
        active = self._party_btn.get_active()
        self._shuffle_btn.set_sensitive(not active)
        if not Lp.settings.get_value('dark-ui'):
            settings = Gtk.Settings.get_default()
            settings.set_property("gtk-application-prefer-dark-theme", active)
        Lp.player.set_party(active)
        # We need to show the popover only in this case
        # In other cases, "current-changed" will trigger it
        if active and Lp.player.is_playing():
            self._show_next_popover()

    """
        On party change, sync toolbar
        @param player as Player
        @param is party as bool
    """
    def _on_party_changed(self, player, is_party):
        # GTK fail to change colors on popover, so destroy it
        self._next_popover.destroy()
        self._next_popover = NextPopover()
        if self._party_btn.get_active() != is_party:
            self._activate_party_button()

    """
        Show tooltip if needed
        @param widget as Gtk.Widget
        @param x as int
        @param y as int
        @param keyboard as bool
        @param tooltip as Gtk.Tooltip
    """
    def _on_query_tooltip(self, widget, x, y, keyboard, tooltip):
        layout_title = self._title_label.get_layout()
        layout_artist = self._artist_label.get_layout()
        if layout_title.is_ellipsized() or layout_artist.is_ellipsized():
            artist = escape(self._artist_label.get_text())
            title = escape(self._title_label.get_text())
            self.set_tooltip_markup("<b>%s</b>\n%s" % (artist, title))
        else:
            self.set_tooltip_text('')
