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

from gi.repository import Gtk, GLib, Gio, GdkPixbuf, Gdk

from gettext import gettext as _

from lollypop.helper_task import TaskHelper
from lollypop.define import App, ArtSize, ResponsiveType
from lollypop.objects import Album
from lollypop.logger import Logger
from lollypop.utils import draw_rounded_image, escape
from lollypop.information_store import InformationStore
from lollypop.view_albums_list import AlbumsListView


class InformationPopover(Gtk.Popover):
    """
        Popover with artist information
    """

    def __init__(self, minimal=False):
        """
            Init artist infos
            @param follow_player as bool
        """
        Gtk.Popover.__init__(self)
        self.__scale_factor = 0
        self.__minimal = minimal
        self.set_position(Gtk.PositionType.BOTTOM)
        self.connect("map", self.__on_map)

    def populate(self, artist_id=None):
        """
            Show information for artists
            @param artist_id as int
        """
        helper = TaskHelper()
        builder = Gtk.Builder()
        builder.add_from_resource(
            "/org/gnome/Lollypop/ArtistInformation.ui")
        builder.connect_signals(self)
        widget = builder.get_object("widget")
        self.add(widget)
        artist_label = builder.get_object("artist_label")
        title_label = builder.get_object("title_label")
        artist_artwork = builder.get_object("artist_artwork")
        bio_label = builder.get_object("bio_label")
        if artist_id is None and App().player.current_track.id is not None:
            builder.get_object("lyrics_button").show()
            builder.get_object("lyrics_button").connect(
                "clicked",
                self.__on_lyrics_button_clicked,
                App().player.current_track)
            artist_id = App().player.current_track.artist_ids[0]
            title_label.set_text(App().player.current_track.title)
        artist_name = App().artists.get_name(artist_id)
        artist_label.set_text(artist_name)
        builder.get_object("eventbox").connect(
            "button-release-event",
            self.__on_label_button_release_event,
            artist_name)
        if self.__minimal:
            artist_artwork.hide()
        else:
            artist_artwork.connect(
                "draw",
                self.__on_artwork_draw,
                artist_name)
            self.__set_artist_artwork(artist_artwork, artist_name)
            albums_view = AlbumsListView(ResponsiveType.LIST)
            albums_view.set_size_request(300, -1)
            albums_view.show()
            widget.attach(albums_view, 2, 1, 1, 2)
            albums = []
            for album_id in App().albums.get_ids([artist_id]):
                albums.append(Album(album_id))
            albums_view.populate(albums)
        content = InformationStore.get_bio(artist_name)
        if content is not None:
            bio_label.set_markup(
                GLib.markup_escape_text(content.decode("utf-8")))
        elif not App().settings.get_value("network-access"):
            bio_label.set_text(_("Network access disabled"))
        else:
            bio_label.set_text(_("Loading information"))
            helper.run(
                self.__get_bio_content, artist_name,
                callback=(self.__set_bio_content, bio_label, artist_name))

#######################
# PROTECTED           #
#######################
    def _on_label_realize(self, eventbox):
        """
            @param eventbox as Gtk.EventBox
        """
        eventbox.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))

#######################
# PRIVATE             #
#######################
    def __get_bio_content(self, artist_name):
        """
            Get bio content and call callback
            @param artist_name as str
            @param content as str
        """
        content = None
        try:
            if App().lastfm is not None:
                content = App().lastfm.get_artist_bio(artist_name)
        except Exception as e:
            Logger.info("InformationPopover::__get_bio_content(): %s" % e)
        if content is None:
            try:
                from locale import getdefaultlocale
                import wikipedia
                language = getdefaultlocale()[0][0:2]
                wikipedia.set_lang(language)
                try:
                    page = wikipedia.page("%s %s" % (artist_name, "music"))
                    if artist_name.lower() not in page.title.lower():
                        raise
                except:
                    try:
                        wikipedia.set_lang("en")
                        page = wikipedia.page("%s %s" % (artist_name, "music"))
                    except:
                        pass
                content = page.content.encode(encoding="UTF-8")
            except Exception as e:
                Logger.info("InformationPopover::__get_bio_content(): %s" % e)
        return content

    def __set_bio_content(self, content, label, artist_name):
        """
            Set bio content
            @param content as bytes
            @param label as Gtk.Label
            @param artist_name as str
        """
        if content is not None:
            InformationStore.add_artist_bio(artist_name, content)
            label.set_markup(
                GLib.markup_escape_text(content.decode("utf-8")))
        else:
            label.set_text(_("No information on this artist"))

    def __set_artist_artwork(self, image, artist_name):
        """
            Set artist artwork
            @param image as Gtk.Image
            @param artist_name as str
        """
        size = ArtSize.ARTIST_SMALL * 3 * self.get_scale_factor()
        artwork_path = self.__get_artist_artwork_path_from_cache(
            artist_name,
            size)
        if artwork_path is None:
            return
        f = Gio.File.new_for_path(artwork_path)
        (status, data, tag) = f.load_contents(None)
        if status:
            bytes = GLib.Bytes(data)
            stream = Gio.MemoryInputStream.new_from_bytes(bytes)
            bytes.unref()
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(
                stream,
                size,
                size,
                True,
                None)
            stream.close()
            surface = Gdk.cairo_surface_create_from_pixbuf(
                pixbuf,
                image.get_scale_factor(),
                None)
            image.set_from_surface(surface)

    def __get_artist_artwork_path_from_cache(self, artist, size):
        """
            Get artist artwork path
            @param artist as str
            @param size as int
            @return str
        """
        path = InformationStore.get_artwork_path(artist, size)
        if path is not None:
            return path
        return None

    def __on_lyrics_button_clicked(self, button, track):
        """
            Show lyrics
            @param button as Gtk.Button
            @param track as Track
        """
        self.hide()
        App().window.container.show_lyrics(track)

    def __on_label_button_release_event(self, button, event, artist):
        """
            Show information cache (for edition)
            @param button as Gtk.Button
            @param event as Gdk.Event
        """
        uri = "file://%s/%s.txt" % (InformationStore._INFO_PATH,
                                    escape(artist))
        Gtk.show_uri_on_window(App().window,
                               uri,
                               Gdk.CURRENT_TIME)

    def __on_artwork_draw(self, image, ctx, artist_name):
        """
            Draw rounded image
            @param image as Gtk.Image
            @param ctx as cairo.Context
            @param artist_name as str
        """
        if image.get_style_context().has_class("artwork-icon"):
            return
        # Update image if scale factor changed
        if self.__scale_factor != image.get_scale_factor():
            self.__scale_factor = image.get_scale_factor()
            self.__set_artist_artwork(image, artist_name)
        draw_rounded_image(image, ctx)
        return True

    def __on_map(self, widget):
        """
            Connect signal and resize
            @param widget as Gtk.Widget
        """
        size = App().window.get_size()
        if self.__minimal:
            self.set_size_request(400, 600)
        else:
            self.set_size_request(min(size[0] * 0.6, 1000),
                                  min(size[1] * 0.7, 800))
