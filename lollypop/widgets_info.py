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

from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Gio

from threading import Thread
from gettext import gettext as _

try:
    from lollypop.wikipedia import Wikipedia
except:
    pass
from lollypop.define import Lp
from lollypop.utils import get_network_available
from lollypop.cache import InfoCache
from lollypop.lio import Lio


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
        self._stop = False
        self.__cancel = Gio.Cancellable.new()
        self._artist = ""
        self.set_transition_duration(500)
        self.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/InfoContent.ui")
        self.__content = builder.get_object("content")
        self.__image = builder.get_object("image")
        self._menu_found = builder.get_object("menu-found")
        self._menu_not_found = builder.get_object("menu-not-found")
        self.__error = builder.get_object("error")
        self.add_named(builder.get_object("widget"), "widget")
        self.add_named(builder.get_object("notfound"), "notfound")
        self._spinner = builder.get_object("spinner")
        self.add_named(self._spinner, "spinner")

    def clear(self):
        """
            Clear content
        """
        self.__content.set_text("")
        self.__image.hide()
        self.__image.clear()

    def stop(self):
        """
            Stop loading
        """
        self._stop = True
        self.__cancel.cancel()

    @property
    def artist(self):
        """
            Current artist on screen as str
        """
        return self._artist

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
                    f = Lio.File.new_for_uri(image_url)
                    (status, data, tag) = f.load_contents(self.__cancel)
                    if status:
                        bytes = GLib.Bytes(data)
                        stream = Gio.MemoryInputStream.new_from_bytes(bytes)
                        bytes.unref()
                        del data
                    else:
                        data = None
                InfoCache.add(prefix, content, data, suffix)
            GLib.idle_add(self.__set_content, content, stream)
        except Exception as e:
            print("InfoContent::set_content: %s" % e)

#######################
# PROTECTED           #
#######################
    def _load_cache_content(self, prefix, suffix):
        """
            Load from cache
            @param prefix as str
            @param suffix as str
            @return True if loaded
        """
        (content, data) = InfoCache.get(prefix, suffix)
        if content is not None:
            stream = None
            if data is not None:
                bytes = GLib.Bytes(data)
                stream = Gio.MemoryInputStream.new_from_bytes(bytes)
                bytes.unref()
                del data
            GLib.idle_add(self.__set_content, content, stream)
            return True
        return False

    def __on_not_found(self):
        """
            Show not found child
        """
        if get_network_available():
            error = _("No information for this artist")
        else:
            error = _("Network access disabled")
        self.__error.set_markup(
                       '<span font_weight="bold" size="xx-large">' +
                       error +
                       "</span>")
        self.set_visible_child_name("notfound")

#######################
# PRIVATE             #
#######################
    def __set_content(self, content, stream):
        """
            Set content
            @param content as string
            @param data as Gio.MemoryInputStream
        """
        if content is not None:
            self.__content.set_markup(
                              GLib.markup_escape_text(content.decode("utf-8")))
            if stream is not None:
                scale = self.__image.get_scale_factor()
                # Will happen if cache is broken or when reading empty files
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(
                               stream,
                               Lp().settings.get_value(
                                        "cover-size").get_int32() + 50 * scale,
                               -1,
                               True,
                               None)
                    stream.close()
                    surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf,
                                                                   scale,
                                                                   None)
                    del pixbuf
                    self.__image.set_from_surface(surface)
                    del surface
                    self.__image.show()
                except:
                    pass
            self.set_visible_child_name("widget")
        else:
            self.__on_not_found()
        self._spinner.stop()


class WikipediaContent(InfoContent):
    """
        Show wikipedia content
    """

    def __init__(self):
        """
            Init widget
        """
        InfoContent.__init__(self)
        self.__album = ""
        self.__menu_model = Gio.Menu()
        self._menu_not_found.set_menu_model(self.__menu_model)
        self._menu_found.set_menu_model(self.__menu_model)
        self.__app = Gio.Application.get_default()

    def populate(self, artist, album):
        """
            Populate content
            @param artist as str
            @param album as str
            @thread safe
        """
        self._artist = artist
        self.__album = album
        if not self._load_cache_content(artist, "wikipedia"):
            GLib.idle_add(self.set_visible_child_name, "spinner")
            self._spinner.start()
            self.__load_page_content(artist)
        elif get_network_available():
            t = Thread(target=self.__setup_menu,
                       args=(self._artist, self.__album))
            t.daemon = True
            t.start()

    def clear(self):
        """
            Clear model and then content
        """
        self.__menu_model.remove_all()
        InfoContent.clear(self)

#######################
# PROTECTED           #
#######################
    def __on_not_found(self):
        """
            Show not found child
        """
        InfoContent.__on_not_found(self)
        if get_network_available():
            t = Thread(target=self.__setup_menu,
                       args=(self._artist, self.__album))
            t.daemon = True
            t.start()

#######################
# PRIVATE             #
#######################
    def __load_page_content(self, artist):
        """
            Load artist page content
            @param artist as str
        """
        GLib.idle_add(self.__menu_model.remove_all)
        wp = Wikipedia()
        try:
            (url, content) = wp.get_page_infos(artist)
        except:
            url = content = None
        if not self._stop:
            InfoContent.set_content(self, self._artist, content,
                                    url, "wikipedia")
            if get_network_available():
                t = Thread(target=self.__setup_menu,
                           args=(self._artist, self.__album))
                t.daemon = True
                t.start()

    def __setup_menu(self, artist, album):
        """
            Setup menu for artist
            @param artist as str
            @param album as str
        """
        wp = Wikipedia()
        result = wp.search(artist)
        result += wp.search(artist + " " + album)
        cleaned = list(set(result))
        if artist in cleaned:
            cleaned.remove(artist)
        GLib.idle_add(self.__setup_menu_strings, cleaned)

    def __setup_menu_strings(self, strings):
        """
            Setup a menu with strings
            @param strings as [str]
        """
        if strings:
            self._menu_not_found.show()
            self._menu_found.show()
        else:
            return
        i = 0
        for string in strings:
            action = Gio.SimpleAction(name="wikipedia_%s" % i)
            self.__app.add_action(action)
            action.connect("activate",
                           self.__on_search_activated,
                           string)
            self.__menu_model.append(string, "app.wikipedia_%s" % i)
            i += 1

    def __on_search_activated(self, action, variant, artist):
        """
            Switch to page
            @param action as SimpleAction
            @param variant as GVariant
            @param artist as str
        """
        InfoCache.remove(artist, "wikipedia")
        InfoContent.clear(self)
        self.set_visible_child_name("spinner")
        self._spinner.start()
        t = Thread(target=self.__load_page_content, args=(artist,))
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
        self._artist = artist
        if not self._load_cache_content(artist, "lastfm"):
            GLib.idle_add(self.set_visible_child_name, "spinner")
            self._spinner.start()
            self.__load_page_content(artist)

#######################
# PRIVATE             #
#######################
    def __load_page_content(self, artist):
        """
            Load artists page content
            @param artist as str
        """
        try:
            (url, content) = Lp().lastfm.get_artist_info(artist)
        except:
            url = content = None
        if not self._stop:
            InfoContent.set_content(self, artist, content, url, "lastfm")
