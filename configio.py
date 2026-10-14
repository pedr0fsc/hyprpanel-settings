"""Read/write Hyprland lua + hyprlock/hypridle configs from a JSON model."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from theme import hex_to_rgba, load_colors, load_theme_meta, list_presets

HOME = Path.home()
HYPR_DIR = HOME / ".config" / "hypr"
STATE_PATH = HYPR_DIR / "hyprpanel" / "state.json"
LUA_PATH = HYPR_DIR / "hyprland.lua"
CONF_MIRROR = HYPR_DIR / "hyprpanel" / "hyprland.conf"
LOCK_PATH = HYPR_DIR / "hyprlock.conf"
IDLE_PATH = HYPR_DIR / "hypridle.conf"
BACKUP_DIR = HYPR_DIR / "backups"
SERP_SETTINGS = HOME / ".config" / "serpantinum" / "settings.json"


def panel_command() -> str:
    return (
        shutil.which("hyprpanel-settings")
        or shutil.which("hyprpanel")
        or str(HOME / ".local" / "bin" / "hyprpanel")
    )


def launcher_bin() -> str:
    found = shutil.which("hypr-launcher")
    if found:
        return found
    local = HOME / ".local" / "bin" / "hypr-launcher"
    return str(local)


PANEL_BIN = panel_command()
LAUNCHER_BIN = Path(launcher_bin())


def _now() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _lua_str(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _bool(v: Any) -> str:
    return "true" if v else "false"


def which_first(*names: str) -> str:
    for name in names:
        path = shutil.which(name)
        if path:
            return path
    return names[0]


def detect_file_manager() -> str:
    return which_first("nautilus", "thunar", "nemo", "pcmanfm-qt", "dolphin", "xdg-open")


def detect_task_manager() -> str:
    if shutil.which("gnome-system-monitor"):
        return "gnome-system-monitor"
    term = which_first("kitty", "alacritty", "foot")
    for tool in ("btop", "htop", "top"):
        if shutil.which(tool):
            return f"{term} -e {tool}"
    return f"{term} -e top"


def detect_launcher() -> str:
    # Serpantinum's IPC often returns success without showing a window.
    # Prefer wofi, which is installed and working on this machine.
    if shutil.which("wofi"):
        return "wofi --show drun"
    if LAUNCHER_BIN.exists():
        return str(LAUNCHER_BIN)
    return "serpantinum msg toggle launcher"


def detect_lock() -> str:
    if shutil.which("serpantinum"):
        return "serpantinum lock"
    return "hyprlock"


def default_model() -> dict[str, Any]:
    colors = load_colors()
    meta = load_theme_meta()
    mauve = colors.get("mauve", "#88d0ed")
    blue = colors.get("blue", "#88d0ed")
    surface2 = colors.get("surface2", "#303638")
    crust = colors.get("crust", "#0f1416")
    text = colors.get("text", "#dee3e6")
    red = colors.get("red", "#ffb4ab")
    green = colors.get("green", "#b3cad5")
    base = colors.get("base", "#0a0f11")

    return {
        "mainMod": "SUPER",
        "programs": {
            "terminal": which_first("kitty", "alacritty", "foot"),
            "fileManager": detect_file_manager(),
            "menu": detect_launcher(),
        },
        "appearance": {
            "gaps_in": 5,
            "gaps_out": 20,
            "border_size": 2,
            "active_border": [hex_to_rgba(mauve, 0.93), hex_to_rgba(blue, 0.81)],
            "active_border_angle": 45,
            "inactive_border": hex_to_rgba(surface2, 0.67),
            "resize_on_border": False,
            "allow_tearing": False,
            "layout": "dwindle",
            "rounding": int(meta.get("borderRadius") or 10),
            "rounding_power": 2.0,
            "active_opacity": 1.0,
            "inactive_opacity": 1.0,
            "shadow_enabled": True,
            "shadow_range": 4,
            "shadow_render_power": 3,
            "shadow_color": "0xee1a1a1a",
            "blur_enabled": True,
            "blur_size": 3,
            "blur_passes": 1,
            "blur_vibrancy": 0.1696,
            "animations_enabled": True,
            "disable_hyprland_logo": False,
            "force_default_wallpaper": -1,
        },
        "input": {
            "kb_layout": "br",
            "kb_variant": "abnt2",
            "kb_model": "",
            "kb_options": "",
            "follow_mouse": 1,
            "sensitivity": 0.0,
            "natural_scroll": True,
            "xcursor_size": 24,
            "hyprcursor_size": 24,
        },
        "monitor": {
            "output": "eDP-1",
            "mode": "preferred",
            "position": "auto",
            "scale": 1,
        },
        "monitors": [],
        "autostart": [
            "setsid serpantinumd start >/dev/null 2>&1 &",
            "wl-paste --type text --watch cliphist store",
            "wl-paste --type image --watch cliphist store",
        ],
        "lock": {
            "engine": "serpantinum",
            "command": "serpantinum lock",
            "hide_cursor": False,
            "grace": 0,
            "ignore_empty_input": False,
            "background": "screenshot",
            "wallpaper": "",
            "blur_passes": 3,
            "font": meta.get("fontFamily") or "Adwaita Mono",
            "clock_size": 90,
            "date_size": 22,
            "date_format": "%A, %d %B %Y",
            "inner_color": hex_to_rgba(base, 0.35),
            "outer_color": hex_to_rgba(mauve, 0.93),
            "check_color": hex_to_rgba(green, 0.93),
            "fail_color": hex_to_rgba(red, 0.93),
            "font_color": hex_to_rgba(text, 1.0),
            "placeholder": "type password",
            "rounding": int(meta.get("borderRadius") or 8),
            "outline_thickness": 2,
            "show_date": True,
            "show_clock": True,
        },
        "idle": {
            "lock_cmd": "serpantinum lock",
        },
        "binds": default_binds(),
        "extra_lua": "",
        "sync_rounding_with_serpantinum": True,
    }


def default_binds() -> list[dict[str, Any]]:
    fm = detect_file_manager()
    launch = detect_launcher()
    lock = detect_lock()
    task = detect_task_manager()
    term = which_first("kitty", "alacritty", "foot")
    binds: list[dict[str, Any]] = [
        bind("apps", "Open terminal", ["SUPER"], "RETURN", "exec", term),
        bind("apps", "App launcher", ["SUPER"], "SPACE", "exec", launch),
        bind("apps", "File manager", ["SUPER"], "E", "exec", fm),
        bind("apps", "Hyprpanel settings", ["SUPER"], "comma", "exec", str(PANEL_BIN)),
        bind("windows", "Close window", ["SUPER"], "Q", "close", ""),
        bind("windows", "Fullscreen", ["SUPER"], "F", "fullscreen", ""),
        bind("windows", "Toggle floating", ["SUPER"], "V", "float", ""),
        bind("windows", "Toggle split", ["SUPER"], "J", "layout", "togglesplit"),
        bind("system", "Show desktop", ["SUPER"], "D", "exec", "hyprctl dispatch togglespecialworkspace desktop"),
        bind("system", "Task manager", ["CTRL", "SHIFT"], "Escape", "exec", task),
        bind("system", "Lock screen", ["SUPER"], "L", "exec", lock),
        bind("system", "Lock screen (Shift)", ["SUPER", "SHIFT"], "L", "exec", lock),
        bind("system", "Exit Hyprland", ["SUPER"], "M", "exit", ""),
        bind("focus", "Focus left", ["SUPER"], "left", "focus", "left"),
        bind("focus", "Focus right", ["SUPER"], "right", "focus", "right"),
        bind("focus", "Focus up", ["SUPER"], "up", "focus", "up"),
        bind("focus", "Focus down", ["SUPER"], "down", "focus", "down"),
        bind("windows", "Resize left", ["SUPER", "CTRL"], "left", "resize_delta", "-40 0", repeating=True),
        bind("windows", "Resize right", ["SUPER", "CTRL"], "right", "resize_delta", "40 0", repeating=True),
        bind("windows", "Resize up", ["SUPER", "CTRL"], "up", "resize_delta", "0 -40", repeating=True),
        bind("windows", "Resize down", ["SUPER", "CTRL"], "down", "resize_delta", "0 40", repeating=True),
        bind("windows", "Resize left (J)", ["SUPER", "CTRL"], "J", "resize_delta", "-40 0", repeating=True),
        bind("windows", "Resize down (K)", ["SUPER", "CTRL"], "K", "resize_delta", "0 40", repeating=True),
        bind("windows", "Resize up (I)", ["SUPER", "CTRL"], "I", "resize_delta", "0 -40", repeating=True),
        bind("windows", "Resize right (L)", ["SUPER", "CTRL"], "L", "resize_delta", "40 0", repeating=True),
        bind("mouse", "Move window", ["SUPER"], "mouse:272", "drag", "", mouse=True),
        bind("mouse", "Resize window", ["SUPER"], "mouse:273", "resize", "", mouse=True),
        bind("media", "Volume up", [], "XF86AudioRaiseVolume", "exec", "wpctl set-volume -l 1 @DEFAULT_AUDIO_SINK@ 5%+", locked=True, repeating=True),
        bind("media", "Volume down", [], "XF86AudioLowerVolume", "exec", "wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-", locked=True, repeating=True),
        bind("media", "Mute", [], "XF86AudioMute", "exec", "wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle", locked=True, repeating=True),
        bind("media", "Mic mute", [], "XF86AudioMicMute", "exec", "wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle", locked=True, repeating=True),
        bind("media", "Brightness up", [], "XF86MonBrightnessUp", "exec", "brightnessctl -e4 -n2 set 5%+", locked=True, repeating=True),
        bind("media", "Brightness down", [], "XF86MonBrightnessDown", "exec", "brightnessctl -e4 -n2 set 5%-", locked=True, repeating=True),
        bind("media", "Next track", [], "XF86AudioNext", "exec", "playerctl next", locked=True),
        bind("media", "Play / pause", [], "XF86AudioPause", "exec", "playerctl play-pause", locked=True),
        bind("media", "Play / pause (play key)", [], "XF86AudioPlay", "exec", "playerctl play-pause", locked=True),
        bind("media", "Previous track", [], "XF86AudioPrev", "exec", "playerctl previous", locked=True),
    ]
    for i in range(1, 11):
        key = str(i % 10)
        binds.append(bind("workspaces", f"Workspace {i}", ["SUPER"], key, "workspace", str(i)))
        binds.append(bind("workspaces", f"Move to workspace {i}", ["SUPER", "SHIFT"], key, "movetoworkspace", str(i)))
    return binds


def bind(
    category: str,
    description: str,
    mods: list[str],
    key: str,
    kind: str,
    arg: str,
    *,
    mouse: bool = False,
    locked: bool = False,
    repeating: bool = False,
    enabled: bool = True,
) -> dict[str, Any]:
    return {
        "id": f"{category}:{description}:{'+'.join(mods)}-{key}",
        "category": category,
        "description": description,
        "mods": mods,
        "key": key,
        "kind": kind,
        "arg": arg,
        "mouse": mouse,
        "locked": locked,
        "repeating": repeating,
        "enabled": enabled,
    }


def load_model() -> dict[str, Any]:
    model = default_model()
    if STATE_PATH.exists():
        try:
            saved = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            model = _deep_merge(model, saved)
        except Exception:
            pass
    else:
        parsed = parse_existing_lua()
        if parsed:
            model = _deep_merge(model, parsed)
        parsed_lock = parse_existing_lock()
        if parsed_lock:
            model["lock"] = _deep_merge(model["lock"], parsed_lock)
    _ensure_panel_bind(model)
    migrate_model(model)
    refresh_monitors(model)
    return model


def _find_bind(binds: list[dict[str, Any]], mods: list[str], key: str) -> dict[str, Any] | None:
    want = [m.upper() for m in mods]
    for item in binds:
        have = [str(m).upper() for m in (item.get("mods") or [])]
        if have == want and str(item.get("key") or "") == key:
            return item
    return None


def _upsert_bind(binds: list[dict[str, Any]], item: dict[str, Any]) -> None:
    existing = _find_bind(binds, item.get("mods") or [], item.get("key") or "")
    if existing:
        existing.update({k: item[k] for k in ("description", "kind", "arg", "category", "repeating", "locked", "mouse", "enabled") if k in item})
        return
    binds.append(item)


def migrate_model(model: dict[str, Any]) -> None:
    programs = model.setdefault("programs", {})
    fm = detect_file_manager()
    launch = detect_launcher()
    lock = detect_lock()
    task = detect_task_manager()
    programs["fileManager"] = fm if "dolphin" in str(programs.get("fileManager") or "") or not programs.get("fileManager") else programs["fileManager"]
    if not shutil.which(str(programs.get("fileManager") or "").split()[0]):
        programs["fileManager"] = fm
    if "serpantinumd toggle" in str(programs.get("menu") or "") or not programs.get("menu"):
        programs["menu"] = launch
    binds = model.setdefault("binds", [])

    for item in binds:
        arg = str(item.get("arg") or "")
        desc = str(item.get("description") or "").lower()
        key = str(item.get("key") or "")
        mods = [str(m).upper() for m in (item.get("mods") or [])]
        if arg == "dolphin" or (item.get("kind") == "exec" and "file" in desc and "dolphin" in arg):
            item["arg"] = programs["fileManager"]
            item["description"] = "File manager"
        if "btop" in arg:
            item["arg"] = task
        if "serpantinumd lock" in arg or arg == "serpantinumd lock":
            item["arg"] = lock
        if mods == ["SUPER"] and key == "L" and ("wofi" in arg or "launcher" in arg):
            item["mods"] = ["SUPER"]
            item["key"] = "SPACE"
            item["arg"] = launch
            item["description"] = "App launcher"
            item["kind"] = "exec"
            item["category"] = "apps"

    _upsert_bind(binds, bind("apps", "File manager", ["SUPER"], "E", "exec", programs["fileManager"]))
    _upsert_bind(binds, bind("apps", "App launcher", ["SUPER"], "SPACE", "exec", launch))
    _upsert_bind(binds, bind("system", "Lock screen", ["SUPER"], "L", "exec", lock))
    _upsert_bind(binds, bind("system", "Task manager", ["CTRL", "SHIFT"], "Escape", "exec", task))
    for desc, key, delta in (
        ("Resize left", "left", "-40 0"),
        ("Resize right", "right", "40 0"),
        ("Resize up", "up", "0 -40"),
        ("Resize down", "down", "0 40"),
        ("Resize left (J)", "J", "-40 0"),
        ("Resize down (K)", "K", "0 40"),
        ("Resize up (I)", "I", "0 -40"),
        ("Resize right (L)", "L", "40 0"),
    ):
        _upsert_bind(binds, bind("windows", desc, ["SUPER", "CTRL"], key, "resize_delta", delta, repeating=True))

    model["lock"]["command"] = lock
    model["idle"]["lock_cmd"] = lock
    model["hyprpanel_migrate"] = 2


def serpantinum_monitor_scales() -> dict[str, float]:
    try:
        data = json.loads(SERP_SETTINGS.read_text(encoding="utf-8"))
        monitors = ((data.get("display") or {}).get("monitors") or {})
        out: dict[str, float] = {}
        for name, info in monitors.items():
            if isinstance(info, dict) and info.get("scale") is not None:
                out[name] = float(info["scale"])
        return out
    except Exception:
        return {}


def restore_serpantinum_scales(scales: dict[str, float]) -> None:
    if not scales or not SERP_SETTINGS.exists():
        return
    try:
        data = json.loads(SERP_SETTINGS.read_text(encoding="utf-8"))
        display = data.setdefault("display", {})
        monitors = display.setdefault("monitors", {})
        changed = False
        for name, scale in scales.items():
            cur = monitors.setdefault(name, {})
            if cur.get("scale") != scale:
                cur["scale"] = scale
                changed = True
        if changed:
            SERP_SETTINGS.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except Exception:
        pass


def refresh_monitors(model: dict[str, Any]) -> None:
    scales = serpantinum_monitor_scales()
    live: list[dict[str, Any]] = []
    try:
        data = json.loads(hyprctl("monitors", "-j").stdout or "[]")
        for mon in data:
            name = mon.get("name") or ""
            scale = scales.get(name, mon.get("scale") or 1)
            if str(scale) == "auto":
                scale = scales.get(name, 1)
            live.append(
                {
                    "output": name,
                    "mode": "preferred",
                    "position": "auto",
                    "scale": scale,
                }
            )
    except Exception:
        live = []
    if not live:
        saved = model.get("monitors") or []
        if saved:
            live = saved
        else:
            mon = model.get("monitor") or {"output": "eDP-1", "mode": "preferred", "position": "auto", "scale": 1}
            if mon.get("scale") in (None, "", "auto"):
                mon["scale"] = scales.get(mon.get("output") or "eDP-1", 1)
            live = [mon]
    for mon in live:
        name = mon.get("output") or ""
        if name in scales:
            mon["scale"] = scales[name]
        if mon.get("scale") in (None, "", "auto"):
            mon["scale"] = 1
    model["monitors"] = live
    model["monitor"] = live[0]


def _lua_scale(value: Any) -> str:
    if value in (None, "", "auto"):
        return "1"
    try:
        number = float(value)
        if number == int(number):
            return str(int(number))
        return str(number)
    except (TypeError, ValueError):
        return "1"


def generate_monitors_lua(model: dict[str, Any]) -> str:
    mons = model.get("monitors") or [model.get("monitor") or {}]
    blocks = []
    for mon in mons:
        blocks.append(
            "\n".join(
                [
                    "hl.monitor({",
                    f'    output   = {_lua_str(mon.get("output") or "")},',
                    f'    mode     = {_lua_str(str(mon.get("mode") or "preferred"))},',
                    f'    position = {_lua_str(str(mon.get("position") or "auto"))},',
                    f"    scale    = {_lua_scale(mon.get('scale'))},",
                    "})",
                ]
            )
        )
    return "\n".join(blocks)


def apply_monitor_scales(model: dict[str, Any]) -> None:
    for mon in model.get("monitors") or [model.get("monitor") or {}]:
        name = mon.get("output") or ""
        if not name:
            continue
        scale = _lua_scale(mon.get("scale"))
        mode = mon.get("mode") or "preferred"
        lua = f'hl.monitor({{ output = "{name}", mode = "{mode}", position = "auto", scale = {scale} }})'
        hyprctl("eval", lua)
        hyprctl("keyword", "monitor", f"{name},{mode},auto,{scale}")


def save_state(model: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(model, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(base)
    for key, value in overlay.items():
        if key == "binds" and isinstance(value, list) and value:
            out[key] = value
            continue
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = deepcopy(value)
    return out


def _ensure_panel_bind(model: dict[str, Any]) -> None:
    binds = model.setdefault("binds", [])
    for item in binds:
        if "hyprpanel" in (item.get("arg") or "") or "Hyprpanel" in (item.get("description") or ""):
            item["arg"] = str(PANEL_BIN)
            return
    binds.insert(
        3,
        bind("apps", "Hyprpanel settings", ["SUPER"], "comma", "exec", str(PANEL_BIN)),
    )


def parse_existing_lua() -> dict[str, Any]:
    if not LUA_PATH.exists():
        return {}
    text = LUA_PATH.read_text(encoding="utf-8")
    out: dict[str, Any] = {"appearance": {}, "input": {}, "programs": {}, "autostart": []}

    def grab_int(key: str) -> int | None:
        m = re.search(rf"{key}\s*=\s*(-?\d+)", text)
        return int(m.group(1)) if m else None

    def grab_float(key: str) -> float | None:
        m = re.search(rf"{key}\s*=\s*(-?\d+(?:\.\d+)?)", text)
        return float(m.group(1)) if m else None

    def grab_bool(key: str) -> bool | None:
        m = re.search(rf"{key}\s*=\s*(true|false)", text)
        return m.group(1) == "true" if m else None

    def grab_str(key: str) -> str | None:
        m = re.search(rf'{key}\s*=\s*"([^"]*)"', text)
        return m.group(1) if m else None

    app = out["appearance"]
    for key in ("gaps_in", "gaps_out", "border_size", "rounding"):
        v = grab_int(key)
        if v is not None:
            app[key] = v
    for key in ("rounding_power", "active_opacity", "inactive_opacity", "blur_vibrancy"):
        v = grab_float(key)
        if v is not None:
            app[key] = v
    mapping = {
        "resize_on_border": "resize_on_border",
        "allow_tearing": "allow_tearing",
        "disable_hyprland_logo": "disable_hyprland_logo",
        "natural_scroll": None,
    }
    for key in ("resize_on_border", "allow_tearing", "disable_hyprland_logo"):
        v = grab_bool(key)
        if v is not None:
            app[key] = v
    layout = grab_str("layout")
    if layout:
        app["layout"] = layout

    active = re.search(
        r"active_border\s*=\s*\{\s*colors\s*=\s*\{([^}]+)\}\s*,\s*angle\s*=\s*(\d+)",
        text,
        re.S,
    )
    if active:
        cols = re.findall(r'"([^"]+)"', active.group(1))
        if cols:
            app["active_border"] = cols
        app["active_border_angle"] = int(active.group(2))
    inactive = re.search(r'inactive_border\s*=\s*"([^"]+)"', text)
    if inactive:
        app["inactive_border"] = inactive.group(1)

    shadow_color = re.search(r"shadow\s*=\s*\{[^}]*color\s*=\s*(0x[0-9a-fA-F]+)", text, re.S)
    if shadow_color:
        app["shadow_color"] = shadow_color.group(1)
    for key, dest in (("enabled", "shadow_enabled"), ("range", "shadow_range"), ("render_power", "shadow_render_power")):
        m = re.search(rf"shadow\s*=\s*\{{[^}}]*{key}\s*=\s*([^\s,]+)", text, re.S)
        if m:
            raw = m.group(1)
            app[dest] = raw == "true" if raw in ("true", "false") else int(raw)

    blur = re.search(r"blur\s*=\s*\{(.*?)\n\s*\}", text, re.S)
    if blur:
        block = blur.group(1)
        if re.search(r"enabled\s*=\s*true", block):
            app["blur_enabled"] = True
        if re.search(r"enabled\s*=\s*false", block):
            app["blur_enabled"] = False
        m = re.search(r"size\s*=\s*(\d+)", block)
        if m:
            app["blur_size"] = int(m.group(1))
        m = re.search(r"passes\s*=\s*(\d+)", block)
        if m:
            app["blur_passes"] = int(m.group(1))
        m = re.search(r"vibrancy\s*=\s*([0-9.]+)", block)
        if m:
            app["blur_vibrancy"] = float(m.group(1))

    anim = re.search(r"animations\s*=\s*\{\s*enabled\s*=\s*(true|false)", text)
    if anim:
        app["animations_enabled"] = anim.group(1) == "true"

    inp = out["input"]
    for key in ("kb_layout", "kb_variant", "kb_model", "kb_options"):
        v = grab_str(key)
        if v is not None:
            inp[key] = v
    v = grab_int("follow_mouse")
    if v is not None:
        inp["follow_mouse"] = v
    v = grab_float("sensitivity")
    if v is not None:
        inp["sensitivity"] = v
    v = grab_bool("natural_scroll")
    if v is not None:
        inp["natural_scroll"] = v
    m = re.search(r'hl\.env\("XCURSOR_SIZE",\s*"(\d+)"\)', text)
    if m:
        inp["xcursor_size"] = int(m.group(1))
    m = re.search(r'hl\.env\("HYPRCURSOR_SIZE",\s*"(\d+)"\)', text)
    if m:
        inp["hyprcursor_size"] = int(m.group(1))

    for key, var in (("terminal", "terminal"), ("fileManager", "fileManager"), ("menu", "menu")):
        m = re.search(rf'local {var}\s*=\s*"([^"]+)"', text)
        if m:
            out["programs"][key] = m.group(1)

    starts = re.findall(r'hl\.exec_cmd\("([^"]+)"\)', text)
    if starts:
        # keep unique autostart-looking lines from hyprland.start
        start_block = re.search(r'hl\.on\("hyprland\.start".*?end\)', text, re.S)
        if start_block:
            out["autostart"] = re.findall(r'hl\.exec_cmd\("([^"]+)"\)', start_block.group(0))

    binds = parse_binds_from_lua(text, out.get("programs") or {})
    if binds:
        out["binds"] = binds

    extra = re.search(r"(--------------------------------\n---- WINDOWS AND WORKSPACES ----.*)$", text, re.S)
    if extra:
        out["extra_lua"] = extra.group(1).strip()
    return {k: v for k, v in out.items() if v}


def parse_binds_from_lua(text: str, programs: dict[str, str] | None = None) -> list[dict[str, Any]]:
    programs = programs or {}
    binds: list[dict[str, Any]] = []
    line_re = re.compile(
        r'hl\.bind\(\s*(.+?)\s*,\s*(.+?)(?:,\s*(\{.*?\}))?\s*\)\s*(?:--\s*(.*))?$',
        re.M,
    )
    for match in line_re.finditer(text):
        keys_expr, dsp, flags, comment = match.group(1), match.group(2), match.group(3) or "", match.group(4) or ""
        if " .. key" in keys_expr or "workspace = i" in dsp:
            continue
        mods, key = _split_keys(keys_expr)
        if not key or "mainMod" in key or ".." in key:
            continue
        kind, arg = _parse_dispatcher(dsp, programs)
        label = comment.strip()
        if (not label or label.startswith("-") or label.lower() in {
            "movimento de foco", "workspaces 1-10", "controle do rato", "teclas multimídia",
            "aplicações e atalhos estilo windows 11",
        }):
            label = _describe(kind, arg, key)
        item = bind(
            _guess_category(kind, key, arg),
            label,
            mods,
            key,
            kind,
            arg,
            mouse="mouse = true" in flags or key.startswith("mouse"),
            locked="locked = true" in flags,
            repeating="repeating = true" in flags,
        )
        binds.append(item)

    if re.search(r"for i = 1, 10 do", text):
        existing = {(tuple(b["mods"]), b["key"]) for b in binds}
        for i in range(1, 11):
            key = str(i % 10)
            if (tuple(["SUPER"]), key) not in existing:
                binds.append(bind("workspaces", f"Workspace {i}", ["SUPER"], key, "workspace", str(i)))
            if (tuple(["SUPER", "SHIFT"]), key) not in existing:
                binds.append(bind("workspaces", f"Move to workspace {i}", ["SUPER", "SHIFT"], key, "movetoworkspace", str(i)))
    return binds


def _split_keys(expr: str) -> tuple[list[str], str]:
    expr = expr.strip()
    expr = expr.replace('mainMod .. " + "', '"SUPER + "')
    expr = expr.replace("mainMod .. \" + \" .. key", '"SUPER + {key}"')
    parts: list[str] = []
    if expr.startswith('"') and expr.endswith('"'):
        raw = expr.strip('"')
        bits = [b.strip() for b in raw.split("+")]
        if bits:
            key = bits[-1]
            mods = [b.upper() if b.lower() != "shift" else "SHIFT" for b in bits[:-1]]
            mods = [m.replace("SUPER", "SUPER") for m in mods]
            return mods, key
    # concatenated expressions like mainMod .. " + RETURN"
    m = re.search(r'\.\.\s*" \+ ([^"]+)"', expr)
    if m:
        return ["SUPER"], m.group(1)
    return [], expr.strip('"')


def _parse_dispatcher(dsp: str, programs: dict[str, str] | None = None) -> tuple[str, str]:
    dsp = dsp.strip()
    programs = programs or {}
    m = re.search(r"hl\.dsp\.exec_cmd\((.*)\)\s*$", dsp)
    if m:
        inner = m.group(1).strip()
        str_m = re.match(r'"([^"]*)"', inner)
        if str_m:
            return "exec", str_m.group(1)
        ident = inner.split(",")[0].strip()
        if ident in programs:
            return "exec", programs[ident]
        aliases = {"terminal": "kitty", "fileManager": "dolphin", "menu": "serpantinumd toggle launcher"}
        return "exec", programs.get(ident) or aliases.get(ident, ident)
    if "window.close" in dsp:
        return "close", ""
    if "window.kill" in dsp:
        return "kill", ""
    if "window.float" in dsp:
        return "float", ""
    if "window.fullscreen" in dsp:
        return "fullscreen", ""
    if "window.pseudo" in dsp:
        return "pseudo", ""
    if "window.drag" in dsp:
        return "drag", ""
    if "window.resize" in dsp:
        return "resize", ""
    if "dsp.exit" in dsp:
        return "exit", ""
    m = re.search(r'focus\(\{\s*direction\s*=\s*"(\w+)"', dsp)
    if m:
        return "focus", m.group(1)
    m = re.search(r"focus\(\{\s*workspace\s*=\s*([^}]+)", dsp)
    if m:
        return "workspace", m.group(1).strip().strip('"')
    m = re.search(r"window\.move\(\{\s*workspace\s*=\s*([^}]+)", dsp)
    if m:
        return "movetoworkspace", m.group(1).strip().strip('"')
    m = re.search(r'layout\("([^"]+)"\)', dsp)
    if m:
        return "layout", m.group(1)
    m = re.search(r'toggle_special\("?([^")]+)"?\)', dsp)
    if m:
        return "special", m.group(1)
    return "custom", dsp


def _guess_category(kind: str, key: str, arg: str) -> str:
    if key.startswith("XF86"):
        return "media"
    if key.startswith("mouse"):
        return "mouse"
    if kind in ("workspace", "movetoworkspace", "special"):
        return "workspaces"
    if kind in ("focus",):
        return "focus"
    if kind in ("close", "float", "fullscreen", "drag", "resize", "pseudo", "layout"):
        return "windows"
    if kind in ("exit",) or "lock" in arg or "btop" in arg:
        return "system"
    return "apps"


def _describe(kind: str, arg: str, key: str) -> str:
    labels = {
        "exec": f"Run {arg}" if arg else "Run command",
        "close": "Close window",
        "kill": "Kill window",
        "float": "Toggle floating",
        "fullscreen": "Fullscreen",
        "pseudo": "Pseudo tile",
        "drag": "Move window",
        "resize": "Resize window",
        "exit": "Exit Hyprland",
        "focus": f"Focus {arg}",
        "workspace": f"Workspace {arg}",
        "movetoworkspace": f"Move to workspace {arg}",
        "layout": arg or "Layout",
        "special": "Toggle special workspace",
        "custom": "Custom action",
    }
    return labels.get(kind, kind)


def parse_existing_lock() -> dict[str, Any]:
    if not LOCK_PATH.exists():
        return {}
    text = LOCK_PATH.read_text(encoding="utf-8")
    out: dict[str, Any] = {}
    if re.search(r"hide_cursor\s*=\s*true", text):
        out["hide_cursor"] = True
    m = re.search(r"path\s*=\s*(\S+)", text)
    if m:
        path = m.group(1)
        out["background"] = "screenshot" if path == "screenshot" else "wallpaper"
        if path != "screenshot":
            out["wallpaper"] = path
    m = re.search(r"blur_passes\s*=\s*(\d+)", text)
    if m:
        out["blur_passes"] = int(m.group(1))
    m = re.search(r"\$font\s*=\s*(.+)", text)
    if m:
        out["font"] = m.group(1).strip()
    return out


def keys_pretty(mods: list[str], key: str) -> str:
    pretty_key = {
        "RETURN": "Enter",
        "comma": ",",
        "period": ".",
        "mouse:272": "LMB",
        "mouse:273": "RMB",
        "mouse:274": "MMB",
        "mouse_up": "Scroll Up",
        "mouse_down": "Scroll Down",
        "left": "←",
        "right": "→",
        "up": "↑",
        "down": "↓",
        "space": "Space",
        "Escape": "Esc",
    }.get(key, key.replace("XF86", ""))
    bits = [m.title() if m != "SUPER" else "Super" for m in mods]
    bits.append(pretty_key)
    return " + ".join(bits)


def keys_lua(mods: list[str], key: str) -> str:
    bits = list(mods) + [key]
    return " + ".join(bits)


def dispatcher_lua(item: dict[str, Any]) -> str:
    kind = item.get("kind") or "exec"
    arg = item.get("arg") or ""
    if kind == "exec":
        return f"hl.dsp.exec_cmd({_lua_str(arg)})"
    if kind == "close":
        return "hl.dsp.window.close()"
    if kind == "kill":
        return "hl.dsp.window.kill()"
    if kind == "float":
        return 'hl.dsp.window.float({ action = "toggle" })'
    if kind == "fullscreen":
        return "hl.dsp.window.fullscreen()"
    if kind == "pseudo":
        return "hl.dsp.window.pseudo()"
    if kind == "drag":
        return "hl.dsp.window.drag()"
    if kind == "resize":
        return "hl.dsp.window.resize()"
    if kind == "resize_delta":
        parts = (arg or "40 0").split()
        dx = parts[0] if parts else "40"
        dy = parts[1] if len(parts) > 1 else "0"
        return f"hl.dsp.window.resize({{ x = {dx}, y = {dy}, relative = true }})"
    if kind == "move_dir":
        direction = {"left": "left", "right": "right", "up": "up", "down": "down", "l": "left", "r": "right", "u": "up", "d": "down"}.get(arg, arg or "left")
        return f'hl.dsp.window.move({{ direction = "{direction}" }})'
    if kind == "exit":
        return "hl.dsp.exit()"
    if kind == "focus":
        direction = {"left": "left", "right": "right", "up": "up", "down": "down", "l": "left", "r": "right", "u": "up", "d": "down"}.get(arg, arg or "left")
        return f'hl.dsp.focus({{ direction = "{direction}" }})'
    if kind == "workspace":
        try:
            n = int(arg)
            return f"hl.dsp.focus({{ workspace = {n} }})"
        except ValueError:
            return f"hl.dsp.focus({{ workspace = {_lua_str(arg)} }})"
    if kind == "movetoworkspace":
        try:
            n = int(arg)
            return f"hl.dsp.window.move({{ workspace = {n} }})"
        except ValueError:
            return f"hl.dsp.window.move({{ workspace = {_lua_str(arg)} }})"
    if kind == "layout":
        return f"hl.dsp.layout({_lua_str(arg or 'togglesplit')})"
    if kind == "special":
        return f"hl.dsp.workspace.toggle_special({_lua_str(arg or 'magic')})"
    if kind == "custom":
        return arg or "hl.dsp.no_op()"
    return f"hl.dsp.exec_cmd({_lua_str(arg)})"


def flags_lua(item: dict[str, Any]) -> str:
    flags = []
    if item.get("mouse"):
        flags.append("mouse = true")
    if item.get("locked"):
        flags.append("locked = true")
    if item.get("repeating"):
        flags.append("repeating = true")
    desc = item.get("description")
    if desc:
        flags.append(f"description = {_lua_str(desc)}")
    if not flags:
        return ""
    return "{ " + ", ".join(flags) + " }"


def generate_lua(model: dict[str, Any]) -> str:
    a = model["appearance"]
    i = model["input"]
    p = model["programs"]
    colors = a["active_border"]
    if isinstance(colors, str):
        colors = [colors]
    color_list = ", ".join(_lua_str(c) for c in colors)
    autostart = "\n".join(f"  hl.exec_cmd({_lua_str(cmd)})" for cmd in model.get("autostart") or [])

    bind_lines = []
    for item in model.get("binds") or []:
        if not item.get("enabled", True):
            continue
        keys = keys_lua(item.get("mods") or [], item.get("key") or "")
        dsp = dispatcher_lua(item)
        flags = flags_lua(item)
        if flags:
            bind_lines.append(f'hl.bind({_lua_str(keys)}, {dsp}, {flags})')
        else:
            bind_lines.append(f'hl.bind({_lua_str(keys)}, {dsp})')
    binds_block = "\n".join(bind_lines)

    extra = model.get("extra_lua") or DEFAULT_RULES
    if "hyprpanel-float" not in extra:
        extra = extra.rstrip() + """

