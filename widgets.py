"""Reusable GTK widgets styled like Serpantinum Guide rows."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, GLib, Gtk, Pango

ICON_FONT = "Iosevka Nerd Font"


def icon_label(glyph: str, size: int = 16, css: str = "hp-icon") -> Gtk.Label:
    label = Gtk.Label(label=glyph)
    label.add_css_class(css)
    label.set_xalign(0.5)
    desc = Pango.FontDescription()
    desc.set_family(ICON_FONT)
    desc.set_size(size * Pango.SCALE)
    label.set_css_classes([css])
    attr = Pango.AttrList()
    attr.insert(Pango.attr_family_new(ICON_FONT))
    attr.insert(Pango.attr_size_new(size * Pango.SCALE))
    label.set_attributes(attr)
    try:
        label.set_markup(
            f'<span font_family="Iosevka Nerd Font" size="{size * 1024}">{glyph}</span>'
        )
    except Exception:
        pass
    return label


def text(value: str, css: str = "", xalign: float = 0.0, wrap: bool = False) -> Gtk.Label:
    label = Gtk.Label(label=value, xalign=xalign)
    if css:
        for cls in css.split():
            label.add_css_class(cls)
    if wrap:
        label.set_wrap(True)
        label.set_hexpand(True)
    return label


def button(label: str, css: str = "hp-btn", icon: str | None = None) -> Gtk.Button:
    if icon:
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.append(icon_label(icon, 14))
        box.append(Gtk.Label(label=label))
        btn = Gtk.Button()
        btn.set_child(box)
    else:
        btn = Gtk.Button(label=label)
    for cls in css.split():
        btn.add_css_class(cls)
    return btn


def icon_button(glyph: str, css: str = "hp-btn-ghost") -> Gtk.Button:
    btn = Gtk.Button()
    btn.set_child(icon_label(glyph, 14))
    for cls in css.split():
        btn.add_css_class(cls)
    return btn


def card() -> Gtk.Box:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    box.add_css_class("hp-card")
    box.set_margin_start(2)
    box.set_margin_end(2)
    box.set_margin_top(2)
    box.set_margin_bottom(2)
    return box


def settings_row(title: str, description: str = "", icon: str | None = None) -> tuple[Gtk.Box, Gtk.Box]:
    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    row.set_hexpand(True)
    row.set_margin_start(12)
    row.set_margin_end(12)
    row.set_margin_top(10)
    row.set_margin_bottom(10)
    if icon:
        badge = Gtk.Box()
        badge.set_valign(Gtk.Align.CENTER)
        badge.append(icon_label(icon, 16))
        row.append(badge)
    texts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    texts.set_hexpand(True)
    texts.set_valign(Gtk.Align.CENTER)
    title_l = text(title)
    title_l.set_xalign(0)
    texts.append(title_l)
    if description:
        desc = text(description, "dim")
        desc.set_xalign(0)
        desc.set_wrap(True)
        texts.append(desc)
    row.append(texts)
    control = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    control.set_valign(Gtk.Align.CENTER)
    row.append(control)
    return row, control


def labeled_switch(title: str, description: str, value: bool, on_change: Callable[[bool], None], icon: str | None = None) -> Gtk.Box:
    wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    wrap.add_css_class("hp-card")
    row, control = settings_row(title, description, icon)
    sw = Gtk.Switch()
    sw.set_active(value)
    sw.set_valign(Gtk.Align.CENTER)
    sw.connect("notify::active", lambda s, *_: on_change(s.get_active()))
    control.append(sw)
    wrap.append(row)
    return wrap


def labeled_scale(
    title: str,
    description: str,
    value: float,
    lo: float,
    hi: float,
    step: float,
    on_change: Callable[[float], None],
    digits: int = 0,
    icon: str | None = None,
) -> Gtk.Box:
    wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    wrap.add_css_class("hp-card")
    row, control = settings_row(title, description, icon)
    adj = Gtk.Adjustment(value=value, lower=lo, upper=hi, step_increment=step, page_increment=step * 4)
    scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
    scale.set_draw_value(True)
    scale.set_digits(digits)
    scale.set_size_request(180, -1)
    scale.set_hexpand(False)
    scale.connect("value-changed", lambda s: on_change(s.get_value()))
    control.append(scale)
    wrap.append(row)
    wrap._scale = scale  # type: ignore[attr-defined]
    return wrap


def labeled_entry(title: str, description: str, value: str, on_change: Callable[[str], None], icon: str | None = None) -> Gtk.Box:
    wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    wrap.add_css_class("hp-card")
    row, control = settings_row(title, description, icon)
    entry = Gtk.Entry()
    entry.set_text(value or "")
    entry.set_size_request(220, -1)
    entry.add_css_class("hp-search")
    entry.connect("changed", lambda e: on_change(e.get_text()))
    control.append(entry)
    wrap.append(row)
    wrap._entry = entry  # type: ignore[attr-defined]
    return wrap


def labeled_dropdown(
    title: str,
    description: str,
    options: list[str],
    current: str,
    on_change: Callable[[str], None],
    icon: str | None = None,
) -> Gtk.Box:
    wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    wrap.add_css_class("hp-card")
    row, control = settings_row(title, description, icon)
    store = Gtk.StringList.new(options)
    drop = Gtk.DropDown(model=store)
    try:
        idx = options.index(current)
    except ValueError:
        idx = 0
    drop.set_selected(idx)
    drop.connect(
        "notify::selected",
        lambda d, *_: on_change(options[d.get_selected()]) if d.get_selected() < len(options) else None,
    )
    control.append(drop)
    wrap.append(row)
    return wrap


def kbd_pill(text_value: str) -> Gtk.Label:
    label = Gtk.Label(label=text_value)
    label.add_css_class("hp-kbd")
    return label


def spacer(height: int = 8) -> Gtk.Box:
    box = Gtk.Box()
    box.set_size_request(-1, height)
    return box


def section_header(title: str, description: str = "") -> Gtk.Box:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    box.set_margin_bottom(8)
    box.append(text(title, "hp-section-title"))
    if description:
        desc = text(description, "hp-section-desc")
        desc.set_wrap(True)
        box.append(desc)
    return box


class Toast(Gtk.Revealer):
    def __init__(self) -> None:
        super().__init__()
        self.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        self.set_valign(Gtk.Align.END)
        self.set_halign(Gtk.Align.CENTER)
        self.set_margin_bottom(18)
        self._label = Gtk.Label()
        self._box = Gtk.Box()
        self._box.add_css_class("hp-toast")
        self._box.set_margin_start(12)
        self._box.set_margin_end(12)
        self._box.append(self._label)
        self.set_child(self._box)
        self._source = 0

    def show_message(self, message: str, error: bool = False, timeout: int = 2800) -> None:
        self._label.set_text(message)
        if error:
            self._box.add_css_class("error")
        else:
            self._box.remove_css_class("error")
        self.set_reveal_child(True)
        if self._source:
            GLib.source_remove(self._source)

        def hide() -> bool:
            self.set_reveal_child(False)
            self._source = 0
            return False

        self._source = GLib.timeout_add(timeout, hide)


def color_swatch(hex_color: str, width: int = 18, height: int = 18, radius: int = 4) -> Gtk.DrawingArea:
    area = Gtk.DrawingArea()
    area.set_content_width(width)
    area.set_content_height(height)
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    r, g, b = int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255

    def draw(_area, cr, w, hgt):
        cr.set_source_rgb(r, g, b)
        rr = min(radius, w / 2, hgt / 2)
        cr.new_sub_path()
        cr.arc(w - rr, rr, rr, -1.57, 0)
        cr.arc(w - rr, hgt - rr, rr, 0, 1.57)
        cr.arc(rr, hgt - rr, rr, 1.57, 3.14)
        cr.arc(rr, rr, rr, 3.14, 4.71)
        cr.close_path()
        cr.fill()

    area.set_draw_func(draw)
    return area


def hex_to_rgba(hex_color: str) -> Gdk.RGBA:
    color = Gdk.RGBA()
    h = hex_color.lstrip("#")
    if len(h) == 8:
        color.parse(f"#{h[:6]}")
        color.alpha = int(h[6:8], 16) / 255
    else:
        color.parse(f"#{h[:6]}")
        color.alpha = 1.0
    return color


def rgba_to_hypr(color: Gdk.RGBA) -> str:
    r = int(round(color.red * 255))
    g = int(round(color.green * 255))
    b = int(round(color.blue * 255))
    a = int(round(color.alpha * 255))
    return f"rgba({r:02x}{g:02x}{b:02x}{a:02x})"


def parse_hypr_color(value: str) -> Gdk.RGBA:
    color = Gdk.RGBA()
    value = (value or "").strip()
    m = None
    if value.startswith("rgba(") and value.endswith(")"):
        inner = value[5:-1]
        if len(inner) == 8 and all(ch in "0123456789abcdefABCDEF" for ch in inner):
            color.parse(f"#{inner[:6]}")
            color.alpha = int(inner[6:8], 16) / 255
            return color
    if value.startswith("#"):
        color.parse(value[:7])
        return color
    color.parse("#88d0ed")
    return color
