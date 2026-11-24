#!/usr/bin/env bash
# Helper for the AUR upload after GitHub exists and AUR SSH is configured.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AUR_DIR="${AUR_DIR:-$HOME/src/aur/hyprpanel-settings}"

if [[ ! -d "$AUR_DIR/.git" ]]; then
  mkdir -p "$(dirname "$AUR_DIR")"
  git clone ssh://aur@aur.archlinux.org/hyprpanel-settings.git "$AUR_DIR"
fi

cp "$ROOT/PKGBUILD" "$AUR_DIR/PKGBUILD"
(
  cd "$ROOT"
  makepkg --printsrcinfo > "$AUR_DIR/.SRCINFO"
)

cd "$AUR_DIR"
git add PKGBUILD .SRCINFO
git status
echo "Review the diff, then:"
echo "  git commit -m 'Update hyprpanel-settings $1'"
echo "  git push"
