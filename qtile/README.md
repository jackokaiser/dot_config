# Qtile config

A port of my XMonad setup (`~/.xmonad`), targeting Wayland on Ubuntu 26.04.
Same mental model: 12 workspaces in a grid that mirrors the number pad,
reached by the matching number-pad key or by walking the grid with
`super`+arrows.

```
7:Paper   8:Dbg    9:Pix
4:Docs    5:Dev    6:Web
1:Term    2:Serv   3:Client
0:Chat    Extr1    Extr2
```

The config also runs unchanged under X11, so an X11 fallback session still
behaves; only the launcher and locker commands differ.

## Install

**Don't use the packaged qtile.** Ubuntu 26.04 (Resolute Raccoon) ships
`qtile 0.34.0-1`, and 0.34.0 is the release where the Wayland backend was
rewritten from scratch in C — the rewrite landed without the idle protocols,
so **`swayidle` does nothing on 0.34.0 and you get no auto-lock at all**.
`idle_inhibit` came back in 0.34.1 and `idle_notify` in 0.35.0.

Get 0.36.0 instead. It builds against wlroots **0.19**, the same version
0.34.x needs, so it drops straight onto 26.04's system libraries. (0.37.0
wants wlroots 0.20, which 26.04 almost certainly doesn't carry — check
`apt list 'libwlroots*'` before reaching for it.)

```sh
sudo apt install python3-venv python3-dev libffi-dev libxcb1-dev \
                 libcairo2-dev libpango1.0-dev pkg-config \
                 libwlroots-0.19-dev wayland-protocols libwayland-bin libinput-dev \
                 swaylock swayidle grim slurp wl-clipboard gammastep \
                 brightnessctl wireplumber wofi dex \
                 terminator blueman copyq

python3 -m venv ~/.local/share/qtile-venv
~/.local/share/qtile-venv/bin/pip install --no-binary qtile \
    --config-settings=backend=wayland 'qtile==0.36.0' \
    psutil dbus-fast pulsectl pulsectl-asyncio pyxdg
sudo ln -sf ~/.local/share/qtile-venv/bin/qtile /usr/local/bin/qtile
```

**`--no-binary qtile` and `--config-settings=backend=wayland` are required,
not cosmetic.** PyPI carries a prebuilt manylinux wheel for `qtile==0.36.0`
whose `_ffi.so` (the wayland C backend) is compiled for CPython 3.13. Ubuntu
26.04's `python3` is 3.14, so a plain `pip install qtile==0.36.0` silently
installs that ABI-incompatible wheel: the `.so` is present on disk but Python
refuses to import it, and `qtile start -b wayland` fails with no windows and
`Wayland backend not built` in the log. `--no-binary qtile` forces a source
build against the system's `libwlroots-0.19-dev` (matching the running
interpreter's ABI); `--config-settings=backend=wayland` makes qtile's build
backend (`builder.py`) raise instead of silently continuing if that build
fails for any reason, e.g. a missing header. Confirm you got a matching `.so`
before logging out:

```sh
find ~/.local/share/qtile-venv -iname "_ffi*.so"
# should show _ffi.cpython-314-*.so (or whatever `python3 --version` is),
# never cpython-313
```

Those Python extras are not optional in practice — each one silently
downgrades a widget to a "missing dependencies" placeholder rather than
erroring:

| Package | Needed by |
|---|---|
| `psutil` | CPU / memory / battery |
| `dbus-fast`, `pyxdg` | `StatusNotifier` (the tray) |
| `pulsectl`, `pulsectl-asyncio` | `PulseVolume` |

Alternatively, wait for the 26.10 packages (`qtile 0.36.0-1`) or pull that
source package into 26.04.

Register the session and log in:

```sh
sudo install -m 755 ~/.config/qtile/start-qtile /usr/local/bin/start-qtile
sudo cp ~/.config/qtile/qtile.desktop /usr/share/wayland-sessions/
```

(The session file points at `/usr/local/bin/start-qtile` rather than a path
under `$HOME`, so it carries no username.)

Check the config before logging out — this catches everything except runtime
behaviour:

```sh
~/.local/share/qtile-venv/bin/python -c \
  "from libqtile.confreader import Config; c=Config('$HOME/.config/qtile/config.py'); c.load(); c.validate(); print('ok')"
```

## Keyboard layout — the one real gotcha

Qtile resolves a binding to a physical key through that key's **unshifted
(level 0)** keysym. That is true on both backends: X11 reads
`code_to_syms[keycode][0]`, and the Wayland backend calls
`xkb_keymap_key_get_syms_by_level(..., level 0, ...)` in `qw/keyboard.c`.

On the fr (azerty) layout the unshifted top row is `& é " ' ( - è _ ç à ) =`,
so `Key([mod], "7")` grabs nothing you can reach. The number row is bound in
`config.py` by those keysym names (`NUMROW_KEYS`). If you ever switch to a us
layout, replace `NUMROW_KEYS` with the plain digits.

The number pad is unaffected: it is bound by the numlock-off names
(`KP_Home`, `KP_Up`, …), which is the unshifted level, so it works with
numlock on or off.

Under Wayland there is no `setxkbmap`; the layout is set by `wl_input_rules`
in `config.py` and qtile applies it to each keyboard as it appears.

## Keys

`super` is mod throughout.

