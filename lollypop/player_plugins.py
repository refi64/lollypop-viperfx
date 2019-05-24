# Copyright (c) 2014-2019 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from lollypop.define import App
from lollypop.logger import Logger


class PluginsPlayer:
    """
        Replay gain player
    """

    def __init__(self, playbin):
        """
            Init playbin
            @param playbin as Gst.bin
        """
        self.__playbin = playbin
        self.init()

    def init(self):
        """
            Init playbin
        """
        bin = Gst.ElementFactory.make("bin", "bin")

        rg_audioconvert1 = Gst.ElementFactory.make("audioconvert",
                                                   "audioconvert1")
        rg_audioconvert2 = Gst.ElementFactory.make("audioconvert",
                                                   "audioconvert2")
        rg_audioconvert3 = Gst.ElementFactory.make("audioconvert",
                                                   "audioconvert3")
        self.volume = Gst.ElementFactory.make("volume",
                                              "volume")
        self.volume.props.volume = 0.0
        self.rgvolume = Gst.ElementFactory.make("rgvolume",
                                                "rgvolume")
        rglimiter = Gst.ElementFactory.make("rglimiter",
                                            "rglimiter")
        rg_audiosink = Gst.ElementFactory.make("autoaudiosink",
                                               "autoaudiosink")

        if not bin or not rg_audioconvert1 or\
           not rg_audioconvert2 or not self.rgvolume or\
           not rglimiter or not rg_audiosink:
            Logger.info("Replay Gain not available, ")
            Logger.info("please check your gstreamer installation...")
            return

        if self.rgvolume is not None:
            self.rgvolume.props.album_mode = 1
            self.rgvolume.props.pre_amp = App().settings.get_value(
                "replaygain").get_double()

        bin.add(self.volume)
        bin.add(self.rgvolume)
        bin.add(rg_audioconvert1)
        bin.add(rg_audioconvert2)
        bin.add(rg_audioconvert3)
        bin.add(rglimiter)
        bin.add(rg_audiosink)

        if App().settings.get_value("equalizer-enabled"):
            self.__equalizer = Gst.ElementFactory.make("equalizer-10bands",
                                                       "equalizer-10bands")
            rg_audioconvert4 = Gst.ElementFactory.make("audioconvert",
                                                       "audioconvert4")
            bin.add(rg_audioconvert4)
            bin.add(self.__equalizer)
        else:
            self.__equalizer = None

        rg_audioconvert1.link(self.rgvolume)
        self.rgvolume.link(rg_audioconvert2)
        self.rgvolume.link(rglimiter)
        rg_audioconvert2.link(self.volume)
        self.volume.link(rg_audioconvert3)

        if self.__equalizer is None:
            rg_audioconvert3.link(rg_audiosink)
        else:
            rg_audioconvert3.link(self.__equalizer)
            self.__equalizer.link(rg_audioconvert4)
            rg_audioconvert4.link(rg_audiosink)

        bin.add_pad(Gst.GhostPad.new(
            "sink",
            rg_audioconvert1.get_static_pad("sink")))
        self.__playbin.set_property("audio-sink", bin)
        self.update_equalizer()

    def update_equalizer(self):
        """
            Update equalizer based on current settings
        """
        i = 0
        for value in App().settings.get_value("equalizer"):
            self.set_equalizer(i, value)
            i += 1

    def set_equalizer(self, band, value):
        """
            Set 10bands equalizer
            @param band as int
            @param value as int
        """
        try:
            if self.__equalizer is not None:
                self.__equalizer.set_property("band%s" % band, value)
        except Exception as e:
            Logger.error("PluginsPlayer::set_equalizer():", e)

#######################
# PRIVATE             #
#######################
