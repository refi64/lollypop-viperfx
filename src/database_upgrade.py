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

from lollypop.sqlcursor import SqlCursor


class DatabaseUpgrade:
    """
        Manage database schema upgrades
    """

    def __init__(self, version, db):
        """
            Init object
            @param version as int
            @param db as Database
        """
        self._version = version
        self._db = db
        # Here are schema upgrade, key is database version,
        # value is sql request
        self._UPGRADES = {
            1: "update tracks set duration=CAST(duration as INTEGER);"
                         }

    """
        Return upgrade count
        @return int
    """
    def count(self):
        return len(self._UPGRADES)

    """
        Upgrade database based on version
        @return new db version as int
    """
    def do_db_upgrade(self):
        with SqlCursor(self._db) as sql:
            for i in range(self._version+1, len(self._UPGRADES)+1):
                try:
                    sql.execute(self._UPGRADES[i])
                    sql.commit()
                except Exception as e:
                    print("Database upgrade failed: ", e)
            return len(self._UPGRADES)
