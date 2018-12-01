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

from gi.repository import GLib, Gtk, Gdk

from gettext import gettext as _
from random import randint

from lollypop.define import App


class DonationContainer:
    """
        Donation management for main view
    """

    __DONATION = 1

    def __init__(self):
        """
            Init container
        """
        # Show donation notification
        if App().settings.get_value("donation").get_int32() != self.__DONATION:
            GLib.timeout_add_seconds(randint(3600, 7200),
                                     self.__show_donation)

############
# PRIVATE  #
############
    def __show_donation(self):
        """
            Show a notification telling user to donate a little
        """
        from lollypop.app_notification import AppNotification
        notification = AppNotification(
            _("Please consider a donation to the project"),
            [_("PayPal"), _("Patreon")],
            [lambda: Gtk.show_uri_on_window(
                App().window,
                "https://www.paypal.me/lollypopgnome",
                Gdk.CURRENT_TIME),
             lambda: Gtk.show_uri_on_window(
                App().window,
                "https://www.patreon.com/gnumdk",
                Gdk.CURRENT_TIME)])
        self.add_overlay(notification)
        notification.show()
        notification.set_reveal_child(True)
        App().settings.set_value("donation",
                                 GLib.Variant("i", self.__DONATION))
