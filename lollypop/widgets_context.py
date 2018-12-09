# Copyright (c) 2014-2018 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from lollypop.widgets_rating import RatingWidget
from lollypop.widgets_loved import LovedWidget
from lollypop.objects import Album, Track, Disc
from lollypop.define import App
from lollypop.logger import Logger


class ContextWidget(Gtk.EventBox):
    """
        Context widget
    """

    def __init__(self, object, button):
        """
            Init widget
            @param object as Track/Album
            @param button as Gtk.Button
        """
        Gtk.EventBox.__init__(self)
        self.__object = object
        self.__button = button

        self.connect("button-release-event", self.__on_button_release_event)

        grid = Gtk.Grid()
        grid.show()

        if isinstance(object, Disc):
            play_button = Gtk.Button.new_from_icon_name(
                "media-playback-start-symbolic",
                Gtk.IconSize.BUTTON)
            play_button.connect("clicked", self.__on_play_button_clicked)
            play_button.get_style_context().add_class("dim-button")
            play_button.set_tooltip_text(_("Play"))
            play_button.set_margin_end(2)
            play_button.show()
            grid.add(play_button)
        else:
            edit_button = Gtk.Button.new_from_icon_name(
                "document-properties-symbolic",
                Gtk.IconSize.BUTTON)
            edit_button.connect("clicked", self.__on_edit_button_clicked)
            edit_button.get_style_context().add_class("dim-button")
            edit_button.set_tooltip_text(_("Modify information"))
            edit_button.set_margin_end(2)
            grid.add(edit_button)
            # Check portal for tag editor
            if App().art.tag_editor:
                edit_button.show()

        if isinstance(object, Track):
            add_to_queue = True
            string = _("Add to queue")
            icon = "zoom-in-symbolic"
            if App().player.track_in_queue(self.__object):
                add_to_queue = False
                string = _("Remove from queue")
                icon = "zoom-out-symbolic"
            queue_button = Gtk.Button.new_from_icon_name(icon,
                                                         Gtk.IconSize.BUTTON)
            queue_button.connect("clicked",
                                 self.__on_queue_button_clicked,
                                 add_to_queue)
            queue_button.get_style_context().add_class("dim-button")
            queue_button.set_tooltip_text(string)
            queue_button.set_margin_end(2)
            queue_button.show()
            grid.add(queue_button)
        else:
            add = True
            string = _("Add to current playlist")
            icon = "list-add-symbolic"
            # Search album in player
            if isinstance(object, Disc):
                album = object.album
            else:
                album = object
            player_album_track_ids = []
            for _album in App().player.albums:
                if album.id == _album.id:
                    player_album_track_ids += _album.track_ids
            if len(set(player_album_track_ids) &
                    set(object.track_ids)) == len(object.track_ids):
                add = False
                string = _("Remove from current playlist")
                icon = "list-remove-symbolic"
            current_playlist_button = Gtk.Button.new_from_icon_name(
                icon,
                Gtk.IconSize.BUTTON)
            current_playlist_button.connect(
                                    "clicked",
                                    self.__on_current_playlist_button_clicked,
                                    add)
            current_playlist_button.get_style_context().add_class("dim-button")
            current_playlist_button.set_tooltip_text(string)
            current_playlist_button.set_margin_end(2)
            current_playlist_button.show()
            grid.add(current_playlist_button)

        playlist_button = Gtk.Button.new_from_icon_name("view-list-symbolic",
                                                        Gtk.IconSize.BUTTON)
        playlist_button.connect("clicked", self.__on_playlist_button_clicked)
        playlist_button.get_style_context().add_class("dim-button")
        playlist_button.set_tooltip_text(_("Add to playlist"))
        playlist_button.show()
        grid.add(playlist_button)

        if isinstance(self.__object, Track):
            rating = RatingWidget(object)
            rating.set_margin_end(2)
            rating.set_property("halign", Gtk.Align.END)
            rating.set_property("hexpand", True)
            rating.show()
            loved = LovedWidget(object)
            loved.set_margin_end(2)
            loved.show()
            grid.add(rating)
            grid.add(loved)
        self.add(grid)

#######################
# PRIVATE             #
#######################
    def __on_button_release_event(self, widget, event):
        """
            Block signal
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        return True

    def __on_play_button_clicked(self, button):
        """
            Play disc
            @param button as Gtk.Button
        """
        try:
            App().player.clear_albums()
            album = Album(self.__object.album.id)
            # search wanted disc
            for disc in album.discs:
                if disc.number == self.__object.number:
                    album.set_tracks(disc.tracks)
                    break
            App().player.add_album(album)
            App().player.load(album.tracks[0])
        except Exception as e:
            Logger.error("ContextWidget::__on_play_button_clicked(): %s", e)

    def __on_queue_button_clicked(self, button, add_to_queue):
        """
            Add or remove track to/from queue
            @param button as Gtk.Button
            @param add_to_queue as bool
        """
        if isinstance(self.__object, Album):
            for track_id in self.__object.track_ids:
                if add_to_queue:
                    App().player.append_to_queue(track_id, False)
                else:
                    App().player.remove_from_queue(track_id, False)
        elif isinstance(self.__object, Track):
            if add_to_queue:
                App().player.append_to_queue(self.__object.id, False)
            else:
                App().player.remove_from_queue(self.__object.id, False)
        App().player.emit("queue-changed")
        self.hide()

    def __on_current_playlist_button_clicked(self, button, add):
        """
            Add to/remove from current playback
            @param button as Gtk.Button
            @param add as bool
        """
        if isinstance(self.__object, Disc):
            album = self.__object.album.clone(True)
            album.set_discs([self.__object])
        else:
            album = self.__object.clone(True)
        if add:
            App().player.add_album(album)
        elif isinstance(self.__object, Disc):
            App().player.remove_disc(self.__object, album.id)
        else:
            App().player.remove_album_by_id(album.id)
        self.hide()

    def __on_edit_button_clicked(self, button):
        """
            Run tags editor
            @param button as Gtk.Button
        """
        path = GLib.filename_from_uri(self.__object.uri)[0]
        if GLib.find_program_in_path("flatpak-spawn") is not None:
            argv = ["flatpak-spawn", "--host", App().art.tag_editor, path]
        else:
            argv = [App().art.tag_editor, path]
        try:
            (pid, stdin, stdout, stderr) = GLib.spawn_async(
                argv, flags=GLib.SpawnFlags.SEARCH_PATH |
                GLib.SpawnFlags.STDOUT_TO_DEV_NULL,
                standard_input=False,
                standard_output=False,
                standard_error=False
            )
        except Exception as e:
            Logger.error("ContextWidget::__on_edit_button_clicked(): %s" % e)
        self.hide()

    def __on_playlist_button_clicked(self, button):
        """
            Show playlist_button manager
            @param button as Gtk.Button
        """
        App().window.container.show_playlist_manager(self.__object)
        self.hide()
