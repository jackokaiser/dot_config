"""
Qtile configuration, ported from my XMonad setup.

The organising idea is unchanged from XMonad: 12 workspaces laid out in a
grid that mirrors the number pad, navigated either by hitting the matching
number-pad key or by walking the grid with super+arrows.

    7:Paper   8:Dbg    9:Pix
    4:Docs    5:Dev    6:Web
    1:Term    2:Serv   3:Client
    0:Chat    Extr1    Extr2

Primary target is the Wayland backend, but everything here also works under
X11, so a fallback session still behaves.  The handful of places that differ
are guarded by IS_WAYLAND.

IMPORTANT, keyboard layout: qtile resolves a binding to a physical key
through that key's *unshifted* (level 0) keysym -- on X11 via
`code_to_syms[keycode][0]`, on Wayland via `xkb_keymap_key_get_syms_by_level(
..., level 0, ...)`.  On the fr (azerty) layout the unshifted top row is
& é " ' ( - è _ ç à ) =, so `Key([mod], "7")` grabs nothing reachable.  The
number row is therefore bound below by those keysym names.  If you ever move
to a us layout, swap NUMROW_KEYS for the plain digits.

The number pad looks contradictory and isn't: every physical keypad key's
symbol table is the pair [nav keysym, digit keysym] (e.g. [KP_Home, KP_7]),
regardless of the `numpad:*` xkb option (see wl_input_rules) -- level 0 is
always the nav keysym, level 1 is always the digit.  Only which level gets
*selected* for apps depends on the option.  `numpad:mac` (the current
default) pins the KEYPAD key type to the digit level unconditionally, so apps
always get digits regardless of NumLock state -- at the cost of the
keyboard's NumLock LED never lighting up, since qtile then never has a reason
to assert that modifier.  Tried plain `numpad:pc` (digit level only while
NumLock is actually on, honest LED) to get the LED back; on this external
keyboard it just didn't produce digits at all, so back to numpad:mac.  Either
way, qtile's own
bindings below ask the keymap for level 0 explicitly, so they
keep working as KP_Home/KP_Up/... no matter which option is active.
"""

import os
import subprocess

from libqtile import bar, hook, layout, qtile, widget
from libqtile.config import Click, Drag, Group, Key, Match, Screen
from libqtile.lazy import lazy

def _detect_backend():
    """Which backend are we running under?

    `libqtile.qtile` is a module-level global that starts life as a
    `_UndefinedQtile` placeholder whose `core.name` is None, and is only
    rebound to the real Qtile object by `libqtile.init()`.  So depending on
    load order this can legitimately be None rather than raising -- hence the
    environment fallbacks rather than a bare try/except.

    Only cosmetic choices (launcher, locker) depend on this; nothing that can
    fail the config, so a wrong guess is never fatal.
    """
    name = getattr(getattr(qtile, "core", None), "name", None)
    if name in ("wayland", "x11"):
        return name
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    if os.environ.get("XDG_SESSION_TYPE") == "x11" or os.environ.get("DISPLAY"):
        return "x11"
    return "wayland"


BACKEND = _detect_backend()
IS_WAYLAND = BACKEND == "wayland"

# --------------------------------------------------------------------------
# Basics
# --------------------------------------------------------------------------

MOD = "mod4"  # super

TERMINAL = "terminator"
BROWSER = "brave-browser"
EDITOR = "emacs"
FILE_MANAGER = "nautilus"
LAUNCHER = "rofi -show drun" if not IS_WAYLAND else "wofi --show drun"
LOCKER = "swaylock -f -c 000000" if IS_WAYLAND else "slock"

QTILE_DIR = os.path.expanduser("~/.config/qtile")

# Colours lifted from xmobarrc / xmonad.hs
BAR_BG = "#000000"
BAR_FG = "#999999"
TITLE_FG = "#eeeeee"
CURRENT_WS = "#e6744c"
VISIBLE_WS = "#c185a7"
URGENT_WS = "#cc0000"
FOCUSED_BORDER = "#ff0000"
NORMAL_BORDER = "#cccccc"

FONT = "Ubuntu Mono"
FONTSIZE = 14

# --------------------------------------------------------------------------
# Workspaces, laid out as the number pad
# --------------------------------------------------------------------------

GROUP_GRID = [
    ["7:Paper", "8:Dbg", "9:Pix"],
    ["4:Docs", "5:Dev", "6:Web"],
    ["1:Term", "2:Serv", "3:Client"],
    ["0:Chat", "Extr1", "Extr2"],
]