### Workspaces
| Key | Action |
|---|---|
| `super` + numpad key | Go to that workspace |
| `super` + number row (azerty position) | Same, from the main keyboard |
| `super` + `shift` + either | Send window there, stay put |
| `super` + arrows | Walk the workspace grid (no wrap, like XMonad's `Plane … Finite`) |
| `super` + `shift` + arrows | Carry the window along and follow it |

### Screens (`a z e` = physical `q w e`)
| Key | Action |
|---|---|
| `super` + `a` / `z` / `e` | Focus screen 0 / 1 / 2 |
| `super` + `shift` + `a` / `z` / `e` | Send window to that screen |

Screen 0 is the leftmost monitor. With two monitors, `super`+`e` is a
harmless no-op (`focus_screen` bounds-checks the index).

### Windows & layout
| Key | Action |
|---|---|
| `super` + `k` | Close window |
| `super` + `t` | Sink a floating window back into tiling |
| `super` + `j` / `o` | Focus next window |
| `super` + `shift` + `j` | Focus previous window |
| `super` + `Return` | Promote window to master |
| `super` + `space` | Next layout |
| `super` + `h` / `l` | Shrink / grow the master area |
| `super` + `n` | Reset window sizes |
| `super` + `f` | Toggle fullscreen |
| `super` + `u` | Focus urgent window |
| `super` + `b` | Toggle the bar |

Layouts, in cycle order: `MonadTall` (≈ ResizableTall), `MonadWide` (≈ Mirror
ResizableTall), `Max` (≈ Full), `Matrix` (≈ Grid), `MonadThreeCol` (≈
ThreeColMid). `0:Chat` starts on `Max` and `9:Pix` on `MonadThreeCol`, the
equivalent of XMonad's `onWorkspace`.

### Launchers & session
| Key | Action |
|---|---|
| `super` + `F1` / `F2` / `F4` | Nautilus / Brave / launcher |
| `super` + `F11` / `F12` | Emacs / terminal |
| `super` + `shift` + `Return` | Terminal |
| `super` + `p` | Launcher |
| `super` + `shift` + `l` | Lock (swaylock) |
| `super` + `q` | Reload config (no restart, keeps windows) |
| `super` + `ctrl` + `q` | Restart qtile |
| `super` + `shift` + `q` | Quit |
| `super` + `Print` | Screenshot of the output (also copied to clipboard) |
| `super` + `ctrl` + `Print` | Screenshot of a selected region (ditto) |

## What changed coming from XMonad

**Replaced because Wayland has no equivalent:**

| Was | Now |
|---|---|
| `setxkbmap fr`, `synclient` | `wl_input_rules` in `config.py` |
| `xcompmgr` | built-in compositing |
| `nitrogen` | `Screen(wallpaper=…, wallpaper_mode="fill")` |
| `stalonetray` | `widget.StatusNotifier` |
| `xmobar` | qtile's bar, same colours and template |
| `slock` + `xautolock` | `swaylock` + `swayidle` |
| `scrot` | `grim` + `slurp`, bound directly in `config.py` |
| `xrandr` in the session script | outputs' preferred modes, or `kanshi` |
| `numlockx` | `kb_options="numpad:mac"` |
| hand-listed tray applets | `dex -a` (XDG autostart) |
| `redshift` | `gammastep` |
| `lux` | `brightnessctl` |
| `amixer -D pulse` | `wpctl` (PipeWire-native) |
| `synapse` | `wofi` (Wayland) / `rofi` (X11) |

**Behavioural differences:**

- **`super`+`ctrl`+`Print` grabs a region, not the focused window.** Under
  Wayland no client may read another client's contents, so there is no
  `scrot -u`; `slurp` lets you drag a selection instead.
- **`super`+`q` no longer recompiles.** `reload_config` re-reads `config.py`
  in place, and a syntax error leaves the running config untouched instead of
  killing the session. Log: `~/.local/share/qtile/qtile.log`.
- **`super`+`z` is only "focus screen 1" now.** In `xmonad.hs` it was bound
  twice (`MirrorExpand`, then the screen binding, which won); `super`+`h`/`l`
  cover resizing.
- **Workspace switching uses `Group.toscreen`**, which swaps workspaces
  between screens when the target is already visible elsewhere — the same
  behaviour as XMonad's `greedyView`.
- **`xautolock-guard` is gone entirely.** qtile ≥ 0.35 implements the
  idle-inhibit protocol, so browsers and call apps hold the idle timer open
  themselves — the thing the old script faked by polling PulseAudio and
  `/dev/video*`. If some app turns out not to participate, `swayidle` can be
  stopped around it rather than reviving the poller.

## The number pad

`numlockx` is X11-only, and qtile still has no numlock setting on Wayland
([qtile#4225](https://github.com/qtile/qtile/issues/4225)). Instead the
config sets the plain xkb option `numpad:mac` in `wl_input_rules`, which
xkbcommon applies the same way under Wayland as under X11:

```
numpad:mac    Numeric keypad always enters digits (as in macOS)
```

This is better than what numlockx gave you — the pad types digits from the
very first keystroke of the session, and there is no NumLock state left to
get toggled off by accident.

It looks like it should break the workspace bindings, and doesn't. Comparing
the compiled keymaps (`setxkbmap -layout fr [-option numpad:mac] -print |
xkbcomp -xkb - out.xkb`), `numpad:mac` changes exactly one thing — the
`KEYPAD` key *type*:

```
-        modifiers= Shift+NumLock;        +        modifiers= none;
-        map[NumLock]= Level2;            +        map[none]= Level2;
```

The symbol table is untouched: `key <KP7> { [ KP_Home, KP_7 ] };` either way.
Applications get level 2 (the digit) because the type now always selects it,
while qtile asks the keymap for **level 0** explicitly and still gets
`KP_Home`. Same keypress, both answers. So the bindings below stay as they
are.

## Files

| File | Role |
|---|---|
| `config.py` | Everything: groups, keys, layouts, bar, input rules, window rules |
| `autostart.sh` | `dex -a` plus the few things it can't cover |
| `start-qtile` | Sets the session environment, then `exec qtile start -b wayland` |
| `qtile.desktop` | Session entry for `/usr/share/wayland-sessions/` |
