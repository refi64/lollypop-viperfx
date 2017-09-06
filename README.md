# Lollypop

[![Join the chat at https://gitter.im/gnumdk/lollypop](https://badges.gitter.im/gnumdk/lollypop.svg)](https://gitter.im/gnumdk/lollypop?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

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

- `gtk3 >= 3.14`
- `gobject-introspection`
- `appstream-glib`
- `gir1.2-gstreamer-1.0 (Debian)`
- `python3`
- `meson >= 0.41`
- `ninja`
- `totem-plparser`
- `python-cairo`
- `python-dbus`
- `python-gobject`
- `python-sqlite`
- `python-pylast >= 1.0`

## Building from git

```bash
$ git clone https://github.com/gnumdk/lollypop.git
$ cd lollypop
$ meson builddir --prefix=/usr
# sudo ninja -C builddir install
```

In case you want the integration with [Last.fm](http://last.fm) to work you need to install `pylast`

```bash
# apt-get install python3-pip
# pip3 install pylast
```

### On Debian (Jessie)

```bash
$ git clone https://github.com/gnumdk/lollypop.git
$ cd lollypop
# apt-get install meson libglib2.0-dev yelp-tools libgirepository1.0-dev libgtk-3-dev
$ meson builddir --prefix=/usr
# sudo ninja -C builddir install
```

### On Fedora

```bash
$ git clone https://github.com/gnumdk/lollypop.git
$ cd lollypop
# sudo dnf install meson glib2-devel yelp-tools gtk3-devel gobject-introspection-devel python3
$ meson builddir --prefix=/usr
# sudo ninja -C builddir install
```
