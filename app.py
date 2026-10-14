"""Hyprpanel — Serpantinum-styled Hyprland configuration panel."""

from __future__ import annotations

import copy
import os
import subprocess
from pathlib import Path
import sys
from typing import Any, Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gio, GLib, Gtk, Pango

import configio
import theme
import widgets as w

PAGES = [
    ("bindings", "󰌌", "Bindings"),
    ("appearance", "󰏘", "Appearance"),
    ("presets", "󰃉", "Presets"),
    ("lockscreen", "󰌾", "Lockscreen"),
    ("input", "󰌏", "Input"),
    ("autostart", "󰑓", "Autostart"),
    ("monitors", "󰍹", "Monitors"),
    ("misc", "󰒓", "Misc"),
]

CATEGORIES = [
    ("all", "All"),
    ("apps", "Apps"),
    ("windows", "Windows"),
    ("workspaces", "Workspaces"),
    ("focus", "Focus"),
    ("media", "Media"),
    ("system", "System"),
    ("mouse", "Mouse"),
]

KIND_OPTIONS = [
    ("exec", "Launch command"),
    ("close", "Close window"),
    ("float", "Toggle floating"),
    ("fullscreen", "Fullscreen"),
    ("focus", "Move focus"),
    ("move_dir", "Move window"),
    ("resize_delta", "Resize with keys (dx dy)"),
    ("workspace", "Switch workspace"),
    ("movetoworkspace", "Move window to workspace"),
    ("layout", "Layout message"),
    ("special", "Special workspace"),
    ("drag", "Drag window (mouse)"),
    ("resize", "Resize window (mouse)"),
    ("exit", "Exit Hyprland"),
    ("custom", "Custom Lua"),
]

QUICK_ACTIONS = [
    ("Custom / keep current", None),
    ("Open file manager", {"kind": "exec", "arg": configio.detect_file_manager(), "category": "apps", "description": "File manager"}),
    ("Open terminal", {"kind": "exec", "arg": configio.which_first("kitty", "alacritty", "foot"), "category": "apps", "description": "Open terminal"}),
    ("App launcher (wofi)", {"kind": "exec", "arg": "wofi --show drun", "category": "apps", "description": "App launcher"}),
    ("Serpantinum launcher", {"kind": "exec", "arg": str(configio.LAUNCHER_BIN), "category": "apps", "description": "Serpantinum launcher"}),
    ("Lock screen", {"kind": "exec", "arg": configio.detect_lock(), "category": "system", "description": "Lock screen"}),
    ("Task manager", {"kind": "exec", "arg": configio.detect_task_manager(), "category": "system", "description": "Task manager"}),
    ("Hyprpanel settings", {"kind": "exec", "arg": str(configio.PANEL_BIN), "category": "apps", "description": "Hyprpanel settings"}),
    ("Resize left", {"kind": "resize_delta", "arg": "-40 0", "category": "windows", "description": "Resize left", "repeating": True}),
    ("Resize right", {"kind": "resize_delta", "arg": "40 0", "category": "windows", "description": "Resize right", "repeating": True}),
    ("Resize up", {"kind": "resize_delta", "arg": "0 -40", "category": "windows", "description": "Resize up", "repeating": True}),
    ("Resize down", {"kind": "resize_delta", "arg": "0 40", "category": "windows", "description": "Resize down", "repeating": True}),
    ("Move window left", {"kind": "move_dir", "arg": "left", "category": "windows", "description": "Move window left"}),
    ("Move window right", {"kind": "move_dir", "arg": "right", "category": "windows", "description": "Move window right"}),
    ("Move window up", {"kind": "move_dir", "arg": "up", "category": "windows", "description": "Move window up"}),
    ("Move window down", {"kind": "move_dir", "arg": "down", "category": "windows", "description": "Move window down"}),
    ("Close window", {"kind": "close", "arg": "", "category": "windows", "description": "Close window"}),
    ("Toggle floating", {"kind": "float", "arg": "", "category": "windows", "description": "Toggle floating"}),
    ("Fullscreen", {"kind": "fullscreen", "arg": "", "category": "windows", "description": "Fullscreen"}),
]

GDK_SPECIAL = {
    Gdk.KEY_Return: "RETURN",
    Gdk.KEY_KP_Enter: "RETURN",
    Gdk.KEY_Escape: "ESCAPE",
    Gdk.KEY_space: "SPACE",
    Gdk.KEY_Tab: "TAB",
    Gdk.KEY_BackSpace: "BACKSPACE",
    Gdk.KEY_Delete: "DELETE",
    Gdk.KEY_comma: "comma",
    Gdk.KEY_period: "period",
    Gdk.KEY_Left: "left",
    Gdk.KEY_Right: "right",
    Gdk.KEY_Up: "up",
    Gdk.KEY_Down: "down",
    Gdk.KEY_Home: "Home",
    Gdk.KEY_End: "End",
    Gdk.KEY_Page_Up: "Prior",
    Gdk.KEY_Page_Down: "Next",
    Gdk.KEY_Print: "Print",
    Gdk.KEY_F1: "F1",
    Gdk.KEY_F2: "F2",
    Gdk.KEY_F3: "F3",
    Gdk.KEY_F4: "F4",
    Gdk.KEY_F5: "F5",
    Gdk.KEY_F6: "F6",
    Gdk.KEY_F7: "F7",
    Gdk.KEY_F8: "F8",
    Gdk.KEY_F9: "F9",
    Gdk.KEY_F10: "F10",
    Gdk.KEY_F11: "F11",
    Gdk.KEY_F12: "F12",
}