hl.window_rule({
    name  = "hyprpanel-float",
    match = { class = "io.hyprpanel.Hyprpanel" },
    float = true,
})
"""

    monitors_block = generate_monitors_lua(model)
    file_manager = p.get("fileManager") or detect_file_manager()
    menu = p.get("menu") or detect_launcher()

    return f"""-- =============================================================================
-- Hyprland Lua config managed by Hyprpanel
-- Visual editor: Super + ,   (or run `hyprpanel`)
-- Edit via the panel when possible. This file is regenerated on Apply.
-- =============================================================================

local terminal    = {_lua_str(p.get("terminal") or "kitty")}
local fileManager = {_lua_str(file_manager)}
local menu        = {_lua_str(menu)}

------------------
---- MONITORS ----
------------------
{monitors_block}

-------------------
---- AUTOSTART ----
-------------------
hl.on("hyprland.start", function ()
{autostart}
end)

-------------------------------
---- ENVIRONMENT VARIABLES ----
-------------------------------
hl.env("XCURSOR_SIZE", {_lua_str(str(i.get("xcursor_size") or 24))})
hl.env("HYPRCURSOR_SIZE", {_lua_str(str(i.get("hyprcursor_size") or 24))})

-----------------------
---- LOOK AND FEEL ----
-----------------------
hl.config({{
    general = {{
        gaps_in  = {int(a.get("gaps_in") or 5)},
        gaps_out = {int(a.get("gaps_out") or 20)},
        border_size = {int(a.get("border_size") or 2)},
        col = {{
            active_border   = {{ colors = {{{color_list}}}, angle = {int(a.get("active_border_angle") or 45)} }},
            inactive_border = {_lua_str(a.get("inactive_border") or "rgba(303638aa)")},
        }},
        resize_on_border = {_bool(a.get("resize_on_border"))},
        allow_tearing = {_bool(a.get("allow_tearing"))},
        layout = {_lua_str(a.get("layout") or "dwindle")},
    }},
    decoration = {{
        rounding       = {int(a.get("rounding") or 10)},
        rounding_power = {float(a.get("rounding_power") or 2)},
        active_opacity   = {float(a.get("active_opacity") or 1)},
        inactive_opacity = {float(a.get("inactive_opacity") or 1)},
        shadow = {{
            enabled      = {_bool(a.get("shadow_enabled", True))},
            range        = {int(a.get("shadow_range") or 4)},
            render_power = {int(a.get("shadow_render_power") or 3)},
            color        = {a.get("shadow_color") or "0xee1a1a1a"},
        }},
        blur = {{
            enabled   = {_bool(a.get("blur_enabled", True))},
            size      = {int(a.get("blur_size") or 3)},
            passes    = {int(a.get("blur_passes") or 1)},
            vibrancy  = {float(a.get("blur_vibrancy") or 0.1696)},
        }},
    }},
    animations = {{
        enabled = {_bool(a.get("animations_enabled", True))},
    }},
}})

