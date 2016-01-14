#Lollypop


Lollypop is a new GNOME music playing application.


For users: http://gnumdk.github.io/lollypop-web

For translators: https://www.transifex.com/projects/p/lollypop/

It provides:
- mp3/4, ogg and flac.
- Genre/Cover browsing
- Genre/Artist/Cover browsing
- Search
- Main playlist (called queue in other apps)
- Party mode
- Replay gain
- Cover art downloader
- Context artist view
- MTP sync
- Fullscreen view
- Radios support
- Last.fm support
- Auto install codecs
- HiDPI support
- Tunein support

##Depends on
- gtk3
- gobject-introspection
- gir1.2-gstreamer-1.0 (Debian)
- python3
- intltool (make)
- itstool (make)
- totem-plparser
- python (make)
- python-cairo
- python-dbus
- python-gobject
- python-sqlite
- python-pylast >= 1.0

##Building from git
```
$ git clone https://github.com/gnumdk/lollypop.git
$ cd lollypop
$ ./autogen.sh
$ make
# make install
```

In case you want the integration with [Last.fm](http://last.fm) to work you need to install `pylast`
```
# apt-get install python3-pip
# pip3 install pylast
```

### On Debian (Jessie)
```
$ git clone https://github.com/gnumdk/lollypop.git
$ cd lollypop
# apt-get install autoconf
# apt-get install libglib2.0-dev
# apt-get install intltool
# apt-get install yelp-tools 
# apt-get install libgirepository1.0-dev
# apt-get install libgtk-3-dev
$ ./autogen.sh
$ make
# make install
```

Instead of `make install` you might want to use `checkinstall`
```
# apt-get checkinstall
# checkinstall
```
This will allow you to uninstall Lollypop as a package, for example with `apt-get uninstall lollypop`.
