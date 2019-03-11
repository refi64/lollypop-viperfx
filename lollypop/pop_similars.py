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

from gi.repository import Gtk, Gio, GLib, Pango

from lollypop.define import App, ArtSize
from lollypop.utils import get_network_available
from lollypop.widgets_utils import Popover
from lollypop.logger import Logger


class ArtistRow(Gtk.ListBoxRow):
    """
        An artist row
    """

    def __init__(self, artist_name):
        """
            Init row
            @param artist_name as str
        """
        Gtk.ListBoxRow.__init__(self)
        self.__artist_name = artist_name
        grid = Gtk.Grid()
        grid.set_column_spacing(5)
        label = Gtk.Label.new(artist_name)
        label.set_property("halign", Gtk.Align.START)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        self.__artwork = Gtk.Image.new()
        self.__artwork.set_size_request(ArtSize.ARTIST_SMALL,
                                        ArtSize.ARTIST_SMALL)
        App().art_helper.set_artist_artwork(artist_name,
                                            ArtSize.ARTIST_SMALL,
                                            ArtSize.ARTIST_SMALL,
                                            self.get_scale_factor(),
                                            self.__on_artist_artwork)
        grid.add(self.__artwork)
        grid.add(label)
        grid.show_all()
        self.add(grid)

    @property
    def artist_name(self):
        """
            Get artist name
            @return str
        """
        return self.__artist_name

#######################
# PRIVATE             #
#######################
    def __on_artist_artwork(self, surface):
        """
            Set artist artwork
            @param surface as cairo.Surface
        """
        if surface is None:
            self.__artwork.get_style_context().add_class("artwork-icon")
            self.__artwork.set_from_icon_name("avatar-default-symbolic",
                                              Gtk.IconSize.INVALID)
            self.__artwork.set_pixel_size(ArtSize.ARTIST_SMALL)
        else:
            self.__artwork.set_from_surface(surface)


class SimilarsPopover(Popover):
    """
        A popover with similar artists
    """

    def __init__(self):
        """
            Init popover
        """
        Popover.__init__(self)
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/SimilarsPopover.ui")
        self.__show_all = GLib.find_program_in_path("youtube-dl") is not None
        self.__added = []
        self.__cancellable = Gio.Cancellable()
        self.connect("map", self.__on_map)
        self.connect("unmap", self.__on_unmap)
        self.__stack = builder.get_object("stack")
        self.__spinner = builder.get_object("spinner")
        self.__spinner.start()
        self.__listbox = Gtk.ListBox()
        self.__listbox.get_style_context().add_class("trackswidget")
        self.__listbox.set_vexpand(True)
        self.__listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.__listbox.set_activate_on_single_click(True)
        self.__listbox.connect("row-activated", self.__on_row_activated)
        self.__listbox.show()
        self.__stack.add(self.__listbox)
        self.add(builder.get_object("widget"))

    def populate(self, artist_ids):
        """
            Populate view artist ids
            @param artist ids as int
        """
        if get_network_available():
            artists = []
            for artist_id in artist_ids:
                artist_name = App().artists.get_name(artist_id)
                artists.append(artist_name)
                App().spotify.get_artist_id(artist_name,
                                            self.__on_get_artist_id)
        if App().lastfm is not None:
            App().task_helper.run(self.__get_lastfm_similars, artists,
                                  self.get_scale_factor(),
                                  callback=(self.__populate,))

#######################
# PRIVATE             #
#######################
    def __get_lastfm_similars(self, artists, scale_factor):
        """
            Get similars artists from lastfm
            @param artists as [str]
            @param scale_factor as int
            @return [str]
        """
        similars = []
        for artist in artists:
            if not self.__cancellable.is_cancelled():
                similars += App().lastfm.get_similars(artist,
                                                      scale_factor,
                                                      self.__cancellable)
        Logger.info("SimilarsPopover::Last.fm: %s" % similars)
        return similars

    def __populate(self, artists):
        """
            Populate view with artists
            @param artists as [str]
        """
        if artists:
            artist = artists.pop(0)
            if artist in self.__added:
                GLib.idle_add(self.__populate, artists)
                return
            self.__added.append(artist)
            artist_id = App().artists.get_id(artist)
            row = None
            if artist_id is not None:
                # We want real artist name (with case)
                artist_name = App().artists.get_name(artist_id)
                albums = App().artists.get_albums([artist_id])
                if albums:
                    row = ArtistRow(artist_name)
            elif self.__show_all:
                row = ArtistRow(artist)
            if row is not None:
                row.show()
                self.__listbox.add(row)
            GLib.idle_add(self.__populate, artists)
        else:
            if self.__listbox.get_children():
                self.__stack.set_visible_child(self.__listbox)
            else:
                self.__stack.set_visible_child_name("no-result")

    def __on_get_artist_id(self, artist_id):
        """
            Get similars
            @param artist_id as str
        """
        App().task_helper.run(App().spotify.get_similar_artists, artist_id,
                              self.get_scale_factor(),
                              self.__cancellable,
                              callback=(self.__populate,))

    def __on_map(self, widget):
        """
            Resize widget on map
            @param widget as Gtk.Widget
        """
        self.set_size_request(300, 400)

    def __on_unmap(self, widget):
        """
            Cancel loading
            @param widget as Gtk.Widget
        """
        self.__cancellable.cancel()

    def __on_row_activated(self, widget, row):
        """
            Play searched item when selected
            @param widget as Gtk.ListBox
            @param row as Gtk.ListBoxRow
        """
        self.popdown()
        artist_name = row.artist_name
        artist_id = App().artists.get_id(artist_name)
        if artist_id is None:
            App().lookup_action("search").activate(GLib.Variant("s",
                                                                artist_name))
        else:
            GLib.idle_add(App().window.container.show_artist_view, [artist_id])