hl.curve("easeOutQuint",   {{ type = "bezier", points = {{ {{0.23, 1}},    {{0.32, 1}}    }} }})
hl.curve("easeInOutCubic", {{ type = "bezier", points = {{ {{0.65, 0.05}}, {{0.36, 1}}    }} }})
hl.curve("linear",         {{ type = "bezier", points = {{ {{0, 0}},       {{1, 1}}       }} }})
hl.curve("almostLinear",   {{ type = "bezier", points = {{ {{0.5, 0.5}},   {{0.75, 1}}    }} }})
hl.curve("quick",          {{ type = "bezier", points = {{ {{0.15, 0}},    {{0.1, 1}}     }} }})
hl.curve("easy",           {{ type = "spring", mass = 1, stiffness = 238.1191, dampening = 24.21279333 }})

hl.animation({{ leaf = "global",        enabled = true,  speed = 10,   bezier = "default" }})
hl.animation({{ leaf = "border",        enabled = true,  speed = 5.39, bezier = "easeOutQuint" }})
hl.animation({{ leaf = "windows",       enabled = true,  speed = 4.79, spring = "easy" }})
hl.animation({{ leaf = "windowsIn",     enabled = true,  speed = 4.1,  spring = "easy",         style = "popin 87%" }})
hl.animation({{ leaf = "windowsOut",    enabled = true,  speed = 1.49, bezier = "linear",       style = "popin 87%" }})
hl.animation({{ leaf = "fadeIn",        enabled = true,  speed = 1.73, bezier = "almostLinear" }})
hl.animation({{ leaf = "fadeOut",       enabled = true,  speed = 1.46, bezier = "almostLinear" }})
hl.animation({{ leaf = "fade",          enabled = true,  speed = 3.03, bezier = "quick" }})
hl.animation({{ leaf = "layers",        enabled = true,  speed = 3.81, bezier = "easeOutQuint" }})
hl.animation({{ leaf = "layersIn",      enabled = true,  speed = 4,    bezier = "easeOutQuint", style = "fade" }})
hl.animation({{ leaf = "layersOut",     enabled = true,  speed = 1.5,  bezier = "linear",       style = "fade" }})
hl.animation({{ leaf = "fadeLayersIn",  enabled = true,  speed = 1.79, bezier = "almostLinear" }})
hl.animation({{ leaf = "fadeLayersOut", enabled = true,  speed = 1.39, bezier = "almostLinear" }})
hl.animation({{ leaf = "workspaces",    enabled = true,  speed = 1.94, bezier = "almostLinear", style = "fade" }})
hl.animation({{ leaf = "workspacesIn",  enabled = true,  speed = 1.21, bezier = "almostLinear", style = "fade" }})
hl.animation({{ leaf = "workspacesOut", enabled = true,  speed = 1.94, bezier = "almostLinear", style = "fade" }})
hl.animation({{ leaf = "zoomFactor",    enabled = true,  speed = 7,    bezier = "quick" }})

