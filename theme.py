"""Load Serpantinum colors/presets and build matching GTK CSS."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HOME = Path.home()
SERP_SETTINGS = HOME / ".config" / "serpantinum" / "settings.json"
SERP_COLORS = HOME / ".local" / "state" / "serpantinum" / "qs_colors.json"
SERP_PRESETS = HOME / ".local" / "share" / "serpantinum" / "src" / "assets" / "themes"
SERP_FONT_DIR = HOME / ".local" / "share" / "serpantinum" / "src" / "assets" / "fonts"

FALLBACK = {
    "base": "#0a0f11",
    "mantle": "#171c1f",
    "crust": "#0f1416",
    "text": "#dee3e6",
    "subtext0": "#bfc8cc",
    "subtext1": "#8a9296",
    "surface0": "#1b2023",
    "surface1": "#252b2d",
    "surface2": "#303638",
    "overlay0": "#dee3e6",
    "overlay1": "#dee3e6",
    "overlay2": "#dee3e6",
    "blue": "#88d0ed",
    "sapphire": "#004d61",
    "peach": "#c4c3eb",
    "green": "#b3cad5",
    "red": "#ffb4ab",
    "mauve": "#88d0ed",
    "pink": "#434465",
    "yellow": "#354a53",
    "maroon": "#93000a",
    "teal": "#b3cad5",
}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
        text = "".join(
            line for line in text.splitlines(True) if not line.lstrip().startswith("//")
        )
        return json.loads(text)
    except Exception:
        return {}


def load_settings() -> dict[str, Any]:
    return _read_json(SERP_SETTINGS)


def load_colors() -> dict[str, str]:
    colors = dict(FALLBACK)
    live = _read_json(SERP_COLORS)
    if live:
        colors.update({k: v for k, v in live.items() if isinstance(v, str) and v.startswith("#")})
    settings = load_settings()
    theme = settings.get("theme") or {}
    stored = theme.get("colors") or {}
    if stored and not live:
        colors.update({k: v for k, v in stored.items() if isinstance(v, str) and v.startswith("#")})
    return colors


def load_theme_meta() -> dict[str, Any]:
    settings = load_settings()
    theme = settings.get("theme") or {}
    return {
        "fontFamily": theme.get("fontFamily") or "Adwaita Mono",
        "borderRadius": int(theme.get("borderRadius") or 8),
        "activePreset": theme.get("activePreset") or "Matugen",
        "matugen": bool(theme.get("matugen", True)),
        "colors": load_colors(),
    }


def list_presets() -> list[dict[str, Any]]:
    presets: list[dict[str, Any]] = []
    if not SERP_PRESETS.is_dir():
        return presets
    for path in sorted(SERP_PRESETS.glob("*.json")):
        data = _read_json(path)
        name = data.get("name") or path.stem
        colors = data.get("colors") or {}
        presets.append(
            {
                "name": name,
                "file": str(path),
                "isMatugen": bool(data.get("isMatugen")),
                "colors": colors if colors else dict(FALLBACK),
            }
        )
    return presets


def hex_to_rgba(hex_color: str, alpha: float = 1.0) -> str:
    h = hex_color.lstrip("#")
    if len(h) == 8:
        return f"rgba({h.lower()})"
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    a = max(0, min(255, int(round(alpha * 255))))
    return f"rgba({h.lower()}{a:02x})"


def hex_to_rgb_css(hex_color: str, alpha: float | None = None) -> str:
    h = hex_color.lstrip("#")
    if len(h) == 8:
        a = int(h[6:8], 16) / 255.0
        h = h[:6]
        if alpha is None:
            alpha = a
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    if alpha is None:
        return f"rgb({r},{g},{b})"
    return f"rgba({r},{g},{b},{alpha:.3f})"


def luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")[:6]
    r, g, b = int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_text(bg: str) -> str:
    return "#0a0f11" if luminance(bg) > 0.55 else "#dee3e6"


def build_css(meta: dict[str, Any] | None = None) -> str:
    meta = meta or load_theme_meta()
    c = meta["colors"]
    radius = int(meta["borderRadius"])
    font = meta["fontFamily"]
    icon_font = "Iosevka Nerd Font, Symbols Nerd Font Mono, Adwaita Mono, monospace"

    def col(name: str, fallback: str | None = None) -> str:
        return c.get(name) or FALLBACK.get(name) or fallback or "#888888"

    return f"""
