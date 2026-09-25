#!/bin/bash
#
# Run once by qtile's startup_once hook.  Port of ~/.xmonad/startup-hook.
#
# Gone, because Wayland, qtile or Ubuntu handles them natively now:
#   xcompmgr    -> compositing is built in
#   nitrogen    -> Screen(wallpaper=...) in config.py
#   setxkbmap   -> wl_input_rules in config.py
#   synclient   -> wl_input_rules in config.py
#   numlockx    -> kb_options="numpad:mac" in config.py
#   stalonetray -> widget.StatusNotifier in config.py
#   scrot       -> grim/slurp piped into swappy, bound directly in config.py
#   xautolock-guard -> qtile >= 0.35 speaks the idle-inhibit protocol, so
#                      browsers and call apps stop the idle timer themselves

run_once() {
	pgrep -f "$1" >/dev/null || "$@" &
}

# Make the session environment visible to DBus-activated services.  Without
# this the tray (StatusNotifier), the portals and the screenshot tooling
# don't see WAYLAND_DISPLAY and quietly misbehave.
dbus-update-activation-environment --systemd \
	WAYLAND_DISPLAY XDG_CURRENT_DESKTOP XDG_SESSION_TYPE DISPLAY 2>/dev/null

# Pin monitor positions (~/.config/kanshi/config) -- qtile's Wayland backend
# auto-arranges outputs by connect order, not physical position, so without
# this the laptop panel and the external monitor can land in the wrong
# left/right order.  Runs before anything else so bars/windows appear on the
# right screen from the start.
run_once kanshi

# Start everything that ships an XDG autostart entry -- the freedesktop
# mechanism Ubuntu already uses, so anything installed later is picked up
# without editing this file.  Entries marked OnlyShowIn=GNOME are skipped
# because XDG_CURRENT_DESKTOP is "qtile".
run_once dex -a

# Things dex won't cover:
#   nm-applet needs --indicator to speak SNI instead of the old XEmbed tray
#   gnome-keyring's autostart entry is OnlyShowIn=GNOME;Unity;MATE
run_once nm-applet --indicator
gnome-keyring-daemon --start --components=gpg,pkcs11,secrets,ssh >/dev/null 2>&1

# Clipboard manager, replacing the xmonad `copyq &` startup-hook line.
# CopyQ grabs its own global hotkey directly rather than through the WM
# (see mod+v in config.py, which just toggles its window via the CLI).
run_once copyq

# Lock after 3 minutes idle, and before suspend.  Requires qtile >= 0.35;
# the C Wayland backend only regained idle-notify-v1 then.  See README.
run_once swayidle -w \
	timeout 180 'swaylock -f -c 000000' \
	before-sleep 'swaylock -f -c 000000'

# Coding when it's dark (gammastep is the Wayland-native redshift).
# Location is the centre of France, not where I actually am: this file is in
# a public repo, and sunset timing doesn't need better than country accuracy.
# For the real thing without hardcoding it, use `gammastep -l geoclue2`.
run_once gammastep -l 46.6:2.5
