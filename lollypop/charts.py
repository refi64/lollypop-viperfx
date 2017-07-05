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

from threading import Thread
from time import time

from lollypop.charts_itunes import ItunesCharts
from lollypop.charts_spotify import SpotifyCharts
from lollypop.charts_lastfm import LastfmCharts
from lollypop.define import Lp


class Charts:
    """
        Charts
    """

    def __init__(self):
        """
            Init charts
        """
        self.__time = int(time())
        self.__providers = [SpotifyCharts(self.__time),
                            LastfmCharts(self.__time),
                            ItunesCharts(self.__time)]

    def start(self):
        """
            Start charts update
        """
        t = Thread(target=self.__update)
        t.daemon = True
        t.start()

    def stop(self):
        """
            Stop downloads
        """
        for provider in self.__providers:
            provider.stop()

#######################
# PRIVATE             #
#######################
    def __update(self):
        """
            Update charts
            @thread safe
        """
        # Remove charts older than one week
        t = self.__time - 604800
        Lp().db.del_tracks(Lp().tracks.get_old_charts_track_ids(t))
        # Update charts
        for provider in self.__providers:
            provider.update()
