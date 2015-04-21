#!/usr/bin/python
# Copyright (c) 2014-2015 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# Copyright (C) 2010 Jonathan Matthew (replay gain code)
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

from gi.repository import Gst

from lollypop.define import Objects

class PlayerReplayGain:
    """
        Init replay gain on playbin
        @param playbin as Gst play bin
    """
    def __init__(self, playbin):
        self._rgfilter = Gst.ElementFactory.make("bin", "bin")

        self._rg_audioconvert1 = Gst.ElementFactory.make("audioconvert",
                                                         "audioconvert")
        self._rg_audioconvert2 = Gst.ElementFactory.make("audioconvert",
                                                         "audioconvert2")

        self._rgvolume = Gst.ElementFactory.make("rgvolume",
                                                 "rgvolume")
        self._rglimiter = Gst.ElementFactory.make("rglimiter",
                                                  "rglimiter")
        self._rg_audiosink = Gst.ElementFactory.make("autoaudiosink",
                                                     "autoaudiosink")

        if not self._rgfilter or not self._rg_audioconvert1 or\
           not self._rg_audioconvert2 or not self._rgvolume or\
           not self._rglimiter or not self._rg_audiosink:
            print("Replay Gain not available, ")
            print("please check your gstreamer installation...")
            return

        self._rgvolume.props.pre_amp = Objects.settings.get_value(
                                            "replaygain").get_double()

        self._rgfilter.add(self._rgvolume)
        self._rgfilter.add(self._rg_audioconvert1)
        self._rgfilter.add(self._rg_audioconvert2)
        self._rgfilter.add(self._rglimiter)
        self._rgfilter.add(self._rg_audiosink)

        self._rg_audioconvert1.link(self._rgvolume)
        self._rgvolume.link(self._rg_audioconvert2)
        self._rgvolume.link(self._rglimiter)
        self._rg_audioconvert2.link(self._rg_audiosink)

        self._rgfilter.add_pad(Gst.GhostPad.new(
                                "sink",
                                self._rg_audioconvert1.get_static_pad("sink")))

        playbin.set_property("audio-sink", self._rgfilter)

