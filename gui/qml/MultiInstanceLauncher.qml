import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    id: root
    width: 1180
    height: 760
    minimumWidth: 980
    minimumHeight: 650
    visible: true
    title: "XXZ Multi Instance"
    color: theme.bg

    property var launcherState: ({
        instances: [],
        available: [],
        configuredCount: 0,
        runningCount: 0,
        pausedCount: 0,
        maxInstances: 8
    })
    property string notice: "Ready"
    property bool noticeOk: true
    property bool busy: false

    function reloadState() {
        if (!launcherBridge) {
            return
        }
        launcherState = JSON.parse(launcherBridge.stateJson())
    }

    function handleResult(text) {
        const result = JSON.parse(text)
        notice = result.message || "Done"
        noticeOk = !!result.ok
        busy = false
        reloadState()
    }

    function runAction(action) {
        busy = true
        notice = "Working..."
        noticeOk = true
        launcherBridge.runAction(action)
    }

    function resourceIndex(value) {
        const values = ["auto", "full", "balanced", "economy"]
        const found = values.indexOf(String(value || "auto"))
        return found < 0 ? 0 : found
    }

    Component.onCompleted: reloadState()

    Timer {
        interval: 1200
        repeat: true
        running: true
        onTriggered: root.reloadState()
    }

    Connections {
        target: launcherBridge
        function onActionFinished(result) {
            root.handleResult(result)
        }
    }

    QtObject {
        id: theme
        property color bg: "#0b0d10"
        property color chrome: "#111419"
        property color panel: "#161a20"
        property color panelHover: "#1b2028"
        property color input: "#101318"
        property color border: "#2b313b"
        property color borderSoft: "#222831"
        property color text: "#f2f4f7"
        property color muted: "#a5adb8"
        property color faint: "#69727f"
        property color accent: "#f5a524"
        property color accentHover: "#ffb43a"
        property color accentSoft: "#2c2110"
        property color ok: "#35c46a"
        property color warn: "#f0a52b"
        property color danger: "#ef5b5b"
    }

    component ActionButton: Rectangle {
        id: button
        property string label: ""
        property bool secondary: false
        property bool destructive: false
        property bool enabled: true
        signal clicked()

        implicitWidth: Math.max(82, labelText.implicitWidth + 28)
        implicitHeight: 34
        radius: 6
        opacity: enabled ? 1 : 0.45
        color: {
            if (destructive) return mouse.containsMouse ? "#6e2828" : "#512222"
            if (secondary) return mouse.containsMouse ? theme.panelHover : theme.input
            return mouse.containsMouse ? theme.accentHover : theme.accent
        }
        border.width: secondary || destructive ? 1 : 0
        border.color: destructive ? "#934040" : theme.border

        Text {
            id: labelText
            anchors.centerIn: parent
            text: button.label
            color: button.secondary ? theme.text : "#15100a"
            font.pixelSize: 12
            font.weight: Font.DemiBold
        }

        MouseArea {
            id: mouse
            anchors.fill: parent
            enabled: button.enabled
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: button.clicked()
        }
    }

    component StyledField: TextField {
        color: theme.text
        placeholderTextColor: theme.faint
        selectionColor: theme.accent
        selectedTextColor: "#111111"
        font.pixelSize: 12
        leftPadding: 11
        rightPadding: 11
        background: Rectangle {
            radius: 6
            color: theme.input
            border.width: parent.activeFocus ? 1 : 1
            border.color: parent.activeFocus ? theme.accent : theme.border
        }
    }

    component StyledCombo: ComboBox {
        id: combo
        font.pixelSize: 12
        leftPadding: 11
        rightPadding: 28
        contentItem: Text {
            leftPadding: 0
            rightPadding: combo.indicator.width + combo.spacing
            text: combo.displayText
            font: combo.font
            color: theme.text
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        indicator: Text {
            x: combo.width - width - 10
            anchors.verticalCenter: parent.verticalCenter
            text: "v"
            color: theme.muted
            font.pixelSize: 11
        }
        background: Rectangle {
            radius: 6
            color: theme.input
            border.width: 1
            border.color: combo.activeFocus ? theme.accent : theme.border
        }
        popup: Popup {
            y: combo.height + 4
            width: combo.width
            implicitHeight: Math.min(contentItem.implicitHeight + 8, 280)
            padding: 4
            contentItem: ListView {
                clip: true
                implicitHeight: contentHeight
                model: combo.popup.visible ? combo.delegateModel : null
                currentIndex: combo.highlightedIndex
                ScrollIndicator.vertical: ScrollIndicator {}
            }
            background: Rectangle {
                radius: 6
                color: theme.panel
                border.width: 1
                border.color: theme.border
            }
        }
        delegate: ItemDelegate {
            width: combo.width - 8
            height: 34
            highlighted: combo.highlightedIndex === index
            contentItem: Text {
                text: modelData && modelData.label !== undefined ? modelData.label : modelData
                color: theme.text
                font.pixelSize: 11
                elide: Text.ElideRight
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle {
                radius: 4
                color: parent.highlighted ? theme.panelHover : "transparent"
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 78
            color: theme.chrome
            border.width: 0

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 22
                anchors.rightMargin: 22
                spacing: 18

                ColumnLayout {
                    spacing: 2
                    Text {
                        text: "XXZ MULTI INSTANCE"
                        color: theme.text
                        font.pixelSize: 19
                        font.weight: Font.Bold
                    }
                    Text {
                        text: root.launcherState.runningCount + " running  /  "
                              + root.launcherState.configuredCount + " configured  /  "
                              + root.launcherState.maxInstances + " slots"
                        color: theme.muted
                        font.pixelSize: 11
                    }
                }

                Item { Layout.fillWidth: true }

                Rectangle {
                    Layout.preferredWidth: statusText.implicitWidth + 26
                    Layout.preferredHeight: 30
                    radius: 6
                    color: root.noticeOk ? "#12261a" : "#321a1a"
                    border.width: 1
                    border.color: root.noticeOk ? "#275a37" : "#743434"
                    Text {
                        id: statusText
                        anchors.centerIn: parent
                        text: root.notice
                        color: root.noticeOk ? theme.ok : theme.danger
                        font.pixelSize: 11
                        font.weight: Font.Medium
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 58
            color: "#0e1115"
            border.width: 1
            border.color: theme.borderSoft

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 22
                anchors.rightMargin: 22
                spacing: 8
                ActionButton {
                    label: "Start All"
                    enabled: !root.busy && root.launcherState.configuredCount > 0
                    onClicked: root.runAction("start-all")
                }
                ActionButton {
                    label: "Pause All"
                    secondary: true
                    enabled: !root.busy && root.launcherState.runningCount > 0
                    onClicked: root.runAction("pause-all")
                }
                ActionButton {
                    label: "Resume All"
                    secondary: true
                    enabled: !root.busy && root.launcherState.pausedCount > 0
                    onClicked: root.runAction("resume-all")
                }
                ActionButton {
                    label: "Stop All"
                    destructive: true
                    enabled: !root.busy && root.launcherState.runningCount > 0
                    onClicked: root.runAction("stop-all")
                }
                Item { Layout.fillWidth: true }
                ActionButton {
                    label: "Tile Windows"
                    secondary: true
                    enabled: !root.busy
                    onClicked: root.runAction("align")
                }
                ActionButton {
                    label: "Refresh"
                    secondary: true
                    enabled: !root.busy
                    onClicked: root.reloadState()
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: 18
            spacing: 16

            Rectangle {
                Layout.preferredWidth: 310
                Layout.fillHeight: true
                radius: 8
                color: theme.panel
                border.width: 1
                border.color: theme.borderSoft

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 11

                    Text {
                        text: "ADD EMULATOR"
                        color: theme.text
                        font.pixelSize: 14
                        font.weight: Font.DemiBold
                    }
                    Text {
                        text: root.launcherState.available.length > 0
                              ? "Detected emulator profiles"
                              : "No LDPlayer or MuMu profiles detected"
                        color: root.launcherState.available.length > 0 ? theme.muted : theme.warn
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }

                    StyledCombo {
                        id: emulatorChoice
                        Layout.fillWidth: true
                        Layout.preferredHeight: 38
                        model: root.launcherState.available
                        textRole: "label"
                        enabled: model.length > 0
                    }

                    Text {
                        text: "PLAYER TAG"
                        color: theme.faint
                        font.pixelSize: 10
                        font.weight: Font.DemiBold
                    }
                    StyledField {
                        id: newPlayerTag
                        Layout.fillWidth: true
                        Layout.preferredHeight: 38
                        placeholderText: "#PLAYER_TAG"
                    }

                    Text {
                        text: "RESOURCE MODE"
                        color: theme.faint
                        font.pixelSize: 10
                        font.weight: Font.DemiBold
                    }
                    StyledCombo {
                        id: newResource
                        Layout.fillWidth: true
                        Layout.preferredHeight: 38
                        model: ["auto", "full", "balanced", "economy"]
                        currentIndex: 0
                    }

                    ActionButton {
                        label: "Add Selected Instance"
                        Layout.fillWidth: true
                        enabled: root.launcherState.available.length > 0
                                 && root.launcherState.configuredCount < root.launcherState.maxInstances
                                 && !root.busy
                        onClicked: {
                            const selected = root.launcherState.available[emulatorChoice.currentIndex]
                            const result = launcherBridge.addInstance(
                                JSON.stringify(selected || {}),
                                newPlayerTag.text,
                                newResource.currentText
                            )
                            root.handleResult(result)
                            if (JSON.parse(result).ok) {
                                newPlayerTag.text = ""
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        color: theme.borderSoft
                    }

                    Text {
                        text: "AUTO RESOURCE BUDGET"
                        color: theme.text
                        font.pixelSize: 12
                        font.weight: Font.DemiBold
                    }
                    Text {
                        text: "1 worker: 60 FPS / 4 threads\n2-4 workers: 30 FPS / 2 threads\n5-8 workers: 24 FPS / 1 thread"
                        color: theme.muted
                        font.pixelSize: 11
                        lineHeight: 1.35
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                    }

                    Item { Layout.fillHeight: true }

                    Text {
                        text: "Worker output: logs/instances/<id>.log"
                        color: theme.faint
                        font.pixelSize: 10
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                    }
                }
            }

            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                GridLayout {
                    width: parent.width
                    columns: width >= 760 ? 2 : 1
                    columnSpacing: 12
                    rowSpacing: 12

                    Repeater {
                        model: root.launcherState.instances

                        delegate: Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 244
                            radius: 8
                            color: modelData.running ? "#141f19" : theme.panel
                            border.width: 1
                            border.color: modelData.running ? "#2e6741" : theme.borderSoft

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 14
                                spacing: 8

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8
                                    Rectangle {
                                        Layout.preferredWidth: 34
                                        Layout.preferredHeight: 34
                                        radius: 6
                                        color: modelData.running ? "#1c3a27" : theme.input
                                        Text {
                                            anchors.centerIn: parent
                                            text: String(modelData.slot || "?")
                                            color: modelData.running ? theme.ok : theme.muted
                                            font.pixelSize: 14
                                            font.weight: Font.Bold
                                        }
                                    }
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 1
                                        Text {
                                            text: modelData.name
                                            color: theme.text
                                            font.pixelSize: 14
                                            font.weight: Font.DemiBold
                                            elide: Text.ElideRight
                                            Layout.fillWidth: true
                                        }
                                        Text {
                                            text: modelData.emulator.toUpperCase() + "  /  ADB " + modelData.emulator_port
                                            color: theme.muted
                                            font.pixelSize: 10
                                        }
                                    }
                                    Text {
                                        text: modelData.paused ? "PAUSED" : (modelData.running ? "RUNNING" : "STOPPED")
                                        color: modelData.paused ? theme.warn : (modelData.running ? theme.ok : theme.faint)
                                        font.pixelSize: 10
                                        font.weight: Font.Bold
                                    }
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8
                                    StyledField {
                                        id: playerTagField
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 34
                                        text: modelData.player_tag || ""
                                        placeholderText: "#PLAYER_TAG"
                                        onEditingFinished: {
                                            const result = launcherBridge.savePlayerTag(modelData.id, text)
                                            root.handleResult(result)
                                        }
                                    }
                                    StyledCombo {
                                        id: resourceChoice
                                        Layout.preferredWidth: 112
                                        Layout.preferredHeight: 34
                                        model: ["auto", "full", "balanced", "economy"]
                                        currentIndex: root.resourceIndex(modelData.resource_profile)
                                        onActivated: {
                                            const result = launcherBridge.saveResourceProfile(
                                                modelData.id,
                                                currentText
                                            )
                                            root.handleResult(result)
                                        }
                                    }
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 48
                                    radius: 6
                                    color: theme.input
                                    border.width: 1
                                    border.color: theme.borderSoft
                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 10
                                        anchors.rightMargin: 10
                                        spacing: 8
                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 1
                                            Text {
                                                text: modelData.brawler
                                                      ? modelData.brawler + "  ->  " + (modelData.target || "?")
                                                      : "Waiting for worker status"
                                                color: theme.text
                                                font.pixelSize: 11
                                                elide: Text.ElideRight
                                                Layout.fillWidth: true
                                            }
                                            Text {
                                                text: modelData.running
                                                      ? ("PID " + modelData.pid + "  /  " + (modelData.runtime_state || "starting"))
                                                      : ("Queue: " + modelData.queue_path)
                                                color: theme.faint
                                                font.pixelSize: 9
                                                elide: Text.ElideMiddle
                                                Layout.fillWidth: true
                                            }
                                        }
                                    }
                                }

                                Flow {
                                    Layout.fillWidth: true
                                    spacing: 7
                                    ActionButton {
                                        label: modelData.running ? (modelData.paused ? "Resume" : "Pause") : "Start"
                                        enabled: !root.busy
                                        onClicked: root.runAction(
                                            modelData.running
                                            ? ((modelData.paused ? "resume:" : "pause:") + modelData.id)
                                            : ("start:" + modelData.id)
                                        )
                                    }
                                    ActionButton {
                                        label: "Restart"
                                        secondary: true
                                        enabled: modelData.running && !root.busy
                                        onClicked: root.runAction("restart:" + modelData.id)
                                    }
                                    ActionButton {
                                        label: "Stop"
                                        destructive: true
                                        enabled: modelData.running && !root.busy
                                        onClicked: root.runAction("stop:" + modelData.id)
                                    }
                                    ActionButton {
                                        label: "Log"
                                        secondary: true
                                        enabled: !root.busy
                                        onClicked: root.runAction("log:" + modelData.id)
                                    }
                                    ActionButton {
                                        label: "Remove"
                                        secondary: true
                                        enabled: !modelData.running && !root.busy
                                        onClicked: root.runAction("delete:" + modelData.id)
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        visible: root.launcherState.instances.length === 0
                        Layout.fillWidth: true
                        Layout.columnSpan: 2
                        Layout.preferredHeight: 180
                        radius: 8
                        color: theme.panel
                        border.width: 1
                        border.color: theme.borderSoft
                        Text {
                            anchors.centerIn: parent
                            text: "No instances configured"
                            color: theme.muted
                            font.pixelSize: 14
                        }
                    }
                }
            }
        }
    }
}
