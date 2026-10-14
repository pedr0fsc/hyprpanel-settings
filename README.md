# Hyprpanel Settings

A GTK4 settings app for Hyprland that follows [Serpantinum](https://github.com) theme presets. Edit keybinds, gaps, borders, blur, lockscreen, input, autostart, and monitors without writing Lua by hand.

Hyprland 0.55+ uses `~/.config/hypr/hyprland.lua`. This panel writes that file, plus `hyprlock.conf` and `hypridle.conf`, and keeps a readable `.conf` mirror.

The AUR name is **`hyprpanel-settings`** because [`hyprpanel`](https://aur.archlinux.org/packages/hyprpanel) is already a different bar/shell.

## Run

```bash
hyprpanel-settings
```

Default shortcut after you apply config: **Super + ,**

## Install from this tree

```bash
make install-local          # ~/.local
sudo make install PREFIX=/usr
```

## Arch / AUR

Package names:

- `hyprpanel-settings` — tagged release
- `hyprpanel-settings-git` — latest git (`packaging/aur/PKGBUILD`)

Build the local tree without GitHub:

```bash
makepkg -si -p PKGBUILD.local
```

### Publish on GitHub

```bash
cd ~/hyprpanel-settings
git remote add origin git@github.com:pedr0fsc/hyprpanel-settings.git
git push -u origin main
git tag v0.1.0
git push origin v0.1.0
```

Update `url=` in `PKGBUILD` if your GitHub username is not `pedr0fsc`.

### Publish on the AUR

You need an [AUR account](https://aur.archlinux.org/register) and an SSH key uploaded there. The first clone of a new package name creates the empty AUR repo if you are logged in.

```bash
ssh-keygen -t ed25519 -f ~/.ssh/aur -C "aur"
# add ~/.ssh/aur.pub at https://aur.archlinux.org/account/

# tagged release package
cd ~/hyprpanel-settings
makepkg --printsrcinfo > .SRCINFO
git clone ssh://aur@aur.archlinux.org/hyprpanel-settings.git ~/src/aur/hyprpanel-settings
cp PKGBUILD .SRCINFO ~/src/aur/hyprpanel-settings/
cd ~/src/aur/hyprpanel-settings
git add PKGBUILD .SRCINFO
git commit -m "Initial import: hyprpanel-settings 0.1.0"
git push

# git snapshot package
git clone ssh://aur@aur.archlinux.org/hyprpanel-settings-git.git ~/src/aur/hyprpanel-settings-git
cp ~/hyprpanel-settings/packaging/aur/PKGBUILD ~/hyprpanel-settings/packaging/aur/.SRCINFO \
  ~/src/aur/hyprpanel-settings-git/
cd ~/src/aur/hyprpanel-settings-git
git add PKGBUILD .SRCINFO
git commit -m "Initial import: hyprpanel-settings-git"
git push
```

Or run `packaging/publish-aur.sh 0.1.0` after AUR SSH works. The GitHub tag `v0.1.0` must exist before the release PKGBUILD can download its tarball. Until then, install from this tree with `makepkg -si -p PKGBUILD.local`.

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
