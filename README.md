# Hyprpanel Settings

A GTK4 settings app for [Hyprland](https://hypr.land) that follows [Serpantinum](https://github.com/ilyamiro/serpantinum) theme presets. Edit keybinds, gaps, borders, blur, lockscreen, input, autostart, and monitors without writing Lua by hand.

Hyprland 0.55+ uses `~/.config/hypr/hyprland.lua`. This panel writes that file, plus `hyprlock.conf` and `hypridle.conf`, and keeps a readable `.conf` mirror.

The package name is **`hyprpanel-settings`** because [`hyprpanel`](https://aur.archlinux.org/packages/hyprpanel) on the AUR is already a different bar/shell.

## Requirements

- [Hyprland](https://hypr.land) 0.55 or newer (Lua config)
- [Serpantinum](https://github.com/ilyamiro/serpantinum)
- Python 3, GTK 4, `python-gobject`, `python-cairo`

Optional, used by the default profile:

| Package | Used for |
| --- | --- |
| `nautilus` | file manager |
| `kitty` | terminal and task-manager host |
| `htop` | task manager |
| `hyprlock` | lockscreen fallback |
| `wofi` | optional alternate launcher |

## Install

### From Git (recommended)

```bash
git clone https://github.com/pedr0fsc/hyprpanel-settings.git
cd hyprpanel-settings
make install-local
```

That installs to `~/.local`:

- `~/.local/bin/hyprpanel-settings`
- `~/.local/bin/hypr-serpantinum-launcher`
- `~/.local/bin/hypr-show-desktop`
- `~/.local/share/hyprpanel-settings/`
- desktop entry and icon

Make sure `~/.local/bin` is on your `PATH`. Then log out of Hyprland or run:

```bash
hash -r
hyprpanel-settings
```

System-wide install:

```bash
sudo make install PREFIX=/usr
```

### Arch Linux package from this repo

```bash
git clone https://github.com/pedr0fsc/hyprpanel-settings.git
cd hyprpanel-settings
makepkg -si -p PKGBUILD.local
```

### AUR

An AUR package named `hyprpanel-settings` is planned. Arch User Repository registration is temporarily closed for maintenance, so it is not listed yet.

```bash
yay -S hyprpanel-settings
# or: paru -S hyprpanel-settings
```

## Keybinds widget

Hyprpanel writes `~/.config/hypr/hyprpanel/keybinds.json` whenever the bindings list changes. A Serpantinum desktop widget reads that file and updates on its own.

After `make install-local`, the **Keybinds** type appears in Serpantinum’s widget editor. **Super + D** sends windows to a special workspace so the desktop widgets are visible; press it again to restore each window to its previous workspace.

## Run

```bash
hyprpanel-settings
```

Default shortcut: **Super + ,**

Click **Apply & Reload** to write `~/.config/hypr/hyprland.lua` and reload Hyprland. Previous configs are copied under `~/.config/hypr/backups/`.

## Default profile

This is the default binding profile shipped by the program (the same layout used on this machine).

### Apps

| Shortcut | Action |
| --- | --- |
| Super + Enter | Open terminal (`kitty`) |
| Super + Space | Serpantinum launcher |
| Super + E | File manager (`nautilus` if installed) |
| Super + , | Hyprpanel settings |
| Super + M | Exit Hyprland |

### Windows

| Shortcut | Action |
| --- | --- |
| Super + Q | Close window |
| Super + F | Fullscreen |
| Super + V | Toggle floating |
| Super + J | Toggle split |
| Super + Ctrl + arrows | Resize window |
| Super + Ctrl + I / J / K / L | Resize window (vim-style) |
| Super + LMB | Move window |
| Super + RMB | Resize window |

### Focus and workspaces

| Shortcut | Action |
| --- | --- |
| Super + arrows | Move focus |
| Super + 1–0 | Switch workspace |
| Super + Shift + 1–0 | Move window to workspace |

### System

| Shortcut | Action |
| --- | --- |
| Super + L | Lock (Serpantinum) |
| Super + Shift + L | Lock |
| Super + D | Show desktop (toggle; restore windows to their workspaces) |
| Ctrl + Shift + Esc | Task manager (`htop` in kitty) |

### Media and hardware keys

| Shortcut | Action |
| --- | --- |
| Volume up / down / mute | `wpctl` |
| Mic mute | `wpctl` |
| Brightness up / down | `brightnessctl` |
| Play / pause / next / previous | `playerctl` |

## Uninstall

```bash
make uninstall PREFIX="$HOME/.local"
rm -f ~/.local/bin/hyprpanel
```

Pacman package:

```bash
sudo pacman -R hyprpanel-settings
```

## License

MIT