class HyprpanelWindow(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application) -> None:
        super().__init__(application=app, title="Hyprpanel")
        self.add_css_class("hyprpanel")
        self.set_default_size(1120, 740)
        self.set_size_request(820, 560)
        self.model = configio.load_model()
        self._saved = copy.deepcopy(self.model)
        self.dirty = False
        self.page = "bindings"
        self.category = "all"
        self.search = ""
        self.css_provider = Gtk.CssProvider()
        self._nav_buttons: dict[str, Gtk.Button] = {}
        self._page_boxes: dict[str, Gtk.Box] = {}
        self._bind_list: Gtk.Box | None = None
        self._preset_grid: Gtk.FlowBox | None = None
        self._lock_preview: Gtk.DrawingArea | None = None
        self._autostart_box: Gtk.Box | None = None
        self._search_entry: Gtk.Entry | None = None
        self.toast = w.Toast()
        self._apply_css()
        self._watch_theme()
        self.set_child(self._build())
        self.connect("close-request", self._on_close)

    def _apply_css(self) -> None:
        css = theme.build_css()
        self.css_provider.load_from_data(css.encode("utf-8"))
        display = Gdk.Display.get_default()
        Gtk.StyleContext.add_provider_for_display(
            display,
            self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _watch_theme(self) -> None:
        for path in (theme.SERP_COLORS, theme.SERP_SETTINGS):
            if not path.exists():
                continue
            gfile = Gio.File.new_for_path(str(path))
            monitor = gfile.monitor_file(Gio.FileMonitorFlags.NONE, None)
            monitor.connect("changed", lambda *_: GLib.idle_add(self._refresh_theme))
            setattr(self, f"_mon_{path.name}", monitor)

    def _refresh_theme(self) -> bool:
        self._apply_css()
        if self._lock_preview:
            self._lock_preview.queue_draw()
        return False

    def mark_dirty(self) -> None:
        self.dirty = True
        if hasattr(self, "apply_btn"):
            self.apply_btn.set_sensitive(True)
            self.revert_btn.set_sensitive(True)

    def _build(self) -> Gtk.Widget:
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        body.set_vexpand(True)
        body.append(self._build_sidebar())
        body.append(self._build_content())
        root.append(body)
        root.append(self._build_footer())
        overlay = Gtk.Overlay()
        overlay.set_child(root)
        overlay.add_overlay(self.toast)
        return overlay

    def _build_sidebar(self) -> Gtk.Widget:
        side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        side.add_css_class("hp-sidebar")
        side.set_size_request(248, -1)
        side.set_margin_start(14)
        side.set_margin_end(10)
        side.set_margin_top(16)
        side.set_margin_bottom(16)

        brand = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        row = Gtk.Box(spacing=10)
        row.append(w.icon_label("󰒓", 20, "hp-icon-lg"))
        title = w.text("Hyprpanel", "hp-title")
        row.append(title)
        brand.append(row)
        brand.append(w.text("Hyprland + Serpantinum", "hp-subtitle"))
        side.append(brand)

        search = Gtk.Entry()
        search.set_placeholder_text("Search settings…")
        search.add_css_class("hp-search")
        search.connect("changed", self._on_search)
        self._search_entry = search
        side.append(search)

        nav = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        nav.set_vexpand(True)
        for key, icon, label in PAGES:
            btn = Gtk.Button()
            inner = Gtk.Box(spacing=10)
            inner.append(w.icon_label(icon, 16))
            lab = Gtk.Label(label=label, xalign=0)
            lab.add_css_class("hp-nav-label")
            lab.set_hexpand(True)
            inner.append(lab)
            btn.set_child(inner)
            btn.add_css_class("hp-nav")
            if key == self.page:
                btn.add_css_class("active")
            btn.connect("clicked", lambda _b, k=key: self._goto(k))
            self._nav_buttons[key] = btn
            nav.append(btn)
        side.append(nav)

        hint = w.text("Open anytime with Super + ,", "dim")
        hint.set_wrap(True)
        side.append(hint)
        return side

    def _build_content(self) -> Gtk.Widget:
        self.stack = Gtk.Stack()
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_UP_DOWN)
        self.stack.set_transition_duration(180)
        self._page_builders = {
            "bindings": self._page_bindings,
            "appearance": self._page_appearance,
            "presets": self._page_presets,
            "lockscreen": self._page_lock,
            "input": self._page_input,
            "autostart": self._page_autostart,
            "monitors": self._page_monitors,
            "misc": self._page_misc,
        }
        for key in self._page_builders:
            self.stack.add_named(Gtk.Box(), key)
        self.stack.connect("notify::visible-child-name", lambda *_: self._ensure_page())
        self._ensure_page()
        return self.stack

    def _ensure_page(self) -> None:
        key = self.stack.get_visible_child_name() or self.page
        if key in self._page_boxes:
            return
        builder = self._page_builders.get(key)
        if not builder:
            return
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        inner.set_margin_start(18)
        inner.set_margin_end(22)
        inner.set_margin_top(18)
        inner.set_margin_bottom(24)
        inner.set_hexpand(True)
        builder(inner)
        self._page_boxes[key] = inner
        scroller.set_child(inner)
        old = self.stack.get_child_by_name(key)
        if old is not None:
            self.stack.remove(old)
        self.stack.add_named(scroller, key)
        self.stack.set_visible_child_name(key)

    def _build_footer(self) -> Gtk.Widget:
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        bar.add_css_class("hp-footer")
        bar.set_margin_start(16)
        bar.set_margin_end(16)
        bar.set_margin_top(10)
        bar.set_margin_bottom(10)
        self.status = w.text("Editing live Hyprland lua + hyprlock.conf", "dim")
        self.status.set_hexpand(True)
        self.status.set_xalign(0)
        bar.append(self.status)
        preview = w.button("Live preview", "hp-btn hp-btn-blue", "󰍽")
        preview.connect("clicked", lambda *_: self._live_preview())
        bar.append(preview)
        self.revert_btn = w.button("Revert", "hp-btn")
        self.revert_btn.set_sensitive(False)
        self.revert_btn.connect("clicked", lambda *_: self._revert())
        bar.append(self.revert_btn)
        self.apply_btn = w.button("Apply & reload", "hp-btn-accent", "󰄬")
        self.apply_btn.connect("clicked", lambda *_: self._apply())
        bar.append(self.apply_btn)
        return bar

    def _goto(self, key: str) -> None:
        self.page = key
        self.stack.set_visible_child_name(key)
        self._ensure_page()
        for name, btn in self._nav_buttons.items():
            if name == key:
                btn.add_css_class("active")
            else:
                btn.remove_css_class("active")

    def _on_search(self, entry: Gtk.Entry) -> None:
        self.search = entry.get_text().strip().lower()
        mapping = {
            "bind": "bindings",
            "key": "bindings",
            "shortcut": "bindings",
            "gap": "appearance",
            "border": "appearance",
            "blur": "appearance",
            "round": "appearance",
            "shadow": "appearance",
            "theme": "presets",
            "preset": "presets",
            "nord": "presets",
            "lock": "lockscreen",
            "hyprlock": "lockscreen",
            "password": "lockscreen",
            "keyboard": "input",
            "touchpad": "input",
            "mouse": "input",
            "start": "autostart",
            "exec": "autostart",
            "monitor": "monitors",
            "scale": "monitors",
            "anim": "misc",
            "cursor": "input",
        }
        if self.search:
            for needle, page in mapping.items():
                if needle in self.search:
                    self._goto(page)
                    break
        if self.page == "bindings":
            self._rebuild_binds()

    def _page_bindings(self, box: Gtk.Box) -> None:
        box.append(w.section_header(
            "Key bindings",
            "Windows-like: Super+L lock · Super+E files · Super+Space launcher · Ctrl+Shift+Esc task manager. "
            "Resize: Super+Ctrl+arrows or Super+Ctrl+I/J/K/L.",
        ))
        tools = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        chips = Gtk.Box(spacing=6)
        chips.set_hexpand(True)
        self._category_chips: dict[str, Gtk.ToggleButton] = {}
        group_leader: Gtk.ToggleButton | None = None
        for key, label in CATEGORIES:
            chip = Gtk.ToggleButton(label=label)
            chip.add_css_class("hp-chip")
            if group_leader is None:
                group_leader = chip
            else:
                chip.set_group(group_leader)
            chip.set_active(key == "all")
            chip.connect("toggled", self._on_category, key)
            self._category_chips[key] = chip
            chips.append(chip)
        row = Gtk.Box(spacing=8)
        row.append(chips)
        add = w.button("Add binding", "hp-btn-accent", "󰐕")
        add.set_valign(Gtk.Align.CENTER)
        add.connect("clicked", lambda *_: self._edit_bind(None))
        row.append(add)
        tools.append(row)
        box.append(tools)
        self._bind_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.append(self._bind_list)
        self._rebuild_binds()

    def _on_category(self, btn: Gtk.ToggleButton, key: str) -> None:
        if btn.get_active():
            self.category = key
            self._rebuild_binds()

    def _rebuild_binds(self) -> None:
        if not self._bind_list:
            return
        child = self._bind_list.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self._bind_list.remove(child)
            child = nxt
        query = self.search
        shown = 0
        for item in self.model.get("binds") or []:
            cat = item.get("category") or "apps"
            if self.category != "all" and cat != self.category:
                continue
            hay = " ".join(
                [
                    item.get("description") or "",
                    item.get("key") or "",
                    " ".join(item.get("mods") or []),
                    item.get("arg") or "",
                    cat,
                ]
            ).lower()
            if query and query not in hay:
                continue
            self._bind_list.append(self._bind_row(item))
            shown += 1
        if shown == 0:
            self._bind_list.append(w.text("No bindings match this filter.", "dim"))

    def _bind_row(self, item: dict[str, Any]) -> Gtk.Widget:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row.add_css_class("hp-bind-row")
        row.set_margin_start(2)
        row.set_margin_end(2)
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        left.set_hexpand(True)
        left.set_margin_start(4)
        left.set_margin_top(2)
        left.set_margin_bottom(2)
        title = Gtk.Label(label=item.get("description") or "Binding", xalign=0)
        title.set_ellipsize(Pango.EllipsizeMode.END)
        left.append(title)
        keys = Gtk.Box(spacing=5)
        pretty = configio.keys_pretty(item.get("mods") or [], item.get("key") or "")
        for part in pretty.split(" + "):
            keys.append(w.kbd_pill(part))
        left.append(keys)
        arg = item.get("arg") or ""
        meta = w.text(f"{item.get('kind')}" + (f" · {arg}" if arg else ""), "dim")
        meta.set_ellipsize(Pango.EllipsizeMode.END)
        left.append(meta)
        row.append(left)
        capture = w.icon_button("󰌏", "hp-btn")
        capture.set_tooltip_text("Recapture shortcut")
        capture.connect("clicked", lambda *_: self._capture_into(item))
        row.append(capture)
        edit = w.icon_button("󰏫", "hp-btn")
        edit.set_tooltip_text("Edit action")
        edit.connect("clicked", lambda *_: self._edit_bind(item))
        row.append(edit)
        delete = w.icon_button("󰆴")
        delete.set_tooltip_text("Remove binding")
        delete.connect("clicked", lambda *_: self._delete_bind(item))
        row.append(delete)
        return row

    def _delete_bind(self, item: dict[str, Any]) -> None:
        binds = self.model.get("binds") or []
        self.model["binds"] = [b for b in binds if b is not item]
        self.mark_dirty()
        self._rebuild_binds()

    def _capture_into(self, item: dict[str, Any]) -> None:
        dialog = CaptureDialog(self, item)
        dialog.present()

    def _edit_bind(self, item: dict[str, Any] | None) -> None:
        dialog = BindEditor(self, item)
        dialog.present()

    def _page_appearance(self, box: Gtk.Box) -> None:
        box.append(w.section_header("Look and feel", "These map to general {} and decoration {} in Hyprland. Live preview applies instantly; Apply writes the files."))
        a = self.model["appearance"]

        def setn(key: str) -> Callable[[float], None]:
            def inner(val: float) -> None:
                a[key] = int(round(val)) if key not in ("rounding_power", "active_opacity", "inactive_opacity", "blur_vibrancy") else float(val)
                self.mark_dirty()
                try:
                    configio.apply_live_appearance(self.model)
                except Exception:
                    pass
            return inner

        def setb(key: str) -> Callable[[bool], None]:
            def inner(val: bool) -> None:
                a[key] = val
                self.mark_dirty()
                try:
                    configio.apply_live_appearance(self.model)
                except Exception:
                    pass
            return inner

        box.append(w.labeled_scale("Inner gaps", "Space between tiled windows", a.get("gaps_in", 5), 0, 40, 1, setn("gaps_in"), icon="󰝤"))
        box.append(w.labeled_scale("Outer gaps", "Space between windows and screen edges", a.get("gaps_out", 20), 0, 80, 1, setn("gaps_out"), icon="󰍽"))
        box.append(w.labeled_scale("Border size", "Window border thickness in pixels", a.get("border_size", 2), 0, 12, 1, setn("border_size"), icon="󰇼"))
        box.append(w.labeled_scale("Rounding", "Corner radius. Matches Serpantinum when you sync presets.", a.get("rounding", 10), 0, 32, 1, setn("rounding"), icon="󰹟"))
        box.append(w.labeled_scale("Rounding power", "How sharp the rounded corners feel", float(a.get("rounding_power") or 2), 1, 10, 0.1, setn("rounding_power"), digits=1))
        box.append(w.labeled_dropdown("Layout", "Tiling algorithm", ["dwindle", "master", "scrolling"], a.get("layout") or "dwindle", lambda v: (a.__setitem__("layout", v), self.mark_dirty()), icon="󰕮"))
        box.append(w.labeled_switch("Blur", "Background blur behind windows", bool(a.get("blur_enabled", True)), setb("blur_enabled"), icon="󰈷"))
        box.append(w.labeled_scale("Blur size", "Blur kernel size", a.get("blur_size", 3), 1, 20, 1, setn("blur_size")))
        box.append(w.labeled_scale("Blur passes", "More passes look smoother and cost more GPU", a.get("blur_passes", 1), 1, 5, 1, setn("blur_passes")))
        box.append(w.labeled_switch("Shadows", "Drop shadows under windows", bool(a.get("shadow_enabled", True)), setb("shadow_enabled"), icon="󰐾"))
        box.append(w.labeled_scale("Shadow range", "How far shadows spread", a.get("shadow_range", 4), 0, 40, 1, setn("shadow_range")))
        box.append(w.labeled_scale("Active opacity", "Focused window opacity", float(a.get("active_opacity") or 1), 0.4, 1.0, 0.01, setn("active_opacity"), digits=2))
        box.append(w.labeled_scale("Inactive opacity", "Unfocused window opacity", float(a.get("inactive_opacity") or 1), 0.4, 1.0, 0.01, setn("inactive_opacity"), digits=2))
        box.append(w.labeled_switch("Animations", "Window and workspace motion", bool(a.get("animations_enabled", True)), setb("animations_enabled"), icon="󰁕"))
        box.append(self._border_colors_card())

    def _border_colors_card(self) -> Gtk.Widget:
        wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        wrap.add_css_class("hp-card")
        row, control = w.settings_row("Window borders", "Active gradient uses two Serpantinum-style colors.", "󰏘")
        wrap.append(row)
        colors = self.model["appearance"].get("active_border") or ["rgba(88d0edee)"]
        if isinstance(colors, str):
            colors = [colors]
            self.model["appearance"]["active_border"] = colors
        while len(colors) < 2:
            colors.append(colors[-1])
        pickers = Gtk.Box(spacing=10)
        pickers.set_margin_start(12)
        pickers.set_margin_end(12)
        pickers.set_margin_bottom(12)

        def add_picker(label: str, getter, setter):
            col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            col.append(w.text(label, "dim"))
            btn = Gtk.ColorDialogButton()
            dialog = Gtk.ColorDialog()
            btn.set_dialog(dialog)
            btn.set_rgba(w.parse_hypr_color(getter()))
            btn.connect("notify::rgba", lambda b, *_: (setter(w.rgba_to_hypr(b.get_rgba())), self.mark_dirty(), self._live_preview(silent=True)))
            col.append(btn)
            pickers.append(col)

        add_picker("Active A", lambda: colors[0], lambda v: colors.__setitem__(0, v))
        add_picker("Active B", lambda: colors[1], lambda v: colors.__setitem__(1, v))
        add_picker("Inactive", lambda: self.model["appearance"].get("inactive_border") or "rgba(303638aa)", lambda v: self.model["appearance"].__setitem__("inactive_border", v))
        wrap.append(pickers)
        return wrap

    def _page_presets(self, box: Gtk.Box) -> None:
        box.append(w.section_header("Serpantinum presets", "Apply a Serpantinum palette to Hyprland borders and the hyprlock theme. The panel itself already follows your live Serpantinum colors."))
        current = theme.load_theme_meta().get("activePreset") or "Matugen"
        box.append(w.text(f"Active Serpantinum preset: {current}", "dim"))
        live = w.button("Match current Serpantinum colors", "hp-btn-accent", "󰑐")
        live.connect("clicked", lambda *_: self._apply_current_theme())
        box.append(live)
        flow = Gtk.FlowBox()
        flow.set_valign(Gtk.Align.START)
        flow.set_max_children_per_line(3)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_homogeneous(True)
        flow.set_column_spacing(10)
        flow.set_row_spacing(10)
        self._preset_grid = flow
        for preset in theme.list_presets():
            flow.append(self._preset_card(preset, current))
        box.append(flow)

    def _preset_card(self, preset: dict[str, Any], current: str) -> Gtk.Widget:
        btn = Gtk.Button()
        btn.add_css_class("hp-preset")
        if preset["name"] == current:
            btn.add_css_class("active")
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        inner.set_margin_start(8)
        inner.set_margin_end(8)
        inner.set_margin_top(8)
        inner.set_margin_bottom(8)
        name = Gtk.Label(label=preset["name"], xalign=0)
        inner.append(name)
        colors = preset.get("colors") or {}
        keys = [k for k in ("base", "blue", "mauve", "green", "peach", "red", "text") if k in colors]
        bar = Gtk.DrawingArea()
        bar.set_content_width(220)
        bar.set_content_height(16)
        hexes = [colors[k] for k in keys]

        def draw(_area, cr, width, height, palette=hexes):
            n = max(1, len(palette))
            slot = width / n
            for i, hx in enumerate(palette):
                h = hx.lstrip("#")[:6]
                cr.set_source_rgb(int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255)
                cr.rectangle(i * slot, 0, slot + 0.5, height)
                cr.fill()

        bar.set_draw_func(draw)
        inner.append(bar)
        hint = w.text("Matugen follows wallpaper" if preset.get("isMatugen") else "Click to apply to Hyprland + lock", "dim")
        inner.append(hint)
        btn.set_child(inner)
        btn.connect("clicked", lambda *_: self._apply_named_preset(preset))
        return btn

    def _apply_current_theme(self) -> None:
        configio.apply_preset_colors(self.model, theme.load_colors())
        meta = theme.load_theme_meta()
        if self.model.get("sync_rounding_with_serpantinum"):
            self.model["appearance"]["rounding"] = int(meta.get("borderRadius") or 8)
            self.model["lock"]["rounding"] = int(meta.get("borderRadius") or 8)
            self.model["lock"]["font"] = meta.get("fontFamily") or "Adwaita Mono"
        self.mark_dirty()
        self._live_preview()
        if self._lock_preview:
            self._lock_preview.queue_draw()
        self.toast.show_message("Borders and lockscreen matched to Serpantinum")

    def _apply_named_preset(self, preset: dict[str, Any]) -> None:
        colors = preset.get("colors") or theme.load_colors()
        if preset.get("isMatugen"):
            colors = theme.load_colors()
        configio.apply_preset_colors(self.model, colors)
        self.mark_dirty()
        self._live_preview()
        if self._lock_preview:
            self._lock_preview.queue_draw()
        self.toast.show_message(f"Applied {preset['name']} to Hyprland + lockscreen")

    def _page_lock(self, box: Gtk.Box) -> None:
        box.append(w.section_header("Lockscreen", "Serpantinum has its own lock UI. Hyprlock is still used by hypridle and as a fallback. Both are themed here."))
        lock = self.model["lock"]
        preview = Gtk.DrawingArea()
        preview.add_css_class("hp-preview")
        preview.set_content_width(640)
        preview.set_content_height(320)
        preview.set_hexpand(True)
        preview.set_draw_func(self._draw_lock)
        self._lock_preview = preview
        box.append(preview)

        def set_engine(v: str) -> None:
            lock["engine"] = "serpantinum" if v.startswith("Serpantinum") else "hyprlock"
            lock["command"] = "serpantinum lock" if lock["engine"] == "serpantinum" else "hyprlock"
            self.model["idle"]["lock_cmd"] = lock["command"]
            for item in self.model.get("binds") or []:
                if item.get("description") == "Lock screen":
                    item["arg"] = lock["command"]
            self.mark_dirty()

        current_engine = "Serpantinum lock" if lock.get("engine") == "serpantinum" else "Hyprlock"
        box.append(w.labeled_dropdown("Lock engine", "Command used by Super+Shift+L and hypridle", ["Serpantinum lock", "Hyprlock"], current_engine, set_engine, icon="󰌾"))
        box.append(w.labeled_dropdown("Background", "Hyprlock backdrop", ["screenshot", "wallpaper", "color"], lock.get("background") or "screenshot", lambda v: (lock.__setitem__("background", v), self.mark_dirty(), preview.queue_draw()), icon="󰋩"))
        box.append(w.labeled_entry("Wallpaper path", "Used when background is wallpaper", lock.get("wallpaper") or "", lambda v: (lock.__setitem__("wallpaper", v), self.mark_dirty()), icon="󰉏"))
        box.append(w.labeled_entry("Font", "Clock and input field", lock.get("font") or "Adwaita Mono", lambda v: (lock.__setitem__("font", v), self.mark_dirty(), preview.queue_draw())))
        box.append(w.labeled_scale("Clock size", "Time widget on hyprlock", lock.get("clock_size", 90), 32, 140, 1, lambda v: (lock.__setitem__("clock_size", int(v)), self.mark_dirty(), preview.queue_draw())))
        box.append(w.labeled_scale("Blur passes", "How strongly the lock background blurs", lock.get("blur_passes", 3), 0, 6, 1, lambda v: (lock.__setitem__("blur_passes", int(v)), self.mark_dirty())))
        box.append(w.labeled_scale("Field rounding", "Password box corner radius", lock.get("rounding", 8), 0, 24, 1, lambda v: (lock.__setitem__("rounding", int(v)), self.mark_dirty(), preview.queue_draw())))
        box.append(w.labeled_switch("Show clock", "Large time in the center", bool(lock.get("show_clock", True)), lambda v: (lock.__setitem__("show_clock", v), self.mark_dirty(), preview.queue_draw())))
        box.append(w.labeled_switch("Show date", "Date under the clock", bool(lock.get("show_date", True)), lambda v: (lock.__setitem__("show_date", v), self.mark_dirty(), preview.queue_draw())))
        box.append(w.labeled_switch("Hide cursor", "Hide the pointer on hyprlock", bool(lock.get("hide_cursor")), lambda v: (lock.__setitem__("hide_cursor", v), self.mark_dirty())))
        box.append(w.labeled_entry("Placeholder", "Text inside the empty password field", lock.get("placeholder") or "", lambda v: (lock.__setitem__("placeholder", v), self.mark_dirty(), preview.queue_draw())))
        test = w.button("Test lockscreen", "hp-btn hp-btn-blue", "󰷛")
        test.connect("clicked", lambda *_: self._test_lock())
        box.append(test)

    def _draw_lock(self, area: Gtk.DrawingArea, cr, width: int, height: int) -> None:
        colors = theme.load_colors()
        lock = self.model["lock"]
        def rgb(hex_color: str, a: float = 1.0):
            h = hex_color.lstrip("#")[:6]
            cr.set_source_rgba(int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)
        rgb(colors.get("crust", "#0f1416"))
        cr.rectangle(0, 0, width, height)
        cr.fill()
        rgb(colors.get("base", "#0a0f11"), 0.55)
        cr.rectangle(0, 0, width, height)
        cr.fill()
        cr.select_font_face(lock.get("font") or "Adwaita Mono", 0, 1)
        if lock.get("show_clock", True):
            rgb(colors.get("text", "#dee3e6"))
            cr.set_font_size(min(64, max(28, width / 10)))
            time_s = GLib.DateTime.new_now_local().format("%H:%M")
            xbear, ybear, tw, th, _, _ = cr.text_extents(time_s)
            cr.move_to((width - tw) / 2, height * 0.38)
            cr.show_text(time_s)
        if lock.get("show_date", True):
            rgb(colors.get("subtext0", "#bfc8cc"))
            cr.set_font_size(14)
            date_s = GLib.DateTime.new_now_local().format("%A, %d %B")
            xbear, ybear, tw, th, _, _ = cr.text_extents(date_s)
            cr.move_to((width - tw) / 2, height * 0.38 + 28)
            cr.show_text(date_s)
        fw, fh = 240, 40
        fx, fy = (width - fw) / 2, height * 0.62
        mauve = colors.get("mauve", "#88d0ed")
        rgb(colors.get("surface0", "#1b2023"), 0.85)
        _rounded(cr, fx, fy, fw, fh, int(lock.get("rounding") or 8))
        cr.fill()
        rgb(mauve)
        cr.set_line_width(2)
        _rounded(cr, fx, fy, fw, fh, int(lock.get("rounding") or 8))
        cr.stroke()
        rgb(colors.get("subtext0", "#bfc8cc"))
        cr.set_font_size(12)
        ph = lock.get("placeholder") or "type password"
        xbear, ybear, tw, th, _, _ = cr.text_extents(ph)
        cr.move_to(fx + (fw - tw) / 2, fy + fh / 2 + th / 2)
        cr.show_text(ph)

    def _test_lock(self) -> None:
        cmd = self.model["lock"].get("command") or "serpantinum lock"
        subprocess.Popen(["bash", "-lc", cmd], start_new_session=True)
        self.toast.show_message(f"Launching {cmd}")

    def _page_input(self, box: Gtk.Box) -> None:
        box.append(w.section_header("Keyboard and pointer", "Writes input {} plus cursor size environment variables."))
        i = self.model["input"]

        def setv(key: str, cast=str):
            def inner(val):
                i[key] = cast(val) if not isinstance(val, bool) else val
                self.mark_dirty()
            return inner

        box.append(w.labeled_entry("Layout", "XKB layout, e.g. br, us, es", i.get("kb_layout") or "us", setv("kb_layout"), icon="󰌌"))
        box.append(w.labeled_entry("Variant", "Optional variant such as abnt2 or intl", i.get("kb_variant") or "", setv("kb_variant")))
        box.append(w.labeled_entry("Options", "XKB options, e.g. caps:escape", i.get("kb_options") or "", setv("kb_options")))
        box.append(w.labeled_scale("Follow mouse", "0 off, 1 loose, 2 strict, 3 always", i.get("follow_mouse", 1), 0, 3, 1, lambda v: (i.__setitem__("follow_mouse", int(v)), self.mark_dirty())))
        box.append(w.labeled_scale("Sensitivity", "Pointer speed from −1 to 1", float(i.get("sensitivity") or 0), -1, 1, 0.05, lambda v: (i.__setitem__("sensitivity", float(v)), self.mark_dirty()), digits=2, icon="󰍽"))
        box.append(w.labeled_switch("Natural scroll", "Touchpad scrolling like macOS", bool(i.get("natural_scroll")), lambda v: (i.__setitem__("natural_scroll", v), self.mark_dirty()), icon="󰁝"))
        box.append(w.labeled_scale("Cursor size", "XCURSOR_SIZE / HYPRCURSOR_SIZE", i.get("xcursor_size", 24), 16, 48, 1, lambda v: (i.__setitem__("xcursor_size", int(v)), i.__setitem__("hyprcursor_size", int(v)), self.mark_dirty())))

        p = self.model["programs"]
        box.append(w.spacer(6))
        box.append(w.section_header("Default programs", "Used by the built-in application shortcuts."))
        box.append(w.labeled_entry("Terminal", "Super + Enter", p.get("terminal") or "kitty", lambda v: self._set_program("terminal", v), icon="󰆍"))
        box.append(w.labeled_entry("File manager", "Super + E", p.get("fileManager") or "dolphin", lambda v: self._set_program("fileManager", v), icon="󰉋"))
        box.append(w.labeled_entry("Launcher", "Super + L", p.get("menu") or "serpantinumd toggle launcher", lambda v: self._set_program("menu", v), icon="󰵆"))

    def _set_program(self, key: str, value: str) -> None:
        self.model["programs"][key] = value
        mapping = {"terminal": ("Open terminal",), "fileManager": ("File manager",), "menu": ("App launcher",)}
        for item in self.model.get("binds") or []:
            if item.get("description") in mapping.get(key, ()):
                item["arg"] = value
        self.mark_dirty()
        self._rebuild_binds()

    def _page_autostart(self, box: Gtk.Box) -> None:
        box.append(w.section_header("Autostart", "Commands run once when Hyprland starts (exec-once / hl.on hyprland.start)."))
        self._autostart_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.append(self._autostart_box)
        add = w.button("Add command", "hp-btn-accent", "󰐕")
        add.connect("clicked", lambda *_: self._add_autostart())
        box.append(add)
        self._rebuild_autostart()

    def _rebuild_autostart(self) -> None:
        if not self._autostart_box:
            return
        child = self._autostart_box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self._autostart_box.remove(child)
            child = nxt
        for idx, cmd in enumerate(self.model.get("autostart") or []):
            row = Gtk.Box(spacing=8)
            row.add_css_class("hp-bind-row")
            entry = Gtk.Entry()
            entry.set_text(cmd)
            entry.set_hexpand(True)
            entry.add_css_class("hp-search")
            entry.connect("changed", lambda e, i=idx: self._set_autostart(i, e.get_text()))
            row.append(entry)
            delete = w.icon_button("󰆴")
            delete.connect("clicked", lambda _b, i=idx: self._del_autostart(i))
            row.append(delete)
            self._autostart_box.append(row)

    def _set_autostart(self, idx: int, value: str) -> None:
        cmds = self.model.setdefault("autostart", [])
        if 0 <= idx < len(cmds):
            cmds[idx] = value
            self.mark_dirty()

    def _del_autostart(self, idx: int) -> None:
        cmds = self.model.setdefault("autostart", [])
        if 0 <= idx < len(cmds):
            cmds.pop(idx)
            self.mark_dirty()
            self._rebuild_autostart()

    def _add_autostart(self) -> None:
        self.model.setdefault("autostart", []).append("")
        self.mark_dirty()
        self._rebuild_autostart()

    def _page_monitors(self, box: Gtk.Box) -> None:
        box.append(w.section_header("Monitors", "Scale is pinned to Serpantinum’s UI scale (your 1.0x). Apply no longer writes scale = auto, which was resetting it to 1.5x."))
        configio.refresh_monitors(self.model)
        mon = self.model["monitor"]

        def set_mon(key: str, raw: str) -> None:
            value: Any = raw
            if key == "scale":
                try:
                    value = float(raw)
                    if value == int(value):
                        value = int(value)
                except ValueError:
                    value = 1
            mon[key] = value
            if self.model.get("monitors"):
                self.model["monitors"][0][key] = value
            self.mark_dirty()

        box.append(w.labeled_entry("Output", "Monitor name, e.g. eDP-1", mon.get("output") or "", lambda v: set_mon("output", v), icon="󰍹"))
        box.append(w.labeled_entry("Mode", "preferred, highrr, or 1920x1200@60", str(mon.get("mode") or "preferred"), lambda v: set_mon("mode", v)))
        box.append(w.labeled_entry("Position", "auto or XxY", str(mon.get("position") or "auto"), lambda v: set_mon("position", v)))
        box.append(w.labeled_entry("Scale", "Use 1 to match Serpantinum 1.0x. Do not use auto.", str(mon.get("scale") if mon.get("scale") not in (None, "auto") else 1), lambda v: set_mon("scale", v)))
        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        info.add_css_class("hp-card")
        info.set_margin_top(8)
        title_row, _ = w.settings_row("Detected outputs", "From hyprctl monitors", "󰍺")
        info.append(title_row)
        proc = configio.hyprctl("monitors")
        detected = Gtk.Label(label=proc.stdout.strip() or "hyprctl not available", xalign=0)
        detected.set_wrap(True)
        detected.add_css_class("dim")
        detected.set_margin_start(12)
        detected.set_margin_end(12)
        detected.set_margin_bottom(12)
        info.append(detected)
        box.append(info)

    def _page_misc(self, box: Gtk.Box) -> None:
        box.append(w.section_header("Other Hyprland options", "Smaller compositor toggles plus a readable .conf mirror."))
        a = self.model["appearance"]
        box.append(w.labeled_switch("Disable Hyprland logo wallpaper", "misc.disable_hyprland_logo", bool(a.get("disable_hyprland_logo")), lambda v: (a.__setitem__("disable_hyprland_logo", v), self.mark_dirty()), icon="󰸉"))
        box.append(w.labeled_switch("Resize on border", "Drag borders to resize", bool(a.get("resize_on_border")), lambda v: (a.__setitem__("resize_on_border", v), self.mark_dirty())))
        box.append(w.labeled_switch("Allow tearing", "Lower latency, may flicker on some GPUs", bool(a.get("allow_tearing")), lambda v: (a.__setitem__("allow_tearing", v), self.mark_dirty())))
        box.append(w.labeled_switch("Sync rounding with Serpantinum", "When matching a preset, also copy border radius and font", bool(self.model.get("sync_rounding_with_serpantinum", True)), lambda v: (self.model.__setitem__("sync_rounding_with_serpantinum", v), self.mark_dirty()), icon="󰗜"))
        paths = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        paths.add_css_class("hp-card")
        row, _ = w.settings_row("Files this panel writes", "Backups land in ~/.config/hypr/backups", "󰈙")
        paths.append(row)
        for label, path in (
            ("Live config", configio.LUA_PATH),
            (".conf mirror", configio.CONF_MIRROR),
            ("Lockscreen", configio.LOCK_PATH),
            ("Idle lock command", configio.IDLE_PATH),
            ("Panel state", configio.STATE_PATH),
        ):
            line = Gtk.Label(label=f"{label}: {path}", xalign=0)
            line.add_css_class("dim")
            line.set_margin_start(12)
            line.set_margin_end(12)
            line.set_wrap(True)
            paths.append(line)
        paths.append(w.spacer(4))
        box.append(paths)
        open_dir = w.button("Open config folder", "hp-btn", "󰉋")
        open_dir.connect("clicked", lambda *_: subprocess.Popen(["xdg-open", str(configio.HYPR_DIR)]))
        box.append(open_dir)

    def _live_preview(self, silent: bool = False) -> None:
        try:
            configio.apply_live_appearance(self.model)
            if not silent:
                self.toast.show_message("Live preview sent to Hyprland")
        except Exception as exc:
            self.toast.show_message(str(exc), error=True)

    def _apply(self) -> None:
        try:
            backup = configio.backup_configs()
            configio.write_configs(self.model)
            ok, msg = configio.reload_hypr(self.model)
            if not ok:
                self.toast.show_message(msg or "hyprctl reload failed", error=True)
                return
            self._saved = copy.deepcopy(self.model)
            self.dirty = False
            self.apply_btn.set_sensitive(True)
            self.revert_btn.set_sensitive(False)
            self.status.set_text(f"Saved. Backup: {backup.name}")
            self.toast.show_message("Config written and Hyprland reloaded")
        except Exception as exc:
            self.toast.show_message(f"Could not apply: {exc}", error=True)

    def _revert(self) -> None:
        self.model = copy.deepcopy(self._saved)
        self.dirty = False
        self.revert_btn.set_sensitive(False)
        self._rebuild_binds()
        self._rebuild_autostart()
        if self._lock_preview:
            self._lock_preview.queue_draw()
        try:
            configio.apply_live_appearance(self.model)
        except Exception:
            pass
        self.toast.show_message("Reverted unsaved changes")

    def _on_close(self, *_args):
        return False


