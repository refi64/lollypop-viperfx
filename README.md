Lollypop
========================

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

=== Depends on ===
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

=== Building from git ===

$ git clone https://github.com/gnumdk/lollypop.git

$ cd lollypop

$ ./autogen.sh

$ make

\# make install
