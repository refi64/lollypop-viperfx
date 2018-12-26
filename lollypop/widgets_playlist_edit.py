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

from gi.repository import Gtk, GLib, Pango

from threading import Thread
from gettext import gettext as _

from lollypop.define import App, Type
from lollypop.cellrenderer import CellRendererAlbum
from lollypop.objects import Track


class PlaylistEditWidget(Gtk.Bin):
    """
        Widget playlists editor
    """

    def __init__(self, playlist_id):
        """
            Init widget
            @param playlist id as int
        """
        Gtk.Bin.__init__(self)
        self.__playlist_id = playlist_id

        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/PlaylistEditWidget.ui")
        builder.connect_signals(self)

        self.__infobar = builder.get_object("infobar")
        self.__infobar_label = builder.get_object("infobarlabel")

        self.__view = builder.get_object("view")

        self.__model = Gtk.ListStore(int,
                                     str,
                                     str,
                                     int)

        self.__view.set_model(self.__model)

        # 3 COLUMNS NEEDED
        renderer0 = CellRendererAlbum()
        column0 = Gtk.TreeViewColumn("pixbuf1", renderer0, album=0)
        renderer1 = Gtk.CellRendererText()
        renderer1.set_property("ellipsize-set", True)
        renderer1.set_property("ellipsize", Pango.EllipsizeMode.END)
        column1 = Gtk.TreeViewColumn("text1", renderer1, markup=1)
        column1.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column1.set_expand(True)
        renderer2 = Gtk.CellRendererPixbuf()
        column2 = Gtk.TreeViewColumn("delete", renderer2)
        column2.add_attribute(renderer2, "icon-name", 2)
        column2.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column2.set_property("fixed_width", 50)

        self.__view.append_column(column0)
        self.__view.append_column(column1)
        self.__view.append_column(column2)

        self.add(builder.get_object("widget"))

    def populate(self):
        """
            populate view if needed
        """
        if len(self.__model) == 0:
            t = Thread(target=self.__append_tracks)
            t.daemon = True
            t.start()

#######################
# PROTECTED           #
#######################
    def _on_response(self, infobar, response_id):
        """
            Hide infobar
            @param widget as Gtk.Infobar
            @param reponse id as int
        """
        if response_id == Gtk.ResponseType.CLOSE:
            self.__infobar.hide()
            self.__view.grab_focus()
            self.__view.get_selection().unselect_all()

    def _on_row_activated(self, view, path, column):
        """
            Delete playlist
            @param TreeView, TreePath, TreeViewColumn
        """
        iterator = self.__model.get_iter(path)
        if iterator:
            if column.get_title() == "delete":
                self.__show_infobar(path)
            else:
                self.__infobar.hide()

    def _on_selection_changed(self, selection):
        """
            On selection changed, show infobar
            @param selection as Gtk.TreeSelection
        """
        count = selection.count_selected_rows()
        if count > 0:
            self.__infobar_label.set_markup(_("Remove?"))
            self.__infobar.show()
            # GTK 3.20 https://bugzilla.gnome.org/show_bug.cgi?id=710888
            self.__infobar.queue_resize()
        else:
            self.__infobar.hide()

    def _on_delete_confirm(self, button):
        """
            Delete tracks after confirmation
            @param button as Gtk.Button
        """
        selection = self.__view.get_selection()
        selected = selection.get_selected_rows()[1]
        rows = []
        for item in selected:
            rows.append(Gtk.TreeRowReference.new(self.__model, item))

        tracks = []
        for row in rows:
            iterator = self.__model.get_iter(row.get_path())
            track = Track(self.__model.get_value(iterator, 3))
            tracks.append(track)
            if self.__playlist_id == Type.LOVED and App().lastfm is not None:
                if track.album.artist_id == Type.COMPILATIONS:
                    artist_name = ", ".join(track.artists)
                else:
                    artist_name = ", ".join(track.album.artists)
                t = Thread(target=App().lastfm.unlove,
                           args=(artist_name, track.name))
                t.daemon = True
                t.start()
            self.__model.remove(iterator)
        App().playlists.remove_tracks(self.__playlist_id, tracks)
        self.__infobar.hide()
        self.__unselectall()

#######################
# PRIVATE             #
#######################
    def __unselectall(self):
        """
            Unselect all in view
        """
        self.__view.get_selection().unselect_all()
        self.__view.grab_focus()

    def __append_tracks(self):
        """
            Append tracks
        """
        track_ids = App().playlists.get_track_ids(self.__playlist_id)
        GLib.idle_add(self.__append_track, track_ids)

    def __append_track(self, track_ids):
        """
            Append track while tracks not empty
            @param track_ids as [track_id as int]
        """
        if track_ids:
            track = Track(track_ids.pop(0))
            if track.album.artist_ids[0] == Type.COMPILATIONS:
                artists = ", ".join(track.artists)
            else:
                artists = ", ".join(track.album.artists)
            self.__model.append([track.album.id,
                                "<b>%s</b>\n%s" % (
                                   GLib.markup_escape_text(artists),
                                   GLib.markup_escape_text(track.name)),
                                 "user-trash-symbolic", track.id])
            GLib.idle_add(self.__append_track, track_ids)