# Number-pad keysyms, in the same grid order.  These are the unshifted
# (numlock-off) names, so they match the physical key whether or not numlock
# is on -- which is what both backends grab on.
NUMPAD_KEYS = [
    ["KP_Home", "KP_Up", "KP_Prior"],
    ["KP_Left", "KP_Begin", "KP_Right"],
    ["KP_End", "KP_Down", "KP_Next"],
    ["KP_Insert", "KP_Delete", "KP_Enter"],
]

# Top-row keysyms on the fr layout, same grid order, so the number row
# shadows the number pad exactly as it did under XMonad.
#      7 8 9 / 4 5 6 / 1 2 3 / 0 - =
NUMROW_KEYS = [
    ["egrave", "underscore", "ccedilla"],
    ["apostrophe", "parenleft", "minus"],
    ["ampersand", "eacute", "quotedbl"],
    ["agrave", "parenright", "equal"],
]

GROUP_NAMES = [name for row in GROUP_GRID for name in row]
N_ROWS = len(GROUP_GRID)
N_COLS = len(GROUP_GRID[0])

# Per-workspace layouts, the equivalent of XMonad's onWorkspace.
GROUP_LAYOUTS = {
    "0:Chat": "max",           # just Slack, full screen
    "9:Pix": "monadthreecol",  # gimp panels left and right of the image
}

# Where windows go on their own, the equivalent of the XMonad manage hook.
GROUP_MATCHES = {
    "0:Chat": [Match(wm_class="Slack")],
    "9:Pix": [Match(wm_class="Gimp")],
}

groups = [
    Group(
        name,
        layout=GROUP_LAYOUTS.get(name),
        matches=GROUP_MATCHES.get(name, []),
    )
    for name in GROUP_NAMES
]


def _neighbour(name, d_row, d_col):
    """The group d_row/d_col away in the grid, or None at the edge.

    XMonad used Plane ... Finite, i.e. no wrap-around; same here.
    """
    if name not in GROUP_NAMES:
        return None
    row, col = divmod(GROUP_NAMES.index(name), N_COLS)
    row, col = row + d_row, col + d_col
    if not (0 <= row < N_ROWS and 0 <= col < N_COLS):
        return None
    return GROUP_GRID[row][col]


@lazy.function
def plane_focus(qtile, d_row, d_col):
    """Walk the workspace grid (super + arrows)."""
    target = _neighbour(qtile.current_group.name, d_row, d_col)
    if target:
        qtile.groups_map[target].toscreen(toggle=False)


@lazy.function
def plane_carry(qtile, d_row, d_col):
    """Walk the grid dragging the focused window along (super+shift+arrows)."""
    target = _neighbour(qtile.current_group.name, d_row, d_col)
    if target and qtile.current_window:
        qtile.current_window.togroup(target, switch_group=True)


def _screen_by_x(qtile, rank):
    """The rank-th screen counting left to right by physical x position.

    `qtile.screens` is ordered by however the Wayland backend enumerates
    outputs -- connector/detection order on wlroots -- not by where they
    sit on the desktop.  A docked laptop routinely enumerates the
    built-in eDP-1 before the external monitor even though xrandr places
    eDP-1 to its *right*, so screen index 0 is not reliably "the left
    screen".  Every screen-targeting binding/hook goes through this
    instead of a hardcoded index so "left"/"right" always match reality.
    """
    screens = sorted(qtile.screens, key=lambda s: s.x)
    return screens[rank] if rank < len(screens) else None


@lazy.function
def focus_screen_by_x(qtile, rank):
    scr = _screen_by_x(qtile, rank)
    if scr:
        qtile.focus_screen(scr.index)


@lazy.function
def window_to_screen_by_x(qtile, rank):
    scr = _screen_by_x(qtile, rank)
    if scr and qtile.current_window:
        qtile.current_window.toscreen(scr.index)


# --------------------------------------------------------------------------
# Keys
# --------------------------------------------------------------------------

# Screenshots: grim grabs pixels, piped straight into swappy -- a minimal
# GTK window where you drag to crop (and annotate if you want), then Ctrl+S
# to save under SHOT_DIR or Escape to throw the shot away. Nothing ever
# touches the clipboard; swappy only copies if you press its copy button.
# There is no Wayland equivalent of `scrot -u`: no client may read another
# client's pixels, so the second binding pre-selects a region with slurp
# before handing it to swappy, instead of grabbing the focused window.
SHOT_DIR = os.path.expanduser("~/Pictures/screenshots")
SWAPPY_CONFIG = os.path.join(os.path.dirname(__file__), "swappy.conf")
_swappy = f'swappy -c "{SWAPPY_CONFIG}" -f -'
SHOT_SCREEN = ["sh", "-c", f'mkdir -p "{SHOT_DIR}" && grim - | {_swappy}']
SHOT_REGION = ["sh", "-c", f'mkdir -p "{SHOT_DIR}" && grim -g "$(slurp)" - | {_swappy}']

