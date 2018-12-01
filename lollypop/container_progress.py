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

from gi.repository import GLib

from lollypop.progressbar import ProgressBar

from lollypop.define import App


class ProgressContainer:
    """
        Progress bar management for main view
    """

    def __init__(self):
        """
            Init container
        """
        self.__pulse_timeout = None
        self._progress = ProgressBar()
        self._progress.set_property("hexpand", True)

    def pulse(self, pulse):
        """
            Make progress bar visible/pulse if pulse is True
            @param pulse as bool
        """
        if pulse and not self._progress.is_visible():
            self._progress.show()
            if self.__pulse_timeout is None:
                self.__pulse_timeout = GLib.timeout_add(500, self.__pulse)
        else:
            if self.__pulse_timeout is not None:
                GLib.source_remove(self.__pulse_timeout)
                self.__pulse_timeout = None
                self._progress.hide()

    @property
    def progress(self):
        """
            Progress bar
            @return ProgressBar
        """
        return self._progress

############
# PRIVATE  #
############
    def __pulse(self):
        """
            Make progress bar pulse while visible
            @param pulse as bool
        """
        if self._progress.is_visible() and not App().scanner.is_locked():
            self._progress.pulse()
            return True
        else:
            self._progress.set_fraction(0.0, self)
            self.__pulse_timeout = None
            return False