@define-color hp-base {col("base")};
@define-color hp-mantle {col("mantle")};
@define-color hp-crust {col("crust")};
@define-color hp-text {col("text")};
@define-color hp-subtext0 {col("subtext0")};
@define-color hp-subtext1 {col("subtext1")};
@define-color hp-surface0 {col("surface0")};
@define-color hp-surface1 {col("surface1")};
@define-color hp-surface2 {col("surface2")};
@define-color hp-overlay0 {col("overlay0")};
@define-color hp-blue {col("blue")};
@define-color hp-sapphire {col("sapphire")};
@define-color hp-peach {col("peach")};
@define-color hp-green {col("green")};
@define-color hp-red {col("red")};
@define-color hp-mauve {col("mauve")};
@define-color hp-pink {col("pink")};
@define-color hp-yellow {col("yellow")};
@define-color hp-teal {col("teal")};

window.hyprpanel, .hyprpanel {{
  background-color: @hp-base;
  color: @hp-text;
  font-family: "{font}", "Adwaita Mono", monospace;
  font-size: 13px;
}}

.hyprpanel * {{
  font-family: "{font}", "Adwaita Mono", monospace;
}}

.hyprpanel .hp-icon,
.hyprpanel .hp-icon-lg,
.hp-icon,
.hp-icon-lg {{
  font-family: "Iosevka Nerd Font", "Iosevka NF", "Symbols Nerd Font Mono", monospace;
}}

.hp-icon {{
  font-size: 16px;
}}

.hp-icon-lg {{
  font-size: 18px;
}}

.hp-sidebar {{
  background-color: alpha(@hp-surface0, 0.42);
  border-right: 1px solid alpha(@hp-surface2, 0.35);
}}

.hp-header {{
  background-color: transparent;
}}

.hp-title {{
  font-weight: 700;
  font-size: 15px;
  color: @hp-text;
}}

.hp-subtitle {{
  color: @hp-subtext0;
  font-size: 11px;
}}

.hp-search {{
  background-color: alpha(@hp-surface0, 0.72);
  color: @hp-text;
  border: 1px solid alpha(@hp-surface2, 0.5);
  border-radius: {radius}px;
  padding: 8px 12px;
  min-height: 36px;
  box-shadow: none;
}}
.hp-search:focus {{
  border-color: alpha(@hp-mauve, 0.8);
  box-shadow: 0 0 0 2px alpha(@hp-mauve, 0.18);
}}

.hp-nav {{
  background: transparent;
  border: none;
  border-radius: {radius}px;
  padding: 8px 10px;
  color: @hp-subtext0;
  min-height: 36px;
}}
.hp-nav:hover {{
  background-color: alpha(@hp-surface1, 0.55);
  color: @hp-text;
}}
.hp-nav.active {{
  background-color: alpha(@hp-mauve, 0.16);
  color: @hp-text;
}}
.hp-nav.active .hp-nav-label {{
  color: @hp-text;
  font-weight: 600;
}}

.hp-nav-label {{
  color: inherit;
}}

.hp-section-title {{
  font-size: 18px;
  font-weight: 700;
  color: @hp-text;
}}

.hp-section-desc {{
  font-size: 12px;
  color: @hp-subtext0;
}}

.hp-card {{
  background-color: alpha(@hp-surface0, 0.42);
  border-radius: {radius}px;
  border: 1px solid alpha(@hp-surface2, 0.18);
  padding: 4px;
}}

.hp-bind-row {{
  background-color: alpha(@hp-surface0, 0.42);
  border-radius: {radius}px;
  border: 1px solid transparent;
  padding: 8px 10px 8px 8px;
  min-height: 64px;
}}
.hp-bind-row:hover {{
  background-color: alpha(@hp-surface1, 0.45);
  border-color: alpha(@hp-surface2, 0.35);
}}

.hp-pill {{
  background-color: alpha(@hp-surface1, 0.7);
  color: @hp-text;
  border-radius: {max(4, radius - 2)}px;
  padding: 3px 8px;
  font-size: 11px;
  font-weight: 600;
}}

.hp-pill-accent {{
  background-color: alpha(@hp-mauve, 0.22);
  color: @hp-mauve;
}}

.hp-chip {{
  background-color: alpha(@hp-surface0, 0.6);
  color: @hp-subtext0;
  border-radius: {radius}px;
  padding: 4px 10px;
  border: 1px solid alpha(@hp-surface2, 0.3);
}}
.hp-chip.active, .hp-chip:checked {{
  background-color: alpha(@hp-mauve, 0.18);
  color: @hp-text;
  border-color: alpha(@hp-mauve, 0.4);
}}

.hp-btn {{
  background-color: alpha(@hp-surface1, 0.7);
  color: @hp-text;
  border: 1px solid alpha(@hp-surface2, 0.35);
  border-radius: {radius}px;
  padding: 6px 12px;
  min-height: 32px;
}}
.hp-btn:hover {{
  background-color: alpha(@hp-surface2, 0.55);
}}

