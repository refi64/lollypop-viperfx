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

from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Gio

from threading import Thread
from cgi import escape
from os import mkdir, path

try:
    from lollypop.wikipedia import Wikipedia
except:
    pass
from lollypop.define import Lp, Type


class ArtistContent(Gtk.Stack):
    """
        Widget showing artist image and bio
    """

    _CACHE_PATH = path.expanduser("~") + "/.cache/lollypop_infos"

    def __init__(self):
        """
            Init artist content
        """
        Gtk.Stack.__init__(self)
        self._artist = Type.NONE
        self.set_transition_duration(500)
        self.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/ArtistContent.ui')
        self._content = builder.get_object('content')
        self._image = builder.get_object('image')
        self._image_frame = builder.get_object('frame')
        self.add_named(builder.get_object('widget'), 'widget')
        self.add_named(builder.get_object('notfound'), 'notfound')
        self.add_named(builder.get_object('spinner'), 'spinner')
        if not path.exists(self._CACHE_PATH):
            try:
                mkdir(self._CACHE_PATH)
            except:
                print("Can't create %s" % self._CACHE_PATH)

    def should_update(self, artist):
        """
            Should widget be updated
            @param artist as str
        """
        if artist is None:
            artist = Lp.player.get_current_artist()
        return artist != self._artist

    def clear_artist(self):
        """
            Clear current artist
        """
        self._artist = Type.NONE

    def clear(self):
        """
            Clear content
        """
        self._content.set_text('')
        self._image_frame.hide()
        self._image.clear()

    def populate(self, content, image_url, suffix):
        """
            populate widget with content
            @param content as string
            @param image url as string
            @param suffix as string
            @thread safe
        """
        try:
            data = None
            stream = None
            if content is not None:
                if image_url is not None:
                    f = Gio.File.new_for_uri(image_url)
                    (status, data, tag) = f.load_contents()
                    if status:
                        stream = Gio.MemoryInputStream.new_from_data(data,
                                                                     None)
                self._save_to_cache(self._artist, content, data, suffix)
            GLib.idle_add(self._set_content, content, stream)
        except Exception as e:
            print("ArtistContent::populate: %s" % e)

    def uncache(self, artist, suffix):
        """
            Remove artist from cache
            @param artist as string
            @param suffix as string
        """
        filepath = "%s/%s_%s.txt" % (self._CACHE_PATH,
                                     "".join(
                                        [c for c in artist if
                                         c.isalpha() or
                                         c.isdigit() or c == ' ']).rstrip(),
                                     suffix)
        f = Gio.File.new_for_path(filepath)
        try:
            f.delete(None)
        except:
            pass
        filepath = "%s/%s_%s" % (self._CACHE_PATH,
                                 "".join([c for c in artist if
                                          c.isalpha() or
                                          c.isdigit() or c == ' ']).rstrip(),
                                 suffix)
        f = Gio.File.new_for_path(filepath)
        try:
            f.delete(None)
        except:
            pass

#######################
# PRIVATE             #
#######################
    def _set_content(self, content, stream):
        """
            Set content
            @param content as string
            @param data as Gio.MemoryInputStream
        """
        # Happens if widget is destroyed while loading content from the web
        if self.get_child_by_name('widget') is None:
            return
        if content is not None:
            self._content.set_markup(escape(content.decode('utf-8')))
            if stream is not None:
                scale = self._image.get_scale_factor()
                pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(stream,
                                                                   250*scale,
                                                                   -1,
                                                                   True,
                                                                   None)
                surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf, 0, None)
                del pixbuf
                self._image.set_from_surface(surface)
                del surface
                self._image_frame.show()
            self.set_visible_child_name('widget')
        else:
            self.set_visible_child_name('notfound')

    def _save_to_cache(self, artist, content, data, suffix):
        """
            Save data to cache
            @param content as string
            @param data as bytes
            @param suffix as string
        """
        if content is None:
            return

        filepath = "%s/%s_%s" % (self._CACHE_PATH,
                                 "".join([c for c in artist if
                                          c.isalpha() or
                                          c.isdigit() or c == ' ']).rstrip(),
                                 suffix)
        f = Gio.File.new_for_path(filepath+".txt")
        fstream = f.replace(None, False,
                            Gio.FileCreateFlags.REPLACE_DESTINATION, None)
        if fstream is not None:
            fstream.write(content, None)
            fstream.close()
        if data is not None:
            stream = Gio.MemoryInputStream.new_from_data(data, None)
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(stream,
                                                               800,
                                                               -1,
                                                               True,
                                                               None)
            pixbuf.savev(filepath+".jpg", "jpeg", ["quality"], ["90"])
            del pixbuf

    def _load_cache_content(self, artist, suffix):
        """
            Load from cache
            @param artist as str
            @param suffix as str
            @return True if loaded
        """
        (content, data) = self._load_from_cache(artist, suffix)
        if content:
            stream = None
            if data is not None:
                stream = Gio.MemoryInputStream.new_from_data(data, None)
            GLib.idle_add(self._set_content, content, stream)
            return True
        return False

    def _load_from_cache(self, artist, suffix):
        """
            Load content from cache
            @return (content as string, data as bytes)
        """
        filepath = "%s/%s_%s" % (self._CACHE_PATH,
                                 "".join([c for c in artist if
                                          c.isalpha() or
                                          c.isdigit() or c == ' ']).rstrip(),
                                 suffix)
        content = None
        data = None
        if path.exists(filepath+".txt"):
            f = Gio.File.new_for_path(filepath+".txt")
            (status, content, tag) = f.load_contents()
            if status and path.exists(filepath+".jpg"):
                f = Gio.File.new_for_path(filepath+".jpg")
                (status, data, tag) = f.load_contents()
                if not status:
                    data = None
        if content is None:
            return (None, None)
        else:
            return (content, data)