hl.config({{
    dwindle = {{ preserve_split = true }},
    master = {{ new_status = "master" }},
    scrolling = {{ fullscreen_on_one_column = true }},
    misc = {{
        force_default_wallpaper = {int(a.get("force_default_wallpaper") if a.get("force_default_wallpaper") is not None else -1)},
        disable_hyprland_logo = {_bool(a.get("disable_hyprland_logo"))},
    }},
}})

---------------
---- INPUT ----
---------------
hl.config({{
    input = {{
        kb_layout  = {_lua_str(i.get("kb_layout") or "us")},
        kb_variant = {_lua_str(i.get("kb_variant") or "")},
        kb_model   = {_lua_str(i.get("kb_model") or "")},
        kb_options = {_lua_str(i.get("kb_options") or "")},
        kb_rules   = "",
        follow_mouse = {int(i.get("follow_mouse") or 1)},
        sensitivity = {float(i.get("sensitivity") or 0)},
        touchpad = {{ natural_scroll = {_bool(i.get("natural_scroll"))} }},
    }},
}})

---------------------
---- KEYBINDINGS ----
---------------------
{binds_block}

{extra}
"""


DEFAULT_RULES = """--------------------------------
---- WINDOWS AND WORKSPACES ----
--------------------------------
hl.window_rule({
    name  = "suppress-maximize-events",
    match = { class = ".*" },
    suppress_event = "maximize",
})

