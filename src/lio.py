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

import gi
gi.require_version("Soup", "2.4")

from gi.repository import Gio, GObject, Soup

from lollypop.define import Lp


class Lio:
    class File(GObject.Object, Gio.File):
        """
            Extending Gio.File
            - http download over libsoup
        """
        def new_for_uri(uri):
            f = Gio.File.new_for_uri(uri)
            f.__class__ = Lio.File
            return f

        def load_contents(self, cancellable=None):
            """
                Load uri with libsoup (better performance)
                @param cancellable as Gio.Cancellable
            """
            try:
                uri = self.get_uri()
                if uri.startswith("http") or uri.startswith("https"):
                    session = Soup.Session.new()
                    request = session.request(uri)
                    stream = request.send(cancellable)
                    bytes = bytearray(0)
                    buf = stream.read_bytes(1024, cancellable).get_data()
                    while buf:
                        bytes += buf
                        buf = stream.read_bytes(1024, cancellable).get_data()
                    return (True, bytes, "")
                else:
                    return Gio.File.load_contents(self, cancellable)
            except Exception as e:
                # FIXME Use debug, need to be moved outside utils.py
                if Lp().debug:
                    print("Lio.load_contents():",  e)
                return (False, b"", "")