def _rounded(cr, x, y, w, h, r) -> None:
    r = max(0, min(r, w / 2, h / 2))
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -1.57, 0)
    cr.arc(x + w - r, y + h - r, r, 0, 1.57)
    cr.arc(x + r, y + h - r, r, 1.57, 3.14)
    cr.arc(x + r, y + r, r, 3.14, 4.71)
    cr.close_path()


class CaptureDialog(Gtk.Window):
    def __init__(self, parent: HyprpanelWindow, item: dict[str, Any]) -> None:
        super().__init__(title="Capture shortcut", transient_for=parent, modal=True)
        self.add_css_class("hyprpanel")
        self.parent_win = parent
        self.item = item
        self.set_default_size(420, 180)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        box.append(w.text("Press the new shortcut", "hp-section-title"))
        self.preview = w.text("Waiting for keys…", "hp-section-desc")
        box.append(self.preview)
        cancel = w.button("Cancel", "hp-btn")
        cancel.connect("clicked", lambda *_: self.close())
        box.append(cancel)
        self.set_child(box)
        controller = Gtk.EventControllerKey()
        controller.connect("key-pressed", self._on_key)
        self.add_controller(controller)

    def _on_key(self, _c, keyval, keycode, state) -> bool:
        mods: list[str] = []
        if state & Gdk.ModifierType.SUPER_MASK:
            mods.append("SUPER")
        if state & Gdk.ModifierType.CONTROL_MASK:
            mods.append("CTRL")
        if state & Gdk.ModifierType.ALT_MASK:
            mods.append("ALT")
        if state & Gdk.ModifierType.SHIFT_MASK:
            mods.append("SHIFT")
        if keyval in (
            Gdk.KEY_Shift_L, Gdk.KEY_Shift_R, Gdk.KEY_Control_L, Gdk.KEY_Control_R,
            Gdk.KEY_Alt_L, Gdk.KEY_Alt_R, Gdk.KEY_Super_L, Gdk.KEY_Super_R, Gdk.KEY_Meta_L, Gdk.KEY_Meta_R,
        ):
            self.preview.set_text(" + ".join(mods) or "…")
            return True
        key = GDK_SPECIAL.get(keyval)
        if not key:
            name = Gdk.keyval_name(keyval) or ""
            if len(name) == 1:
                key = name.upper() if name.isalpha() else name
            else:
                key = name
        self.item["mods"] = mods
        self.item["key"] = key
        self.parent_win.mark_dirty()
        self.parent_win._rebuild_binds()
        self.parent_win.toast.show_message(f"Set to {configio.keys_pretty(mods, key)}")
        self.close()
        return True


