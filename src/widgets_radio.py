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


# Radio widget is a pixbuf with one label: radio name
class RadioWidget:
    """
        Init radio widget
        @param name as string
        @param uri as string 
    """
    def __init__(self, name, uri):
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/RadioWidget.ui')
        builder.connect_signals(self)
        self._cover = builder.get_object('cover')

        self._name = name
        self._uri = uri

        title = builder.get_object('title')
        title.set_label(name)

        self.add(builder.get_object('widget'))
        self.set_cover()

    def do_get_preferred_width(self):
        return (ArtSize.BIG+ArtSize.BORDER*2, ArtSize.BIG+ArtSize.BORDER*2)

    """
        Set cover for album if state changed
        @param force as bool
    """
    def set_cover(self, force=False):
        selected = Objects.player.current.id == Navigation.RADIOS and\
                   self._name == Objects.player.current.title
        if self._cover and (selected != self._selected or force):
            self._selected = selected
            pixbuf = Objects.art.get_radio(self._name,
                                           ArtSize.BIG,
                                           selected)
            self._cover.set_from_pixbuf(pixbuf)
            del pixbuf

    """
        Update cover for album id id needed
        @param album id as int
    """
    def update_cover(self, album_id):
        if self._cover and self._album_id == album_id:
            self._selected = Objects.player.current.id == Navigation.RADIOS\
                             and self._name == Objects.player.current.title
            pixbuf = Objects.art.get_radio(self._name,
                                           ArtSize.BIG,
                                           self._selected)
            self._cover.set_from_pixbuf(pixbuf)
            del pixbuf

#######################
# PRIVATE             #
#######################
    """
        Show popup
    """
    
