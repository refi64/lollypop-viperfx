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

from gettext import gettext as _

from lollypop.define import Type, App, SelectionListMask


class ShownLists:
    """
        Handle shown lists
    """
    def get(mask, get_all=False):
        """
            Get list
            @param mask as bit mask
            @param get_all as bool
        """
        wanted = App().settings.get_value("shown-album-lists")
        lists = []
        if mask & SelectionListMask.LIST_ONE:
            if get_all or Type.POPULARS in wanted:
                lists.append((Type.POPULARS, _("Popular albums"), ""))
            if get_all or Type.RANDOMS in wanted:
                lists.append((Type.RANDOMS, _("Random albums"), ""))
            if get_all or Type.LOVED in wanted:
                lists.append((Type.LOVED, _("Loved albums"), ""))
            if get_all or Type.RECENTS in wanted:
                lists.append((Type.RECENTS, _("Recently added albums"), ""))
            if get_all or Type.NEVER in wanted:
                lists.append((Type.NEVER, _("Unplayed albums"), ""))
            if get_all or Type.PLAYLISTS in wanted:
                lists.append((Type.PLAYLISTS, _("Playlists"), ""))
            if get_all or Type.RADIOS in wanted:
                lists.append((Type.RADIOS, _("Radios"), ""))
            if get_all or Type.YEARS in wanted:
                lists.append((Type.YEARS, _("Years"), ""))
            if get_all or Type.ALL in wanted:
                lists.append((Type.ALL, _("All albums"), ""))
            if get_all or (Type.ARTISTS in wanted and
                           not mask & SelectionListMask.ALL_ARTISTS):
                lists.append((Type.ARTISTS, _("All artists"), ""))
        if get_all or (mask & SelectionListMask.COMPILATIONS and
                       Type.COMPILATIONS in wanted):
            lists.append((Type.COMPILATIONS, _("Compilations"), ""))
        if mask & SelectionListMask.LIST_ONE:
            if get_all:
                lists.append((Type.USB_DISKS, _("USB disks"), ""))
        return lists


class ShownPlaylists:
    """
        Handle shown playlists
    """
    def get(get_all=False):
        """
            get list
            @param get_all as bool
        """
        wanted = App().settings.get_value("shown-playlists")
        lists = []
        if get_all or Type.POPULARS in wanted:
            lists.append((Type.POPULARS, _("Popular tracks"), ""))
        if get_all or Type.LOVED in wanted:
            lists.append((Type.LOVED, App().playlists.LOVED, ""))
        if get_all or Type.RECENTS in wanted:
            lists.append((Type.RECENTS, _("Recently played"), ""))
        if get_all or Type.NEVER in wanted:
            lists.append((Type.NEVER, _("Unplayed"), ""))
        if get_all or Type.RANDOMS in wanted:
            lists.append((Type.RANDOMS, _("Random tracks"), ""))
        return lists
