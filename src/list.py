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


# Double linked list
class LinkedList:
    """
        Init list
        @param value as int
    """
    def __init__(self, value=None, next=None, prev=None):
        self.__value = value
        self.__next = next
        self.__prev = prev

    """
        True if list has next
        @return has next as bool
    """
    def has_next(self):
        return self.__next is not None

    """
        Return next
        @return next as LinkedList
    """
    def get_next(self):
        return self.__next

    """
        Set next
        @param next as linked list
    """
    def set_next(self, next):
        self.__next = next

    """
        True if list has prev
        @return has next as bool
    """
    def has_prev(self):
        return self.__prev is not None

    """
        Return prev
        @return prev as LinkedList
    """
    def get_prev(self):
        return self.__prev

    """
        Set prev
        @param prev as linked list
    """
    def set_prev(self, prev):
        self.__prev = prev

    """
        Get value
        @return value as int
    """
    def get_value(self):
        return self.__value
