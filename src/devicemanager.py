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

from gi.repository import Gtk, GLib, GObject, Pango
import os
from time import sleep
from shutil import copyfile
from gettext import gettext as _
from _thread import start_new_thread

from lollypop.define import Objects
from lollypop.utils import translate_artist_name


# Dialog for synchronize mtp devices
class DeviceManagerWidget(Gtk.Bin):
    __gsignals__ = {
        'sync-finished': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    """
        Init ui with a scrolled treeview
        @param device as Device
        @param progress bar as Gtk.ProgressBar
        @param parent as Gtk.Widget
    """
    def __init__(self, device, progress, parent):
        Gtk.Bin.__init__(self)
        self._parent = parent
        self._device = device
        self._progress = progress
        self._on_disk_playlists = None
        self._syncing = False
        self._errors = False
        self._in_thread = False
        self._path = None
        self._total = 0  # Total files to sync
        self._done = 0   # Handled files on sync
        self._fraction = 0.0

        builder = Gtk.Builder()
        builder.add_from_resource(
                '/org/gnome/Lollypop/DeviceManagerWidget.ui'
                                  )
        self._error_label = builder.get_object('error-label')

        self._model = Gtk.ListStore(bool, str)
        self._model.set_sort_column_id(1, Gtk.SortType.ASCENDING)
        self._model.set_sort_func(1, self._sort_items)

        self._view = builder.get_object('view')
        self._view.set_model(self._model)

        builder.connect_signals(self)

        self.add(builder.get_object('widget'))

        self._infobar = builder.get_object('infobar')
        self._infobar_label = builder.get_object('infobarlabel')

        renderer0 = Gtk.CellRendererToggle()
        renderer0.set_property('activatable', True)
        renderer0.connect('toggled', self._on_playlist_toggled)
        column0 = Gtk.TreeViewColumn("toggle", renderer0, active=0)

        renderer1 = Gtk.CellRendererText()
        renderer1.set_property('ellipsize-set', True)
        renderer1.set_property('ellipsize', Pango.EllipsizeMode.END)
        renderer1.set_property('editable', True)
        column1 = Gtk.TreeViewColumn('text', renderer1, text=1)
        column1.set_expand(True)

        self._view.append_column(column0)
        self._view.append_column(column1)

    """
        Populate playlists, thread safe
    """
    def populate(self):
        self._model.clear()
        playlists = Objects.playlists.get()
        GLib.idle_add(self._append_playlists, playlists)

    """
        Set available playlists
        @param path as str
    """
    def set_playlists(self, playlists, path):
        self._on_disk_playlists = playlists
        self._path = path

    """
        @return True if syncing
    """
    def is_syncing(self):
        return self._syncing

    """
        Start synchronisation
    """
    def sync(self):
        self._syncing = True
        self._view.set_sensitive(False)
        self._progress.show()
        playlists = []
        for item in self._model:
            if item[0]:
                playlists.append(item[1])
        start_new_thread(self._sync, (playlists,))

    """
        Cancel synchronisation
    """
    def cancel_sync(self):
        self._view.set_sensitive(True)
        self._syncing = False

#######################
# PRIVATE             #
#######################
    """
        Sort model
    """
    def _sort_items(self, model, itera, iterb, data):
        a = model.get_value(itera, 1)
        b = model.get_value(iterb, 1)
        return a > b

    """
        Append a playlist
        @param playlists as [str]
        @param playlist selected as bool
    """
    def _append_playlists(self, playlists):
        if playlists:
            playlist = playlists.pop(0)
            selected = playlist[1]+".m3u" in self._on_disk_playlists
            self._model.append([selected, playlist[1]])
            GLib.idle_add(self._append_playlists, playlists)
        else:
            self._view.get_selection().unselect_all()

    """
        Update progress bar smoothly
    """
    def _update_progress(self):
        current = self._progress.get_fraction()
        if self._syncing:
            progress = (self._fraction-current)/10000
        else:
            progress = 0.001

        if current < self._fraction:
            self._progress.set_fraction(current+progress)
            if not self._progress.is_visible():
                self._progress.show()
        if self._syncing or current < 1.0:
            GLib.idle_add(self._update_progress)
        else:
            GLib.timeout_add(1000, self._progress.hide)

    """
        Sync playlists with device as this
        @param playlists as [str]
    """
    def _sync(self, playlists):
        try:
            GLib.idle_add(self._progress.set_fraction, 0.0)
            self._in_thread = True
            self._errors = False
            sql = Objects.db.get_cursor()
            # For progress bar
            self._total = 1
            self._done = 0
            self._fraction = 0.0
            GLib.idle_add(self._update_progress)

            # New tracks
            for playlist in playlists:
                self._fraction = self._done/self._total
                self._total += len(Objects.playlists.get_tracks(playlist))
            # Old tracks
            for root, dirs, files in os.walk(self._path+"/tracks"):
                for f in files:
                    self._total += 1

            # Copy new tracks to device
            if self._syncing:
                self._copy_to_device(playlists, sql)

            # Remove old tracks from device
            if self._syncing:
                self._remove_from_device(playlists, sql)

            # Empty dirs, do not remove them or sync will fail
            # I/O errors...
            if self._syncing:
                self._empty_dirs(self._path+"/tracks")

            # Delete old playlists
            for f in os.listdir(self._path):
                if f.endswith(".m3u") and f[:-4] not in playlists:
                    self._delete("%s/%s" % (self._path, f))

        except Exception as e:
            print("DeviceManagerWidget::_sync(): %s" % e)
            self._errors = True
        self._fraction = 1.0
        if self._syncing:
            GLib.idle_add(self._view.set_sensitive, True)
            GLib.idle_add(self.emit, 'sync-finished')
        
        GLib.idle_add(self._progress.hide)
        self._syncing = False
        self._in_thread = False

    """
        Copy file from playlist to device
        @param playlists as [str]
        @param sql cursor
    """
    def _copy_to_device(self, playlists, sql):
        for playlist in playlists:
            # Create playlist
            try:
                m3u = open("%s/%s.m3u" % (self._path, playlist), "w")
                m3u.write("#EXTM3U\n")
            except:
                m3u = None

            # Start copying
            tracks_id = Objects.playlists.get_tracks_id(playlist, sql)
            for track_id in tracks_id:
                if not self._syncing:
                    self._fraction = 1.0
                    self._in_thread = False
                    return
                album_id = Objects.tracks.get_album_id(track_id, sql)
                album_name = Objects.albums.get_name(album_id, sql)
                artist_name = translate_artist_name(
                                 Objects.albums.get_artist_name(album_id, sql))
                track_path = Objects.tracks.get_path(track_id, sql)
                on_device_album_path = "%s/tracks/%s_%s" %\
                                       (self._path,
                                        artist_name.lower(),
                                        album_name.lower())

                self._mkdir(on_device_album_path)

                # Copy album art
                art = Objects.art.get_art_path(album_id, sql)
                if art:
                    dst_art = "%s/cover.jpg" % on_device_album_path
                    if not os.path.exists(dst_art):
                        self._copyfile(art, dst_art)

                track_name = os.path.basename(track_path)
                dst_path = "%s/%s" % (on_device_album_path, track_name)
                if m3u:
                    m3u.write("tracks/%s_%s/%s\n" %
                              (artist_name.lower(),
                               album_name.lower(),
                               track_name))
                if not os.path.exists(dst_path):
                    self._copyfile(track_path, dst_path)
                else:
                    self._done += 1
                self._done += 1
                self._fraction = self._done/self._total
            if m3u:
                m3u.close()

    """
        Delete files not available in playlist
        if sql None, delete all files
        @param playlists as [str]
        @param sql cursor
    """
    def _remove_from_device(self, playlists, sql):
        tracks_path = []
        tracks_id = []

        # Get tracks ids
        for playlist in playlists:
            tracks_id += Objects.playlists.get_tracks_id(playlist, sql)

        # Get tracks paths
        for track_id in tracks_id:
            if not self._syncing:
                self._fraction = 1.0
                self._in_thread = False
                return
            album_id = Objects.tracks.get_album_id(track_id, sql)
            album_name = Objects.albums.get_name(album_id, sql)
            artist_name = translate_artist_name(
                                 Objects.albums.get_artist_name(album_id, sql))
            track_path = Objects.tracks.get_path(track_id, sql)
            album_path = "%s/tracks/%s_%s" % (self._path,
                                              artist_name.lower(),
                                              album_name.lower())
            track_name = os.path.basename(track_path)
            dst_path = "%s/%s" % (album_path, track_name)
            tracks_path.append(dst_path)

        # Delete file on device and not in playlists
        for root, dirs, files in os.walk("%s/tracks" % self._path):
            for f in files:
                if not self._syncing:
                    self._fraction = 1.0
                    self._in_thread = False
                    return
                if f != "cover.jpg":
                    filepath = os.path.join(root, f)
                    if filepath not in tracks_path:
                        self._delete(filepath)
                self._done += 1
                self._fraction = self._done/self._total

    """
        Del empty dirs, cover.jpg doesn't count
        @param path as str
    """
    def _empty_dirs(self, path):
        for root, dirs, files in os.walk(path, topdown=False):
            for d in dirs:
                if not self._syncing:
                    self._fraction = 1.0
                    self._in_thread = False
                    return
                dirpath = os.path.join(root, d)
                ls = os.listdir(dirpath)
                if len(ls) == 1:
                    if ls[0] == "cover.jpg":
                        self._delete("%s/%s" % (dirpath, ls[0]))
                        self._done += 1
                        self._fraction = self._done/self._total

    """
        Copy file
        @param trackpath as str
        @param destination path as str
    """
    def _copyfile(self, track_path, dst_path, retry=0):
        try:
            copyfile(track_path, dst_path)
        except Exception as e:
            print("DeviceManagerWidget::_copyfile(): %s" % e)
            sleep(5)
            if retry < 5:
                retry += 1
                self._copyfile(track_path, dst_path, retry)
            else:
                self._errors = True

    """
        Delete file
        @param path as str
    """
    def _delete(self, path, retry=0):
        try:
            os.remove(path)
        except Exception as e:
            print("DeviceManagerWidget::_delete(): %s" % e)
            sleep(5)
            if retry < 5:
                retry += 1
                self._delete(path, retry)
            else:
                self._errors = True

    """
        Make dir in device
        @param path as str
    """
    def _mkdir(self, path, retry=0):
        try:
            os.makedirs(path, exist_ok=True)
        except Exception as e:
            print("DeviceManagerWidget::_mkdir(): %s" % e)
            sleep(5)
            if retry < 5:
                retry += 1
                self._mkdir(path, retry)
            else:
                self._errors = True

    """
        Show information bar with error message
    """
    def _show_info_bar(self):
        error_text = _("Unknown error while syncing,"
                       " try to reboot your device")
        try:
            stat = os.statvfs(self._path)
            # Check available size, seems to be 1024 but can't test with
            # my android device, so less than 1Mo should be a good test
            if stat.f_frsize * stat.f_bavail < 1048576:
                error_text = _("No free space available on device")
        except:
            pass
        self._error_label.set_text(error_text)
        self._infobar.show()

    """
        Hide infobar
        @param widget as Gtk.Infobar
        @param reponse id as int
    """
    def _on_response(self, infobar, response_id):
        if response_id == Gtk.ResponseType.CLOSE:
            self._infobar.hide()

    """
        When playlist is activated, add object to playlist
        @param widget as cell renderer
        @param path as str representation of Gtk.TreePath
    """
    def _on_playlist_toggled(self, view, path):
        iterator = self._model.get_iter(path)
        toggle = not self._model.get_value(iterator, 0)
        self._model.set_value(iterator, 0, toggle)
