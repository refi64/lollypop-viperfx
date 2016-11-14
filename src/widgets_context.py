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

from gi.repository import Gtk

from gettext import gettext as _

from lollypop.widgets_rating import RatingWidget
from lollypop.widgets_loved import LovedWidget
from lollypop.objects import Album
from lollypop.define import Lp


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


class ContextWidget(Gtk.Grid):
    """
        Context widget
    """

    def __init__(self, object):
        """
            Init widget
            @param object as Track/Album
        """
        Gtk.Grid.__init__(self)
        self._object = object

        playlist = HoverWidget('view-list-symbolic',
                               self.__show_playlist_manager)
        playlist.set_tooltip_text(_("Playlists"))
        playlist.show()

        rating = RatingWidget(object)
        rating.set_margin_top(5)
        rating.set_margin_bottom(5)
        rating.set_property('halign', Gtk.Align.START)
        rating.set_property('hexpand', True)
        rating.show()

        loved = LovedWidget(object.id)
        loved.set_margin_end(5)
        loved.set_margin_top(5)
        loved.set_margin_bottom(5)
        loved.show()

        self.set_property('halign', Gtk.Align.END)
        self.add(playlist)
        self.add(rating)
        self.add(loved)

#######################
# PRIVATE             #
#######################
    def __show_playlist_manager(self, args):
        """
            Show playlist manager
            @param args as []
        """
        Lp().window.show_playlist_manager(self._object.id,
                                          self._object.genre_ids,
                                          self._object.artist_ids,
                                          isinstance(self._object, Album))
