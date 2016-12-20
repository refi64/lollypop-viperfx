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

from locale import strxfrm

from lollypop.utils import noaccents


class FastScroll(Gtk.ScrolledWindow):
    """
        Widget showing letter and allowing fast scroll on click
        Do not call show on widget, not needed
    """

    def __init__(self, view, model, scrolled):
        """
            Init widget
            @param view as Gtk.TreeView
            @param model as Gtk.ListStore
            @param scrolled as Gtk.ScrolledWindow
        """
        Gtk.ScrolledWindow.__init__(self)
        self.__hide_id = None
        self.__in_widget = False
        self.set_vexpand(True)
        self.set_margin_end(10)
        self.get_style_context().add_class('fastscroll')
        self.set_policy(Gtk.PolicyType.NEVER,
                        Gtk.PolicyType.AUTOMATIC)
        self.set_property('halign', Gtk.Align.END)
        self.__chars = []
        self.__view = view
        self.__model = model
        self.__scrolled = scrolled
        self.__grid = Gtk.Grid()
        self.__grid.set_orientation(Gtk.Orientation.VERTICAL)
        self.__grid.set_property('valign', Gtk.Align.END)
        self.__grid.show()
        eventbox = Gtk.EventBox()
        eventbox.add(self.__grid)
        eventbox.connect('button-press-event', self.__on_button_press)
        eventbox.show()
        self.add(eventbox)
        scrolled.get_vadjustment().connect('value_changed', self.__on_scroll)

    def clear(self):
        """
            Clear values
        """
        for child in self.__grid.get_children():
            child.destroy()
        self.__chars = []
        self.hide()

    def add_char(self, c):
        """
            Add a char to widget, will not be shown
            @param c as char
        """
        to_add = noaccents(c.upper())
        if to_add not in self.__chars:
            self.__chars.append(to_add)

    def populate(self):
        """
            Populate widget based on current chars
        """
        for c in sorted(self.__chars, key=strxfrm):
            label = Gtk.Label()
            label.set_markup("<span font='Monospace'><b>%s</b></span>" % c)
            label.show()
            self.__grid.add(label)
        GLib.idle_add(self.__check_value_to_mark)

#######################
# PRIVATE             #
#######################
    def __check_value_to_mark(self):
        """
            Look at visible treeview range, and mark char as needed
        """
        try:
            (start, end) = self.__view.get_visible_range()
            # As start may not really visible, use next
            # start.next()
            if start is not None and end is not None:
                # Check if start is really visible
                area = self.__view.get_cell_area(start)
                if area.y + area.height / 2 < 0:
                    start.next()
                # Check if end is really visible
                area = self.__view.get_cell_area(end)
                scrolled_allocation = self.__scrolled.get_allocation()
                if area.y + area.height / 2 > scrolled_allocation.height:
                    end.prev()
                start_row = start[0]
                end_row = end[0]
                if start_row is not None and end_row is not None:
                    start_iter = self.__model.get_iter(start_row)
                    end_iter = self.__model.get_iter(end_row)
                    start_value = noaccents(
                            self.__model.get_value(start_iter, 3))[0].upper()
                    end_value = noaccents(
                            self.__model.get_value(end_iter, 3))[0].upper()
                    self.__mark_values(start_value, end_value)
        except Exception as e:
            print("FastScroll::__check_value_to_mark()", e)

    def __mark_values(self, start, end):
        """
            Mark values
            @param start as char
            @param end as char
        """
        chars = sorted(self.__chars, key=strxfrm)
        start_idx = chars.index(start)
        end_idx = chars.index(end)
        selected = chars[start_idx:end_idx+1]
        for child in self.__grid.get_children():
            label = child.get_text()
            mark = True if label in selected else False
            if mark:
                child.get_style_context().remove_class('dim-label')
            else:
                child.get_style_context().add_class('dim-label')

    def __on_button_press(self, eventbox, event):
        """
            Scroll to activated child char
        """
        char = None
        for child in self.__grid.get_children():
            allocation = child.get_allocation()
            if event.x >= allocation.x and\
               event.x <= allocation.x + allocation.width and\
               event.y >= allocation.y and\
               event.y <= allocation.y + allocation.height:
                char = child.get_text()
                break
        if char is not None:
            for row in self.__model:
                if row[0] < 0:
                    continue
                if noaccents(row[3])[0].upper() == char:
                    self.__view.scroll_to_cell(self.__model.get_path(row.iter),
                                               None, True, 0, 0)
                    break

    def __on_scroll(self, adj):
        """
            Show a popover with current letter
            @param adj as Gtk.Adjustement
        """
        self.__check_value_to_mark()
