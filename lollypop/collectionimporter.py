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

from gi.repository import GLib, Gio

from gettext import gettext as _


from lollypop.define import Lp
from lollypop.tagreader import TagReader
from lollypop.utils import is_audio


class CollectionImporter:
    """
        Import files to main collection (as files)
    """
    def __init__(self):
        """
            Init collection scanner
        """
        self.__tag_reader = TagReader()

    def add(self, uris):
        """
            Add uris to collection
        """
        GLib.idle_add(Lp().window.pulse, True)
        walk_uris = list(uris)
        while walk_uris:
            uri = walk_uris.pop(0)
            if not uri:
                continue
            try:
                f = Gio.File.new_for_uri(uri)
                file_type = f.query_file_type(Gio.FileQueryInfoFlags.NONE,
                                              None)
                if file_type == Gio.FileType.DIRECTORY:
                    infos = f.enumerate_children(
                        "standard::name,standard::type,standard::is-hidden",
                        Gio.FileQueryInfoFlags.NONE,
                        None)
                    for info in infos:
                        f = infos.get_child(info)
                        child_uri = f.get_uri()
                        if info.get_is_hidden():
                            continue
                        elif info.get_file_type() == Gio.FileType.DIRECTORY:
                            walk_uris.append(child_uri)
                        else:
                            if is_audio(f):
                                self.__add_file(f)
                elif is_audio(f):
                    self.__add_file(f)
                else:
                    print("CollectionImporter: not an audio file", uri)
            except Exception as e:
                print("CollectionImporter::add():", e)
        GLib.idle_add(Lp().window.pulse, False)

#######################
# PRIVATE             #
#######################
    def __add_file(self, f):
        """
            Add file to collection
            @param f as Gio.File
        """
        try:
            # We only import to primary collection
            music_uris = Lp().settings.get_music_uris()
            if music_uris:
                music_uri = music_uris[0]
            else:
                print("CollectionImporter::__add_file(): No collection")
                return
            info = self.__tag_reader.get_info(f.get_uri())
            tags = info.get_tags()
            name = f.get_basename()
            title = self.__tag_reader.get_title(tags, name)
            artists = self.__tag_reader.get_artists(tags)
            album_artists = self.__tag_reader.get_album_artist(tags)
            album_name = self.__tag_reader.get_album_name(tags)
            genres = self.__tag_reader.get_genres(tags)
            tracknumber = self.__tag_reader.get_tracknumber(tags, name)
            year = self.__tag_reader.get_original_year(tags)
            if year is None:
                year = self.__tag_reader.get_year(tags)

            # If no artists tag, use album artist
            if album_artists == "":
                album_artists = artists
            if album_artists == "":
                album_artists = _("Unknown")
            extension = f.get_uri().split(".")[-1]
            dest_dir_uri = "%s/%s/%s/%s" % (music_uri,
                                            genres,
                                            album_artists,
                                            album_name)
            dest_dir = Gio.File.new_for_uri(dest_dir_uri)
            if not dest_dir.query_exists():
                dest_dir.make_directory_with_parents(None)
            if tracknumber == 0:
                dest_uri = "%s/%s.%s" % (dest_dir_uri, title, extension)
            else:
                dest_uri = "%s/%02d_%s.%s" % (dest_dir_uri, tracknumber,
                                              title, extension)
            dest = Gio.File.new_for_uri(dest_uri)
            f.copy(dest, Gio.FileCopyFlags.NONE, None, None, None)
        except Exception as e:
            print("CollectionImporter::__add_file():", e)
