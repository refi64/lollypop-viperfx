#!/usr/bin/env python3

from os import environ, path
from subprocess import call

prefix = environ.get('MESON_INSTALL_PREFIX', '/usr/local')
datadir = path.join(prefix, 'share')
destdir = environ.get('DESTDIR', '')

if not destdir:
    print('Updating icon cache...')
    call(['gtk-update-icon-cache', '-qtf', path.join(datadir, 'icons', 'hicolor')])
    print("Installing new Schemas")
    call(['glib-compile-schemas', path.join(datadir, 'glib-2.0/schemas')])
    call(['chmod', '+x', path.join(prefix, 'bin', 'lollypop')])
    call(['chmod', '+x', path.join(prefix, 'bin', 'lollypop-cli')])
    call(['chmod', '+x', path.join(prefix, 'libexec', 'lollypop-sp')])
