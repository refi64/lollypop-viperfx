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
from lollypop.objects import Album, Track
from lollypop.define import App, TAG_EDITORS
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
        self.connect("enter-notify-event", self.__on_enter_notify_event)
        self.connect("leave-notify-event", self.__on_leave_notify_event)
        self.connect("button-press-event", self.__on_button_press_event)

#######################
# PRIVATE             #
#######################
    def __on_enter_notify_event(self, widget, event):
        """
            On enter notify, change love opacity
            @param widget as Gtk.EventBox
            @param event as Gdk.Event
        """
        self.set_opacity(0.8)

    def __on_leave_notify_event(self, widget, event):
        """
            On leave notify, change love opacity
            @param widget as Gtk.EventBox (can be None)
            @param event as Gdk.Event (can be None)
        """
        self.set_opacity(0.2)

    def __on_button_press_event(self, widget, event):
        """
            On button press, toggle loved status
            @param widget as Gtk.EventBox
            @param event as Gdk.Event
        """
        self.__func(self, *self.__args)
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

        # Search for available tag editors
        self.__editor = App().settings.get_value("tag-editor").get_string()
        if not self.__editor:
            for tag_editor in TAG_EDITORS:
                if GLib.find_program_in_path(tag_editor) is not None:
                    self.__editor = tag_editor
                    break

        # Check portal for tag editor
        dbus_helper = DBusHelper()
        dbus_helper.call("CanLaunchTagEditor",
                         GLib.Variant("(s)", (self.__editor,)),
                         self.__on_can_launch_tag_editor, None)
        self.__edit = HoverWidget("document-properties-symbolic",
                                  self.__edit_tags)
        self.__edit.set_tooltip_text(_("Modify information"))
        self.__edit.set_margin_end(10)
        self.add(self.__edit)

        add_to_queue = True
        string = _("Add to queue")
        icon = "list-add-symbolic"
        if isinstance(self.__object, Album):
            if App().player.album_in_queue(self.__object):
                add_to_queue = False
                string = _("Remove from queue")
                icon = "list-remove-symbolic"
        elif isinstance(self.__object, Track):
            if App().player.track_in_queue(self.__object):
                add_to_queue = False
                string = _("Remove from queue")
                icon = "list-remove-symbolic"
        self.__queue = HoverWidget(icon,
                                   self.__queue_track,
                                   add_to_queue)
        self.__queue.get_style_context().add_class("selected")
        self.__queue.set_tooltip_text(string)
        self.__queue.set_margin_end(10)
        self.__queue.show()
        self.add(self.__queue)

        playlist = HoverWidget("view-list-symbolic",
                               self.__show_playlist_manager)
        playlist.set_tooltip_text(_("Add to playlist"))
        playlist.show()
        self.add(playlist)

        if isinstance(self.__object, Track):
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
    def __queue_track(self, hover_widget, add_to_queue):
        """
            Add or remove track to/from queue
            @param hover_widget as HoverWidget
            @param add_to_queue as bool
        """
        if isinstance(self.__object, Album):
            for track_id in self.__object.track_ids:
                if add_to_queue:
                    App().player.append_to_queue(track_id, False)
                else:
                    App().player.del_from_queue(track_id, False)
        elif isinstance(self.__object, Track):
            if add_to_queue:
                App().player.append_to_queue(self.__object.id, False)
            else:
                App().player.del_from_queue(self.__object.id, False)
        App().player.emit("queue-changed")
        self.__button.emit("clicked")

    def __edit_tags(self, hover_widget):
        """
            Run tags editor
            @param hover_widget as HoverWidget
        """
        path = GLib.filename_from_uri(self.__object.uri)[0]
        dbus_helper = DBusHelper()
        dbus_helper.call("LaunchTagEditor",
                         GLib.Variant("(ss)", (self.__editor, path)),
                         None, None)
        self.__button.emit("clicked")

    def __show_playlist_manager(self, hover_widget):
        """
            Show playlist manager
            @param hover_widget as HoverWidget
        """
        App().window.container.show_playlist_manager(
                                          self.__object.id,
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
            source_result = source.call_finish(result)
            if source_result is not None and source_result[0]:
                self.__edit.show()
        except Exception as e:
            print("EditMenu::__on_can_launch_tag_editor():", e)
