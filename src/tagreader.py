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

from gi.repository import GLib, Gst, GstPbutils

# Tag reader class
class TagReader:
    """
        Init tag reader
    """
    def __init__(self):
        self._tagreader = GstPbutils.Discoverer.new(10*Gst.SECOND)

    """
        Return informations on file at path
        @param path as str
        @return GstPbutils.DiscovererInfo
    """
    def get_infos(self, path):
        try:
            uri = GLib.filename_to_uri(path)
            infos = self._tagreader.discover_uri(uri)
            return infos
        except:
            return None
