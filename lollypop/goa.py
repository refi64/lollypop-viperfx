# Copyright (c) 2018 Philipp Wolfer <ph.wolfer@gmail.com>
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
from gi.repository import GObject

try:
    gi.require_version("Goa", "1.0")
    from gi.repository import Goa
except:
    pass

from lollypop.utils import debug


class GoaSyncedAccount(GObject.Object):

    def __init__(self, provider_name):
        GObject.Object.__init__(self)
        self._provider_name = provider_name
        self._proxy = None
        self._account = None
        self._oauth2_based = None
        try:
            self._client = Goa.Client.new_sync()
            self._find_account()
            self.emit("account-switched")
            self._client.connect("account-added", self.on_account_added)
            self._client.connect("account-removed", self.on_account_removed)
            self._client.connect("account-changed", self.on_account_changed)
        except:
            debug("GOA not available")
            self.__client = None

    @GObject.Signal("account-switched")
    def account_switched(self):
        debug("GOA account-switched")

    @property
    def has_account(self):
        return self._proxy is not None

    @property
    def account(self):
        if self._proxy is None:
            return None
        if self._account is None:
            self._account = self._proxy.get_account()
        return self._account

    @property
    def oauth2_based(self):
        if self._proxy is None:
            return None
        if self._oauth2_based is None:
            self._oauth2_based = self._proxy.get_oauth2_based()
        return self._oauth2_based

    def on_account_added(self, client, proxy):
        debug("GOA account added")
        if self._proxy is None and self._account_matches_provider(proxy):
            self._proxy = proxy
            self.emit("account-switched")

    def on_account_removed(self, client, proxy):
        debug("GOA account removed")
        if self._proxy == proxy:
            # Try finding a new account
            self._find_account()
            self.emit("account-switched")

    def on_account_changed(self, client, proxy):
        debug("GOA account changed")
        if self._proxy == proxy:
            self._account = None
            self._oauth2_based = None

    def _find_account(self):
        debug("GOA _find_account")
        self._proxy = None
        try:
            for proxy in self._client.get_accounts():
                if self._account_matches_provider(proxy):
                    debug("GOA account found")
                    self._proxy = proxy
                    return
        except Exception as e:
            debug("GOA _find_account failed: %s" % e)
            pass

    def _account_matches_provider(self, proxy):
        account = proxy.get_account()
        debug("GOA _account_matches_provider: %s = %s ?" %
              (account.props.provider_name, self._provider_name))
        return account.props.provider_name == self._provider_name