.hp-btn-accent {{
  background-color: @hp-mauve;
  color: {contrast_text(col("mauve"))};
  border: none;
  border-radius: {radius}px;
  padding: 8px 16px;
  font-weight: 700;
  min-height: 34px;
}}
.hp-btn-accent:hover {{
  filter: brightness(1.08);
}}

.hp-btn-ghost {{
  background: transparent;
  color: @hp-subtext0;
  border: none;
  border-radius: {radius}px;
  min-height: 28px;
  min-width: 28px;
}}
.hp-btn-ghost:hover {{
  background-color: alpha(@hp-red, 0.16);
  color: @hp-red;
}}

.hp-btn-blue {{
  background-color: alpha(@hp-blue, 0.18);
  color: @hp-blue;
  border: 1px solid alpha(@hp-blue, 0.28);
  border-radius: {radius}px;
}}

entry, spinbutton, textview {{
  background-color: alpha(@hp-surface0, 0.75);
  color: @hp-text;
  border: 1px solid alpha(@hp-surface2, 0.45);
  border-radius: {radius}px;
  caret-color: @hp-mauve;
}}
entry:focus, spinbutton:focus {{
  border-color: alpha(@hp-mauve, 0.75);
  box-shadow: 0 0 0 2px alpha(@hp-mauve, 0.16);
}}

dropdown, combobox {{
  background-color: alpha(@hp-surface0, 0.75);
  color: @hp-text;
  border-radius: {radius}px;
}}

popover, popover > contents {{
  background-color: @hp-mantle;
  color: @hp-text;
  border: 1px solid alpha(@hp-surface2, 0.5);
  border-radius: {radius}px;
}}

switch {{
  background-color: @hp-surface2;
  border-radius: 20px;
  min-width: 42px;
}}
switch:checked {{
  background-color: @hp-mauve;
}}
switch slider {{
  background-color: @hp-text;
  min-width: 18px;
  min-height: 18px;
}}

scale {{
  min-width: 160px;
}}
scale trough {{
  background-color: @hp-surface2;
  border-radius: 8px;
  min-height: 6px;
  min-width: 140px;
}}
scale highlight {{
  background-color: @hp-blue;
  border-radius: 8px;
}}
scale slider {{
  background-color: @hp-text;
  min-width: 14px;
  min-height: 14px;
  border-radius: 99px;
  box-shadow: 0 1px 3px alpha(@hp-crust, 0.5);
}}

scrolledwindow {{
  background: transparent;
  border: none;
}}
scrollbar {{
  background: transparent;
}}
scrollbar slider {{
  background-color: alpha(@hp-surface2, 0.8);
  border-radius: 8px;
  min-width: 6px;
}}

.hp-toast {{
  background-color: @hp-mantle;
  color: @hp-text;
  border: 1px solid alpha(@hp-green, 0.4);
  border-radius: {radius}px;
  padding: 10px 14px;
}}
.hp-toast.error {{
  border-color: alpha(@hp-red, 0.5);
}}

.hp-preview {{
  background-color: @hp-crust;
  border-radius: {radius}px;
  border: 1px solid alpha(@hp-surface2, 0.4);
}}

.hp-preset {{
  background-color: alpha(@hp-surface0, 0.5);
  border-radius: {radius}px;
  border: 1px solid alpha(@hp-surface2, 0.25);
  padding: 10px;
}}
.hp-preset:hover {{
  border-color: alpha(@hp-mauve, 0.45);
}}
.hp-preset.active {{
  border-color: @hp-mauve;
  background-color: alpha(@hp-mauve, 0.12);
}}

.hp-footer {{
  background-color: alpha(@hp-mantle, 0.92);
  border-top: 1px solid alpha(@hp-surface2, 0.35);
}}

.hp-kbd {{
  background-color: alpha(@hp-surface1, 0.85);
  border: 1px solid alpha(@hp-surface2, 0.55);
  border-bottom-width: 2px;
  border-radius: 6px;
  padding: 2px 7px;
  font-size: 11px;
  font-weight: 700;
  color: @hp-text;
}}

label.dim {{
  color: @hp-subtext0;
  font-size: 11px;
}}

checkbutton {{
  color: @hp-text;
}}
checkbutton check {{
  background-color: @hp-surface1;
  border: 1px solid @hp-surface2;
  border-radius: 4px;
}}
checkbutton:checked check {{
  background-color: @hp-mauve;
  border-color: @hp-mauve;
}}
"""
