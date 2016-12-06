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

from gi.repository import Gio, GObject

from urllib.request import urlopen
from urllib.parse import quote


class Lio:
    def uri_escape_string(value, exclude, ignored):
        if exclude is None:
            exclude = ''
        return quote(value, exclude)

    class File(GObject.Object, Gio.File):
        """
            Workaround https://bugzilla.gnome.org/show_bug.cgi?id=775600
        """

        def __init__(self):
            GObject.Object.__init__(self)

        def new_for_uri(uri):
            f = Gio.File.new_for_uri(uri)
            f.__class__ = Lio.File
            return f

        def load_contents(self, cancellable=None):
            try:
                uri = self.get_uri()
                if uri.startswith("http"):
                    data = urlopen(self.get_uri()).read()
                    return (True, data, "")
                else:
                    return Gio.File.load_contents(self, cancellable)
            except Exception as e:
                print(e, uri)
                raise e
