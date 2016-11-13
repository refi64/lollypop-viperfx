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

from gi.repository import Gtk, GLib

from gettext import gettext as _

from lollypop.widgets_rating import RatingWidget
from lollypop.widgets_loved import LovedWidget
from lollypop.objects import Album
from lollypop.define import Lp, TAG_EDITORS


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
        self.set_opacity(0.1)
        self.connect('enter-notify-event', self.__on_enter_notify)
        self.connect('leave-notify-event', self.__on_leave_notify)
        self.connect('button-press-event', self.__on_button_press)

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
        self.set_opacity(0.1)

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

        # Search for tag editor
        self.__tag_editor = None
        favorite = Lp().settings.get_value('tag-editor').get_string()
        for editor in [favorite] + TAG_EDITORS:
            if GLib.find_program_in_path(editor) is not None:
                self.__tag_editor = editor
        if self.__tag_editor is not None:
            edit = HoverWidget('document-properties-symbolic',
                               self.__edit_tags)
            edit.set_tooltip_text(_("Modify information"))
            edit.set_margin_end(10)
            edit.show()

        playlist = HoverWidget('view-list-symbolic',
                               self.__show_playlist_manager)
        playlist.set_tooltip_text(_("Playlists"))
        playlist.show()

        rating = RatingWidget(object)
        rating.set_margin_top(5)
        rating.set_margin_bottom(5)
        rating.set_property('halign', Gtk.Align.END)
        rating.set_property('hexpand', True)
        rating.show()

        loved = LovedWidget(object.id)
        loved.set_margin_end(5)
        loved.set_margin_top(5)
        loved.set_margin_bottom(5)
        loved.show()

        self.set_property('halign', Gtk.Align.END)
        if self.__tag_editor is not None:
            self.add(edit)
        self.add(playlist)
        self.add(rating)
        self.add(loved)

#######################
# PRIVATE             #
#######################
    def __edit_tags(self, args):
        """
            Edit tags
            @param args as []
        """
        try:
            argv = [self.__tag_editor,
                    GLib.filename_from_uri(self.__object.uri)[0], None]
            GLib.spawn_async_with_pipes(
                                    None, argv, None,
                                    GLib.SpawnFlags.SEARCH_PATH |
                                    GLib.SpawnFlags.DO_NOT_REAP_CHILD, None)
        except:
            pass
        self.__button.emit('clicked')

    def __show_playlist_manager(self, args):
        """
            Show playlist manager
            @param args as []
        """
        Lp().window.show_playlist_manager(self.__object.id,
                                          self.__object.genre_ids,
                                          self.__object.artist_ids,
                                          isinstance(self.__object, Album))
        self.__button.emit('clicked')
