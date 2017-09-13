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

from lollypop.widgets_rating import RatingWidget
from lollypop.widgets_loved import LovedWidget
from lollypop.objects import Album
from lollypop.sqlcursor import SqlCursor
from lollypop.define import Lp
from lollypop.helper_dbus import DBusHelper


class HoverWidget(Gtk.EventBox):
    """
        Hover widget
    """

    def __init__(self, name, func, *args):
        """
            Init widget
            @param name as str
            @param func as function
            @param args
        """
        Gtk.EventBox.__init__(self)
        self.__func = func
        self.__args = args
        image = Gtk.Image.new_from_icon_name(name, Gtk.IconSize.MENU)
        image.show()
        self.add(image)
        self.set_opacity(0.2)
        self.connect("enter-notify-event", self.__on_enter_notify)
        self.connect("leave-notify-event", self.__on_leave_notify)
        self.connect("button-press-event", self.__on_button_press)

#######################
# PRIVATE             #
#######################
    def __on_enter_notify(self, widget, event):
        """
            On enter notify, change love opacity
            @param widget as Gtk.EventBox
            @param event as Gdk.Event
        """
        self.set_opacity(0.8)

    def __on_leave_notify(self, widget, event):
        """
            On leave notify, change love opacity
            @param widget as Gtk.EventBox (can be None)
            @param event as Gdk.Event (can be None)
        """
        self.set_opacity(0.2)

    def __on_button_press(self, widget, event):
        """
            On button press, toggle loved status
            @param widget as Gtk.EventBox
            @param event as Gdk.Event
        """
        self.__func(self.__args)
        return True


class ContextWidget(Gtk.Grid):
    """
        Context widget
    """

    def __init__(self, object, button):
        """
            Init widget
            @param object as Track/Album
            @param button as Gtk.Button
        """
        Gtk.Grid.__init__(self)
        self.__object = object
        self.__button = button

        # Check portal for tag editor
        dbus_helper = DBusHelper()
        dbus_helper.call("CanLaunchTagEditor", None,
                         self.__on_can_launch_tag_editor, None)
        self.__edit = HoverWidget("document-properties-symbolic",
                                  self.__edit_tags)
        self.__edit.set_tooltip_text(_("Modify information"))
        self.__edit.set_margin_end(10)
        self.add(self.__edit)

        playlist = HoverWidget("view-list-symbolic",
                               self.__show_playlist_manager)
        playlist.set_tooltip_text(_("Add to playlist"))
        playlist.show()
        self.add(playlist)

        if isinstance(self.__object, Album):
            if Lp().player.album_in_queue(self.__object):
                queue = HoverWidget("list-remove-symbolic",
                                    self.__add_to_queue)
                queue.set_tooltip_text(_("Remove from queue"))
            else:
                queue = HoverWidget("list-add-symbolic", self.__add_to_queue)
                queue.set_tooltip_text(_("Add to queue"))
            queue.set_margin_start(10)
            queue.show()
            self.add(queue)
        else:
            rating = RatingWidget(object)
            rating.set_margin_top(5)
            rating.set_margin_end(10)
            rating.set_margin_bottom(5)
            rating.set_property("halign", Gtk.Align.END)
            rating.set_property("hexpand", True)
            rating.show()

            loved = LovedWidget(object)
            loved.set_margin_end(5)
            loved.set_margin_top(5)
            loved.set_margin_bottom(5)
            loved.show()

            self.add(rating)
            self.add(loved)

#######################
# PRIVATE             #
#######################
    def __save_object(self, args):
        """
            Save object
            @param args as []
        """
        genre_id = Lp().genres.get_id("Web")
        if genre_id is None:
            genre_id = Lp().genres.add("Web")
            Lp().scanner.emit("genre-updated", genre_id, True)
        Lp().albums.del_genres(self.__object.id)
        Lp().albums.add_genre(self.__object.id, genre_id)
        for track_id in self.__object.track_ids:
            Lp().tracks.del_genres(track_id)
            Lp().tracks.add_genre(track_id, genre_id)
        with SqlCursor(Lp().db) as sql:
            sql.commit()
        Lp().scanner.emit("album-updated", self.__object.id, True)

    def __remove_object(self, args):
        """
            Remove object
            @param args as []
        """
        self.__object.remove()

    def __edit_tags(self, args):
        """
            Run tags editor
            @param args as unused
        """
        path = GLib.filename_from_uri(self.__object.uri)[0]
        dbus_helper = DBusHelper()
        dbus_helper.call("LaunchTagEditor", GLib.Variant("(s)", (path,)),
                         None, None)
        self.__button.emit("clicked")

    def __add_to_queue(self, args):
        """
            Add album to queue
            @param args as []
        """
        album_in_queue = Lp().player.album_in_queue(self.__object)
        for track_id in self.__object.track_ids:
            if album_in_queue:
                Lp().player.del_from_queue(track_id, False)
            else:
                Lp().player.append_to_queue(track_id, False)
        Lp().player.emit("queue-changed")
        self.__button.emit("clicked")

    def __show_playlist_manager(self, args):
        """
            Show playlist manager
            @param args as []
        """
        Lp().window.show_playlist_manager(self.__object.id,
                                          self.__object.genre_ids,
                                          self.__object.artist_ids,
                                          isinstance(self.__object, Album))
        self.__button.emit("clicked")

    def __on_can_launch_tag_editor(self, source, result, data):
        """
            Add action if launchable
            @param source as GObject.Object
            @param result as Gio.AsyncResult
            @param data as object
        """
        try:
            if source.call_finish(result)[0]:
                self.__edit.show()
        except Exception as e:
            print("EditMenu::__on_can_launch_tag_editor():", e)
