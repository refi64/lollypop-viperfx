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

from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Gio

from threading import Thread
from cgi import escape

try:
    from lollypop.wikipedia import Wikipedia
except:
    pass
from lollypop.define import Lp, Type
from lollypop.cache import InfoCache


class InfoContent(Gtk.Stack):
    """
        Widget showing artist image and bio
    """

    def __init__(self):
        """
            Init artists content
        """
        Gtk.Stack.__init__(self)
        InfoCache.init()
        self._artists = Type.NONE
        self.set_transition_duration(500)
        self.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/InfoContent.ui')
        self._content = builder.get_object('content')
        self._image = builder.get_object('image')
        self.add_named(builder.get_object('widget'), 'widget')
        self.add_named(builder.get_object('notfound'), 'notfound')
        self._spinner = builder.get_object('spinner')
        self.add_named(self._spinner, 'spinner')

    def clear_artist(self):
        """
            Clear current artist
        """
        self._artists = []

    def clear(self):
        """
            Clear content
        """
        self._content.set_text('')
        self._image.hide()
        self._image.clear()

    def set_content(self, prefix, content, image_url, suffix):
        """
            populate widget with content
            @param prefix as str
            @param content as str
            @param image url as str
            @param suffix as str
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
                InfoCache.cache(prefix, content, data, suffix)
            GLib.idle_add(self._set_content, content, stream)
        except Exception as e:
            print("InfoContent::set_content: %s" % e)

#######################
# PRIVATE             #
#######################
    def _set_content(self, content, stream):
        """
            Set content
            @param content as string
            @param data as Gio.MemoryInputStream
        """
        if content is not None:
            self._content.set_markup(escape(content.decode('utf-8')))
            if stream is not None:
                scale = self._image.get_scale_factor()
                pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(
                           stream,
                           Lp().settings.get_value(
                                        'cover-size').get_int32() + 50 * scale,
                           -1,
                           True,
                           None)
                surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf, 0, None)
                del pixbuf
                self._image.set_from_surface(surface)
                del surface
                self._image.show()
            self.set_visible_child_name('widget')
        else:
            self.set_visible_child_name('notfound')
        self._spinner.stop()

    def _load_cache_content(self, prefix, suffix):
        """
            Load from cache
            @param prefix as str
            @param suffix as str
            @return True if loaded
        """
        (content, data) = InfoCache.get(prefix, suffix)
        if content:
            stream = None
            if data is not None:
                stream = Gio.MemoryInputStream.new_from_data(data, None)
            GLib.idle_add(self._set_content, content, stream)
            return True
        return False


class WikipediaContent(InfoContent):
    """
        Show wikipedia content
    """

    def __init__(self, menu):
        """
            Init widget
            @param menu as Gtk.MenuButton
        """
        InfoContent.__init__(self)
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
        GLib.idle_add(self._setup_menu_strings, [artist])
        if not self._load_cache_content(artist, 'wikipedia'):
            GLib.idle_add(self.set_visible_child_name, 'spinner')
            self._spinner.start()
            self._load_page_content(artist)
        self._setup_menu(artist, album)

    def clear(self):
        """
            Clear model and then content
        """
        self._menu_model.remove_all()
        InfoContent.clear(self)

#######################
# PRIVATE             #
#######################
    def _load_page_content(self, artist):
        """
            Load artist page content
            @param artist as str
        """
        wp = Wikipedia()
        (url, image_url, content) = wp.get_page_infos(artist)
        print(content)
        InfoContent.set_content(self, artist, content, image_url, 'wikipedia')

    def _setup_menu(self, artist, album):
        """
            Setup menu for artist
            @param artist as str
            @param album as str
        """
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
        i = 0
        for string in strings:
            action = Gio.SimpleAction(name="wikipedia_%s" % i)
            self._app.add_action(action)
            action.connect('activate',
                           self._on_search_activated,
                           string)
            self._menu_model.append(string, "app.wikipedia_%s" % i)
            i += 1
        self._menu.show()

    def _on_search_activated(self, action, variant, artist):
        """
            Switch to page
            @param action as SimpleAction
            @param variant as GVariant
            @param artist as str
        """
        InfoCache.uncache(artist, 'wikipedia')
        InfoContent.clear(self)
        self.set_visible_child_name('spinner')
        self._spinner.start()
        t = Thread(target=self._load_page_content, args=(artist,))
        t.daemon = True
        t.start()


class LastfmContent(InfoContent):
    """
        Show lastfm content
    """

    def __init__(self):
        """
            Init widget
        """
        InfoContent.__init__(self)

    def populate(self, artist):
        """
            Populate content
            @param artist as str
            @thread safe
        """
        if not self._load_cache_content(artist, 'lastfm'):
            GLib.idle_add(self.set_visible_child_name, 'spinner')
            self._spinner.start()
            self._load_page_content(artist)

#######################
# PRIVATE             #
#######################
    def _load_page_content(self, artist):
        """
            Load artists page content
            @param artist as str
        """
        (url, image_url, content) = Lp().lastfm.get_artist_infos(artist)
        InfoContent.set_content(self, artist, content, image_url, 'lastfm')
