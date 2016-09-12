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

from gi.repository import Gio

from lollypop.charts_itunes import ItunesCharts
from lollypop.charts_spotify import SpotifyCharts
from lollypop.define import ChartsProvider, Lp


class Charts(ItunesCharts, SpotifyCharts):
    """
        Charts
    """

    def __init__(self):
        """
            Init charts
        """
        self._stop = False
        self._count = 0
        self._cancel = Gio.Cancellable.new()
        ItunesCharts.__init__(self)
        SpotifyCharts.__init__(self)

    def update(self):
        """
            Update charts
        """
        if Lp().settings.get_enum('charts') == ChartsProvider.ITUNES:
            self._count = ItunesCharts._get_album_count(self)
            ItunesCharts.update(self)
        else:
            self._count = SpotifyCharts._get_album_count(self)
            SpotifyCharts.update(self)

    def stop(self):
        """
            Stop downloads
        """
        self._stop = True
#######################
# PRIVATE             #
#######################
