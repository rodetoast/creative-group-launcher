import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: root
    visible: true
    title: "Southpaw 도구 런처"
    width: 980
    height: 620
    minimumWidth: 790
    minimumHeight: 490

    property bool dark: true
    property int selected: 0
    readonly property bool contentReady: content.status === Loader.Ready
    readonly property var detail: catalog.apps[selected]
    readonly property color canvas: dark ? "#171822" : "#f4f3fa"
    readonly property color panel: dark ? "#212331" : "#ffffff"
    readonly property color ink: dark ? "#f1eefb" : "#242338"
    readonly property color muted: dark ? "#aba8c1" : "#514f66"
    readonly property color accent: dark ? "#c4b5ff" : "#5134a9"
    readonly property color selection: dark ? "#373052" : "#e9e1ff"

    color: canvas
    palette.window: panel
    palette.windowText: ink
    palette.buttonText: ink
    palette.text: ink
    palette.button: panel
    palette.highlight: selection
    palette.highlightedText: ink

    Loader {
        id: content
        anchors.fill: parent
        asynchronous: true
        sourceComponent: library
    }

    Rectangle {
        anchors.fill: parent
        visible: !root.contentReady
        color: root.canvas
        z: 1
        Column {
            anchors.centerIn: parent
            spacing: 16
            Label { text: content.status === Loader.Error ? "화면을 열 수 없습니다" : "Southpaw 도구 런처"; color: root.ink; font.pixelSize: 24 }
            BusyIndicator { running: content.status === Loader.Loading }
        }
    }

    Component {
        id: library
        RowLayout {
            spacing: 0
            Rectangle {
                Layout.preferredWidth: 248
                Layout.fillHeight: true
                color: root.panel
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 22
                    spacing: 8
                    Label { text: "SOUTHPAW"; color: root.accent; font.bold: true; font.letterSpacing: 2 }
                    Label { text: "도구 런처"; color: root.ink; font.pixelSize: 27; font.bold: true }
                    Item { Layout.preferredHeight: 16 }
                    Repeater {
                        model: catalog.apps
                        delegate: ItemDelegate {
                            required property int index
                            required property var modelData
                            Layout.fillWidth: true
                            highlighted: root.selected === index
                            text: modelData.name
                            onClicked: root.selected = index
                            background: Rectangle {
                                radius: 8
                                color: parent.highlighted || parent.hovered ? root.selection : "transparent"
                            }
                        }
                    }
                    Item { Layout.fillHeight: true }
                    Switch {
                        text: "라이트 테마"
                        checked: !root.dark
                        onToggled: root.dark = !checked
                    }
                }
            }
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.margins: 28
                spacing: 16
                RowLayout {
                    Layout.fillWidth: true
                    Label {
                        Layout.fillWidth: true
                        text: catalog.status
                        color: root.muted
                        wrapMode: Text.WordWrap
                    }
                    Button {
                        text: "업데이트 확인"
                        enabled: !catalog.busy
                        onClicked: catalog.refresh()
                    }
                }
                Label {
                    text: "런처 설치 버전 v0.1.7 · 런처 최신 버전 v0.1.7"
                    color: root.muted
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
                Rectangle {
                    color: root.panel
                    radius: 14
                    Layout.fillWidth: true
                    implicitHeight: details.implicitHeight + 52
                    ColumnLayout {
                        id: details
                        anchors.margins: 26
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 13
                        Label { text: root.detail.name; color: root.ink; font.pixelSize: 30; font.bold: true }
                        Label {
                            text: root.detail.description
                            color: root.muted
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                        }
                        Rectangle { Layout.fillWidth: true; height: 1; color: root.selection }
                        Label { text: "프로그램 설치 버전    " + (root.detail.installed || "미설치"); color: root.ink }
                        Label { text: "프로그램 최신 버전    " + root.detail.latest; color: root.accent }
                    }
                }
                Item { Layout.fillHeight: true }
            }
        }
    }
}