hl.window_rule({
    name  = "fix-xwayland-drags",
    match = { class = "^$", title = "^$", xwayland = true, float = true, fullscreen = false, pin = false },
    no_focus = true,
})

hl.window_rule({
    name  = "hyprpanel-float",
    match = { class = "io.hyprpanel.Hyprpanel" },
    float = true,
})
"""


def generate_conf_mirror(model: dict[str, Any]) -> str:
    """Readable .conf mirror so settings can be inspected in classic Hyprland syntax."""
    a = model["appearance"]
    i = model["input"]
    p = model["programs"]
    colors = a["active_border"]
    if isinstance(colors, str):
        colors = [colors]
    active = " ".join(colors) + f" {int(a.get('active_border_angle') or 45)}deg"
    lines = [
        "# Mirrored Hyprland config generated by Hyprpanel.",
        "# Hyprland 0.56 loads ~/.config/hypr/hyprland.lua instead of this file.",
        "# This copy exists so you can still read settings in classic .conf form.",
        "",
        f"$mainMod = {model.get('mainMod') or 'SUPER'}",
        f"$terminal = {p.get('terminal') or 'kitty'}",
        f"$fileManager = {p.get('fileManager') or 'dolphin'}",
        f"$menu = {p.get('menu') or 'serpantinumd toggle launcher'}",
        "",
        "general {",
        f"    gaps_in = {a.get('gaps_in')}",
        f"    gaps_out = {a.get('gaps_out')}",
        f"    border_size = {a.get('border_size')}",
        f"    col.active_border = {active}",
        f"    col.inactive_border = {a.get('inactive_border')}",
        f"    resize_on_border = {1 if a.get('resize_on_border') else 0}",
        f"    allow_tearing = {1 if a.get('allow_tearing') else 0}",
        f"    layout = {a.get('layout')}",
        "}",
        "",
        "decoration {",
        f"    rounding = {a.get('rounding')}",
        f"    rounding_power = {a.get('rounding_power')}",
        f"    active_opacity = {a.get('active_opacity')}",
        f"    inactive_opacity = {a.get('inactive_opacity')}",
        "    shadow {",
        f"        enabled = {1 if a.get('shadow_enabled') else 0}",
        f"        range = {a.get('shadow_range')}",
        f"        render_power = {a.get('shadow_render_power')}",
        f"        color = {a.get('shadow_color')}",
        "    }",
        "    blur {",
        f"        enabled = {1 if a.get('blur_enabled') else 0}",
        f"        size = {a.get('blur_size')}",
        f"        passes = {a.get('blur_passes')}",
        f"        vibrancy = {a.get('blur_vibrancy')}",
        "    }",
        "}",
        "",
        "animations {",
        f"    enabled = {1 if a.get('animations_enabled') else 0}",
        "}",
        "",
        "input {",
        f"    kb_layout = {i.get('kb_layout')}",
        f"    kb_variant = {i.get('kb_variant')}",
        f"    follow_mouse = {i.get('follow_mouse')}",
        f"    sensitivity = {i.get('sensitivity')}",
        "    touchpad {",
        f"        natural_scroll = {1 if i.get('natural_scroll') else 0}",
        "    }",
        "}",
        "",
        "misc {",
        f"    force_default_wallpaper = {a.get('force_default_wallpaper')}",
        f"    disable_hyprland_logo = {1 if a.get('disable_hyprland_logo') else 0}",
        "}",
        "",
    ]
    for cmd in model.get("autostart") or []:
        lines.append(f"exec-once = {cmd}")
    lines.append("")
    for item in model.get("binds") or []:
        if not item.get("enabled", True):
            continue
        prefix = "bindm" if item.get("mouse") else "bind"
        extras = []
        if item.get("locked"):
            extras.append("l")
        if item.get("repeating"):
            extras.append("e")
        if extras and not item.get("mouse"):
            prefix = "bind" + "".join(extras)
        mods = ",".join(item.get("mods") or [])
        key = item.get("key") or ""
        kind = item.get("kind")
        arg = item.get("arg") or ""
        dispatcher, param = _conf_dispatcher(kind, arg)
        comment = item.get("description") or ""
        lines.append(f"{prefix} = {mods}, {key}, {dispatcher}, {param}  # {comment}".rstrip())
    lines.append("")
    return "\n".join(lines) + "\n"


def _conf_dispatcher(kind: str, arg: str) -> tuple[str, str]:
    mapping = {
        "exec": ("exec", arg),
        "close": ("killactive", ""),
        "kill": ("forcekillactive", ""),
        "float": ("togglefloating", ""),
        "fullscreen": ("fullscreen", ""),
        "pseudo": ("pseudo", ""),
        "drag": ("movewindow", ""),
        "resize": ("resizewindow", ""),
        "exit": ("exit", ""),
        "focus": ("movefocus", {"left": "l", "right": "r", "up": "u", "down": "d"}.get(arg, arg[:1] if arg else "l")),
        "workspace": ("workspace", arg),
        "movetoworkspace": ("movetoworkspace", arg),
        "layout": ("layoutmsg", arg),
        "special": ("togglespecialworkspace", arg),
        "resize_delta": ("resizeactive", arg),
        "move_dir": ("movewindow", {"left": "l", "right": "r", "up": "u", "down": "d"}.get(arg, arg)),
        "custom": ("exec", arg),
    }
    return mapping.get(kind, ("exec", arg))


def generate_hyprlock(model: dict[str, Any]) -> str:
    lock = model["lock"]
    font = lock.get("font") or "Adwaita Mono"
    bg = lock.get("background") or "screenshot"
    path = "screenshot" if bg == "screenshot" else (lock.get("wallpaper") or "screenshot")
    date_cmd = lock.get("date_format") or "%A, %d %B %Y"
    date_block = ""
    if lock.get("show_date", True):
        date_block = f"""
