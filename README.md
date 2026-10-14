# Hyprpanel Settings

A GTK4 settings app for [Hyprland](https://hypr.land) that follows [Serpantinum](https://github.com/ilyamiro/serpantinum) theme presets. Edit keybinds, gaps, borders, blur, lockscreen, input, autostart, and monitors without writing Lua by hand.

Hyprland 0.55+ uses `~/.config/hypr/hyprland.lua`. This panel writes that file, plus `hyprlock.conf` and `hypridle.conf`, and keeps a readable `.conf` mirror.

The package name is **`hyprpanel-settings`** because [`hyprpanel`](https://aur.archlinux.org/packages/hyprpanel) on the AUR is already a different bar/shell.

## Requirements

- [Hyprland](https://hypr.land) 0.55 or newer (Lua config)
- Python 3, GTK 4, `python-gobject`, `python-cairo`

Optional, used by the default bindings:

| Package | Used for |
| --- | --- |
| `wofi` | application launcher |
| `nautilus` | file manager |
| `kitty` | terminal and task-manager host |
| `htop` | task manager |
| `hyprlock` | lockscreen fallback |

## Install

### From Git (recommended)

```bash
git clone https://github.com/pedr0fsc/hyprpanel-settings.git
cd hyprpanel-settings
make install-local
```

That installs to `~/.local`:

- `~/.local/bin/hyprpanel-settings`
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

Build and install a pacman package without publishing anything:

```bash
git clone https://github.com/pedr0fsc/hyprpanel-settings.git
cd hyprpanel-settings
makepkg -si -p PKGBUILD.local
```

Or, if you already cloned the tree:

```bash
cd hyprpanel-settings
makepkg -si -p PKGBUILD.local
```

### AUR

An AUR package named `hyprpanel-settings` is planned. Arch User Repository registration is temporarily closed for maintenance, so it is not listed yet.

Until then, use **From Git** or **Arch Linux package from this repo** above.

When the AUR listing exists:

```bash
yay -S hyprpanel-settings
# or: paru -S hyprpanel-settings
```

## Run

```bash
hyprpanel-settings
```

Default shortcut after you apply config from the app: **Super + ,**

Click **Apply & Reload** in the panel to write `~/.config/hypr/hyprland.lua` and reload Hyprland. Previous configs are copied under `~/.config/hypr/backups/`.

## Uninstall

User install:

```bash
make uninstall PREFIX="$HOME/.local"
rm -f ~/.local/bin/hyprpanel
```

Pacman package:

```bash
sudo pacman -R hyprpanel-settings
```

## Shortcuts written by the panel

| Shortcut | Action |
| --- | --- |
| Super + L | Lock |
| Super + E | File manager |
| Super + Space | Launcher (wofi) |
| Super + , | This settings app |
| Ctrl + Shift + Esc | Task manager |
| Super + Ctrl + arrows / IJKL | Resize window |

## License

MIT
