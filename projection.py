"""Windows-style display projection: layout, modes, and live Hyprland apply."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, GLib, Gtk

import configio
import theme
import widgets as w

LOCK_PATH = Path(os.environ.get("XDG_RUNTIME_DIR") or "/tmp") / "hypr-place-monitors.lock"

MODES = (
    (
        "internal",
        "󰌢",
        "PC screen only",
        "Show only the built-in display",
    ),
    (
        "duplicate",
        "󰍺",
        "Duplicate",
        "Mirror the same image on every screen",
    ),
    (
        "extend",
        "󰍹",
        "Extend",
        "Use displays as one large desktop",
    ),
    (
        "external",
        "󰐧",
        "Second screen only",
        "Turn off the laptop panel",
    ),
)

ORIENTATIONS = (
    (0, "Landscape"),
    (1, "Portrait"),
    (2, "Landscape (flipped)"),
    (3, "Portrait (flipped)"),
)

SCALE_PRESETS = (1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5)

SNAP_PX = 64


def is_internal(name: str) -> bool:
    upper = (name or "").upper()
    return upper.startswith("EDP") or upper.startswith("LVDS") or upper.startswith("DSI")


def friendly_name(mon: dict[str, Any]) -> str:
    if is_internal(str(mon.get("output") or "")):
        return "Laptop"
    desc = str(mon.get("description") or "").strip()
    make = str(mon.get("make") or "").strip()
    model = str(mon.get("model") or "").strip()
    if desc and desc not in {make, model, f"{make} {model}".strip()}:
        return desc
    label = " ".join(part for part in (make, model) if part).strip()
    return label or str(mon.get("output") or "Display")


def parse_xy(value: Any, fallback: tuple[int, int] = (0, 0)) -> tuple[int, int]:
    raw = str(value or "").strip()
    if not raw or raw.startswith("auto"):
        return fallback
    if "x" not in raw:
        return fallback
    left, right = raw.split("x", 1)
    try:
        return int(float(left)), int(float(right))
    except ValueError:
        return fallback


def format_xy(x: int, y: int) -> str:
    return f"{int(x)}x{int(y)}"


def parse_mode(mode: str | None) -> tuple[int | None, int | None, str | None]:
    raw = str(mode or "").strip()
    if not raw or raw in {"preferred", "highres", "highrr"}:
        return None, None, None
    core = raw.replace("Hz", "")
    if "@" in core:
        res, rate = core.split("@", 1)
    else:
        res, rate = core, None
    if "x" not in res:
        return None, None, rate
    w_s, h_s = res.split("x", 1)
    try:
        return int(float(w_s)), int(float(h_s)), rate
    except ValueError:
        return None, None, rate


def mode_str(mon: dict[str, Any]) -> str:
    mode = str(mon.get("mode") or "preferred").strip() or "preferred"
    return mode


def logical_size(mon: dict[str, Any]) -> tuple[int, int]:
    scale = float(mon.get("scale") or 1) or 1.0
    mw, mh = parse_mode(str(mon.get("mode") or ""))[:2]
    width = int(mon.get("width") or mw or 1920)
    height = int(mon.get("height") or mh or 1080)
    lw = max(1, int(round(width / scale)))
    lh = max(1, int(round(height / scale)))
    transform = int(mon.get("transform") or 0) % 8
    if transform in (1, 3, 5, 7):
        return lh, lw
    return lw, lh


def connected_monitors(model: dict[str, Any]) -> list[dict[str, Any]]:
    return [m for m in (model.get("monitors") or []) if m.get("connected")]


def enabled_monitors(model: dict[str, Any]) -> list[dict[str, Any]]:
    return [m for m in connected_monitors(model) if m.get("enabled", True)]


def sorted_by_priority(model: dict[str, Any]) -> list[dict[str, Any]]:
    mons = list(model.get("monitors") or [])
    return sorted(mons, key=lambda m: (int(m.get("priority") or 99), parse_xy(m.get("position"))[0], parse_xy(m.get("position"))[1], m.get("output") or ""))


def ensure_projection(model: dict[str, Any]) -> dict[str, Any]:
    proj = model.setdefault("projection", {})
    proj.setdefault("mode", infer_mode(model))
    proj.setdefault("extend_positions", {})
    monitors = model.get("monitors") or []
    if not proj.get("primary") and monitors:
        internal = next((m for m in monitors if is_internal(str(m.get("output") or ""))), monitors[0])
        proj["primary"] = internal.get("output") or ""
    return proj


def infer_mode(model: dict[str, Any]) -> str:
    connected = connected_monitors(model)
    if len(connected) <= 1:
        return "extend"
    if any(m.get("mirror") for m in connected):
        return "duplicate"
    enabled = enabled_monitors(model)
    internals = [m for m in connected if is_internal(str(m.get("output") or ""))]
    externals = [m for m in connected if m not in internals]
    if internals and not any(m.get("enabled", True) for m in externals) and all(m.get("enabled", True) for m in internals):
        return "internal"
    if externals and internals and not any(m.get("enabled", True) for m in internals) and any(m.get("enabled", True) for m in externals):
        return "external"
    return "extend"


def query_hypr_monitors() -> list[dict[str, Any]]:
    try:
        data = json.loads(configio.hyprctl("monitors", "all", "-j").stdout or "[]")
        if not data:
            data = json.loads(configio.hyprctl("monitors", "-j").stdout or "[]")
        return data if isinstance(data, list) else []
    except Exception:
        return []


def query_drm_connectors() -> list[dict[str, Any]]:
    root = Path("/sys/class/drm")
    found: list[dict[str, Any]] = []
    if not root.is_dir():
        return found
    for path in sorted(root.glob("card*-*")):
        name = path.name.split("-", 1)[-1]
        if not name:
            continue
        status_path = path / "status"
        enabled_path = path / "enabled"
        status = status_path.read_text(encoding="utf-8").strip() if status_path.exists() else "unknown"
        drm_enabled = enabled_path.read_text(encoding="utf-8").strip() if enabled_path.exists() else ""
        found.append({"output": name, "drm_status": status, "drm_enabled": drm_enabled})
    return found


def live_record(raw: dict[str, Any]) -> dict[str, Any]:
    name = str(raw.get("name") or "")
    x = int(raw.get("x") or 0)
    y = int(raw.get("y") or 0)
    scale = float(raw.get("scale") or 1) or 1.0
    refresh = raw.get("refreshRate")
    width = int(raw.get("width") or 0)
    height = int(raw.get("height") or 0)
    mode = "preferred"
    if width and height:
        rate = f"{refresh:.2f}" if isinstance(refresh, (int, float)) else ""
        mode = f"{width}x{height}@{rate}Hz" if rate else f"{width}x{height}"
    hw = raw.get("hardwareDetails") or {}
    return {
        "output": name,
        "enabled": not bool(raw.get("disabled")),
        "connected": True,
        "mode": mode,
        "position": format_xy(x, y),
        "scale": scale,
        "transform": int(raw.get("transform") or 0),
        "mirror": "" if str(raw.get("mirrorOf") or "none") in {"", "none"} else str(raw.get("mirrorOf")),
        "width": width,
        "height": height,
        "x": x,
        "y": y,
        "refreshRate": refresh,
        "make": raw.get("make") or "",
        "model": raw.get("model") or "",
        "serial": raw.get("serial") or "",
        "description": raw.get("description") or "",
        "physicalWidth": raw.get("physicalWidth") or 0,
        "physicalHeight": raw.get("physicalHeight") or 0,
        "availableModes": list(raw.get("availableModes") or []),
        "focused": bool(raw.get("focused")),
        "dpmsStatus": bool(raw.get("dpmsStatus", True)),
        "vrr": bool(raw.get("vrr")),
        "vrrCapable": bool(hw.get("vrrCapable")),
        "hdr": bool(hw.get("hdr")),
        "currentFormat": raw.get("currentFormat") or "",
        "colorManagementPreset": raw.get("colorManagementPreset") or "",
        "sdrBrightness": raw.get("sdrBrightness"),
        "sdrMaxLuminance": raw.get("sdrMaxLuminance"),
        "id": raw.get("id"),
        "activeWorkspace": ((raw.get("activeWorkspace") or {}).get("name") or ""),
    }


def blank_record(output: str, connected: bool = False) -> dict[str, Any]:
    return {
        "output": output,
        "enabled": False,
        "connected": connected,
        "mode": "preferred",
        "position": "auto",
        "scale": 1,
        "transform": 0,
        "mirror": "",
        "width": 1920,
        "height": 1080 if not is_internal(output) else 1200,
        "x": 0,
        "y": 0,
        "refreshRate": None,
        "make": "",
        "model": "",
        "serial": "",
        "description": "",
        "physicalWidth": 0,
        "physicalHeight": 0,
        "availableModes": [],
        "focused": False,
        "priority": 2 if not is_internal(output) else 1,
    }


def merge_monitors(model: dict[str, Any], *, sync_geometry: bool = True) -> None:
    saved_list = list(model.get("monitors") or [])
    saved = {str(m.get("output") or ""): m for m in saved_list if m.get("output")}
    live_by_name = {str(item.get("name") or ""): live_record(item) for item in query_hypr_monitors() if item.get("name")}
    drm = query_drm_connectors()
    names: list[str] = []
    for name in list(live_by_name) + [d["output"] for d in drm] + list(saved):
        if name and name not in names:
            names.append(name)

    merged: list[dict[str, Any]] = []
    for name in names:
        base = blank_record(name)
        prev = saved.get(name) or {}
        live = live_by_name.get(name)
        drm_hit = next((d for d in drm if d["output"] == name), None)
        base.update({k: v for k, v in prev.items() if k not in {"connected", "focused", "availableModes"}})
        if live:
            meta_keys = (
                "make", "model", "serial", "description", "physicalWidth", "physicalHeight",
                "availableModes", "focused", "dpmsStatus", "vrrCapable", "hdr", "currentFormat",
                "colorManagementPreset", "sdrBrightness", "sdrMaxLuminance", "id", "activeWorkspace",
                "width", "height", "refreshRate",
            )
            for key in meta_keys:
                if live.get(key) not in (None, "", [], 0):
                    base[key] = live[key]
            base["connected"] = True
            if sync_geometry:
                base["position"] = live["position"]
                base["x"] = live["x"]
                base["y"] = live["y"]
                base["scale"] = live.get("scale") or base.get("scale") or 1
                base["transform"] = live.get("transform") or 0
                base["mirror"] = live.get("mirror") or ""
                base["enabled"] = live.get("enabled", True)
                if live.get("mode"):
                    base["mode"] = live["mode"]
        else:
            base["connected"] = bool(drm_hit and drm_hit.get("drm_status") == "connected")
            base["focused"] = False
            if prev:
                base["enabled"] = bool(prev.get("enabled", True))
            elif not base["connected"]:
                base["enabled"] = False
        if "enabled" not in base:
            base["enabled"] = bool(base.get("connected"))
        merged.append(base)

    if not merged:
        fallback = model.get("monitor") or {"output": "eDP-1", "mode": "preferred", "position": "0x0", "scale": 1}
        merged = [blank_record(str(fallback.get("output") or "eDP-1"), connected=True)]
        merged[0].update(fallback)
        merged[0]["enabled"] = True

    _refresh_priorities(model, merged)
    model["monitors"] = merged
    primary = ensure_projection(model).get("primary")
    model["monitor"] = next((m for m in merged if m.get("output") == primary), merged[0])
    ensure_projection(model)
    if not any(m.get("mirror") for m in merged):
        # keep stored mode unless live layout contradicts on next infer from UI
        pass


def _refresh_priorities(model: dict[str, Any], monitors: list[dict[str, Any]] | None = None) -> None:
    proj = ensure_projection(model)
    monitors = monitors if monitors is not None else list(model.get("monitors") or [])
    primary = proj.get("primary") or ""
    enabled = [m for m in monitors if m.get("enabled", True) and m.get("connected")]
    if primary and not any(m.get("output") == primary for m in enabled) and enabled:
        primary = enabled[0]["output"]
        proj["primary"] = primary
    ranked = sorted(
        enabled,
        key=lambda m: (
            0 if m.get("output") == primary else 1,
            parse_xy(m.get("position"))[0],
            parse_xy(m.get("position"))[1],
            m.get("output") or "",
        ),
    )
    order = {m["output"]: i + 1 for i, m in enumerate(ranked)}
    for mon in monitors:
        mon["priority"] = order.get(mon.get("output"), 99)


def _save_extend_positions(model: dict[str, Any]) -> None:
    proj = ensure_projection(model)
    stored = proj.setdefault("extend_positions", {})
    for mon in model.get("monitors") or []:
        if mon.get("enabled", True) and not mon.get("mirror"):
            pos = str(mon.get("position") or "")
            if pos and not pos.startswith("auto"):
                stored[mon["output"]] = pos


def _restore_extend_positions(model: dict[str, Any]) -> None:
    stored = ensure_projection(model).get("extend_positions") or {}
    restored = False
    for mon in enabled_monitors(model):
        saved = stored.get(mon["output"])
        if saved and not str(saved).startswith("auto"):
            mon["position"] = saved
            mon["x"], mon["y"] = parse_xy(saved)
            restored = True
    if not restored:
        pack_row(enabled_monitors(model))


def pack_row(mons: list[dict[str, Any]]) -> None:
    x = 0
    for mon in mons:
        w_px, _h = logical_size(mon)
        mon["position"] = format_xy(x, 0)
        mon["x"], mon["y"] = x, 0
        x += w_px


def set_mode(model: dict[str, Any], mode: str) -> None:
    merge_monitors(model, sync_geometry=False)
    proj = ensure_projection(model)
    connected = connected_monitors(model)
    internal = next((m for m in connected if is_internal(str(m.get("output") or ""))), None)
    externals = [m for m in connected if internal is None or m["output"] != internal["output"]]
    if proj.get("mode") == "extend":
        _save_extend_positions(model)
    proj["mode"] = mode

    def enable_only(names: set[str]) -> None:
        for mon in model.get("monitors") or []:
            on = mon.get("output") in names
            mon["enabled"] = on
            if not on:
                mon["mirror"] = ""

    if mode == "internal":
        target = internal or (connected[0] if connected else None)
        if not target:
            return
        enable_only({target["output"]})
        target["mirror"] = ""
        target["position"] = "0x0"
        target["x"], target["y"] = 0, 0
        proj["primary"] = target["output"]
    elif mode == "external":
        if not externals:
            return
        enable_only({m["output"] for m in externals})
        for mon in externals:
            mon["mirror"] = ""
        pack_row(externals)
        if proj.get("primary") not in {m["output"] for m in externals}:
            proj["primary"] = externals[0]["output"]
    elif mode == "duplicate":
        src = proj.get("primary") or (internal["output"] if internal else (connected[0]["output"] if connected else ""))
        if not any(m.get("output") == src for m in connected) and connected:
            src = connected[0]["output"]
        proj["primary"] = src
        for mon in model.get("monitors") or []:
            if not mon.get("connected"):
                mon["enabled"] = False
                mon["mirror"] = ""
                continue
            mon["enabled"] = True
            if mon["output"] == src:
                mon["mirror"] = ""
                mon["position"] = "0x0"
                mon["x"], mon["y"] = 0, 0
            else:
                mon["mirror"] = src
                mon["position"] = "0x0"
                mon["x"], mon["y"] = 0, 0
    else:
        for mon in model.get("monitors") or []:
            mon["mirror"] = ""
            mon["enabled"] = bool(mon.get("connected"))
        _restore_extend_positions(model)
        enabled = enabled_monitors(model)
        if enabled and proj.get("primary") not in {m["output"] for m in enabled}:
            proj["primary"] = enabled[0]["output"]
        proj["mode"] = "extend"

    _refresh_priorities(model)
    apply_layout(model)


def set_primary(model: dict[str, Any], output: str) -> None:
    proj = ensure_projection(model)
    proj["primary"] = output
    _refresh_priorities(model)
    apply_layout(model)


def move_priority(model: dict[str, Any], output: str, delta: int) -> None:
    ranked = [m for m in sorted_by_priority(model) if m.get("enabled", True) and m.get("connected")]
    names = [m["output"] for m in ranked]
    if output not in names:
        return
    idx = names.index(output)
    dest = max(0, min(len(names) - 1, idx + delta))
    if dest == idx:
        return
    names[idx], names[dest] = names[dest], names[idx]
    ensure_projection(model)["primary"] = names[0]
    for i, name in enumerate(names, start=1):
        for mon in model.get("monitors") or []:
            if mon.get("output") == name:
                mon["priority"] = i
    _refresh_priorities(model)
    apply_layout(model)


def snap_monitor(model: dict[str, Any], moving: dict[str, Any]) -> None:
    others = [m for m in enabled_monitors(model) if m is not moving and not m.get("mirror")]
    x, y = parse_xy(moving.get("position"), (int(moving.get("x") or 0), int(moving.get("y") or 0)))
    mw, mh = logical_size(moving)
    best = None
    best_dist = SNAP_PX + 1
    for other in others:
        ox, oy = parse_xy(other.get("position"))
        ow, oh = logical_size(other)
        candidates = [
            (ox + ow, oy),
            (ox - mw, oy),
            (ox, oy + oh),
            (ox, oy - mh),
            (ox + ow, oy + oh - mh),
            (ox - mw, oy + oh - mh),
            (ox + ow - mw, oy + oh),
            (ox + ow - mw, oy - mh),
        ]
        for cx, cy in candidates:
            dist = abs(cx - x) + abs(cy - y)
            if dist < best_dist:
                best_dist = dist
                best = (cx, cy)
        for gx, gy in ((ox, y), (x, oy), (ox + ow - mw, y), (x, oy + oh - mh)):
            dist = abs(gx - x) + abs(gy - y)
            if dist < best_dist:
                best_dist = dist
                best = (gx, gy)
    if best is not None:
        x, y = best
    moving["position"] = format_xy(x, y)
    moving["x"], moving["y"] = x, y
    _save_extend_positions(model)


def monitor_keyword(mon: dict[str, Any]) -> str:
    name = str(mon.get("output") or "")
    if not mon.get("enabled", True):
        return f"{name},disable"
    parts = [name, mode_str(mon), str(mon.get("position") or "auto"), str(_scale_token(mon.get("scale")))]
    transform = int(mon.get("transform") or 0)
    if transform:
        parts.extend(["transform", str(transform)])
    mirror = str(mon.get("mirror") or "")
    if mirror:
        parts.extend(["mirror", mirror])
    if mon.get("vrr"):
        parts.extend(["vrr", "1"])
    return ",".join(parts)


def _scale_token(value: Any) -> str:
    try:
        number = float(value)
        if number == int(number):
            return str(int(number))
        return str(number)
    except (TypeError, ValueError):
        return "1"


def _lua_scale(value: Any) -> str:
    return _scale_token(value)


def monitors_lua(model: dict[str, Any]) -> str:
    blocks: list[str] = []
    for mon in model.get("monitors") or []:
        name = str(mon.get("output") or "")
        if not name:
            continue
        lines = ["hl.monitor({", f'    output   = {configio._lua_str(name)},']
        if not mon.get("enabled", True):
            lines.append("    disabled = true,")
            lines.append("})")
            blocks.append("\n".join(lines))
            continue
        lines.append(f'    mode     = {configio._lua_str(mode_str(mon))},')
        lines.append(f'    position = {configio._lua_str(str(mon.get("position") or "auto"))},')
        lines.append(f"    scale    = {_lua_scale(mon.get('scale'))},")
        transform = int(mon.get("transform") or 0)
        if transform:
            lines.append(f"    transform = {transform},")
        mirror = str(mon.get("mirror") or "")
        if mirror:
            lines.append(f"    mirror   = {configio._lua_str(mirror)},")
        if mon.get("vrr"):
            lines.append("    vrr      = 1,")
        lines.append("})")
        blocks.append("\n".join(lines))
    if blocks:
        return "\n".join(blocks)
    return "\n".join(
        [
            "hl.monitor({",
            '    output   = "",',
            '    mode     = "preferred",',
            '    position = "auto",',
            "    scale    = 1,",
            "})",
        ]
    )


def apply_layout(model: dict[str, Any]) -> None:
    if not _acquire_lock():
        return
    ensure_projection(model)
    _refresh_priorities(model)
    mons = list(model.get("monitors") or [])
    enabling = [m for m in mons if m.get("enabled", True)]
    disabling = [m for m in mons if not m.get("enabled", True)]
    if not enabling:
        return
    for mon in enabling:
        configio.hyprctl("keyword", "monitor", monitor_keyword(mon))
    for mon in disabling:
        if mon.get("connected"):
            configio.hyprctl("keyword", "monitor", monitor_keyword(mon))
    primary = ensure_projection(model).get("primary") or ""
    if primary:
        configio.hyprctl("keyword", "cursor:default_monitor", primary)


def persist_layout(model: dict[str, Any]) -> None:
    apply_layout(model)
    configio.save_state(model)
    configio.LUA_PATH.parent.mkdir(parents=True, exist_ok=True)
    configio.LUA_PATH.write_text(configio.generate_lua(model), encoding="utf-8")
    configio.CONF_MIRROR.parent.mkdir(parents=True, exist_ok=True)
    configio.CONF_MIRROR.write_text(configio.generate_conf_mirror(model), encoding="utf-8")


def apply_from_state() -> int:
    if not _acquire_lock():
        return 0
    if not configio.STATE_PATH.exists():
        return 0
    try:
        model = json.loads(configio.STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return 0
    merge_monitors(model, sync_geometry=False)
    apply_layout(model)
    return 0


def _acquire_lock() -> bool:
    now = time.time()
    try:
        if LOCK_PATH.exists() and now - LOCK_PATH.stat().st_mtime < 1.2:
            return False
        LOCK_PATH.write_text(str(now), encoding="utf-8")
    except OSError:
        return True
    return True


def inches(mon: dict[str, Any]) -> str:
    pw = float(mon.get("physicalWidth") or 0)
    ph = float(mon.get("physicalHeight") or 0)
    if pw <= 0 or ph <= 0:
        return "—"
    diag = (pw * pw + ph * ph) ** 0.5 / 25.4
    return f"{diag:.1f}\""


def resolution_label(mon: dict[str, Any]) -> str:
    w_px = int(mon.get("width") or 0)
    h_px = int(mon.get("height") or 0)
    mw, mh, _ = parse_mode(str(mon.get("mode") or ""))
    w_px = w_px or mw or 0
    h_px = h_px or mh or 0
    if not w_px or not h_px:
        return str(mon.get("mode") or "preferred")
    rate = mon.get("refreshRate")
    if isinstance(rate, (int, float)) and rate:
        return f"{w_px} × {h_px} @ {rate:.0f} Hz"
    return f"{w_px} × {h_px}"


def scale_label(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 1.0
    pct = int(round(number * 100))
    return f"{pct}%"


def match_gdk_monitor(output: str, mon: dict[str, Any]) -> Gdk.Monitor | None:
    display = Gdk.Display.get_default()
    if display is None:
        return None
    monitors = display.get_monitors()
    geo = None
    for i in range(monitors.get_n_items()):
        item = monitors.get_item(i)
        connector = ""
        for attr in ("get_connector", "get_description", "get_model"):
            getter = getattr(item, attr, None)
            if getter:
                try:
                    connector = str(getter() or "")
                except Exception:
                    connector = ""
            if output and output in connector:
                return item
        rect = item.get_geometry()
        if int(mon.get("x") or 0) == rect.x and int(mon.get("y") or 0) == rect.y:
            geo = item
    return geo


class IdentifyOverlay(Gtk.Window):
    def __init__(self, number: int, mon: dict[str, Any]) -> None:
        super().__init__(title=f"Display {number}")
        self.add_css_class("hyprpanel")
        self.add_css_class("hp-identify")
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_default_size(240, 240)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)
        box.set_margin_start(24)
        box.set_margin_end(24)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        num = Gtk.Label(label=str(number))
        num.add_css_class("hp-identify-number")
        name = Gtk.Label(label=friendly_name(mon))
        name.add_css_class("hp-identify-name")
        out = Gtk.Label(label=str(mon.get("output") or ""))
        out.add_css_class("dim")
        box.append(num)
        box.append(name)
        box.append(out)
        self.set_child(box)


def identify_displays(model: dict[str, Any], parent: Gtk.Window | None = None) -> None:
    overlays: list[IdentifyOverlay] = []
    for mon in sorted_by_priority(model):
        if not (mon.get("connected") and mon.get("enabled", True)):
            continue
        number = int(mon.get("priority") or len(overlays) + 1)
        overlay = IdentifyOverlay(number, mon)
        if parent is not None:
            overlay.set_transient_for(parent)
        overlay.present()
        gdk_mon = match_gdk_monitor(str(mon.get("output") or ""), mon)
        if gdk_mon is not None:
            try:
                overlay.fullscreen_on_monitor(gdk_mon)
            except Exception:
                pass
        overlays.append(overlay)

    def hide() -> bool:
        for overlay in overlays:
            overlay.close()
        return False

    if overlays:
        GLib.timeout_add(2600, hide)


def _hex_rgb(hex_color: str) -> tuple[float, float, float]:
    h = hex_color.lstrip("#")[:6]
    if len(h) < 6:
        h = "88d0ed"
    return int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255


class MonitorCanvas(Gtk.DrawingArea):
    def __init__(
        self,
        get_model: Callable[[], dict[str, Any]],
        get_selected: Callable[[], str],
        on_select: Callable[[str], None],
        on_moved: Callable[[], None],
    ) -> None:
        super().__init__()
        self.add_css_class("hp-proj-canvas")
        self.set_hexpand(True)
        self.set_content_height(210)
        self.set_draw_func(self._draw)
        self._get_model = get_model
        self._get_selected = get_selected
        self._on_select = on_select
        self._on_moved = on_moved
        self._rects: list[tuple[str, float, float, float, float]] = []
        self._view = (1.0, 0.0, 0.0)
        self._drag_name = ""
        self._drag_origin = (0, 0)
        self.dragging = False
        click = Gtk.GestureClick()
        click.connect("pressed", self._pressed)
        self.add_controller(click)
        drag = Gtk.GestureDrag()
        drag.connect("drag-begin", self._drag_begin)
        drag.connect("drag-update", self._drag_update)
        drag.connect("drag-end", self._drag_end)
        self.add_controller(drag)

    def _visible(self) -> list[dict[str, Any]]:
        model = self._get_model()
        if ensure_projection(model).get("mode") == "duplicate":
            primary = ensure_projection(model).get("primary")
            mons = [m for m in enabled_monitors(model) if m.get("output") == primary] or enabled_monitors(model)[:1]
            return mons
        return [m for m in enabled_monitors(model) if not m.get("mirror")]

    def _layout_view(self, width: float, height: float) -> tuple[float, float, float, list[dict[str, Any]]]:
        mons = self._visible()
        if not mons:
            return 0.12, 40.0, 40.0, []
        min_x = min(parse_xy(m.get("position"))[0] for m in mons)
        min_y = min(parse_xy(m.get("position"))[1] for m in mons)
        max_x = max(parse_xy(m.get("position"))[0] + logical_size(m)[0] for m in mons)
        max_y = max(parse_xy(m.get("position"))[1] + logical_size(m)[1] for m in mons)
        box_w = max(1, max_x - min_x)
        box_h = max(1, max_y - min_y)
        pad = 36.0
        scale = min((width - pad * 2) / box_w, (height - pad * 2) / box_h)
        scale = max(0.04, min(scale, 0.28))
        ox = (width - box_w * scale) / 2 - min_x * scale
        oy = (height - box_h * scale) / 2 - min_y * scale
        return scale, ox, oy, mons

    def _draw(self, _area, cr, width: int, height: int) -> None:
        colors = theme.load_colors()
        cr.set_source_rgb(*_hex_rgb(colors.get("crust", "#0f1416")))
        cr.rectangle(0, 0, width, height)
        cr.fill()
        scale, ox, oy, mons = self._layout_view(width, height)
        self._view = (scale, ox, oy)
        self._rects = []
        selected = self._get_selected()
        primary = ensure_projection(self._get_model()).get("primary")
        if not mons:
            cr.set_source_rgb(*_hex_rgb(colors.get("subtext0", "#bfc8cc")))
            cr.set_font_size(13)
            msg = "Connect a display to arrange it here"
            _xb, _yb, tw, _th, _, _ = cr.text_extents(msg)
            cr.move_to((width - tw) / 2, height / 2)
            cr.show_text(msg)
            return
        for mon in mons:
            x, y = parse_xy(mon.get("position"))
            lw, lh = logical_size(mon)
            rx, ry, rw, rh = x * scale + ox, y * scale + oy, lw * scale, lh * scale
            self._rects.append((str(mon.get("output") or ""), rx, ry, rw, rh))
            active = mon.get("output") == selected
            fill = colors.get("surface1", "#252b2d") if not active else colors.get("surface2", "#303638")
            cr.set_source_rgb(*_hex_rgb(fill))
            _round_rect(cr, rx, ry, rw, rh, 8)
            cr.fill()
            border = colors.get("mauve", "#88d0ed") if active else colors.get("surface2", "#303638")
            cr.set_source_rgb(*_hex_rgb(border))
            cr.set_line_width(3 if active else 1.2)
            _round_rect(cr, rx, ry, rw, rh, 8)
            cr.stroke()
            cr.set_source_rgb(*_hex_rgb(colors.get("text", "#dee3e6")))
            cr.select_font_face("Adwaita Sans", 0, 1)
            number = str(int(mon.get("priority") or 1))
            cr.set_font_size(min(48, max(22, rh * 0.42)))
            _xb, _yb, tw, th, _, _ = cr.text_extents(number)
            cr.move_to(rx + (rw - tw) / 2, ry + (rh + th) / 2 - 6)
            cr.show_text(number)
            cr.set_font_size(11)
            label = friendly_name(mon)
            _xb, _yb, tw, th, _, _ = cr.text_extents(label)
            cr.set_source_rgb(*_hex_rgb(colors.get("subtext0", "#bfc8cc")))
            cr.move_to(rx + (rw - tw) / 2, ry + rh + 16)
            cr.show_text(label)
            if mon.get("output") == primary:
                cr.set_source_rgb(*_hex_rgb(colors.get("mauve", "#88d0ed")))
                tag = "MAIN"
                cr.set_font_size(9)
                _xb, _yb, tw, th, _, _ = cr.text_extents(tag)
                cr.move_to(rx + 10, ry + 16)
                cr.show_text(tag)

    def _hit(self, x: float, y: float) -> str:
        for name, rx, ry, rw, rh in reversed(self._rects):
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                return name
        return ""

    def _pressed(self, _g, _n, x: float, y: float) -> None:
        name = self._hit(x, y)
        if name:
            self._on_select(name)

    def _drag_begin(self, _g, x: float, y: float) -> None:
        model = self._get_model()
        if ensure_projection(model).get("mode") != "extend":
            return
        name = self._hit(x, y)
        if not name:
            return
        mon = next((m for m in model.get("monitors") or [] if m.get("output") == name), None)
        if not mon:
            return
        self._drag_name = name
        self._drag_origin = parse_xy(mon.get("position"))
        self.dragging = True
        self._on_select(name)

    def _drag_update(self, _g, dx: float, dy: float) -> None:
        if not self.dragging or not self._drag_name:
            return
        scale = self._view[0] or 0.12
        ox, oy = self._drag_origin
        nx = int(round(ox + dx / scale))
        ny = int(round(oy + dy / scale))
        model = self._get_model()
        mon = next((m for m in model.get("monitors") or [] if m.get("output") == self._drag_name), None)
        if not mon:
            return
        mon["position"] = format_xy(nx, ny)
        mon["x"], mon["y"] = nx, ny
        self.queue_draw()

    def _drag_end(self, *_args) -> None:
        if not self.dragging or not self._drag_name:
            self.dragging = False
            return
        model = self._get_model()
        mon = next((m for m in model.get("monitors") or [] if m.get("output") == self._drag_name), None)
        self.dragging = False
        self._drag_name = ""
        if not mon:
            return
        snap_monitor(model, mon)
        _refresh_priorities(model)
        self.queue_draw()
        self._on_moved()


def _round_rect(cr, x, y, w, h, r) -> None:
    r = max(0, min(r, w / 2, h / 2))
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -1.57, 0)
    cr.arc(x + w - r, y + h - r, r, 0, 1.57)
    cr.arc(x + r, y + h - r, r, 1.57, 3.14)
    cr.arc(x + r, y + r, r, 3.14, 4.71)
    cr.close_path()


class ProjectionPicker(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application) -> None:
        super().__init__(application=app, title="Project displays")
        self.add_css_class("hyprpanel")
        self.add_css_class("hp-picker")
        self.set_default_size(760, 250)
        self.set_resizable(False)
        theme.install_css()
        self.model = configio.load_model()
        merge_monitors(self.model, sync_geometry=True)
        ensure_projection(self.model)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_margin_start(22)
        box.set_margin_end(22)
        box.set_margin_top(18)
        box.set_margin_bottom(18)
        box.append(w.text("Project", "hp-section-title"))
        box.append(w.text("Choose how this PC uses extra displays. Super + P", "hp-section-desc"))
        row = Gtk.Box(spacing=10)
        row.set_homogeneous(True)
        connected = len(connected_monitors(self.model))
        current = ensure_projection(self.model).get("mode") or "extend"
        for key, icon, title, desc in MODES:
            btn = Gtk.Button()
            btn.add_css_class("hp-proj-tile")
            if key == current:
                btn.add_css_class("active")
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            inner.set_halign(Gtk.Align.CENTER)
            inner.set_margin_top(8)
            inner.set_margin_bottom(8)
            inner.append(w.icon_label(icon, 22, "hp-icon-lg"))
            inner.append(w.text(title))
            hint = w.text(desc, "dim")
            hint.set_wrap(True)
            hint.set_justify(Gtk.Justification.CENTER)
            inner.append(hint)
            btn.set_child(inner)
            available = connected >= 2 or key in {"internal", "extend"}
            if key == "external" and connected < 2:
                available = False
            if key == "duplicate" and connected < 2:
                available = False
            btn.set_sensitive(available)
            btn.connect("clicked", lambda _b, mode=key: self._pick(mode))
            row.append(btn)
        box.append(row)
        extra = Gtk.Box(spacing=8)
        extra.set_halign(Gtk.Align.END)
        settings = w.button("Display settings", "hp-btn")
        settings.connect("clicked", self._open_settings)
        extra.append(settings)
        box.append(extra)
        self.set_child(box)
        esc = Gtk.EventControllerKey()
        esc.connect("key-pressed", self._on_key)
        self.add_controller(esc)

    def _on_key(self, _c, keyval, _code, _state) -> bool:
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False

    def _pick(self, mode: str) -> None:
        set_mode(self.model, mode)
        persist_layout(self.model)
        self.close()

    def _open_settings(self, *_args) -> None:
        self.close()
        subprocess_open_panel()


def subprocess_open_panel() -> None:
    from subprocess import Popen

    cmd = configio.panel_command()
    Popen([cmd, "--page", "projection"], start_new_session=True)


def fill_projection_page(window: Any, box: Gtk.Box) -> None:
    """Build the full Display / Projection settings page onto `box`."""
    merge_monitors(window.model, sync_geometry=True)
    ensure_projection(window.model)
    window._proj_selected = ensure_projection(window.model).get("primary") or (
        (window.model.get("monitors") or [{}])[0].get("output") or ""
    )

    box.append(w.section_header(
        "Project to a connected display",
        "Arrange screens, set the main display, then choose PC screen only, Duplicate, Extend, or Second screen only. Super + P opens the quick picker.",
    ))

    window._proj_mode_row = Gtk.Box(spacing=10)
    window._proj_mode_row.set_homogeneous(True)
    window._proj_mode_buttons: dict[str, Gtk.Button] = {}
    box.append(window._proj_mode_row)

    canvas_wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    canvas_wrap.add_css_class("hp-card")
    head, controls = w.settings_row("Rearrange your displays", "Drag a display to move it. Numbers are display priority.", "󰍹")
    identify = w.button("Identify", "hp-btn hp-btn-blue")
    identify.connect("clicked", lambda *_: identify_displays(window.model, window))
    detect = w.button("Detect", "hp-btn")
    detect.connect("clicked", lambda *_: window._proj_detect())
    controls.append(identify)
    controls.append(detect)
    canvas_wrap.append(head)
    window._proj_canvas = MonitorCanvas(
        get_model=lambda: window.model,
        get_selected=lambda: window._proj_selected,
        on_select=lambda name: window._proj_select(name),
        on_moved=lambda: window._proj_moved(),
    )
    window._proj_canvas.set_margin_start(10)
    window._proj_canvas.set_margin_end(10)
    canvas_wrap.append(window._proj_canvas)
    hint = w.text("Drag only works in Extend. Duplicate stacks every screen on the main display.", "dim")
    hint.set_margin_start(12)
    hint.set_margin_bottom(10)
    hint.set_wrap(True)
    canvas_wrap.append(hint)
    box.append(canvas_wrap)

    window._proj_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    box.append(window._proj_list)

    window._proj_details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    box.append(window._proj_details)

    window._rebuild_projection()
    if not getattr(window, "_proj_poll", 0):
        window._proj_poll = GLib.timeout_add_seconds(2, window._proj_tick)