label {{
    monitor =
    text = cmd[update:60000] date +"{date_cmd}"
    font_size = {int(lock.get("date_size") or 22)}
    font_family = $font
    color = {lock.get("font_color")}
    position = 0, -40
    halign = center
    valign = center
}}
"""
    clock_block = ""
    if lock.get("show_clock", True):
        clock_block = f"""
label {{
    monitor =
    text = $TIME
    font_size = {int(lock.get("clock_size") or 90)}
    font_family = $font
    color = {lock.get("font_color")}
    position = 0, 80
    halign = center
    valign = center
}}
"""
    return f"""# Generated by Hyprpanel to match the active Serpantinum palette.
$font = {font}

general {{
    hide_cursor = {"true" if lock.get("hide_cursor") else "false"}
    grace = {int(lock.get("grace") or 0)}
    ignore_empty_input = {"true" if lock.get("ignore_empty_input") else "false"}
}}

animations {{
    enabled = true
    bezier = linear, 1, 1, 0, 0
    animation = fadeIn, 1, 5, linear
    animation = fadeOut, 1, 5, linear
    animation = inputFieldDots, 1, 2, linear
}}

background {{
    monitor =
    path = {path}
    blur_passes = {int(lock.get("blur_passes") or 3)}
    color = {lock.get("inner_color")}
}}

