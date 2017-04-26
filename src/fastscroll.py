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
        self.__leave_timeout_id = None
        self.set_vexpand(True)
        self.set_margin_end(10)
        self.get_style_context().add_class("no-border")
        self.set_policy(Gtk.PolicyType.NEVER,
                        Gtk.PolicyType.EXTERNAL)
        self.set_property("halign", Gtk.Align.END)
        self.get_vscrollbar().hide()
        self.__chars = []
        self.__view = view
        self.__model = model
        self.__scrolled = scrolled
        self.__grid = Gtk.Grid()
        self.__grid.set_orientation(Gtk.Orientation.VERTICAL)
        self.__grid.set_property("valign", Gtk.Align.START)
        self.__grid.show()
        eventbox = Gtk.EventBox()
        eventbox.add(self.__grid)
        eventbox.connect("button-press-event", self.__on_button_press)
        eventbox.show()
        self.add(eventbox)
        scrolled.get_vadjustment().connect("value_changed", self.__on_scroll)
        self.connect("leave-notify-event", self.__on_leave_notify)

    def clear(self):
        """
            Clear values
        """
        for child in self.__grid.get_children():
            child.destroy()

    def clear_chars(self):
        """
            Clear chars
        """
        self.__chars = []

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
            label.set_markup('<span font="Monospace"><b>%s</b></span>' % c)
            label.show()
            self.__grid.add(label)
        GLib.idle_add(self.__check_value_to_mark)
        GLib.idle_add(self.__set_margin)

    def show(self):
        """
            Show widget, remove hide timeout if running
        """
        if self.__leave_timeout_id is not None:
            GLib.source_remove(self.__leave_timeout_id)
            self.__leave_timeout_id = None
        Gtk.ScrolledWindow.show(self)

    def hide(self):
        """
            Hide widget, clean timeout
        """
        self.__leave_timeout_id = None
        Gtk.ScrolledWindow.hide(self)

#######################
# PRIVATE             #
#######################
    def __set_margin(self):
        """
            Get top non static entry and set margin based on it position
        """
        for row in self.__model:
            if row[0] >= 0:
                margin = self.__view.get_background_area(row.path).y + 5
                if margin < 5:
                    margin = 5
                self.set_margin_top(margin)
                break

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
                # Check if start is non static:
                value = self.__get_value_for_path(start, 0)
                while value is not None and value < 0:
                    start.next()
                    value = self.__get_value_for_path(start, 0)
                # Check if end is really visible
                area = self.__view.get_cell_area(end)
                scrolled_allocation = self.__scrolled.get_allocation()
                if area.y + area.height / 2 > scrolled_allocation.height:
                    end.prev()
                start_value = self.__get_value_for_path(start, 3)
                end_value = self.__get_value_for_path(end, 3)
                if start_value is not None and end_value is not None:
                    start_value = noaccents(start_value[0]).upper()
                    end_value = noaccents(end_value[0]).upper()
                    self.__mark_values(start_value, end_value)
        except:
            pass  # get_visible_range() == None

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
                child.set_opacity(0.8)
                if label == chars[start_idx]:
                    y = child.translate_coordinates(self.__grid, 0, 0)[1]
                    self.get_vadjustment().set_value(y)
            else:
                child.set_opacity(0.2)

    def __get_value_for_path(self, path, pos):
        """
            Return value for path
            @param path as Gtk.TreePath
        """
        row = path[0]
        if row is not None:
            iter = self.__model.get_iter(row)
            value = self.__model.get_value(iter, pos)
            return value
        return None

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

    def __on_leave_notify(self, widget, event):
        """
            Force hide after a timeout that can be killed by show
        """
        if self.__leave_timeout_id is not None:
            GLib.source_remove(self.__leave_timeout_id)
            self.__leave_timeout_id = None
        self.__leave_timeout_id = GLib.timeout_add(250, self.hide)

    def __on_scroll(self, adj):
        """
            Show a popover with current letter
            @param adj as Gtk.Adjustement
        """
        GLib.idle_add(self.__check_value_to_mark)
        GLib.idle_add(self.__set_margin)
