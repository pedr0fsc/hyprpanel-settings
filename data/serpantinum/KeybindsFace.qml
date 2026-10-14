import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import "../../../reusables"
import "../../../"

Item {
    id: root
    anchors.fill: parent
    clip: true

    property real minWidth: Scaler.s(260)
    property real minHeight: Scaler.s(280)
    property real maxWidth: Scaler.s(720)
    property real maxHeight: Scaler.s(1100)
    property real minAspect: 0.35
    property real maxAspect: 1.8
    property bool isRound: false
    property bool wantsKeyboardFocus: searchField.activeFocus

    property var groups: []
    property string query: ""
    property bool loaded: false

    readonly property string keybindsPath: {
        let home = Quickshell.env("HOME") || ""
        return home + "/.config/hypr/hyprpanel/keybinds.json"
    }

    readonly property real cardRadius: ThemeBackend.clampedBorderRadius !== undefined
        ? ThemeBackend.clampedBorderRadius
        : ThemeBackend.borderRadius
    readonly property real pad: Math.max(Scaler.s(10), Math.min(Scaler.s(16), root.width * 0.04))

    function groupColor(id) {
        if (typeof ThemeBackend === "undefined")
            return "#cba6f7"
        switch (id) {
        case "apps":
            return ThemeBackend.blue
        case "windows":
            return ThemeBackend.mauve
        case "focus":
            return ThemeBackend.peach
        case "workspaces":
            return ThemeBackend.sapphire
        case "system":
            return ThemeBackend.yellow
        case "media":
            return ThemeBackend.green
        case "mouse":
            return ThemeBackend.pink
        default:
            return ThemeBackend.teal
        }
    }

    function parsePayload(raw) {
        root.loaded = true
        try {
            let obj = JSON.parse(String(raw || "").trim() || "{}")
            root.groups = Array.isArray(obj.groups) ? obj.groups : []
        } catch (e) {
            root.groups = []
        }
    }

    function matchesQuery(item) {
        let q = (root.query || "").trim().toLowerCase()
        if (!q)
            return true
        let hay = ((item.description || "") + " " + (item.keys || "")).toLowerCase()
        return hay.indexOf(q) !== -1
    }

    readonly property var visibleGroups: {
        let out = []
        let src = root.groups || []
        for (let i = 0; i < src.length; i++) {
            let g = src[i]
            let items = []
            let raw = g.items || []
            for (let j = 0; j < raw.length; j++) {
                if (root.matchesQuery(raw[j]))
                    items.push(raw[j])
            }
            if (items.length > 0)
                out.push({
                    id: g.id,
                    title: g.title,
                    items: items
                })
        }
        return out
    }

    FileView {
        id: keybindsFile
        path: root.keybindsPath
        watchChanges: true
        onFileChanged: reload()
        onLoaded: {
            let raw = typeof text === "function" ? text() : text
            root.parsePayload(raw)
        }
    }

    Rectangle {
        anchors.fill: parent
        color: ThemeBackend.surface0
        radius: root.cardRadius
        border.width: 1
        border.color: Qt.rgba(ThemeBackend.text.r, ThemeBackend.text.g, ThemeBackend.text.b, 0.06)
        clip: true

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: root.pad
            spacing: Scaler.s(8)

            RowLayout {
                Layout.fillWidth: true
                spacing: Scaler.s(8)

                Text {
                    text: String.fromCodePoint(0xF030C)
                    font.family: "Iosevka Nerd Font"
                    font.pixelSize: Scaler.s(18)
                    color: ThemeBackend.mauve
                }

                Text {
                    text: typeof I18n !== "undefined" ? I18n.t("widgets.types.keybinds", "Keybinds") : "Keybinds"
                    font.family: ThemeBackend.fontFamily
                    font.pixelSize: Scaler.s(15)
                    font.bold: true
                    color: ThemeBackend.text
                    Layout.fillWidth: true
                }

                Text {
                    text: {
                        let n = 0
                        let gs = root.visibleGroups
                        for (let i = 0; i < gs.length; i++)
                            n += (gs[i].items || []).length
                        return String(n)
                    }
                    font.family: ThemeBackend.fontFamily
                    font.pixelSize: Scaler.s(11)
                    font.bold: true
                    color: ThemeBackend.subtext0
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: Scaler.s(32)
                color: ThemeBackend.surface1
                radius: Math.min(root.cardRadius, Scaler.s(8))

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Scaler.s(10)
                    anchors.rightMargin: Scaler.s(10)
                    spacing: Scaler.s(6)

                    Text {
                        text: String.fromCodePoint(0xF0349)
                        font.family: "Iosevka Nerd Font"
                        font.pixelSize: Scaler.s(13)
                        color: ThemeBackend.subtext0
                    }

                    TextInput {
                        id: searchField
                        Layout.fillWidth: true
                        color: ThemeBackend.text
                        font.family: ThemeBackend.fontFamily
                        font.pixelSize: Scaler.s(12)
                        selectedTextColor: ThemeBackend.crust
                        selectionColor: ThemeBackend.mauve
                        clip: true
                        onTextChanged: root.query = text

                        Text {
                            anchors.fill: parent
                            verticalAlignment: Text.AlignVCenter
                            text: "Filter shortcuts"
                            font.family: ThemeBackend.fontFamily
                            font.pixelSize: Scaler.s(12)
                            color: ThemeBackend.overlay0
                            visible: !searchField.text && !searchField.activeFocus
                        }
                    }
                }
            }

            Flickable {
                id: listFlick
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                contentWidth: width
                contentHeight: listCol.implicitHeight
                boundsBehavior: Flickable.StopAtBounds
                flickableDirection: Flickable.VerticalFlick

                Column {
                    id: listCol
                    width: listFlick.width
                    spacing: Scaler.s(12)

                    Text {
                        width: parent.width
                        visible: root.loaded && root.visibleGroups.length === 0
                        text: root.query ? "No shortcuts match" : "Open Hyprpanel and apply bindings"
                        font.family: ThemeBackend.fontFamily
                        font.pixelSize: Scaler.s(12)
                        color: ThemeBackend.subtext0
                        wrapMode: Text.WordWrap
                    }

                    Repeater {
                        model: root.visibleGroups

                        Column {
                            required property var modelData
                            width: listCol.width
                            spacing: Scaler.s(6)

                            Row {
                                spacing: Scaler.s(8)

                                Rectangle {
                                    width: Scaler.s(8)
                                    height: Scaler.s(8)
                                    radius: width / 2
                                    color: root.groupColor(modelData.id)
                                    anchors.verticalCenter: parent.verticalCenter
                                }

                                Text {
                                    text: modelData.title || modelData.id
                                    font.family: ThemeBackend.fontFamily
                                    font.pixelSize: Scaler.s(11)
                                    font.bold: true
                                    font.capitalization: Font.AllUppercase
                                    color: root.groupColor(modelData.id)
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }

                            Repeater {
                                model: modelData.items

                                RowLayout {
                                    required property var modelData
                                    width: listCol.width
                                    spacing: Scaler.s(8)

                                    Rectangle {
                                        implicitHeight: Scaler.s(22)
                                        implicitWidth: Math.min(keyLab.implicitWidth + Scaler.s(12), listCol.width * 0.55)
                                        radius: Math.min(ThemeBackend.borderRadius, Scaler.s(6))
                                        color: ThemeBackend.surface1
                                        border.width: 1
                                        border.color: Qt.rgba(ThemeBackend.text.r, ThemeBackend.text.g, ThemeBackend.text.b, 0.08)
                                        clip: true

                                        Text {
                                            id: keyLab
                                            anchors.centerIn: parent
                                            text: modelData.keys || ""
                                            font.family: ThemeBackend.fontFamily
                                            font.pixelSize: Scaler.s(10)
                                            font.bold: true
                                            color: ThemeBackend.text
                                        }
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: modelData.description || ""
                                        font.family: ThemeBackend.fontFamily
                                        font.pixelSize: Scaler.s(11)
                                        color: ThemeBackend.subtext1
                                        elide: Text.ElideRight
                                        wrapMode: Text.NoWrap
                                        horizontalAlignment: Text.AlignRight
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