class BindEditor(Gtk.Window):
    def __init__(self, parent: HyprpanelWindow, item: dict[str, Any] | None) -> None:
        super().__init__(title="Edit binding", transient_for=parent, modal=True)
        self.add_css_class("hyprpanel")
        self.parent_win = parent
        self.is_new = item is None
        self.item = item or configio.bind("apps", "New shortcut", ["SUPER"], "X", "exec", "")
        self.set_default_size(480, 420)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_start(18)
        box.set_margin_end(18)
        box.set_margin_top(18)
        box.set_margin_bottom(18)

        def field(label: str, widget: Gtk.Widget) -> None:
            box.append(w.text(label, "dim"))
            box.append(widget)

        self.desc = Gtk.Entry(text=self.item.get("description") or "")
        self.desc.add_css_class("hp-search")
        field("Description", self.desc)

        self.quick = Gtk.DropDown(model=Gtk.StringList.new([name for name, _ in QUICK_ACTIONS]))
        self.quick.set_selected(0)
        self.quick.connect("notify::selected", self._on_quick)
        field("Quick command", self.quick)

        cats = [c[0] for c in CATEGORIES if c[0] != "all"]
        self.cat = Gtk.DropDown(model=Gtk.StringList.new(cats))
        try:
            self.cat.set_selected(cats.index(self.item.get("category") or "apps"))
        except ValueError:
            self.cat.set_selected(0)
        field("Category", self.cat)

        kinds = [k[0] for k in KIND_OPTIONS]
        self.kind = Gtk.DropDown(model=Gtk.StringList.new([f"{k} — {l}" for k, l in KIND_OPTIONS]))
        try:
            self.kind.set_selected(kinds.index(self.item.get("kind") or "exec"))
        except ValueError:
            self.kind.set_selected(0)
        field("Action", self.kind)

        self.arg = Gtk.Entry(text=self.item.get("arg") or "")
        self.arg.add_css_class("hp-search")
        field("Argument (command, workspace, direction…)", self.arg)

        flags = Gtk.Box(spacing=12)
        self.locked = Gtk.CheckButton(label="Works on lockscreen")
        self.locked.set_active(bool(self.item.get("locked")))
        self.repeat = Gtk.CheckButton(label="Repeat while held")
        self.repeat.set_active(bool(self.item.get("repeating")))
        self.mouse = Gtk.CheckButton(label="Mouse bind")
        self.mouse.set_active(bool(self.item.get("mouse")))
        flags.append(self.locked)
        flags.append(self.repeat)
        flags.append(self.mouse)
        box.append(flags)

        actions = Gtk.Box(spacing=8)
        actions.set_halign(Gtk.Align.END)
        capture = w.button("Capture keys", "hp-btn hp-btn-blue")
        capture.connect("clicked", self._capture)
        actions.append(capture)
        save = w.button("Save", "hp-btn-accent")
        save.connect("clicked", self._save)
        actions.append(save)
        box.append(actions)
        self.set_child(box)

    def _on_quick(self, drop: Gtk.DropDown, *_args) -> None:
        idx = drop.get_selected()
        if idx <= 0 or idx >= len(QUICK_ACTIONS):
            return
        spec = QUICK_ACTIONS[idx][1]
        if not spec:
            return
        self.desc.set_text(spec.get("description") or "")
        self.arg.set_text(spec.get("arg") or "")
        kinds = [k[0] for k in KIND_OPTIONS]
        if spec.get("kind") in kinds:
            self.kind.set_selected(kinds.index(spec["kind"]))
        cats = [c[0] for c in CATEGORIES if c[0] != "all"]
        if spec.get("category") in cats:
            self.cat.set_selected(cats.index(spec["category"]))
        self.repeat.set_active(bool(spec.get("repeating")))
        self.mouse.set_active(bool(spec.get("mouse")))

    def _capture(self, *_args) -> None:
        CaptureDialog(self.parent_win, self.item).present()

    def _save(self, *_args) -> None:
        cats = [c[0] for c in CATEGORIES if c[0] != "all"]
        kinds = [k[0] for k in KIND_OPTIONS]
        self.item["description"] = self.desc.get_text().strip() or "Binding"
        self.item["category"] = cats[self.cat.get_selected()] if self.cat.get_selected() < len(cats) else "apps"
        self.item["kind"] = kinds[self.kind.get_selected()] if self.kind.get_selected() < len(kinds) else "exec"
        self.item["arg"] = self.arg.get_text().strip()
        self.item["locked"] = self.locked.get_active()
        self.item["repeating"] = self.repeat.get_active()
        self.item["mouse"] = self.mouse.get_active()
        if self.is_new:
            self.parent_win.model.setdefault("binds", []).append(self.item)
        self.parent_win.mark_dirty()
        self.parent_win._rebuild_binds()
        self.close()


class HyprpanelApp(Gtk.Application):
    def __init__(self, start_page: str = "bindings") -> None:
        super().__init__(application_id="io.hyprpanel.Hyprpanel", flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.start_page = start_page

    def do_activate(self) -> None:  # noqa: N802
        win = self.props.active_window
        if not win:
            win = HyprpanelWindow(self)
            if self.start_page in {p[0] for p in PAGES}:
                win._goto(self.start_page)
        win.present()


def main() -> None:
    os.environ.setdefault("GSK_RENDERER", "cairo")
    argv = sys.argv[1:]
    start_page = "bindings"
    if "--page" in argv:
        idx = argv.index("--page")
        if idx + 1 < len(argv):
            start_page = argv[idx + 1]
    app = HyprpanelApp(start_page=start_page)
    app.run(None)