class WikipediaContent(ArtistContent):
    """
        Show wikipedia content
    """

    def __init__(self, menu):
        """
            Init widget
            @param menu as Gtk.MenuButton
        """
        ArtistContent.__init__(self)
        self._menu = menu
        self._menu_model = Gio.Menu()
        self._menu.set_menu_model(self._menu_model)
        self._app = Gio.Application.get_default()

    def populate(self, artist, album):
        """
            Populate content
            @param artist as str
            @param album as str
            @thread safe
        """
        if artist is None:
            artist = Lp.player.get_current_artist()
        self._artist = artist
        GLib.idle_add(self._setup_menu_strings, [artist])
        if not self._load_cache_content(artist, 'wikipedia'):
            GLib.idle_add(self.set_visible_child_name, 'spinner')
            self._load_page_content(artist, artist)
        self._setup_menu(artist, album)

    def clear(self):
        """
            Clear model and then content
        """
        self._menu_model.remove_all()
        ArtistContent.clear(self)

    def uncache(self, artist):
        """
            Remove artist from cache
            @param artist as string
        """
        if artist is None:
            artist = Lp.player.get_current_artist()
        ArtistContent.uncache(self, artist, 'wikipedia')

#######################
# PRIVATE             #
#######################
    def _load_page_content(self, page, artist):
        """
            Load artist page content
            @param page as str
            @param artist as str
        """
        wp = Wikipedia()
        (url, image_url, content) = wp.get_page_infos(page)
        if artist == self._artist:
            ArtistContent.populate(self, content, image_url, 'wikipedia')

    def _setup_menu(self, artist, album):
        """
            Setup menu for artist
            @param artist as str
            @param album as str
        """
        if artist == self._artist:
            wp = Wikipedia()
            result = wp.search(artist)
            result += wp.search(artist + ' ' + album)
            cleaned = list(set(result))
            if artist in cleaned:
                cleaned.remove(artist)
            GLib.idle_add(self._setup_menu_strings, cleaned)

    def _setup_menu_strings(self, strings):
        """
            Setup a menu with strings
            @param strings as [str]
        """
        if self._artist != Type.NONE:
            i = 0
            for string in strings:
                action = Gio.SimpleAction(name="wikipedia_%s" % i)
                self._app.add_action(action)
                action.connect('activate',
                               self._on_search_activated,
                               string)
                self._menu_model.append(string, "app.wikipedia_%s" % i)
                i += 1
            # TODO: Remove this test later
            if Gtk.get_minor_version() > 16:
                self._menu.show()

    def _on_search_activated(self, action, variant, page):
        """
            Switch to page
            @param SimpleAction
            @param GVariant
        """
        self.uncache(self._artist)
        ArtistContent.clear(self)
        self.set_visible_child_name('spinner')
        t = Thread(target=self._load_page_content, args=(page, self._artist))
        t.daemon = True
        t.start()


class LastfmContent(ArtistContent):
    """
        Show lastfm content
    """

    def __init__(self):
        """
            Init widget
        """
        ArtistContent.__init__(self)

    def populate(self, artist):
        """
            Populate content
            @param artist as string
            @thread safe
        """
        if artist is None:
            artist = Lp.player.get_current_artist()
        self._artist = artist
        if not self._load_cache_content(artist, 'lastfm'):
            GLib.idle_add(self.set_visible_child_name, 'spinner')
            self._load_page_content(artist)

    def uncache(self, artist):
        """
            Remove artist from cache
            @param artist as string
        """
        if artist is None:
            artist = Lp.player.get_current_artist()
        ArtistContent.uncache(self, artist, 'lastfm')

#######################
# PRIVATE             #
#######################
    def _load_page_content(self, artist):
        """
            Load artist page content
            @param artist as str
        """
        (url, image_url, content) = Lp.lastfm.get_artist_infos(artist)
        if artist == self._artist:
            ArtistContent.populate(self, content, image_url, 'lastfm')
