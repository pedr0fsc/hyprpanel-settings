PREFIX ?= /usr
DESTDIR ?=
BINDIR := $(DESTDIR)$(PREFIX)/bin
DATADIR := $(DESTDIR)$(PREFIX)/share/hyprpanel-settings
APPDIR := $(DESTDIR)$(PREFIX)/share/applications
ICONDIR := $(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps
DOCDIR := $(DESTDIR)$(PREFIX)/share/doc/hyprpanel-settings
LICENSEDIR := $(DESTDIR)$(PREFIX)/share/licenses/hyprpanel-settings

.PHONY: install uninstall install-local dist srcinfo

install:
	install -Dm755 data/hyprpanel-settings "$(BINDIR)/hyprpanel-settings"
	install -Dm755 data/hypr-launcher "$(BINDIR)/hypr-launcher"
	install -Dm755 data/hypr-show-desktop "$(BINDIR)/hypr-show-desktop"
	install -Dm755 data/hypr-serpantinum-launcher "$(BINDIR)/hypr-serpantinum-launcher"
	install -Dm644 hyprpanel.py app.py configio.py theme.py widgets.py -t "$(DATADIR)"
	install -Dm644 data/hyprpanel-settings.desktop "$(APPDIR)/hyprpanel-settings.desktop"
	install -Dm644 data/hyprpanel-settings.svg "$(ICONDIR)/hyprpanel-settings.svg"
	install -Dm644 README.md "$(DOCDIR)/README.md"
	install -Dm644 LICENSE "$(LICENSEDIR)/LICENSE"
	install -Dm644 data/serpantinum/KeybindsFace.qml "$(DATADIR)/serpantinum/KeybindsFace.qml"
	install -Dm755 data/serpantinum/install-widget.sh "$(DATADIR)/serpantinum/install-widget.sh"

uninstall:
	rm -f "$(BINDIR)/hyprpanel-settings" "$(BINDIR)/hypr-launcher" "$(BINDIR)/hypr-show-desktop" "$(BINDIR)/hypr-serpantinum-launcher"
	rm -rf "$(DATADIR)"
	rm -f "$(APPDIR)/hyprpanel-settings.desktop"
	rm -f "$(ICONDIR)/hyprpanel-settings.svg"
	rm -rf "$(DOCDIR)" "$(LICENSEDIR)"

install-local:
	$(MAKE) install PREFIX=$(HOME)/.local
	install -Dm755 data/hyprpanel-settings "$(HOME)/.local/bin/hyprpanel"
	update-desktop-database "$(HOME)/.local/share/applications" 2>/dev/null || true
	bash data/serpantinum/install-widget.sh

dist:
	mkdir -p dist
	git archive --format=tar.gz --prefix=hyprpanel-settings-0.1.0/ -o dist/hyprpanel-settings-0.1.0.tar.gz HEAD

srcinfo:
	makepkg --printsrcinfo > .SRCINFO
	cd packaging/aur && makepkg --printsrcinfo > .SRCINFO
