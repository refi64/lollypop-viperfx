# Copyright (c) 2014-2018 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import Gtk, GLib, Pango

from gettext import gettext as _

from lollypop.define import App
from lollypop.logger import Logger


class BehaviourSettingsWidget(Gtk.Bin):
    """
        Widget allowing user to set behaviour options
    """

    def __init__(self):
        """
            Init widget
        """
        Gtk.Bin.__init__(self)
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/SettingsBehaviour.ui")

        switch_scan = builder.get_object("switch_scan")
        switch_scan.set_state(App().settings.get_value("auto-update"))

        switch_background = builder.get_object("switch_background")
        switch_background.set_state(
            App().settings.get_value("background-mode"))

        switch_state = builder.get_object("switch_state")
        switch_state.set_state(App().settings.get_value("save-state"))

        switch_network_access = builder.get_object("switch_network_access")
        network_access = App().settings.get_value("network-access")
        switch_network_access.set_state(network_access)

        switch_transitions = builder.get_object("switch_transitions")
        smooth_transitions = App().settings.get_value("smooth-transitions")
        switch_transitions.set_state(smooth_transitions)
        builder.get_object("transitions_button").set_sensitive(
            smooth_transitions)

        switch_mix_party = builder.get_object("switch_mix_party")
        switch_mix_party.set_state(App().settings.get_value("party-mix"))

        switch_artwork_tags = builder.get_object("switch_artwork_tags")
        grid_behaviour = builder.get_object("grid_behaviour")
        # Check for kid3-cli
        self.__check_for_kid3(switch_artwork_tags, grid_behaviour)

        combo_preview = builder.get_object("combo_preview")

        self.__popover_transitions = builder.get_object("popover-transitions")
        self.__scale_transition_duration = builder.get_object(
            "scale_transition_duration")
        self.__scale_transition_duration.set_range(1, 20)
        self.__scale_transition_duration.set_value(
            App().settings.get_value("transition-duration").get_int32())

        self.__set_outputs(combo_preview)

        self.add(builder.get_object("widget"))
        builder.connect_signals(self)

#######################
# PROTECTED           #
#######################
    def _on_enable_network_access_state_set(self, widget, state):
        """
            Save network access state
            @param widget as Gtk.Switch
            @param state as bool
        """
        App().settings.set_value("network-access",
                                 GLib.Variant("b", state))

    def _on_switch_scan_state_set(self, widget, state):
        """
            Update scan setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        App().settings.set_value("auto-update",
                                 GLib.Variant("b", state))

    def _on_switch_background_state_set(self, widget, state):
        """
            Update background mode setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        App().settings.set_value("background-mode",
                                 GLib.Variant("b", state))

    def _on_switch_state_state_set(self, widget, state):
        """
            Update save state setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        App().settings.set_value("save-state",
                                 GLib.Variant("b", state))

    def _on_transitions_button_clicked(self, widget):
        """
            Show popover
            @param widget as Gtk.Button
        """
        self.__popover_transitions.popup()
        # https://gitlab.gnome.org/GNOME/pango/issues/309
        self.__scale_transition_duration.set_draw_value(True)

    def _on_switch_transitions_state_set(self, widget, state):
        """
            Update smooth transitions setting
            @param widget as Gtk.Button
            @param state as bool
        """
        widget.set_sensitive(state)
        App().settings.set_value("smooth-transitions",
                                 GLib.Variant("b", state))
        App().player.update_crossfading()

    def _on_switch_mix_party_state_set(self, widget, state):
        """
            Update party mix setting
            @param widget as Gtk.Range
        """
        App().settings.set_value("party-mix", GLib.Variant("b", state))
        App().player.update_crossfading()

    def _on_scale_transition_duration_value_changed(self, widget):
        """
            Update mix duration setting
            @param widget as Gtk.Range
        """
        value = widget.get_value()
        App().settings.set_value("transition-duration",
                                 GLib.Variant("i", value))

    def _on_switch_artwork_tags_state_set(self, widget, state):
        """
            Update artwork in tags setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        App().settings.set_value("save-to-tags", GLib.Variant("b", state))

    def _on_combo_preview_changed(self, combo):
        """
            Update preview setting
            @param combo as Gtk.ComboBoxText
        """
        App().settings.set_value("preview-output",
                                 GLib.Variant("s", combo.get_active_id()))
        App().player.set_preview_output()

    def _on_preview_query_tooltip(self, combo, x, y, keyboard, tooltip):
        """
            Show tooltip if needed
            @param combo as Gtk.ComboBoxText
            @param x as int
            @param y as int
            @param keyboard as bool
            @param tooltip as Gtk.Tooltip
        """
        combo.set_tooltip_text(combo.get_active_text())

#######################
# PRIVATE             #
#######################
    def __set_outputs(self, combo):
        """
            Set outputs in combo
            @parma combo as Gtk.ComboxBoxText
        """
        renderer = combo.get_cells()[0]
        renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
        renderer.set_property("max-width-chars", 60)
        if GLib.find_program_in_path("flatpak-spawn") is not None:
            argv = ["flatpak-spawn", "--host", "pacmd", "list-sinks"]
        else:
            argv = ["pacmd", "list-sinks"]
        try:
            (pid, stdin, stdout, stderr) = GLib.spawn_async(
                argv, flags=GLib.SpawnFlags.SEARCH_PATH |
                GLib.SpawnFlags.DO_NOT_REAP_CHILD,
                standard_input=False,
                standard_output=True,
                standard_error=False
            )
            GLib.child_watch_add(GLib.PRIORITY_DEFAULT_IDLE, pid,
                                 self.__on_pacmd_result, stdout, combo)
        except Exception as e:
            Logger.error("SettingsDialog::__set_outputs(): %s" % e)

    def __check_for_kid3(self, switch, grid):
        """
            Update grid/switch based on result
            @param switch as Gtk.Switch
            @param grid as Gtk.Grid
        """
        if not App().art.kid3_available:
            h = grid.child_get_property(switch, "height")
            w = grid.child_get_property(switch, "width")
            l = grid.child_get_property(switch, "left-attach")
            t = grid.child_get_property(switch, "top-attach")
            switch.destroy()
            label = Gtk.Label.new(_("You need to install kid3-cli"))
            label.get_style_context().add_class("dim-label")
            label.set_property("halign", Gtk.Align.END)
            label.show()
            grid.attach(label, l, t, w, h)
        else:
            switch.set_state(App().settings.get_value("save-to-tags"))

    def __on_pacmd_result(self, pid, status, stdout, combo):
        """
            Read output and set combobox
            @param pid as int
            @param status as bool
            @param stdout as int
            @param combo as Gtk.ComboBox
        """
        from re import findall, DOTALL
        GLib.spawn_close_pid(pid)
        io = GLib.IOChannel.unix_new(stdout)
        [status, data] = io.read_to_end()
        if data:
            string = data.decode("utf-8")
            current = App().settings.get_value("preview-output").get_string()
            devices = findall('name: <([^>]*)>', string, DOTALL)
            names = findall('device.description = "([^"]*)"', string, DOTALL)
            if names:
                for i in range(0, len(names)):
                    combo.append(devices[i], names[i])
                    if devices[i] == current:
                        combo.set_active_id(devices[i])
            else:
                combo.set_sensitive(False)