keys = [
    # --- windows -------------------------------------------------------
    Key([MOD], "k", lazy.window.kill(), desc="Close window"),
    Key([MOD], "t", lazy.window.toggle_floating(), desc="Sink floating window back into tiling"),
    Key([MOD], "o", lazy.layout.next(), desc="Focus next window"),
    Key([MOD], "j", lazy.layout.next(), desc="Focus next window"),
    Key([MOD, "shift"], "j", lazy.layout.previous(), desc="Focus previous window"),
    Key(
        [MOD],
        "Return",
        # swap_main only exists on the Monad* layouts -- Max and Matrix have
        # no "master pane" concept, so without this filter the binding
        # throws "No such command" there (0:Chat is pinned to Max, so it'd
        # be every time you press it in that group).
        lazy.layout.swap_main().when(layout=["monadtall", "monadwide", "monadthreecol"]),
        desc="Promote window to master",
    ),
    Key([MOD], "u", lazy.next_urgent(), desc="Focus urgent window"),
    Key([MOD], "f", lazy.window.toggle_fullscreen(), desc="Toggle fullscreen"),

    # --- layout --------------------------------------------------------
    Key([MOD], "space", lazy.next_layout(), desc="Next layout"),
    Key([MOD], "h", lazy.layout.shrink_main(), desc="Shrink master area"),
    Key([MOD], "l", lazy.layout.grow_main(), desc="Grow master area"),
    Key([MOD], "n", lazy.layout.normalize(), desc="Reset window sizes"),
    Key([MOD], "b", lazy.hide_show_bar("top"), desc="Toggle the bar"),

    # --- screens (a z e are the physical q w e keys on azerty) ---------
    Key([MOD], "a", focus_screen_by_x(0), desc="Focus left screen"),
    Key([MOD], "z", focus_screen_by_x(1), desc="Focus right screen"),
    Key([MOD], "e", focus_screen_by_x(2), desc="Focus third screen"),
    Key([MOD, "shift"], "a", window_to_screen_by_x(0), desc="Send window to left screen"),
    Key([MOD, "shift"], "z", window_to_screen_by_x(1), desc="Send window to right screen"),
    Key([MOD, "shift"], "e", window_to_screen_by_x(2), desc="Send window to third screen"),

    # --- walk the workspace grid ---------------------------------------
    Key([MOD], "Left", plane_focus(0, -1), desc="Workspace to the left"),
    Key([MOD], "Right", plane_focus(0, 1), desc="Workspace to the right"),
    Key([MOD], "Up", plane_focus(-1, 0), desc="Workspace above"),
    Key([MOD], "Down", plane_focus(1, 0), desc="Workspace below"),
    Key([MOD, "shift"], "Left", plane_carry(0, -1), desc="Carry window left"),
    Key([MOD, "shift"], "Right", plane_carry(0, 1), desc="Carry window right"),
    Key([MOD, "shift"], "Up", plane_carry(-1, 0), desc="Carry window up"),
    Key([MOD, "shift"], "Down", plane_carry(1, 0), desc="Carry window down"),

    # --- launchers ------------------------------------------------------
    Key([MOD, "shift"], "Return", lazy.spawn(TERMINAL), desc="Terminal"),
    Key([MOD], "F12", lazy.spawn(TERMINAL), desc="Terminal"),
    Key([MOD], "F11", lazy.spawn(EDITOR), desc="Emacs"),
    Key([MOD], "F2", lazy.spawn(BROWSER), desc="Browser"),
    Key([MOD], "F1", lazy.spawn(FILE_MANAGER), desc="File manager"),
    Key([MOD], "F4", lazy.spawn(LAUNCHER), desc="Application launcher"),
    Key([MOD], "p", lazy.spawn(LAUNCHER), desc="Application launcher"),
    Key([MOD, "shift"], "l", lazy.spawn(LOCKER), desc="Lock screen"),
    Key([MOD], "v", lazy.spawn(["copyq", "toggle"]), desc="Toggle clipboard manager"),

    # --- session --------------------------------------------------------
    Key([MOD], "q", lazy.reload_config(), desc="Reload config"),
    Key([MOD, "control"], "q", lazy.restart(), desc="Restart qtile"),
    Key([MOD, "shift"], "q", lazy.shutdown(), desc="Quit qtile"),

    # --- media / brightness --------------------------------------------
    # wpctl (wireplumber) is the PipeWire-native equivalent of the old
    # `amixer -D pulse` calls; brightnessctl replaces lux.
    Key([], "XF86AudioMute", lazy.spawn("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle")),
    Key([], "XF86AudioLowerVolume", lazy.spawn("wpctl set-volume @DEFAULT_AUDIO_SINK@ 10%-")),
    Key([], "XF86AudioRaiseVolume", lazy.spawn("wpctl set-volume @DEFAULT_AUDIO_SINK@ 10%+")),
    Key([], "XF86MonBrightnessUp", lazy.spawn("brightnessctl set +10%")),
    Key([], "XF86MonBrightnessDown", lazy.spawn("brightnessctl set 10%-")),

    # --- screenshots ----------------------------------------------------
    Key([MOD], "Print", lazy.spawn(SHOT_SCREEN), desc="Screenshot of the output, crop/save in swappy"),
    Key([MOD, "control"], "Print", lazy.spawn(SHOT_REGION), desc="Screenshot of a selected region, crop/save in swappy"),
]

