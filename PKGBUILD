# Maintainer: Pedro da Fonseca Schwertner <pedrodafonsecaschwertner@gmail.com>
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
  'wofi: default application launcher binding'
  'nautilus: default file manager binding'
  'kitty: default terminal and task-manager host'
  'htop: task manager TUI'
  'hyprlock: lockscreen fallback when Serpantinum lock is unavailable'
)
conflicts=('hyprpanel-settings-git')
# Replace SKIP with the sha256 of the GitHub v$pkgver tarball after the tag is pushed.
source=("$pkgname-$pkgver.tar.gz::$url/archive/refs/tags/v$pkgver.tar.gz")
sha256sums=('SKIP')

package() {
  cd "$srcdir/$pkgname-$pkgver"
  make DESTDIR="$pkgdir" PREFIX=/usr install
}
