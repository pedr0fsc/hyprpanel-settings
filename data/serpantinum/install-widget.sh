#!/usr/bin/env bash
# Install the Hyprpanel keybinds face into a local Serpantinum tree.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
QS="${SERPANTINUM_DIR:-$HOME/.local/share/serpantinum/src}/quickshell"
DEST="$QS/widgets/faces/keybinds/KeybindsFace.qml"
REG="$QS/widgets/WidgetRegistry.qml"

if [[ ! -f "$REG" ]]; then
  echo "serpantinum widgets not found at $QS" >&2
  exit 0
fi

install -Dm644 "$HERE/KeybindsFace.qml" "$DEST"

python3 - "$REG" <<'PY'
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
if '"keybinds"' in text:
    raise SystemExit(0)

block = '''        "keybinds": {
            name: typeof I18n !== "undefined" ? I18n.t("widgets.types.keybinds", "Keybinds") : "Keybinds",
            icon: String.fromCodePoint(0xF030C),
            iconOffsetX: 0,
            defaultWidth: 340,
            defaultHeight: 560,
            defaultVariant: "list",
            variants: {
                "list": { file: "faces/keybinds/KeybindsFace.qml", icon: "1", label: typeof I18n !== "undefined" ? I18n.t("widgets.variants.list", "List") : "List" }
            }
        },
'''
needle = '        "github": {'
if needle not in text:
    raise SystemExit("WidgetRegistry.qml does not contain the github widget block")
path.write_text(text.replace(needle, block + needle, 1), encoding="utf-8")
PY
echo "Installed Serpantinum keybinds widget -> $DEST"
