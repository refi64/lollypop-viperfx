# Lollypop

![Lollypop logo](https://raw.github.com/gnumdk/lollypop/master/data/icons/hicolor/256x256/apps/org.gnome.Lollypop.png)

Lollypop is a new GNOME music playing application.


- For users: http://gnumdk.github.io/lollypop-web

- For packagers: You need to provide https://github.com/gnumdk/lollypop-portal

- FAQ: https://github.com/gnumdk/lollypop/wiki

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

## Depends on
- gtk3 >= 3.14
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

## Building from git
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
# apt-get install autoconf libglib2.0-dev intltool yelp-tools libgirepository1.0-dev libgtk-3-dev
$ ./autogen.sh
$ make
# make install
```

Instead of `make install` you might want to use `checkinstall`
```
# apt-get install checkinstall
# checkinstall
```
This will allow you to uninstall Lollypop as a package, for example with `apt-get uninstall lollypop`.

### On Fedora
```
$ git clone https://github.com/gnumdk/lollypop.git
$ cd lollypop
# sudo dnf install autoconf glib2-devel intltool yelp-tools gtk3-devel gobject-introspection-devel python3 itstool
$ ./autogen.sh
$ make
# make install
```

