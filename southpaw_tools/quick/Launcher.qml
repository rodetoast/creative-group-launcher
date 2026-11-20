import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Item {
    id: root
    objectName: "southpawQuickLauncher"
    width: 1200
    height: 780

    readonly property var dataView: launcher.view
    readonly property color canvas: launcher.dark ? "#151822" : "#f3f3f8"
    readonly property color sidebar: launcher.dark ? "#1b1e2b" : "#eae9f2"
    readonly property color card: launcher.dark ? "#202432" : "#ffffff"
    readonly property color line: launcher.dark ? "#34394b" : "#dedfea"
    readonly property color ink: launcher.dark ? "#f5f3ff" : "#222335"
    readonly property color muted: launcher.dark ? "#b7b9cb" : "#53566c"
    readonly property color accent: launcher.dark ? "#c5b6ff" : "#5034a4"
    readonly property color accentPad: launcher.dark ? "#342947" : "#e8dfff"
    readonly property color accentInk: launcher.dark ? "#201633" : "#ffffff"
    readonly property color green: launcher.dark ? "#8ed4b4" : "#126044"
    readonly property color amber: launcher.dark ? "#ffd29b" : "#80522c"
    readonly property bool compact: width < 960

    component Caption: Label {
        color: root.muted
        font.pixelSize: 13
        textFormat: Text.PlainText
    }

    component Action: Button {
        id: button
        property string command: ""
        property bool emphasis: false
        property bool destructive: false
        implicitHeight: 40
        implicitWidth: Math.max(78, contentItem.implicitWidth + 28)
        leftPadding: 12
        rightPadding: 12
        font.pixelSize: 13
        font.bold: emphasis
        hoverEnabled: true
        onClicked: if (command) launcher.act(command)
        contentItem: Label {
            text: button.text
            textFormat: Text.PlainText
            color: !button.enabled ? root.muted : button.emphasis ? root.accentInk : button.destructive ? root.amber : root.ink
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font: button.font
            opacity: button.enabled ? 1 : 0.60
        }
        background: Rectangle {
            radius: 9
            color: button.enabled && button.emphasis ? root.accent : button.hovered ? root.accentPad : root.card
            border.color: button.activeFocus ? root.accent : root.line
            border.width: button.activeFocus ? 2 : 1
            Behavior on color { ColorAnimation { duration: 95 } }
        }
    }

    component LibraryRow: ItemDelegate {
        id: item
        required property int index
        required property var modelData
        width: ListView.view ? ListView.view.width : 0
        height: 62
        highlighted: index === launcher.selectedIndex
        activeFocusOnTab: true
        hoverEnabled: true
        Accessible.name: modelData.title
        onClicked: launcher.select(index)
        background: Rectangle {
            radius: 12
            color: item.highlighted || item.hovered ? root.accentPad : "transparent"
            border.color: item.activeFocus ? root.accent : "transparent"
            Behavior on color { ColorAnimation { duration: 100 } }
        }
        contentItem: RowLayout {
            spacing: 9
            Image {
                Layout.preferredWidth: 32
                Layout.preferredHeight: 32
                sourceSize.width: 48
                sourceSize.height: 48
                source: "image://southpaw/" + item.modelData.id
                fillMode: Image.PreserveAspectFit
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                Label {
                    Layout.fillWidth: true
                    text: item.modelData.title
                    textFormat: Text.PlainText
                    elide: Text.ElideRight
                    color: root.ink
                    font.pixelSize: 13
                    font.bold: item.highlighted
                }
                Caption {
                    Layout.fillWidth: true
                    text: item.modelData.state || item.modelData.category
                    elide: Text.ElideRight
                    font.pixelSize: 11
                }
            }
        }
    }

    Rectangle { anchors.fill: parent; color: root.canvas }

    RowLayout {
        anchors.fill: parent
        spacing: 0
        Rectangle {
            Layout.preferredWidth: root.compact ? 200 : 248
            Layout.fillHeight: true
            color: root.sidebar
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: root.compact ? 12 : 18
                spacing: 14
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Image {
                        Layout.preferredWidth: 36
                        Layout.preferredHeight: 36
                        source: launcher.brandIcon
                        fillMode: Image.PreserveAspectFit
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 1
                        Caption { text: "SOUTHPAW"; color: root.accent; font.bold: true; font.letterSpacing: 2 }
                        Label { text: "도구 런처"; color: root.ink; font.pixelSize: 23; font.bold: true }
                    }
                }
                Item { Layout.preferredHeight: 5 }
                Caption { text: "라이브러리" }
                ListView {
                    id: library
                    objectName: "library"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    model: launcher.rows
                    spacing: 4
                    clip: true
                    currentIndex: launcher.selectedIndex
                    activeFocusOnTab: true
                    keyNavigationEnabled: false
                    onMovementEnded: positionViewAtIndex(currentIndex, ListView.Contain)
                    Keys.onUpPressed: launcher.select(Math.max(0, launcher.selectedIndex - 1))
                    Keys.onDownPressed: launcher.select(Math.min(count - 1, launcher.selectedIndex + 1))
                    onCurrentIndexChanged: positionViewAtIndex(currentIndex, ListView.Contain)
                    delegate: LibraryRow {}
                    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                }
                Action {
                    objectName: "settingsAction"
                    Layout.fillWidth: true
                    text: "환경 설정"
                    onClicked: settings.open()
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: root.compact ? 15 : 24
            spacing: 14

            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 5
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 7
                        Rectangle {
                            Layout.preferredWidth: 8
                            Layout.preferredHeight: 8
                            radius: 4
                            color: root.dataView.online ? root.green : root.amber
                        }
                        Caption {
                            objectName: "connectionState"
                            Layout.fillWidth: true
                            text: root.dataView.server_status.text
                            wrapMode: Text.WordWrap
                            ToolTip.visible: hoverStatus.hovered
                            ToolTip.text: root.dataView.server_status.tip
                            HoverHandler { id: hoverStatus }
                        }
                    }
                    Caption {
                        Layout.fillWidth: true
                        text: root.dataView.launcher_versions.text
                        wrapMode: Text.WordWrap
                    }
                }
                Action {
                    objectName: "refreshAction"
                    text: root.dataView.refresh_button.text
                    enabled: root.dataView.refresh_button.enabled
                    command: "refresh"
                }
                Action {
                    objectName: "updateLauncherAction"
                    text: root.dataView.launcher_update_button.text
                    visible: root.dataView.launcher_update_button.visible
                    enabled: root.dataView.launcher_update_button.enabled
                    command: "launcher"
                    emphasis: true
                }
            }

            ScrollView {
                id: body
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                contentWidth: availableWidth
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                ColumnLayout {
                    width: body.availableWidth
                    spacing: 12
                    Rectangle {
                        visible: root.dataView.hasSelection
                        Layout.fillWidth: true
                        implicitHeight: hero.implicitHeight + 32
                        color: root.card
                        border.color: root.line
                        radius: 15
                        RowLayout {
                            id: hero
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.margins: 16
                            spacing: 14
                            Rectangle {
                                Layout.preferredWidth: 59
                                Layout.preferredHeight: 59
                                radius: 13
                                color: root.accentPad
                                Image {
                                    anchors.fill: parent
                                    anchors.margins: 6
                                    source: root.dataView.selectedId ? "image://southpaw/" + root.dataView.selectedId : ""
                                    sourceSize.width: 72
                                    sourceSize.height: 72
                                    fillMode: Image.PreserveAspectFit
                                }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 5
                                Label {
                                    objectName: "appTitle"
                                    Layout.fillWidth: true
                                    text: root.dataView.title.text
                                    textFormat: Text.PlainText
                                    wrapMode: Text.WordWrap
                                    color: root.ink
                                    font.pixelSize: root.compact ? 23 : 28
                                    font.bold: true
                                }
                                Caption {
                                    Layout.fillWidth: true
                                    text: root.dataView.description.text
                                    wrapMode: Text.WordWrap
                                }
                            }
                        }
                    }
                    Rectangle {
                        visible: root.dataView.hasSelection
                        Layout.fillWidth: true
                        implicitHeight: facts.implicitHeight + 26
                        color: root.card
                        border.color: root.line
                        radius: 13
                        RowLayout {
                            id: facts
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.margins: 13
                            spacing: 12
                            Repeater {
                                model: [
                                    {label:"설치 상태", value:root.dataView["설치 상태"]},
                                    {label:"설치 버전", value:root.dataView["설치 버전"]},
                                    {label:root.dataView.latest_app_label.text, value:root.dataView["승인 버전"]},
                                    {label:"다운로드", value:root.dataView["다운로드"]}
                                ]
                                delegate: ColumnLayout {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    Layout.preferredWidth: 110
                                    spacing: 5
                                    Caption { Layout.fillWidth: true; text: modelData.label; wrapMode: Text.WordWrap }
                                    Label {
                                        Layout.fillWidth: true
                                        color: root.ink
                                        text: modelData.value || "—"
                                        textFormat: Text.PlainText
                                        wrapMode: Text.WordWrap
                                        font.pixelSize: 13
                                        font.bold: true
                                    }
                                }
                            }
                        }
                    }
                    Rectangle {
                        visible: root.dataView.hasSelection
                        Layout.fillWidth: true
                        implicitHeight: notes.implicitHeight + 30
                        color: root.card
                        border.color: root.line
                        radius: 13
                        ColumnLayout {
                            id: notes
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.margins: 15
                            spacing: 8
                            Label { text: "변경 사항"; textFormat: Text.PlainText; color: root.ink; font.pixelSize: 15; font.bold: true }
                            Caption {
                                Layout.fillWidth: true
                                text: root.dataView.notes.text
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                    Caption {
                        Layout.fillWidth: true
                        visible: !root.dataView.hasSelection
                        text: "표시할 프로그램이 없습니다. 업데이트 확인을 눌러 목록을 가져오세요."
                        wrapMode: Text.WordWrap
                    }
                }
            }

            Rectangle {
                objectName: "activityPanel"
                Layout.fillWidth: true
                visible: root.dataView.busy || root.dataView.bridgeBusy || root.dataView.message.text.length > 0
                implicitHeight: activity.implicitHeight + 20
                color: root.card
                border.color: root.line
                radius: 10
                RowLayout {
                    id: activity
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.margins: 10
                    spacing: 8
                    BusyIndicator {
                        Layout.preferredHeight: 27
                        Layout.preferredWidth: 27
                        visible: (root.dataView.busy || root.dataView.bridgeBusy) && !root.dataView.knownProgress
                        running: visible
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        Caption {
                            Layout.fillWidth: true
                            text: root.dataView.message.text
                            color: root.dataView.catalogError ? root.amber : root.ink
                            wrapMode: Text.WordWrap
                        }
                        ProgressBar {
                            objectName: "downloadProgress"
                            Layout.fillWidth: true
                            visible: root.dataView.busy || root.dataView.bridgeBusy
                            indeterminate: !root.dataView.progress.visible || !root.dataView.knownProgress
                            from: 0; to: 100
                            value: root.dataView.progress.value
                        }
                    }
                    Action {
                        objectName: "cancelAction"
                        text: "취소"
                        command: "cancel"
                        visible: root.dataView.cancel_button.visible
                        enabled: root.dataView.cancel_button.enabled
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                visible: root.dataView.hasSelection
                spacing: 8
                Action {
                    objectName: "managementAction"
                    text: "프로그램 관리"
                    enabled: !root.dataView.busy
                    onClicked: management.open()
                }
                Item { Layout.fillWidth: true }
                Action {
                    text: "현재 버전 실행"
                    command: "launch"
                    visible: root.dataView.launch_current.visible
                    enabled: root.dataView.launch_current.enabled
                }
                Action {
                    objectName: "primaryAction"
                    text: root.dataView.primary.text
                    enabled: root.dataView.primary.enabled
                    command: "primary"
                    emphasis: true
                }
            }
        }
    }

    component Panel: Dialog {
        parent: root
        anchors.centerIn: parent
        width: Math.min(480, root.width - 48)
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape
        palette.window: root.card
        palette.windowText: root.ink
        palette.text: root.ink
        palette.buttonText: root.ink
        palette.base: root.sidebar
        palette.button: root.card
        background: Rectangle { color: root.card; radius: 15; border.color: root.line }
    }

    Panel {
        id: settings
        objectName: "settingsDialog"
        title: "환경 설정"
        contentItem: ColumnLayout {
            spacing: 10
            Switch {
                objectName: "themeSwitch"
                text: "라이트 테마"
                checked: !launcher.dark
                onToggled: launcher.setDark(!checked)
            }
            Caption {
                Layout.fillWidth: true
                text: root.dataView.connectedRepo || "배포 저장소 미지정"
                wrapMode: Text.WordWrap
            }
            Action {
                text: "연결 설정"
                visible: root.dataView.connection_button.visible
                enabled: root.dataView.connection_button.enabled
                onClicked: { settings.close(); launcher.act("configure") }
            }
            Action { text: "닫기"; onClicked: settings.close() }
        }
    }

    Panel {
        id: management
        objectName: "managementDialog"
        title: "프로그램 관리"
        contentItem: ColumnLayout {
            spacing: 8
            Action {
                Layout.fillWidth: true
                text: "설치 위치 열기"
                enabled: root.dataView.folder_button.enabled
                onClicked: { management.close(); launcher.act("folder") }
            }
            Action {
                Layout.fillWidth: true
                text: "설치된 버전 선택"
                enabled: root.dataView.versions_button.enabled
                onClicked: { management.close(); launcher.act("versions") }
            }
            Action {
                Layout.fillWidth: true
                text: "상세 정보"
                onClicked: { management.close(); launcher.act("details") }
            }
            Action {
                objectName: "removeAction"
                Layout.fillWidth: true
                text: "제거"
                destructive: true
                enabled: root.dataView.remove_button.enabled
                onClicked: { management.close(); launcher.act("remove") }
            }
        }
    }

    Panel {
        id: approval
        objectName: "approvalDialog"
        title: launcher.prompt.title || ""
        onClosed: if (launcher.prompt.title) launcher.reply(false, -1)
        contentItem: ColumnLayout {
            spacing: 10
            ScrollView {
                Layout.fillWidth: true
                Layout.preferredHeight: launcher.prompt.information ? 270 : Math.min(185, Math.max(60, dialogText.contentHeight + 6))
                contentWidth: availableWidth
                TextArea {
                    id: dialogText
                    text: launcher.prompt.text || ""
                    textFormat: TextEdit.PlainText
                    readOnly: true
                    selectByMouse: true
                    wrapMode: TextEdit.Wrap
                    color: root.ink
                    font.pixelSize: 13
                    background: null
                }
            }
            ComboBox {
                id: choices
                objectName: "versionChoices"
                Layout.fillWidth: true
                model: launcher.prompt.choices || []
                visible: count > 0
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                Action {
                    text: launcher.prompt.information ? "닫기" : "취소"
                    onClicked: { launcher.reply(false, -1); approval.close() }
                }
                Action {
                    objectName: "confirmAction"
                    text: "확인"
                    emphasis: true
                    visible: !launcher.prompt.information
                    onClicked: { launcher.reply(true, choices.currentIndex); approval.close() }
                }
            }
        }
    }

    Connections {
        target: launcher
        function onPromptChanged() {
            if (launcher.prompt.title) approval.open()
            else approval.close()
        }
    }
}