{clock_block}
{date_block}

input-field {{
    monitor =
    size = 280, 48
    outline_thickness = {int(lock.get("outline_thickness") or 2)}
    inner_color = {lock.get("inner_color")}
    outer_color = {lock.get("outer_color")}
    check_color = {lock.get("check_color")}
    fail_color = {lock.get("fail_color")}
    font_color = {lock.get("font_color")}
    fade_on_empty = false
    rounding = {int(lock.get("rounding") or 8)}
    font_family = $font
    placeholder_text = {lock.get("placeholder") or "type password"}
    fail_text = $PAMFAIL
    dots_spacing = 0.3
    position = 0, -110
    halign = center
    valign = center
}}
"""


def generate_hypridle(model: dict[str, Any]) -> str:
    cmd = model.get("idle", {}).get("lock_cmd") or model.get("lock", {}).get("command") or "serpantinum lock"
    return f"""general {{
    lock_cmd = {cmd}
}}
"""


def apply_preset_colors(model: dict[str, Any], colors: dict[str, str]) -> None:
    mauve = colors.get("mauve") or colors.get("blue") or "#88d0ed"
    blue = colors.get("blue") or mauve
    surface2 = colors.get("surface2") or "#303638"
    crust = colors.get("crust") or "#0f1416"
    text = colors.get("text") or "#dee3e6"
    red = colors.get("red") or "#ffb4ab"
    green = colors.get("green") or "#a3be8c"
    base = colors.get("base") or "#1e1e2e"
    model["appearance"]["active_border"] = [hex_to_rgba(mauve, 0.93), hex_to_rgba(blue, 0.81)]
    model["appearance"]["inactive_border"] = hex_to_rgba(surface2, 0.67)
    h = crust.lstrip("#")[:6]
    model["appearance"]["shadow_color"] = f"0xee{h}"
    lock = model["lock"]
    lock["inner_color"] = hex_to_rgba(base, 0.4)
    lock["outer_color"] = hex_to_rgba(mauve, 0.93)
    lock["check_color"] = hex_to_rgba(green, 0.93)
    lock["fail_color"] = hex_to_rgba(red, 0.93)
    lock["font_color"] = hex_to_rgba(text, 1.0)


def backup_configs() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dest = BACKUP_DIR / _now()
    dest.mkdir(parents=True, exist_ok=True)
    for path in (LUA_PATH, HYPR_DIR / "hyprland.conf", LOCK_PATH, IDLE_PATH):
        if path.exists():
            shutil.copy2(path, dest / path.name)
    return dest


def write_configs(model: dict[str, Any]) -> None:
    HYPR_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    refresh_monitors(model)
    LUA_PATH.write_text(generate_lua(model), encoding="utf-8")
    CONF_MIRROR.write_text(generate_conf_mirror(model), encoding="utf-8")
    LOCK_PATH.write_text(generate_hyprlock(model), encoding="utf-8")
    IDLE_PATH.write_text(generate_hypridle(model), encoding="utf-8")
    save_state(model)


def hyprctl(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["hyprctl", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def reload_hypr(model: dict[str, Any] | None = None) -> tuple[bool, str]:
    scales = serpantinum_monitor_scales()
    result = hyprctl("reload")
    text = (result.stdout or "") + (result.stderr or "")
    ok = result.returncode == 0
    if model:
        apply_monitor_scales(model)
    restore_serpantinum_scales(scales)
    return ok, text.strip()


def live_keyword(key: str, value: Any) -> None:
    hyprctl("keyword", key, str(value))


def apply_live_appearance(model: dict[str, Any]) -> None:
    a = model["appearance"]
    live_keyword("general:gaps_in", a.get("gaps_in"))
    live_keyword("general:gaps_out", a.get("gaps_out"))
    live_keyword("general:border_size", a.get("border_size"))
    live_keyword("general:layout", a.get("layout"))
    live_keyword("decoration:rounding", a.get("rounding"))
    live_keyword("decoration:rounding_power", a.get("rounding_power"))
    live_keyword("decoration:active_opacity", a.get("active_opacity"))
    live_keyword("decoration:inactive_opacity", a.get("inactive_opacity"))
    live_keyword("decoration:blur:enabled", str(bool(a.get("blur_enabled"))).lower())
    live_keyword("decoration:blur:size", a.get("blur_size"))
    live_keyword("decoration:blur:passes", a.get("blur_passes"))
    live_keyword("decoration:shadow:enabled", str(bool(a.get("shadow_enabled"))).lower())
    live_keyword("decoration:shadow:range", a.get("shadow_range"))
    colors = a.get("active_border") or []
    if isinstance(colors, str):
        colors = [colors]
    angle = int(a.get("active_border_angle") or 45)
    live_keyword("general:col.active_border", f"{' '.join(colors)} {angle}deg")
    live_keyword("general:col.inactive_border", a.get("inactive_border"))
    i = model["input"]
    live_keyword("input:kb_layout", i.get("kb_layout"))
    live_keyword("input:kb_variant", i.get("kb_variant") or "")
    live_keyword("input:follow_mouse", i.get("follow_mouse"))
    live_keyword("input:sensitivity", i.get("sensitivity"))
    live_keyword("input:touchpad:natural_scroll", str(bool(i.get("natural_scroll"))).lower())
    live_keyword("misc:disable_hyprland_logo", str(bool(a.get("disable_hyprland_logo"))).lower())
    live_keyword("animations:enabled", str(bool(a.get("animations_enabled"))).lower())


def list_wallpaper_candidates() -> list[str]:
    roots = [
        HOME / "Pictures",
        HOME / ".cache" / "serpantinum-wallpapers",
        HOME / ".cache" / "serpantinum" / "wallpaper",
        Path("/usr/share/hypr"),
    ]
    found: list[str] = []
    for root in roots:
        if not root.exists():
            continue
        for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
            found.extend(str(p) for p in root.rglob(ext))
            if len(found) > 40:
                return found[:40]
    return found[:40]
