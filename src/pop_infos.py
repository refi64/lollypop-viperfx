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

from gi.repository import Gtk, GLib, Gio, GdkPixbuf

from _thread import start_new_thread
from gettext import gettext as _
from cgi import escape

from lollypop.define import Lp


# Show ArtistInfos in a popover
class InfosPopover(Gtk.Popover):
    """
        Init popover
        @param artist as string
        @param track id as int
    """
    def __init__(self, artist, track_id=None):
        Gtk.Popover.__init__(self)
        self._infos = ArtistInfos(artist, track_id)
        self._infos.show()
        self.add(self._infos)

    """
        Populate view
    """
    def populate(self):
        self._infos.populate()

    """
        Resize popover and set signals callback
    """
    def do_show(self):
        size_setting = Lp.settings.get_value('window-size')
        if isinstance(size_setting[1], int):
            self.set_size_request(700, size_setting[1]*0.5)
        else:
            self.set_size_request(700, 400)
        Gtk.Popover.do_show(self)

    """
        Preferred width
    """
    def do_get_preferred_width(self):
        return (700, 700)


# Show artist informations from lastfm
class ArtistInfos(Gtk.Bin):
    """
        Init artist infos
        @param artist as string
        @param track_id as int
    """
    def __init__(self, artist, track_id):
        Gtk.Bin.__init__(self)
        self._liked = True  # Liked track or not?
        self._wikipedia = True
        self._artist = artist
        self._track_id = track_id
        if self._track_id is not None:
            self._title = Lp.tracks.get_name(track_id)
        self._stack = Gtk.Stack()
        self._stack.set_property('expand', True)
        self._stack.show()

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/ArtistInfos.ui')
        builder.connect_signals(self)
        widget = builder.get_object('widget')
        widget.attach(self._stack, 0, 2, 4, 1)

        self._view_btn = builder.get_object('view_btn')
        self._love_btn = builder.get_object('love_btn')
        self._url_btn = builder.get_object('url_btn')
        self._image = builder.get_object('image')
        self._content = builder.get_object('content')

        self._label = builder.get_object('label')
        self._label.set_text(_("Please wait..."))

        self._scrolled = builder.get_object('scrolled')
        self._spinner = builder.get_object('spinner')
        self._not_found = builder.get_object('notfound')
        self._stack.add(self._spinner)
        self._stack.add(self._not_found)
        self._stack.add(self._scrolled)
        self._stack.set_visible_child(self._spinner)
        self.add(widget)

    """
        Populate informations and artist image
    """
    def populate(self):
        start_new_thread(self._populate, ())

#######################
# PRIVATE             #
#######################
    """
        Same as _populate()
        Horrible code limited to two engines, need rework if adding one more
        @thread safe
    """
    def _populate(self):
        url = None
        if self._wikipedia and Lp.wikipedia is not None:
            self._wikipedia = False
            (url, image_url, content) = Lp.wikipedia.get_artist_infos(
                self._artist)
        if url is None and Lp.lastfm is not None:
            self._wikipedia = True
            (url, image_url, content) = Lp.lastfm.get_artist_infos(
                                            self._artist)

        stream = None
        try:
            if image_url is not None:
                f = Gio.File.new_for_uri(image_url)
                (status, data, tag) = f.load_contents()
                if status:
                    stream = Gio.MemoryInputStream.new_from_data(data,
                                                                 None)
        except Exception as e:
            print("PopArtistInfos::_populate: %s" % e)
            content = None
        GLib.idle_add(self._set_content, content, url, stream)

    """
        Set content on view
        @param content as str
        @param url as str
        @param stream as Gio.MemoryInputStream
    """
    def _set_content(self, content, url, stream):
        if content is not None:
            if Lp.lastfm is not None and Lp.wikipedia is not None:
                self._view_btn.show()
            self._stack.set_visible_child(self._scrolled)
            if self._track_id is None:
                string = "<b>%s</b>" % escape(self._artist)
            else:
                string = "<b>%s</b>   %s" % (escape(self._artist),
                                             escape(self._title))
            self._label.set_markup(string)
            self._url_btn.set_uri(url)
            self._content.set_text(content)
            if self._track_id is not None:
                start_new_thread(self._show_love_btn, ())
            if self._wikipedia:
                self._view_btn.set_tooltip_text(_("Wikipedia"))
                self._url_btn.set_label(_("Last.fm"))
            else:
                self._view_btn.set_tooltip_text(_("Last.fm"))
                self._url_btn.set_label(_("Wikipedia"))
        else:
            self._stack.set_visible_child(self._not_found)
            self._label.set_text(_("No information for this artist..."))
        if stream is not None:
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(stream,
                                                               200,
                                                               -1,
                                                               True,
                                                               None)
            self._image.set_from_pixbuf(pixbuf)
            del pixbuf

    """
        Show love button
    """
    def _show_love_btn(self):
        sql = Lp.db.get_cursor()
        if self._track_id is not None:
            if Lp.playlists.is_present(Lp.playlists._LOVED,
                                       self._track_id,
                                       None,
                                       False,
                                       sql):
                self._liked = False
                self._love_btn.set_tooltip_text(_("I do not love"))
                self._love_btn.set_image(
                    Gtk.Image.new_from_icon_name('face-sick-symbolic',
                                                 Gtk.IconSize.BUTTON))
        GLib.idle_add(self._love_btn.show)
        sql.close()

    """
        Love a track
        @thread safe
    """
    def _love_track(self):
        Lp.playlists.add_loved()

        # Add track to Liked tracks
        sql = Lp.db.get_cursor()
        if self._track_id is not None:
            Lp.playlists.add_track(Lp.playlists._LOVED,
                                   Lp.tracks.get_path(self._track_id,
                                                      sql))
        sql.close()

        Lp.lastfm.love(self._artist, self._title)

    """
        Unlove a track
    """
    def _unlove_track(self):
        Lp.playlists.add_loved()

        # Del track from Liked tracks
        sql = Lp.db.get_cursor()
        if self._track_id is not None:
            Lp.playlists.remove_tracks(
                Lp.playlists._LOVED,
                [Lp.tracks.get_path(self._track_id, sql)])
        sql.close()

        Lp.lastfm.unlove(self._artist, self._title)

    """
        Love a track
        @param btn as Gtk.Button
    """
    def _on_love_btn_clicked(self, btn):
        if self._liked:
            start_new_thread(self._love_track, ())
            btn.set_image(
                Gtk.Image.new_from_icon_name('face-sick-symbolic',
                                             Gtk.IconSize.BUTTON))
            self._liked = False
            btn.set_tooltip_text(_("I do not love"))
        else:
            start_new_thread(self._unlove_track, ())
            btn.set_image(
                Gtk.Image.new_from_icon_name('emblem-favorite-symbolic',
                                             Gtk.IconSize.BUTTON))
            self._liked = True

    """
        Next view
        @param btn as Gtk.Button
    """
    def _on_view_clicked(self, btn):
        self._label.set_text(_("Please wait..."))
        self._view_btn.hide()
        self._love_btn.hide()
        self._url_btn.set_label('')
        self._stack.set_visible_child(self._spinner)
        self.populate()
