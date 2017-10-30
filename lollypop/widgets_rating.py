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

from lollypop.objects import Track
from lollypop.define import Lp, Type
from lollypop.helper_dbus import DBusHelper


class RatingWidget(Gtk.Bin):
    """
        Rate widget
    """

    def __init__(self, object):
        """
            Init widget
            @param object as Track/Album
            @param is album as bool
        """
        Gtk.Bin.__init__(self)
        self.__object = object
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/RatingWidget.ui")
        builder.connect_signals(self)

        self._stars = []
        self._stars.append(builder.get_object("star0"))
        self._stars.append(builder.get_object("star1"))
        self._stars.append(builder.get_object("star2"))
        self._stars.append(builder.get_object("star3"))
        self._stars.append(builder.get_object("star4"))
        self._on_leave_notify(None, None)
        self.add(builder.get_object("widget"))
        if isinstance(object, Track):
            play_count = object.popularity
            self.set_tooltip_text(_("Song played %s times") % play_count)

#######################
# PROTECTED           #
#######################
    def _on_enter_notify(self, widget, event):
        """
            On enter notify, change star opacity
            @param widget as Gtk.EventBox
            @param event as Gdk.Event
        """
        event_star = widget.get_children()[0]
        # First star is hidden (used to clear score)
        if event_star.get_opacity() == 0.0:
            found = True
        else:
            found = False
        for star in self._stars:
            if found:
                star.set_opacity(0.2)
                star.get_style_context().remove_class("selected")
            else:
                star.get_style_context().add_class("selected")
                star.set_opacity(0.8)
            if star == event_star:
                found = True

    def _on_leave_notify(self, widget, event):
        """
            On leave notify, change star opacity
            @param widget as Gtk.EventBox (can be None)
            @param event as Gdk.Event (can be None)
        """
        user_rating = True
        rate = self.__object.get_rate()
        # -1 for compatiblity with previous release
        if rate in [0, -1]:
            rate = self.__object.get_popularity()
            user_rating = False
        if rate < 1:
            for i in range(5):
                self._stars[i].set_opacity(0.2)
                self._stars[i].get_style_context().remove_class("selected")
        else:
            star = self.__star_from_rate(rate)
            # Select wanted star
            for idx in range(0, star):
                widget = self._stars[idx]
                if user_rating:
                    widget.get_style_context().add_class("selected")
                else:
                    widget.get_style_context().remove_class("selected")
                widget.set_opacity(0.8)
            # Unselect others
            for idx in range(star, 5):
                self._stars[idx].set_opacity(0.2)
                self._stars[idx].get_style_context().remove_class("selected")

    def _on_button_press(self, widget, event):
        """
            On button press, set album popularity
            @param widget as Gtk.EventBox
            @param event as Gdk.Event
        """
        if Lp().scanner.is_locked():
            return
        user_rating = True
        rate = self.__object.get_rate()
        # -1 for compatiblity with previous release
        if rate in [0, -1]:
            rate = self.__object.get_popularity()
            user_rating = False
        max_star = self.__star_from_rate(rate)
        event_star = widget.get_children()[0]
        if event_star in self._stars:
            position = self._stars.index(event_star)
        else:
            position = -1
        pop = position + 1
        if event.button != 1:
            self.__object.set_popularity(pop)
        elif pop == 0 or pop == max_star:
            if user_rating:
                self.__object.set_rate(Type.NONE)
            else:
                self.__object.set_popularity(0)
            self._on_leave_notify(None, None)
        else:
            self.__object.set_rate(pop)

        # Save to tags if needed
        if Lp().settings.get_value("save-to-tags") and\
                isinstance(self.__object, Track) and\
                self.__object.id >= 0:
            dbus_helper = DBusHelper()
            dbus_helper.call("CanSetCover", None, self.__on_can_set_cover, pop)
        return True

#######################
# PRIVATE             #
#######################
    def __star_from_rate(self, rate):
        """
            Calculate stars from rate
            @param rate as double
            @return int
        """
        star = min(5, int(rate))
        return star

    def __on_can_set_cover(self, source, result, pop):
        """
            Remove album image from tags
            @param source as GObject.Object
            @param result as Gio.AsyncResult
            @param pop as int
        """
        try:
            can_set_cover = source.call_finish(result)
        except:
            can_set_cover = False
        if can_set_cover:
            if pop == 0:
                value = 0
            elif pop == 1:
                value = 1
            elif pop == 2:
                value = 64
            elif pop == 3:
                value = 128
            elif pop == 4:
                value = 196
            else:
                value = 255
            path = GLib.filename_from_uri(self.__object.uri)[0]
            dbus_helper = DBusHelper()
            dbus_helper.call("SetPopularity",
                             GLib.Variant("(is)", (value, path)),
                             None, None)
        return True
