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

from gi.repository import Gtk, GLib

from lollypop.view import View
from lollypop.define import Lp


class FirstRunView(View):
    """
        Allow user to do initial configuration
    """
    def __init__(self):
        """
            Init view
        """
        View.__init__(self)
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/FirstRunView.ui")
        builder.connect_signals(self)
        self.add(builder.get_object("widget"))

#######################
# PROTECTED           #
#######################
    def _on_state_set(self, switch, state):
        """
            Save network state
            @param switch as Gtk.Switch
            @param state as bool
        """
        Lp().settings.set_value("network-access", GLib.Variant("b", state))

#######################
# PRIVATE             #
#######################
