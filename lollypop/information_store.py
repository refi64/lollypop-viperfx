# Copyright (c) 2014-2019 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import Gio

from lollypop.utils import escape
from lollypop.define import App


class InformationStore:
    """
        Generic class to cache text and images
    """

    def init():
        """
            Init store
        """
        pass

    def get_bio(artist):
        """
            Get content from cache
            @param artist as str
            @return content as bytes
        """
        filepath = "%s/%s.txt" % (App().art._INFO_PATH,
                                  escape(artist))
        content = None
        f = Gio.File.new_for_path(filepath)
        if f.query_exists():
            (status, content, tag) = f.load_contents()
        return content

    def add_artist_bio(artist, content):
        """
            Add artist bio to store
            @param artist as str
            @param content as str
        """
        filepath = "%s/%s.txt" % (App().art._INFO_PATH,
                                  escape(artist))
        if content is not None:
            f = Gio.File.new_for_path(filepath)
            fstream = f.replace(None, False,
                                Gio.FileCreateFlags.REPLACE_DESTINATION, None)
            if fstream is not None:
                fstream.write(content, None)
                fstream.close()
