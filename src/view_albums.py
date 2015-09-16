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

from gi.repository import Gtk, GLib, Gdk

from threading import Thread

from lollypop.view import View
from lollypop.pop_infos import InfosPopover
from lollypop.view_container import ViewContainer
from lollypop.widgets_album import AlbumSimpleWidget, AlbumDetailedWidget
from lollypop.define import Lp, Type, ArtSize


class ArtistView(View):
    """
        Show artist albums and tracks
    """

    try:
        from lollypop.wikipedia import Wikipedia
    except:
        Wikipedia = None

    def __init__(self, artist_id, genre_id):
        """
            Init ArtistView
            @param artist id as int
            @param genre id as int
        """
        View.__init__(self)
        self._artist_id = artist_id
        self._genre_id = genre_id
        self._signal_id = None

        self._artist_name = Lp.artists.get_name(artist_id)
        if Lp.lastfm is not None or self.Wikipedia is not None:
            self._popover = InfosPopover(self._artist_name)
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/ArtistView.ui')
        builder.connect_signals(self)
        self.attach(builder.get_object('ArtistView'), 0, 0, 1, 1)
        builder.get_object('artist').set_label(self._artist_name)

        self._pop_allowed = True

        self._albumbox = Gtk.Grid()
        self._albumbox.set_row_spacing(20)
        self._albumbox.set_property("orientation", Gtk.Orientation.VERTICAL)
        self._albumbox.show()

        self._scrolledWindow.set_property('expand', True)
        self._viewport.set_property("valign", Gtk.Align.START)
        self._viewport.add(self._albumbox)
        self.add(self._scrolledWindow)

    def populate(self, albums):
        """
            Populate the view
        """
        if albums:
            self._add_albums(albums)


#######################
# PRIVATE             #
#######################
    def _get_children(self):
        """
            Return view children
            @return [AlbumWidget]
        """
        return self._albumbox.get_children()

    def _add_albums(self, albums):
        """
            Pop an album and add it to the view,
            repeat operation until album list is empty
            @param [album ids as int]
        """
        size_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
        widget = AlbumDetailedWidget(albums.pop(0),
                                     self._genre_id,
                                     self._pop_allowed,
                                     False,
                                     size_group)
        widget.connect('finished', self._on_album_finished, albums)
        widget.show()
        t = Thread(target=widget.populate)
        t.daemon = True
        t.start()
        self._albumbox.add(widget)

    def _on_album_finished(self, album, albums):
        """
            Add another album
            @param album as AlbumDetailedWidget
            @param [album ids as int]
        """
        if albums and not self._stop:
            self._add_albums(albums)
        else:
            self._stop = False

    def _on_label_realize(self, eventbox):
        """
            Change pointer on label
            @param eventbox as Gtk.EventBox
        """
        if (Lp.lastfm is not None or self.Wikipedia is not None) and\
                self._artist_id != Type.COMPILATIONS:
            eventbox.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND1))

    def _on_label_button_release(self, eventbox, event):
        """
            On clicked label, show artist informations in a popover
            @param eventbox as Gtk.EventBox
            @param event as Gdk.Event
        """
        if (Lp.lastfm is not None or self.Wikipedia is not None) and\
                self._artist_id != Type.COMPILATIONS:
            self._popover.set_relative_to(eventbox)
            self._popover.show()


class AlbumContextView(View):
    """
        Album contextual view
    """

    def __init__(self, widget):
        """
            Init context
            @param main view widget
        """
        View.__init__(self)
        self._widget = widget
        self._viewport.add(widget)
        self._viewport.show()
        self._scrolledWindow.set_min_content_height(ArtSize.BIG+35)
        self._scrolledWindow.show()
        self.add(self._scrolledWindow)

#######################
# PRIVATE             #
#######################
    def _get_children(self):
        """
            Return view children
            @return [AlbumWidget]
        """
        return [self._widget]


class AlbumsView(View):
    """
        Show albums in a box
    """

    def __init__(self, genre_id, is_compilation):
        """
            Init album view
            @param genre id as int
            @param is compilation as bool
        """
        View.__init__(self)
        self._signal = None
        self._context_album_id = None
        self._genre_id = genre_id
        self._is_compilation = is_compilation
        self._albumsongs = None
        self._context_widget = None

        self._albumbox = Gtk.FlowBox()
        self._albumbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._albumbox.connect('child-activated', self._on_album_activated)
        self._albumbox.set_property('column-spacing', 5)
        self._albumbox.set_property('row-spacing', 5)
        self._albumbox.set_homogeneous(True)
        self._albumbox.set_max_children_per_line(1000)
        self._albumbox.show()

        self._viewport.set_property('valign', Gtk.Align.START)
        self._viewport.set_property('margin', 5)
        self._viewport.add(self._albumbox)
        self._scrolledWindow.set_property('expand', True)

        self._context = ViewContainer(500)

        separator = Gtk.Separator()
        separator.show()

        self._paned = Gtk.Paned.new(Gtk.Orientation.VERTICAL)
        self._paned.pack1(self._scrolledWindow, True, False)
        self._paned.pack2(self._context, False, False)
        height = Lp.settings.get_value('paned-context-height').get_int32()
        # We set a stupid max value, safe as self._context is shrinked
        if height == -1:
            height = Lp.window.get_allocated_height()
        self._paned.set_position(height)
        self._paned.connect('notify::position', self._on_position_notify)
        self._paned.show()
        self.add(self._paned)

    def populate(self, albums):
        """
            Populate albums
            @param is compilation as bool
        """
        self._add_albums(albums)

#######################
# PRIVATE             #
#######################
    def _get_children(self):
        """
            Return view children
            @return [AlbumWidget]
        """
        children = []
        for child in self._albumbox.get_children():
            widget = child.get_child()
            children.append(widget)
        return children

    def _populate_context(self, album_id):
        """
            populate context view
            @param album id as int
        """
        size_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
        self._context_widget = AlbumDetailedWidget(album_id,
                                                   self._genre_id,
                                                   True,
                                                   True,
                                                   size_group)
        self._context_widget.populate()
        self._context_widget.show()
        view = AlbumContextView(self._context_widget)
        view.show()
        self._context.add(view)
        self._context.set_visible_child(view)
        self._context.clean_old_views(view)

    def _add_albums(self, albums):
        """
            Pop an album and add it to the view,
            repeat operation until album list is empty
            @param [album ids as int]
        """
        if albums and not self._stop:
            widget = AlbumSimpleWidget(albums.pop(0))
            widget.show()
            self._albumbox.insert(widget, -1)
            GLib.idle_add(self._add_albums, albums)
        else:
            self._stop = False

    def _on_position_notify(self, paned, param):
        """
            Save paned position
            @param paned as Gtk.Paned
            @param param as Gtk.Param
        """
        Lp.settings.set_value('paned-context-height',
                              GLib.Variant('i', paned.get_position()))
        return False

    def _on_album_activated(self, flowbox, child):
        """
            Show Context view for activated album
            @param flowbox as Gtk.Flowbox
            @child as Gtk.FlowboxChild
        """
        if self._context_album_id == child.get_child().get_id():
            self._context_album_id = None
            self._context.hide()
            self._context_widget.remove_signals()
            self._context_widget.destroy()
            self._context_widget = None
        else:
            self._context_album_id = child.get_child().get_id()
            if Lp.settings.get_value('auto-play'):
                Lp.player.play_album(self._context_album_id)
            self._populate_context(self._context_album_id)
            self._context.show()