# Workspaces: number pad and number row both jump straight to a workspace,
# shift sends the focused window there without following it.
for grid_row, numpad_row, numrow_row in zip(GROUP_GRID, NUMPAD_KEYS, NUMROW_KEYS):
    for name, numpad_key, numrow_key in zip(grid_row, numpad_row, numrow_row):
        for key in (numpad_key, numrow_key):
            keys += [
                Key([MOD], key, lazy.group[name].toscreen(toggle=False), desc=f"Go to {name}"),
                Key([MOD, "shift"], key, lazy.window.togroup(name), desc=f"Send window to {name}"),
            ]

# --------------------------------------------------------------------------
# Layouts
# --------------------------------------------------------------------------

layout_defaults = dict(
    border_focus=FOCUSED_BORDER,
    border_normal=NORMAL_BORDER,
    border_width=1,
    margin=0,
)

layouts = [
    layout.MonadTall(**layout_defaults),       # ~ ResizableTall
    layout.MonadWide(**layout_defaults),       # ~ Mirror ResizableTall
    layout.Max(border_width=0),                # ~ noBorders Full
    layout.Matrix(**layout_defaults),          # ~ Grid
    layout.MonadThreeCol(**layout_defaults),   # ~ ThreeColMid, used by 9:Pix
]

floating_layout = layout.Floating(
    border_focus=FOCUSED_BORDER,
    border_normal=NORMAL_BORDER,
    border_width=1,
    float_rules=[
        *layout.Floating.default_float_rules,
        Match(wm_class="rdesktop"),
        Match(wm_class="Gnome-calculator"),
        Match(wm_class="copyq"),
        Match(wm_class="blueman-manager"),
        Match(wm_class="Nm-connection-editor"),
        Match(wm_class="pavucontrol"),
    ],
)

# --------------------------------------------------------------------------
# Bar
# --------------------------------------------------------------------------

widget_defaults = dict(font=FONT, fontsize=FONTSIZE, padding=3, foreground=BAR_FG)
extension_defaults = widget_defaults.copy()


# The tray.  widget.Systray declares supported_backends = {"x11"} and raises
# a ConfigError under Wayland, so it is deliberately not used at all here:
# StatusNotifier speaks the SNI/DBus protocol that current tray apps use and
# works on both backends.  Keeping it unconditional means a mis-detected
# backend cannot break the bar.  (It needs the dbus-fast package.)
def tray_widget():
    return widget.StatusNotifier(icon_size=18, padding=4)


def status_bar(with_tray):
    widgets = [
        widget.GroupBox(
            font=FONT,
            fontsize=FONTSIZE,
            margin_y=2,
            margin_x=0,
            padding_x=4,
            padding_y=4,
            borderwidth=2,
            active="#cccccc",          # workspace holding windows
            inactive="#555555",        # empty workspace
            this_current_screen_border=CURRENT_WS,
            this_screen_border=CURRENT_WS,
            other_current_screen_border=VISIBLE_WS,
            other_screen_border=VISIBLE_WS,
            urgent_border=URGENT_WS,
            urgent_text=URGENT_WS,
            highlight_method="line",
            highlight_color=[BAR_BG, BAR_BG],
            disable_drag=True,
        ),
        widget.CurrentLayout(foreground=VISIBLE_WS),
        widget.WindowName(foreground=TITLE_FG, max_chars=80),
        widget.Chord(foreground=URGENT_WS),
        widget.Battery(
            format="{char} {percent:2.0%}",
            charge_char="AC",
            discharge_char="Bat",
            full_char="AC",
            low_foreground=URGENT_WS,
            low_percentage=0.15,
        ),
        widget.Sep(foreground="#444444"),
        widget.CPU(format="Cpu: {load_percent}%"),
        widget.Sep(foreground="#444444"),
        widget.Memory(format="Mem: {MemPercent}%"),
        widget.Sep(foreground="#444444"),
        widget.PulseVolume(fmt="Vol: {}"),
    ]
    if with_tray:
        widgets += [widget.Spacer(length=8), tray_widget()]
    widgets += [
        widget.Spacer(length=8),
        widget.Clock(format="%a %b %_d %R", foreground=CURRENT_WS),
        widget.Spacer(length=8),
    ]
    return bar.Bar(widgets, 26, background=BAR_BG)


