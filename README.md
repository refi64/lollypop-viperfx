# Lollypop music player (with ViPER's audio support)

## ViPER's audio notes

- **Don't redistribute this.** The terms of it are a bit hazy and not something you probably
  want to play with.
- Only supports Clarity and the EQ for now, because I'm probably going to have to redo the entire
  stinking equalizer screen to make the others configurable. :(

### Installing

```bash
$ flatpak-builder --force-clean --install --user _build org.gnome.Lollypop.json
```

## Original README

[![Please do not theme this app](https://stopthemingmy.app/badge.svg)](https://stopthemingmy.app)

![Lollypop logo](https://gitlab.gnome.org/gnumdk/lollypop/raw/master/data/icons/hicolor/256x256/apps/org.gnome.Lollypop.png)

Lollypop is a new GNOME music playing application.

- Users: https://wiki.gnome.org/Apps/Lollypop

- Translators: https://hosted.weblate.org/projects/gnumdk/

It provides:

- MP3/4, Ogg and FLAC.
- Genre/cover browsing
- Genre/artist/cover browsing
- Search
- Main playlist (called queue in other apps)
- Party mode
- ReplayGain
- Cover art downloader
- Context artist view
- MTP sync
- Fullscreen view
- Radio support
- Last.fm support
- Auto install codecs
- HiDPI support
- TuneIn support

## Depends on

- `gtk3 >= 3.20`
- `gobject-introspection`
- `appstream-glib`
- `gir1.2-gstreamer-1.0 (Debian)`
- `python3`
- `meson >= 0.40`
- `ninja`
- `totem-plparser`
- `python-cairo`
- `python-gobject`
- `python-sqlite`
- `python-pylast >= 1.0`

## Building from Git

```bash
$ git clone https://gitlab.gnome.org/World/lollypop.git
$ cd lollypop
$ meson builddir --prefix=/usr
# sudo ninja -C builddir install
```

Installation of `pylast` is required for integration with [Last.fm](http://last.fm)

```bash
# apt-get install python3-pip
# pip3 install pylast
```

### On Debian/Ubuntu

```bash
$ git clone https://gitlab.gnome.org/World/lollypop.git
$ cd lollypop
# apt-get install meson libglib2.0-dev yelp-tools libgirepository1.0-dev libgtk-3-dev gir1.2-totemplparser-1.0
$ meson builddir --prefix=/usr
# sudo ninja -C builddir install
```

### On Fedora

```bash
$ git clone https://gitlab.gnome.org/World/lollypop.git
$ cd lollypop
# sudo dnf install meson glib2-devel yelp-tools gtk3-devel gobject-introspection-devel python3
$ meson builddir --prefix=/usr
# sudo ninja -C builddir install
```
