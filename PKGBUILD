# Maintainer: Pedro da Fonseca Schwertner <pedrodafonsecaschwertner at gmail dot com>
pkgname=hyprpanel-settings
pkgver=0.1.0
pkgrel=1
pkgdesc="Serpantinum-styled GUI for Hyprland keybinds, appearance, monitors, and hyprlock"
arch=('any')
url="https://github.com/pedr0fsc/hyprpanel-settings"
license=('MIT')
depends=(
  'python'
  'python-gobject'
  'python-cairo'
  'gtk4'
  'hyprland'
)
optdepends=(
  'nautilus: default file manager binding'
  'kitty: default terminal and task-manager host'
  'htop: task manager TUI'
  'hyprlock: lockscreen fallback when Serpantinum lock is unavailable'
  'wofi: optional alternate application launcher'
)
conflicts=('hyprpanel-settings-git')
source=("$pkgname-$pkgver.tar.gz")
sha256sums=('3e423eb83cdbd26883c74c827478e2737ed2075bfbae0b9987ace34dd7b127fc')

package() {
  cd "$srcdir/$pkgname-$pkgver"
  make DESTDIR="$pkgdir" PREFIX=/usr install
}