# One Screen per monitor, left to right.  Extra entries are ignored when
# fewer monitors are connected, so this is safe on the laptop alone.
# `wallpaper` replaces the nitrogen call from the old startup script.
WALLPAPER = os.path.expanduser("~/Pictures/wallpaper.png")
wallpaper_args = (
    dict(wallpaper=WALLPAPER, wallpaper_mode="fill") if os.path.exists(WALLPAPER) else {}
)

screens = [
    Screen(top=status_bar(with_tray=True), **wallpaper_args),
    Screen(top=status_bar(with_tray=False), **wallpaper_args),
    Screen(top=status_bar(with_tray=False), **wallpaper_args),
]

# --------------------------------------------------------------------------
# Input devices (Wayland)
# --------------------------------------------------------------------------
# Under Wayland there is no setxkbmap; the layout is set here instead, and
# qtile applies it to every keyboard as it appears.  This also replaces the
# old `synclient HorizTwoFingerScroll=1` call.
try:
    from libqtile.backend.wayland import InputConfig

    wl_input_rules = {
        # numpad:mac makes the number pad enter digits permanently, which is
        # what numlockx used to do on X11 -- except it can't be toggled off by
        # accident, and it applies from the very first keystroke of the
        # session.  qtile has no numlock setting of its own on Wayland
        # (qtile#4225), but this is an ordinary xkb option, so xkbcommon
        # applies it here exactly as it would under X11.  (Tried plain
        # numpad:pc to get an honest NumLock LED instead -- didn't actually
        # produce digits on this external keyboard, so back to numpad:mac.)
        "type:keyboard": InputConfig(
            kb_layout="fr",
            kb_options="numpad:mac",
            kb_repeat_rate=25,
            kb_repeat_delay=600,
        ),
        "type:touchpad": InputConfig(
            tap=True,
            natural_scroll=False,
            scroll_method="two_finger",
            dwt=True,
        ),
    }
except ImportError:
    # qtile built without the Wayland backend (X11-only install)
    wl_input_rules = None

wl_xcursor_theme = None  # e.g. "Yaru"; None keeps the compositor default
wl_xcursor_size = 24

# --------------------------------------------------------------------------
# Mouse
# --------------------------------------------------------------------------

mouse = [
    Drag([MOD], "Button1", lazy.window.set_position_floating(), start=lazy.window.get_position()),
    Drag([MOD], "Button3", lazy.window.set_size_floating(), start=lazy.window.get_size()),
    Click([MOD], "Button2", lazy.window.bring_to_front()),
]

# --------------------------------------------------------------------------
# Misc behaviour
# --------------------------------------------------------------------------

dgroups_key_binder = None
dgroups_app_rules = []
follow_mouse_focus = True
bring_front_click = False
cursor_warp = False
auto_fullscreen = True
focus_on_window_activation = "urgent"
reconfigure_screens = True
auto_minimize = False

# Java Swing apps misbehave unless the WM claims to be a known-good one;
# same trick as XMonad's setWMName "LG3D".  X11/XWayland only.
wmname = "LG3D"


@hook.subscribe.startup_once
def autostart():
    subprocess.Popen([os.path.join(QTILE_DIR, "autostart.sh")])
    # Start where XMonad used to: terminal workspace on the left screen,
    # dev workspace on the right one.  Sorted by x, not by screen index --
    # see _screen_by_x for why the index alone isn't reliable.
    screens = sorted(qtile.screens, key=lambda s: s.x)
    if len(screens) > 1:
        qtile.groups_map["5:Dev"].toscreen(screens[1].index, toggle=False)
    qtile.groups_map["1:Term"].toscreen(screens[0].index, toggle=False)
